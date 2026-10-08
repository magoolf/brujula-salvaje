/**
 * E2E de contenidos del panel (TKT-023): SCR-035 Listado, SCR-036 Editor, SCR-037 Vista previa y
 * SCR-038 Publicar / Retirar / Reactivar / Eliminar, contra el stack real de Compose (backend, BD,
 * proxy y SSR reales). FLOW-011 y FLOW-012 de extremo a extremo con axe en cada pantalla.
 * Requiere E2E_BASE_URL y E2E_COMPOSE_PROJECT (ver panel-soporte.ts).
 */
import { Page, expect, test } from '@playwright/test';

import {
  crearBorrador,
  crearGuiaPublicable,
  editarComoOtro,
  obtenerContenido,
  publicarPorApi,
  sufijo,
} from './panel-contenidos-soporte';
import { crearCuenta, entrarPorApi, irA, omitirSinStack } from './panel-soporte';
import { sinViolacionesGraves } from './utilidades';

test.beforeEach(() => omitirSinStack());

async function entrarComoEditor(page: Page): Promise<void> {
  await entrarPorApi(page, crearCuenta());
}

test.describe('Panel · contenidos (TKT-023)', () => {
  test('AC_TKT023_01 / AC_TKT023_17 listado de destinos: navegación, tabla, filtros en la URL y axe', async ({ page }) => {
    await entrarComoEditor(page);
    await irA(page, '/panel');
    await page.getByTestId('panel-nav-contenido-destinos').click();
    await expect(page).toHaveURL(/\/panel\/contenido\/destinos$/);
    await expect(page.getByRole('heading', { level: 1, name: 'Destinos' })).toBeVisible();
    await expect(page.getByTestId('panel-nav-contenido-destinos')).toHaveAttribute('aria-current', 'page');
    await expect(page.getByTestId('contenidos-tabla')).toBeVisible();
    await expect(page.getByTestId('contenidos-recuento')).toContainText('destinos');
    await expect(page.getByTestId('contenidos-fila').first()).toBeVisible();
    await sinViolacionesGraves(page);

    await page.getByTestId('contenidos-estado').selectOption('PUBLICADO');
    await page.getByTestId('contenidos-aplicar').click();
    await expect(page).toHaveURL(/estado=PUBLICADO/);
    const verSitio = page.getByTestId('contenidos-ver-sitio').first();
    await expect(verSitio).toHaveAttribute('target', '_blank');
    await expect(verSitio).toHaveAttribute('href', /^\/destinos\/[a-z0-9-]+$/);

    await page.getByTestId('contenidos-q').fill('zzz-no-existe-zzz');
    await page.getByTestId('contenidos-aplicar').click();
    await expect(page.getByTestId('contenidos-sin-coincidencias')).toBeVisible();
    await page.getByTestId('contenidos-sin-limpiar').click();
    await expect(page).toHaveURL(/\/panel\/contenido\/destinos$/);
  });

  test('AC_TKT023_02 / AC_TKT023_04 / AC_TKT023_06 alta de destino: validación, slug propuesto, vista previa sin persistir y guardado', async ({ page }) => {
    await entrarComoEditor(page);
    await irA(page, '/panel/contenido/destinos');
    await page.getByTestId('contenidos-nuevo').click();
    await expect(page.getByRole('heading', { level: 1, name: 'Nuevo destino' })).toBeVisible();
    await expect(page.getByTestId('editor-estado')).toHaveText('Nuevo');

    // Guardar sin título: ErrorSummary con el foco y enlace al campo.
    await page.getByTestId('editor-guardar').click();
    const resumen = page.getByTestId('editor-resumen-errores');
    await expect(resumen).toBeFocused();
    await expect(resumen).toContainText('Corrige 1 problema');
    await page.getByTestId('editor-resumen-enlace').click();
    await expect(page.getByTestId('campo-titulo')).toBeFocused();

    const titulo = `Volcán E2E ${sufijo()}`;
    await page.getByTestId('campo-titulo').fill(titulo);
    await expect(page.getByTestId('campo-slug')).toHaveValue(titulo.toLowerCase().replace(/ /g, '-'));
    await page.getByTestId('campo-resumen').fill('Un volcán activo con lagunas de altura.');
    await expect(page.getByTestId('editor-guardado')).toContainText('Cambios sin guardar');
    await sinViolacionesGraves(page);

    // Vista previa del formulario en memoria (DEC-AUTO-120): nada se crea.
    const creaciones: string[] = [];
    page.on('request', (r) => {
      if (r.method() === 'POST' && r.url().endsWith('/api/v1/panel/contenidos/destinos')) creaciones.push(r.url());
    });
    await page.getByTestId('editor-vista-previa').click();
    await expect(page).toHaveURL(/\/panel\/contenido\/destinos\/nuevo\/vista-previa$/);
    await expect(page.getByTestId('vista-previa-marca')).toHaveText('VISTA PREVIA – NO PUBLICADO');
    await expect(page.getByTestId('vista-previa-titulo')).toHaveText(titulo);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
    await expect(page).toHaveTitle(new RegExp(`Vista previa \\(no publicado\\) — ${titulo}`));
    await expect(page.getByRole('region', { name: 'Vista previa' })).toBeVisible();
    await sinViolacionesGraves(page);
    await page.getByTestId('vista-previa-volver').click();
    await expect(page.getByTestId('campo-titulo')).toHaveValue(titulo);
    await expect(page.getByTestId('editor-aviso')).toContainText('Recuperamos los cambios');
    expect(creaciones).toEqual([]);

    // Guardar borrador: se crea y la URL pasa a /{id}.
    await page.getByTestId('editor-guardar').click();
    await expect(page).toHaveURL(/\/panel\/contenido\/destinos\/\d+$/);
    await expect(page.getByTestId('editor-estado')).toHaveText('Borrador');
    await expect(page.getByTestId('editor-aviso')).toContainText('Borrador guardado');
    await expect(page.getByTestId('campo-titulo')).toHaveValue(titulo);
    await expect(page.getByTestId('editor-accion-principal')).toHaveText('Publicar');
  });

  test('AC_TKT023_07 / AC_TKT023_12 publicar una guía: análisis, confirmación, «Ver en el sitio» e historial', async ({ page }) => {
    test.setTimeout(120_000);
    await entrarComoEditor(page);
    const guia = await crearGuiaPublicable(page);
    await irA(page, `/panel/contenido/guias/${guia.id}`);
    await expect(page.getByTestId('editor-accion-principal')).toHaveText('Publicar');
    await page.getByTestId('editor-accion-principal').click();
    const dialogo = page.getByTestId('dialogo-publicacion');
    await expect(dialogo).toBeVisible();
    await expect(page.getByTestId('publicacion-resumen')).toContainText(`/guias/${guia.slug}`);
    await expect(page.getByTestId('publicacion-aviso-slug')).toBeVisible();
    await sinViolacionesGraves(page);
    const publicar = page.waitForResponse((r) => r.url().endsWith(`/contenidos/guias/${guia.id}/publicar`));
    await page.getByTestId('publicacion-confirmar').click();
    const respuesta = await publicar;
    expect(respuesta.status()).toBe(200);
    expect(respuesta.request().headers()['idempotency-key']).toMatch(/^[0-9a-f-]{36}$/);
    await expect(dialogo).toBeHidden();
    await expect(page.getByTestId('editor-exito')).toContainText('está publicado');
    await expect(page.getByTestId('editor-ver-sitio-exito')).toHaveAttribute('href', `/guias/${guia.slug}`);
    await expect(page.getByTestId('editor-estado')).toHaveText('Publicado');
    await expect(page.getByTestId('campo-slug')).toHaveAttribute('readonly', '');
    await expect(page.getByTestId('editor-accion-principal')).toHaveText('Actualizar publicación');
    await expect(page.getByTestId('editor-historial')).toContainText('Revisión 1');

    // AC-121: restaurar en el formulario no cambia nada público.
    await page.getByTestId('campo-resumen').fill('Resumen modificado y sin guardar.');
    await page.getByTestId('editor-restaurar-1').click();
    await page.getByTestId('editor-confirmacion-confirmar').click();
    await expect(page.getByTestId('campo-resumen')).toHaveValue('Resumen de una guía creada por las pruebas de extremo a extremo.');
    await expect(page.getByTestId('editor-aviso')).toContainText('revisión 1');
    const publica = await page.request.get(`/api/v1/publico/guias/${guia.slug}`);
    expect(publica.status()).toBe(200);
  });

  test('AC_TKT023_07 publicar un borrador incompleto: lista de errores enlazada y sigue en BORRADOR', async ({ page }) => {
    await entrarComoEditor(page);
    const guia = await crearBorrador(page, 'guias', `Guía incompleta ${sufijo()}`);
    await irA(page, `/panel/contenido/guias/${guia.id}`);
    await page.getByTestId('editor-accion-principal').click();
    const errores = page.getByTestId('publicacion-errores');
    await expect(errores).toContainText('No se puede publicar todavía');
    await expect(page.getByTestId('publicacion-confirmar')).toHaveCount(0);
    await sinViolacionesGraves(page);
    await page.getByTestId('publicacion-error-campo').filter({ hasText: 'Resumen' }).click();
    await expect(page.getByTestId('dialogo-publicacion')).toBeHidden();
    await expect(page.getByTestId('campo-resumen')).toBeFocused();
    expect((await obtenerContenido(page, 'guias', guia.id)).estado_editorial).toBe('BORRADOR');
  });

  test('AC_TKT023_10 / AC_TKT023_11 retirar con motivo (impacto) y reactivar como borrador', async ({ page }) => {
    test.setTimeout(120_000);
    await entrarComoEditor(page);
    const guia = await crearGuiaPublicable(page);
    await publicarPorApi(page, 'guias', guia);
    await irA(page, `/panel/contenido/guias/${guia.id}`);
    await expect(page.getByTestId('editor-estado')).toHaveText('Publicado');
    await expect(page.getByTestId('editor-ver-sitio')).toHaveAttribute('href', `/guias/${guia.slug}`);
    await page.getByTestId('editor-mas-acciones').click();
    await page.getByTestId('editor-retirar').click();
    await expect(page.getByTestId('retiro-impacto')).toBeVisible();
    await expect(page.getByTestId('retiro-motivo')).toBeFocused();
    await expect(page.getByTestId('retiro-confirmar')).toBeDisabled();
    await sinViolacionesGraves(page);
    await page.getByTestId('retiro-motivo').fill('Contenido desactualizado (E2E)');
    const retiro = page.waitForResponse((r) => r.url().endsWith(`/contenidos/guias/${guia.id}/retirar`));
    await page.getByTestId('retiro-confirmar').click();
    expect((await retiro).status()).toBe(200);
    await expect(page.getByTestId('editor-exito')).toContainText('se retiró');
    await expect(page.getByTestId('editor-estado')).toHaveText('Retirado');
    await expect(page.getByTestId('editor-retirado')).toContainText('Contenido desactualizado (E2E)');
    await expect(page.getByTestId('campo-titulo')).toBeDisabled();
    const publica = await page.request.get(`/api/v1/publico/guias/${guia.slug}`);
    expect(publica.status()).toBe(410);

    await page.getByTestId('editor-accion-principal').click();
    await page.getByTestId('editor-confirmacion-confirmar').click();
    await expect(page.getByTestId('editor-estado')).toHaveText('Borrador');
    await expect(page.getByTestId('editor-aviso')).toContainText('Reactivaste');
    await expect(page.getByTestId('campo-slug')).toHaveValue(guia.slug ?? '');
  });

  test('AC_TKT023_05 conflicto de versión: aviso sin sobrescribir y «Recargar»', async ({ page }) => {
    await entrarComoEditor(page);
    const tipo = await crearBorrador(page, 'colecciones', `Colección E2E ${sufijo()}`);
    await irA(page, `/panel/contenido/colecciones/${tipo.id}`);
    await expect(page.getByTestId('campo-titulo')).toHaveValue(tipo.titulo);
    await editarComoOtro(page, 'colecciones', tipo.id, { resumen: 'Cambio de otra persona' });
    await page.getByTestId('campo-resumen').fill('Mi cambio');
    await page.getByTestId('editor-guardar').click();
    await expect(page.getByTestId('editor-conflicto')).toContainText('Otra persona guardó cambios');
    await expect(page.getByTestId('campo-resumen')).toHaveValue('Mi cambio');
    expect((await obtenerContenido(page, 'colecciones', tipo.id))['resumen']).toBe('Cambio de otra persona');
    await sinViolacionesGraves(page);
    await page.getByTestId('editor-recargar').click();
    await page.getByTestId('editor-confirmacion-confirmar').click();
    await expect(page.getByTestId('editor-conflicto')).toHaveCount(0);
    await expect(page.getByTestId('campo-resumen')).toHaveValue('Cambio de otra persona');
  });

  test('AC_TKT023_11 / AC_TKT023_13 cambios sin guardar al salir y eliminar un borrador nunca publicado', async ({ page }) => {
    await entrarComoEditor(page);
    const borrador = await crearBorrador(page, 'itinerarios', `Itinerario E2E ${sufijo()}`);
    await irA(page, `/panel/contenido/itinerarios/${borrador.id}`);
    await page.getByTestId('campo-resumen').fill('Sin guardar');
    await page.getByTestId('panel-nav-medios').click();
    const confirmacion = page.getByTestId('editor-confirmacion');
    await expect(confirmacion).toContainText('Si sales ahora, se perderán.');
    await expect(page.getByTestId('editor-confirmacion-cancelar')).toBeFocused();
    await page.getByTestId('editor-confirmacion-cancelar').click();
    await expect(page).toHaveURL(new RegExp(`/panel/contenido/itinerarios/${borrador.id}$`));
    await expect(page.getByTestId('campo-resumen')).toHaveValue('Sin guardar');

    await page.getByTestId('editor-mas-acciones').click();
    await page.getByTestId('editor-eliminar').click();
    await expect(confirmacion).toContainText('no se puede deshacer');
    await page.getByTestId('editor-confirmacion-confirmar').click();
    await expect(page).toHaveURL(/\/panel\/contenido\/itinerarios$/);
    await expect(page.getByTestId('contenidos-aviso')).toContainText('Se eliminó el borrador');
    const eliminado = await page.request.get(`/api/v1/panel/contenidos/itinerarios/${borrador.id}`);
    expect(eliminado.status()).toBe(404);
  });

  test('AC_TKT023_03 / AC_TKT023_14 editor de tipo: checklist ordenable y texto enriquecido con enlace seguro', async ({ page }) => {
    await entrarComoEditor(page);
    const tipo = await crearBorrador(page, 'tipos-aventura', `Tipo E2E ${sufijo()}`);
    await irA(page, `/panel/contenido/tipos-aventura/${tipo.id}`);
    await page.getByTestId('editor-anadir-item').click();
    await page.getByTestId('campo-checklist-0-texto').fill('Agua');
    await page.getByTestId('editor-anadir-item').click();
    await page.getByTestId('campo-checklist-1-texto').fill('Botas');
    await page.locator('#editor-checklist-subir-1').click();
    await expect(page.getByTestId('campo-checklist-0-texto')).toHaveValue('Botas');
    await expect(page.getByTestId('editor-checklist-recuento')).toContainText('2 de 8 mínimo');

    const area = page.getByTestId('campo-descripcion');
    await area.click();
    await page.keyboard.type('Descripción del tipo');
    await page.getByTestId('campo-descripcion-enlace').click();
    await page.getByTestId('campo-descripcion-url').fill('javascript:alert(1)');
    await page.getByTestId('campo-descripcion-url-aplicar').click();
    await expect(page.getByText('Usa una dirección que empiece por http')).toBeVisible();
    await page.getByTestId('campo-descripcion-url').fill('https://example.org');
    await page.getByTestId('campo-descripcion-url-aplicar').click();
    await expect(area.locator('a[href="https://example.org"]')).toHaveCount(1);
    await sinViolacionesGraves(page);

    const guardado = page.waitForResponse((r) => r.url().endsWith(`/contenidos/tipos-aventura/${tipo.id}`) && r.request().method() === 'PUT');
    await page.getByTestId('editor-guardar').click();
    const respuesta = await guardado;
    expect(respuesta.status()).toBe(200);
    const cuerpo = respuesta.request().postDataJSON() as { checklist: { texto: string; orden: number }[]; descripcion: string };
    expect(cuerpo.checklist.map((c) => c.texto)).toEqual(['Botas', 'Agua']);
    expect(cuerpo.descripcion).toContain('<a href="https://example.org">');
    expect(cuerpo.descripcion).not.toContain('javascript:');
    await expect(page.getByTestId('editor-guardado')).toContainText('Guardado a las');
  });
});
