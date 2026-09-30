import { expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

/**
 * FLOW-001/FLOW-004/FLOW-006 (Itinerarios, Tipos de aventura, Guías), FEAT-008/009/010/011/012.
 * Contra datos reales (TKT-007: semilla publicada) cuando `E2E_BASE_URL` apunta al stack real.
 */
test.describe('Itinerarios (SCR-006/007)', () => {
  test('AC_TKT009_01 listado de itinerarios navega a una ficha completa', async ({ page }) => {
    const respuesta = await page.goto('/itinerarios');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);

    await expect(page.getByRole('heading', { level: 1, name: 'Itinerarios' })).toBeVisible();
    const tarjetas = page.getByTestId('tarjeta-itinerario');
    await expect(tarjetas.first()).toBeVisible();
    await sinViolacionesGraves(page);

    const titulo = await tarjetas.first().locator('h3, h2').first().textContent();
    await tarjetas.first().locator('a').first().click();
    await expect(page).toHaveURL(/\/itinerarios\/[a-z0-9-]+$/);
    await page.getByTestId('pagina-itinerario').waitFor({ state: 'visible', timeout: 15_000 });
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(titulo?.trim() ?? '');
    await expect(page.getByTestId('migas-de-pan')).toBeVisible();
    await expect(page.getByTestId('descargo-responsabilidad')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT009_02 un itinerario inexistente responde 404 accesible', async ({ page }) => {
    const respuesta = await page.goto('/itinerarios/no-existe-este-itinerario-xyz');
    expect(respuesta?.status()).toBe(404);
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-no-encontrada')).toBeVisible();
    await sinViolacionesGraves(page);
  });
});

test.describe('Tipos de aventura (SCR-008/009)', () => {
  test('AC_TKT009_03 índice de tipos navega a un detalle con destinos asociados', async ({ page }) => {
    const respuesta = await page.goto('/tipos-de-aventura');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);

    await expect(page.getByRole('heading', { level: 1, name: 'Tipos de aventura' })).toBeVisible();
    const tarjetas = page.getByTestId('tarjeta-tipo');
    await expect(tarjetas.first()).toBeVisible();
    await sinViolacionesGraves(page);

    await tarjetas.first().locator('a').first().click();
    await expect(page).toHaveURL(/\/tipos-de-aventura\/[a-z0-9-]+$/);
    await page.getByTestId('pagina-tipo-aventura').waitFor({ state: 'visible', timeout: 15_000 });
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    // Enlace "Ver todos en Explorar" preaplica el filtro por tipo (FEAT-010, SCR-009).
    await expect(page.getByRole('link', { name: /Ver todos en Explorar/ })).toHaveAttribute(
      'href',
      /\/destinos\?tipo=/,
    );
    await sinViolacionesGraves(page);
  });
});

test.describe('Guías expertas (SCR-010/011/012)', () => {
  test('AC_TKT009_04 índice de guías navega a la categoría y luego a una ficha', async ({ page }) => {
    const respuesta = await page.goto('/guias');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);

    await expect(page.getByRole('heading', { level: 1, name: 'Guías expertas' })).toBeVisible();
    const verTodas = page.getByTestId('guias-ver-todas').first();
    await expect(verTodas).toBeVisible();
    await sinViolacionesGraves(page);

    await verTodas.click();
    await expect(page).toHaveURL(/\/guias\/categoria\/[a-z0-9-]+$/);
    await expect(page.getByTestId('pagina-categoria-guias')).toBeVisible();
    await sinViolacionesGraves(page);

    const primeraGuia = page.getByTestId('categoria-guias-lista').locator('a').first();
    const titulo = await primeraGuia.textContent();
    await primeraGuia.click();
    await expect(page).toHaveURL(/\/guias\/[a-z0-9-]+$/);
    await page.getByTestId('pagina-guia').waitFor({ state: 'visible', timeout: 15_000 });
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(titulo?.trim() ?? '');
    await expect(page.getByTestId('descargo-responsabilidad')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT009_05 una categoría de guías inexistente responde 404', async ({ page }) => {
    const respuesta = await page.goto('/guias/categoria/no-existe-esta-categoria-xyz');
    expect(respuesta?.status()).toBe(404);
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-no-encontrada')).toBeVisible();
  });
});
