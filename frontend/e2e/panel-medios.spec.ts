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
});
