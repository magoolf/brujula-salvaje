import { expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

/** FLOW-007/FEAT-005: mapa de destinos con lista alternativa siempre presente. */
test.describe('Mapa de destinos (SCR-003)', () => {
  test('AC_TKT008_10 el mapa muestra marcadores y su lista alternativa por región', async ({
    page,
  }) => {
    const respuesta = await page.goto('/destinos/mapa');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);

    await expect(page.getByRole('heading', { level: 1, name: 'Mapa de destinos' })).toBeVisible();
    await expect(page.getByTestId('mapa-marcador').first()).toBeVisible();
    // La lista es la alternativa equivalente (1.1.1/2.1.1): siempre presente, no solo con el mapa.
    await expect(page.getByRole('heading', { name: 'Todos los destinos por región' })).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT008_11 pulsar un marcador abre la minitarjeta con acceso a la ficha', async ({
    page,
  }) => {
    await page.goto('/destinos/mapa');
    await esperarHidratacion(page);
    await page.getByTestId('mapa-marcador').first().click();
    const minitarjeta = page.getByTestId('mapa-minitarjeta');
    await expect(minitarjeta).toBeVisible();
    await expect(minitarjeta.getByRole('link', { name: 'Ver destino' })).toHaveAttribute(
      'href',
      /\/destinos\/[a-z0-9-]+$/,
    );
  });
});

/** FLOW-008/FEAT-018: ¿Dónde ir cada mes? */
test.describe('¿Dónde ir cada mes? (SCR-015/016)', () => {
  test('AC_TKT008_12 el índice de meses navega al detalle de un mes', async ({ page }) => {
    const respuesta = await page.goto('/cuando-ir');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('¿Dónde ir cada mes?');

    await page.getByRole('link', { name: /Enero/i }).click();
    await expect(page).toHaveURL(/\/cuando-ir\/1$/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('enero');
    await sinViolacionesGraves(page);
  });

  test('AC_TKT008_13 un segmento de mes inválido responde 404', async ({ page }) => {
    const respuesta = await page.goto('/cuando-ir/13');
    expect(respuesta?.status()).toBe(404);
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-no-encontrada')).toBeVisible();
  });
});
