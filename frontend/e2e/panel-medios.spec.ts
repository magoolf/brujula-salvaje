/**
 * E2E del panel de medios (TKT-022): SCR-039 Biblioteca, SCR-040 Detalle, FLOW-013 y la carga del
 * armazón del panel (OBS-C3-01), contra el stack real de Compose (backend, BD y proxy reales).
 * Requiere E2E_BASE_URL y E2E_COMPOSE_PROJECT (ver panel-soporte.ts).
 */
import AxeBuilder from '@axe-core/playwright';
import { Page, expect, test } from '@playwright/test';

import {
  archivoGrande,
  catalogarPorApi,
  crearLicencia,
  gif,
  medioEnUsoPublicado,
  obtenerPorApi,
  pngSoloCabecera,
  pngValido,
  subirPorApi,
} from './medios-soporte';
import { crearCuenta, entrarPorApi, irA, omitirSinStack } from './panel-soporte';

test.beforeEach(() => omitirSinStack());

async function entrarComoEditor(page: Page): Promise<void> {
  await entrarPorApi(page, crearCuenta());
}

async function axeSinGraves(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page }).analyze();
  const graves = resultado.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)).toEqual([]);
}

test.describe('Panel · medios (TKT-022)', () => {
  test('AC_TKT022_01 subida feliz: progreso, resultado, «Completar datos» y catalogación → DISPONIBLE', async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await entrarComoEditor(page);
    await irA(page, '/panel/medios');
    await expect(page.getByRole('heading', { level: 1, name: 'Medios' })).toBeVisible();
    await expect(page.getByTestId('panel-nav-medios')).toHaveAttribute('aria-current', 'page');

    await page.getByTestId('medios-subir').click();
    await expect(page.getByTestId('subida-reglas')).toHaveText(
      'JPEG, PNG o WebP · hasta 10 MB · mínimo 1.200 px en el lado mayor · hasta 10 a la vez',
    );
    const subida = page.waitForResponse((r) => r.url().endsWith('/api/v1/panel/medios') && r.request().method() === 'POST');
    await page.getByTestId('subida-archivos').setInputFiles([pngValido('amanecer-e2e.png')]);
    await expect(page.getByTestId('subida-progreso')).toBeVisible();
    const respuesta = await subida;
    expect(respuesta.status()).toBe(200);
    expect(respuesta.request().headers()['idempotency-key']).toMatch(/^[0-9a-f-]{36}$/);
    await expect(page.getByTestId('subida-resumen')).toHaveText('1 aceptada');
    await expect(page.getByTestId('subida-anuncio')).toHaveText('1 aceptada');
    const fila = page.getByTestId('subida-resultado-0');
    await expect(fila).toHaveAttribute('data-resultado', 'ACEPTADO');
    await expect(fila).toContainText('amanecer-e2e.png');

    await fila.getByTestId('subida-completar').click();
    await expect(page).toHaveURL(/\/panel\/medios\/\d+$/);
    await expect(page.getByTestId('medio-estado')).toHaveText(/Pendiente de datos/);
    await expect(page.getByTestId('medio-pendientes')).toContainText('Falta el texto alternativo');

    await page.getByTestId('medio-campo-alt').fill('Lago de montaña al amanecer');
    await page.getByTestId('medio-campo-credito').fill('Equipo E2E');
    await page.getByTestId('medio-campo-licencia').selectOption({ index: 1 });
    await page.getByTestId('medio-campo-fuente').fill('https://ejemplo.org/foto');
    await page.getByTestId('medio-guardar').click();
    await expect(page.getByTestId('medio-exito')).toHaveText(/Imagen disponible/);
    await expect(page.getByTestId('medio-estado')).toHaveText(/Disponible/);
    await expect(page.getByTestId('medio-pendiente')).toHaveCount(0);
  });

  test('AC_TKT022_01 cada error de FLOW-013 por archivo (cliente y servidor) y duplicado → «Usar la existente»', async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await entrarComoEditor(page);
    const repetido = pngValido('repetida-e2e.png');
    const existente = await subirPorApi(page, repetido);

    await irA(page, '/panel/medios');
    await page.getByTestId('medios-subir').click();
    const envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/panel/medios') && r.request().method() === 'POST');
    await page.getByTestId('subida-archivos').setInputFiles([
      gif('animada.gif'),
      archivoGrande('enorme.jpg'),
      gif('disfrazada.png', 'image/png'),
      pngSoloCabecera('pequena.png', 400, 300),
      pngSoloCabecera('gigante.png', 8000, 5001),
      pngSoloCabecera('rota.png', 1600, 1000),
      { ...repetido, name: 'otra-vez.png' },
    ]);
    const respuesta = await envio;
    // La validación previa no envía los dos primeros (formato y tamaño).
    const enviados = ((await respuesta.json()) as { resultados: { nombre_archivo: string }[] }).resultados;
    expect(enviados.map((r) => r.nombre_archivo).sort()).toEqual(
      ['disfrazada.png', 'gigante.png', 'otra-vez.png', 'pequena.png', 'rota.png'].sort(),
    );

    await expect(page.getByTestId('subida-resumen')).toHaveText('0 aceptadas, 6 rechazadas, 1 duplicada');
    const porNombre = (nombre: string) => page.getByTestId('subida-resultados').locator('li', { hasText: nombre });
    await expect(porNombre('animada.gif')).toHaveAttribute('data-motivo', 'formato_no_permitido');
    await expect(porNombre('enorme.jpg')).toHaveAttribute('data-motivo', 'tamano_excedido');
    await expect(porNombre('enorme.jpg')).toContainText('Supera los 10 MB.');
    await expect(porNombre('disfrazada.png')).toHaveAttribute('data-motivo', 'formato_no_permitido');
    await expect(porNombre('pequena.png')).toHaveAttribute('data-motivo', 'dimensiones_insuficientes');
    await expect(porNombre('gigante.png')).toHaveAttribute('data-motivo', 'megapixeles_excedidos');
    await expect(porNombre('rota.png')).toHaveAttribute('data-motivo', 'archivo_corrupto');
    const duplicada = porNombre('otra-vez.png');
    await expect(duplicada).toHaveAttribute('data-resultado', 'DUPLICADO');
    await expect(duplicada).toContainText('Esta imagen ya está en la biblioteca.');
    await duplicada.getByTestId('subida-usar-existente').click();
    await expect(page).toHaveURL(new RegExp(`/panel/medios/${existente.id}$`));
    await expect(page.getByTestId('pagina-medio')).toBeVisible();
  });

  test('AC_TKT022_01 más de 10 archivos: se rechaza la selección completa sin subir ninguno', async ({ page }) => {
    await entrarComoEditor(page);
    await irA(page, '/panel/medios');
    await page.getByTestId('medios-subir').click();
    let envios = 0;
    page.on('request', (r) => {
      if (r.url().endsWith('/api/v1/panel/medios') && r.method() === 'POST') envios++;
    });
    const archivos = Array.from({ length: 11 }, (_, i) => pngSoloCabecera(`lote-${i}.png`, 1600, 1000));
    await page.getByTestId('subida-archivos').setInputFiles(archivos);
    await expect(page.getByTestId('subida-error-seleccion')).toContainText('hasta 10 imágenes a la vez');
    await expect(page.getByTestId('subida-resultados')).toHaveCount(0);
    expect(envios).toBe(0);
  });

  test('AC_TKT022_02 filtros, búsqueda y paginación sincronizados con la URL (atrás, recarga, fuera de rango)', async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await entrarComoEditor(page);
    const pendiente = await subirPorApi(page, pngValido('filtro-e2e.png'));
    const marca = `filtro${pendiente.id}`;
    await catalogarPorApi(page, pendiente.id, { titulo_interno: `Prueba ${marca}` });

    await irA(page, '/panel/medios');
    const total = Number((await page.getByTestId('medios-recuento').textContent())?.match(/\d+/)?.[0]);
    expect(total).toBeGreaterThan(48);
    await expect(page.getByTestId('medios-rejilla').locator('li')).toHaveCount(48);
    await page.getByTestId('paginacion').getByRole('link', { name: 'Página 2' }).click();
    await expect(page).toHaveURL(/\/panel\/medios\?pagina=2$/);
    await expect(page.getByTestId('paginacion').locator('[aria-current="page"]')).toHaveText('2');

    // Filtros: se aplican al enviar, vuelven a la página 1 y quedan en la URL.
    await page.getByTestId('medios-estado').selectOption('PENDIENTE_METADATOS');
    await page.getByTestId('medios-q').fill(marca);
    await page.getByTestId('medios-aplicar').click();
    await expect(page).toHaveURL(new RegExp(`\\?estado=PENDIENTE_METADATOS&q=${marca}$`));
    await expect(page.getByTestId('medios-recuento')).toHaveText('1 imagen');
    await expect(page.getByTestId(`medio-mosaico-${pendiente.id}`)).toContainText('Pendiente de datos');

    // Atrás: vuelve la página 2 sin filtros y el formulario sigue a la URL.
    await page.goBack();
    await expect(page).toHaveURL(/\/panel\/medios\?pagina=2$/);
    await expect(page.getByTestId('medios-estado')).toHaveValue('');
    await expect(page.getByTestId('medios-q')).toHaveValue('');
    await page.goForward();
    await expect(page.getByTestId('medios-q')).toHaveValue(marca);

    // Recarga completa con filtros en la URL (compartible).
    await irA(page, `/panel/medios?estado=PENDIENTE_METADATOS&en_uso=false&q=${marca}`);
    await expect(page.getByTestId('medios-en-uso')).toHaveValue('false');
    await expect(page.getByTestId('medios-estado')).toHaveValue('PENDIENTE_METADATOS');
    await expect(page.getByTestId('medios-recuento')).toHaveText('1 imagen');

    // Sin coincidencias y «Quitar filtros».
    await irA(page, '/panel/medios?q=sin-coincidencias-e2e-zz');
    await expect(page.getByTestId('medios-sin-coincidencias')).toBeVisible();
    await page.getByTestId('medios-sin-limpiar').click();
    await expect(page).toHaveURL(/\/panel\/medios$/);
    await expect(page.getByTestId('medios-rejilla')).toBeVisible();

    // Página fuera de rango (404 pagina_fuera_de_rango) y valores inválidos en la URL.
    await irA(page, '/panel/medios?pagina=9999');
    await expect(page.getByTestId('medios-pagina-fuera')).toBeVisible();
    await page.getByTestId('medios-pagina-fuera').getByRole('link', { name: 'Ir a la primera página' }).click();
    await expect(page).toHaveURL(/\/panel\/medios$/);
    await irA(page, '/panel/medios?estado=NO_VALE&en_uso=quiza');
    await expect(page.getByTestId('medios-rejilla')).toBeVisible();
  });

  test('AC_TKT022_03 detalle: validación previa, 400 por campo, 422 de regla de negocio y retiro bloqueado en uso', async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await entrarPorApi(page, crearCuenta({ rol: 'ADMINISTRADOR', conMfa: true }));
    const incompatible = await crearLicencia(page, false);
    const enUso = await medioEnUsoPublicado(page);
    const nuevo = await subirPorApi(page, pngValido('detalle-e2e.png'));

    // Validación previa en el cliente: URL de la fuente (RULE-021).
    await irA(page, `/panel/medios/${nuevo.id}`);
    await expect(page.getByTestId('medio-ficha')).toContainText('1600 × 1000 px');
    await expect(page.getByTestId('medio-sin-usos')).toBeVisible();
    await page.getByTestId('medio-campo-fuente').fill('ftp://ejemplo.org/foto');
    await page.getByTestId('medio-guardar').click();
    await expect(page.getByTestId('medio-campo-fuente-error')).toContainText('http:// o https://');
    await expect(page.getByTestId('medio-campo-fuente')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByTestId('medio-campo-fuente')).toBeFocused();
    // Al editar el campo desaparece su error.
    await page.getByTestId('medio-campo-fuente').fill('');
    await expect(page.getByTestId('medio-campo-fuente-error')).toHaveCount(0);

    // 400 real de la API con `errors` por campo (se altera el cuerpo enviado para forzarlo).
    const rutaPut = `**/api/v1/panel/medios/${nuevo.id}`;
    await page.route(rutaPut, async (ruta) => {
      if (ruta.request().method() !== 'PUT') return ruta.continue();
      await ruta.continue({ postData: JSON.stringify({ texto_alternativo: 'x'.repeat(300) }) });
    });
    const respuesta400 = page.waitForResponse((r) => r.request().method() === 'PUT');
    await page.getByTestId('medio-campo-alt').fill('Texto válido');
    await page.getByTestId('medio-guardar').click();
    expect((await respuesta400).status()).toBe(400);
    await expect(page.getByTestId('medio-campo-alt-error')).toBeVisible();
    await expect(page.getByTestId('medio-campo-alt')).toBeFocused();
    await page.unroute(rutaPut);

    // 422 regla_negocio: licencia incompatible en un medio usado por contenido publicado.
    await irA(page, `/panel/medios/${enUso.id}`);
    await expect(page.getByTestId('medio-uso').first()).toBeVisible();
    await expect(page.getByTestId('medio-retiro-bloqueado')).toBeVisible();
    await expect(page.getByTestId('medio-retirar')).toHaveAttribute('aria-disabled', 'true');
    await page.getByTestId('medio-retirar').click({ force: true });
    await expect(page.getByTestId('medio-dialogo-retiro')).toBeHidden();
    await page.getByTestId('medio-campo-licencia').selectOption(String(incompatible.id));
    const respuesta422 = page.waitForResponse((r) => r.request().method() === 'PUT');
    await page.getByTestId('medio-guardar').click();
    expect((await respuesta422).status()).toBe(422);
    await expect(page.getByTestId('medio-campo-licencia-error')).toContainText('Licencia incompatible');
    await expect(page.getByTestId('medio-campo-licencia')).toHaveAttribute('aria-invalid', 'true');
    expect((await obtenerPorApi(page, enUso.id)).licencia?.id).toBe(enUso.licencia?.id);

    // DISPONIBLE: vaciar un dato obligatorio se impide antes de enviar (RULE-005).
    await irA(page, `/panel/medios/${enUso.id}`);
    await page.getByTestId('medio-campo-credito').fill('');
    let puts = 0;
    page.on('request', (r) => {
      if (r.method() === 'PUT') puts++;
    });
    await page.getByTestId('medio-guardar').click();
    await expect(page.getByTestId('medio-campo-credito-error')).toContainText('Obligatorio');
    expect(puts).toBe(0);
  });

  test('AC_TKT022_03 retirar y reactivar con confirmación accesible', async ({ page }) => {
    test.setTimeout(90_000);
    await entrarComoEditor(page);
    const medio = await subirPorApi(page, pngValido('retiro-e2e.png'));
    await irA(page, `/panel/medios/${medio.id}`);
    const retirar = page.getByTestId('medio-retirar');
    await retirar.click();
    const dialogo = page.getByTestId('medio-dialogo-retiro');
    await expect(dialogo).toBeVisible();
    await expect(page.getByTestId('medio-dialogo-retiro-cancelar')).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(dialogo).toBeHidden();
    await expect(retirar).toBeFocused();

    await retirar.click();
    await page.getByTestId('medio-dialogo-retiro-confirmar').click();
    await expect(dialogo).toBeHidden();
    await expect(page.getByTestId('medio-estado')).toHaveText(/Retirado/);
    await expect(page.getByTestId('medio-retirado')).toBeVisible();
    await expect(page.getByTestId('medio-formulario')).toHaveCount(0);
    expect((await obtenerPorApi(page, medio.id)).estado).toBe('RETIRADO');

    await page.getByTestId('medio-reactivar').click();
    await page.getByTestId('medio-dialogo-reactivar-confirmar').click();
    await expect(page.getByTestId('medio-estado')).toHaveText(/Pendiente de datos/);
    expect((await obtenerPorApi(page, medio.id)).estado).toBe('PENDIENTE_METADATOS');

    await irA(page, '/panel/medios/999999999');
    await expect(page.getByTestId('panel-no-encontrada')).toBeVisible();
    await irA(page, '/panel/medios/no-es-un-id');
    await expect(page.getByTestId('panel-no-encontrada')).toBeVisible();
  });

  for (const ancho of [320, 1280]) {
    test(`AC_TKT022_05 axe sin violaciones serious/critical en SCR-039 y SCR-040 a ${ancho} px`, async ({ page }) => {
      test.setTimeout(90_000);
      await page.setViewportSize({ width: ancho, height: 900 });
      await entrarComoEditor(page);
      const medio = await subirPorApi(page, pngValido(`axe-${ancho}.png`));
      await irA(page, '/panel/medios');
      await expect(page.getByTestId('medios-rejilla')).toBeVisible();
      await axeSinGraves(page);
      await page.getByTestId('medios-subir').click();
      await page.getByTestId('subida-archivos').setInputFiles([gif('axe.gif'), pngValido(`axe-subida-${ancho}.png`)]);
      await expect(page.getByTestId('subida-resultados')).toBeVisible();
      await axeSinGraves(page);
      await irA(page, '/panel/medios?q=sin-coincidencias-e2e-zz');
      await expect(page.getByTestId('medios-sin-coincidencias')).toBeVisible();
      await axeSinGraves(page);
      await irA(page, `/panel/medios/${medio.id}`);
      await expect(page.getByTestId('medio-formulario')).toBeVisible();
      await page.getByTestId('medio-campo-fuente').fill('no-es-url');
      await page.getByTestId('medio-guardar').click();
      await expect(page.getByTestId('medio-campo-fuente-error')).toBeVisible();
      await axeSinGraves(page);
      await page.getByTestId('medio-retirar').click();
      await expect(page.getByTestId('medio-dialogo-retiro')).toBeVisible();
      await axeSinGraves(page);
    });
  }

  test('AC_TKT022_07 carga completa de /panel/**: armazón con <main> mientras se resuelve la sesión', async ({
    page,
    browser,
  }) => {
    test.setTimeout(60_000);
    await entrarComoEditor(page);
    let sesionResuelta = false;
    await page.route('**/api/v1/panel/auth/sesion', async (ruta) => {
      await new Promise((r) => setTimeout(r, 1500));
      await ruta.continue();
      sesionResuelta = true;
    });
    await page.goto('/panel/medios?estado=DISPONIBLE');
    const carga = page.locator('main[data-testid="panel-cargando"]');
    await expect(carga).toBeVisible();
    await expect(carga.getByRole('status')).toHaveText('Cargando el panel…');
    expect(sesionResuelta).toBe(false);
    await expect(page.getByTestId('pagina-medios')).toBeVisible();
    await expect(page).toHaveURL(/\/panel\/medios\?estado=DISPONIBLE$/);
    await expect(page).toHaveTitle(/^Medios/);
    await expect(page.locator('main')).toHaveCount(1);
    // Para la persona es la carga inicial: el foco sigue en el documento (el primer Tab llega a los
    // saltos de accesibilidad), no en el h1 al que lo llevaría una navegación interna.
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);
    // La carga no añade una entrada al historial.
    expect(await page.evaluate(() => history.length)).toBe(2);

    // Sin sesión (contexto nuevo): tras la carga, SCR-030 con un `siguiente` seguro.
    const contexto = await browser.newContext();
    const anonima = await contexto.newPage();
    await anonima.route('**/api/v1/panel/auth/sesion', async (ruta) => {
      await new Promise((r) => setTimeout(r, 1500));
      await ruta.continue();
    });
    await anonima.goto('/panel/medios/5');
    await expect(anonima.locator('main[data-testid="panel-cargando"]')).toBeVisible();
    await expect(anonima).toHaveURL(/\/panel\/acceso\?siguiente=%2Fpanel%2Fmedios%2F5$/);
    await expect(anonima.getByTestId('acceso-usuario')).toBeVisible();
    await contexto.close();
  });
});
