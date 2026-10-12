import { expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * TKT-042 (DEC-AUTO-999, encadenado en el PR de TKT-021): el salto «Ir a la lista de destinos» del
 * mapa usaba href="#lista-destinos-mapa", que con <base href="/"> se resuelve a /#lista-… y saca al
 * visitante del mapa. Ahora apunta a la ruta actual con el fragmento, con y sin JavaScript.
 */
const RUTA = '/destinos/mapa';

test.describe('TKT-042 salto a la lista del mapa', () => {
  test.describe('sin JavaScript (HTML del servidor)', () => {
    test.use({ javaScriptEnabled: false });

    test('AC_TKT042_salto_01 el href es absoluto a la propia ruta y el salto deja la lista visible', async ({
      page,
    }) => {
      await page.goto(RUTA);
      const salto = page.locator('a.salto');
      await expect(salto).toHaveAttribute('href', `${RUTA}#lista-destinos-mapa`);
      await salto.click();
      await expect(page).toHaveURL(new RegExp(`${RUTA}#lista-destinos-mapa$`));
      await expect(page.locator('#lista-destinos-mapa')).toBeInViewport();
    });
  });

  test('AC_TKT042_salto_02 con JavaScript conserva la ruta y los parámetros y deja la lista visible', async ({
    page,
  }) => {
    await page.goto(`${RUTA}?origen=prueba`);
    await esperarHidratacion(page);
    const salto = page.locator('a.salto');
    await expect(salto).toHaveAttribute('href', `${RUTA}?origen=prueba#lista-destinos-mapa`);
    await salto.click();
    await expect(page).toHaveURL(new RegExp(`${RUTA}\\?origen=prueba#lista-destinos-mapa$`));
    await expect(page.locator('#lista-destinos-mapa')).toBeInViewport();
  });
});
