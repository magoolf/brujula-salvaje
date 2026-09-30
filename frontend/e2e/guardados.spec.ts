import { expect, test } from '@playwright/test';

import { esperarFichaDestino, esperarHidratacion, sinViolacionesGraves } from './utilidades';

/**
 * FLOW-009/FEAT-020/021 (RULE-013): guardar/quitar/compartir, 100 % en el navegador. Se limpia
 * `localStorage` entre pruebas para que no dependan unas de otras.
 */
test.describe('Guardados y compartir (MOD-006)', () => {
  // Una sola limpieza al principio (NO `addInitScript`: se repetiría en cada navegación posterior
  // de la propia prueba y borraría lo que la prueba acaba de guardar). Cada prueba reutiliza esta
  // primera carga de `/destinos` en vez de recargarla otra vez, para no encadenar dos navegaciones
  // completas a la misma URL en el mismo caso (fuente de intermitencia observada en este entorno).
  test.beforeEach(async ({ page }) => {
    await page.goto('/destinos');
    await page.evaluate(() => localStorage.clear());
    await esperarHidratacion(page);
  });

  test('AC_TKT008_06 guardados vacío ofrece explorar y Sorpréndeme', async ({ page }) => {
    await page.goto('/guardados');
    await esperarHidratacion(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mis aventuras guardadas');
    await expect(page.getByText('Aún no has guardado aventuras')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT008_07 guardar un destino desde la ficha lo añade a Mis guardados y se puede quitar', async ({
    page,
  }) => {
    const href = await page
      .getByTestId('tarjeta-destino')
      .first()
      .locator('a')
      .first()
      .getAttribute('href');
    await page.goto(href ?? '/destinos');
    await esperarFichaDestino(page);

    const botonGuardar = page.getByTestId('ficha-boton-guardar');
    await expect(botonGuardar).toHaveAttribute('aria-pressed', 'false');
    await botonGuardar.click();
    await expect(botonGuardar).toHaveAttribute('aria-pressed', 'true');
    const titulo = await page.getByRole('heading', { level: 1 }).textContent();

    await page.goto('/guardados');
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-guardados')).toContainText(titulo?.trim() ?? '');

    await page.getByRole('button', { name: /Quitar/ }).first().click();
    await expect(page.getByText('Aún no has guardado aventuras')).toBeVisible();
  });

  test('AC_TKT008_08 vaciar todo pide confirmación antes de borrar', async ({ page }) => {
    await page.getByTestId('tarjeta-destino').first().locator('[data-testid="boton-guardar-destino"]').click();

    await page.goto('/guardados');
    await esperarHidratacion(page);
    await page.getByTestId('guardados-vaciar').click();
    await expect(page.getByRole('alertdialog')).toBeVisible();
    await expect(page.getByText('No se puede')).toBeVisible();
    await page.getByTestId('guardados-vaciar-confirmar').click();
    await expect(page.getByText('Aún no has guardado aventuras')).toBeVisible();
  });

});

/**
 * AC_TKT008_09 en su propio `describe` (fuera del `beforeEach` compartido de arriba): lo que prueba
 * es el mecanismo de compartir/portapapeles, no el listado de `/destinos` en sí, pero llega a él dos
 * veces (listado + ficha) porque extrae el `href` de una tarjeta real. QA (ciclo 2/3, logs del proxy
 * inspeccionados) confirmó que esas dos cargas completas, con caché fría, disparan ~69 peticiones
 * casi simultáneas (sobre todo derivados de imagen) que superan el `burst=60` del límite de borde de
 * `infra/proxy/nginx.conf` (fuera de `archivos_permitidos`; investigación de fondo ya abierta en
 * TKT-018) — un 429 ahí deja la página sin `<main>` y esta prueba nunca ve la ficha. QA verificó por
 * su parte que el propio mecanismo de portapapeles es correcto (9/9 en los 3 motores) bloqueando esas
 * peticiones de imagen, así que aquí se aísla la prueba de la misma forma: se abortan las peticiones
 * a `/media/**` (irrelevantes para este aserto) antes de navegar, sin perder cobertura real del AC.
 */
test.describe('Guardados y compartir (MOD-006) — compartir', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/media/**', (route) => route.abort());
  });

  test('AC_TKT008_09 compartir copia el enlace al portapapeles cuando no hay función nativa', async ({
    page,
  }) => {
    // `context.grantPermissions(['clipboard-read', 'clipboard-write'])` solo existe en Chromium
    // (Firefox/WebKit lanzan "Unknown permission"): en vez de depender del modelo de permisos real
    // del navegador (distinto en cada motor), se sustituye `navigator.clipboard.writeText` por un
    // doble de prueba antes de que cargue cualquier script de la página, y se fuerza la ausencia de
    // `navigator.share` para asegurar la vía de respaldo en los 3 proyectos por igual.
    await page.addInitScript(() => {
      Object.defineProperty(window.navigator, 'share', { value: undefined, configurable: true });
      Object.defineProperty(window.navigator, 'clipboard', {
        value: {
          writeText: (texto: string) => {
            (window as unknown as { __textoCopiado?: string }).__textoCopiado = texto;
            return Promise.resolve();
          },
        },
        configurable: true,
      });
    });

    await page.goto('/destinos');
    await page.evaluate(() => localStorage.clear());
    await esperarHidratacion(page);

    const href = await page
      .getByTestId('tarjeta-destino')
      .first()
      .locator('a')
      .first()
      .getAttribute('href');
    await page.goto(href ?? '/destinos');
    await esperarFichaDestino(page);

    await page.getByTestId('ficha-boton-compartir').click();
    await expect(page.getByText('Copiamos el enlace al portapapeles.')).toBeVisible();
    const copiado = await page.evaluate(
      () => (window as unknown as { __textoCopiado?: string }).__textoCopiado,
    );
    expect(copiado).toContain(href);
  });
});
