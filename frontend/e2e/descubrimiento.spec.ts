import { expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

/**
 * FLOW-001 (Inicio → Explorar destinos → Ficha de destino), FEAT-001/003/006. Contra datos reales
 * (TKT-007: 24 destinos publicados) cuando `E2E_BASE_URL` apunta al stack de `compose.yaml`.
 */
test.describe('Descubrimiento de destinos (FLOW-001)', () => {
  test('AC_TKT008_01 inicio muestra destacados y navega a Explorar destinos', async ({ page }) => {
    const respuesta = await page.goto('/');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);

    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByTestId('inicio-cta-explorar')).toBeVisible();
    await sinViolacionesGraves(page);

    await page.getByTestId('inicio-cta-explorar').click();
    await expect(page).toHaveURL(/\/destinos$/);
    await expect(page.getByRole('heading', { level: 1, name: 'Explorar destinos' })).toBeVisible();
  });

  test('AC_TKT008_02 explorar destinos lista tarjetas y abre una ficha completa', async ({
    page,
  }) => {
    const respuesta = await page.goto('/destinos');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);

    const recuento = page.getByTestId('destinos-recuento');
    await expect(recuento).toBeVisible();
    await expect(recuento).toContainText('destino');

    const tarjetas = page.getByTestId('tarjeta-destino');
    await expect(tarjetas.first()).toBeVisible();
    const titulo = await tarjetas.first().locator('h3, h2').first().textContent();

    await tarjetas.first().locator('a').first().click();
    await expect(page).toHaveURL(/\/destinos\/[a-z0-9-]+$/);
    await expect(page.getByTestId('pagina-destino')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(titulo?.trim() ?? '');
    await expect(page.getByTestId('migas-de-pan')).toBeVisible();
    await expect(page.getByTestId('descargo-responsabilidad')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT008_03 una ficha de destino inexistente responde 404 accesible', async ({ page }) => {
    const respuesta = await page.goto('/destinos/no-existe-este-destino-xyz');
    expect(respuesta?.status()).toBe(404);
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-no-encontrada')).toBeVisible();
    await sinViolacionesGraves(page);
  });
});
