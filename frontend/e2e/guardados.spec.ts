import { expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

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
    await esperarHidratacion(page);

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

  test('AC_TKT008_09 compartir copia el enlace al portapapeles cuando no hay función nativa', async ({
    page,
    context,
  }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    const href = await page
      .getByTestId('tarjeta-destino')
      .first()
      .locator('a')
      .first()
      .getAttribute('href');
    await page.goto(href ?? '/destinos');
    await esperarHidratacion(page);

    // jsdom/Chromium headless no expone navigator.share: se fuerza para asegurar la vía de respaldo.
    await page.evaluate(() => {
      Object.defineProperty(window.navigator, 'share', { value: undefined, configurable: true });
    });
    await page.getByTestId('ficha-boton-compartir').click();
    await expect(page.getByText('Copiamos el enlace al portapapeles.')).toBeVisible();
  });
});
