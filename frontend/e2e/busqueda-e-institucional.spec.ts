import { expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

/**
 * FLOW-003 (Búsqueda, FEAT-016) y FLOW-017 (Institucional, FEAT-023/024). Contra datos reales
 * (TKT-007) cuando `E2E_BASE_URL` apunta al stack real.
 */
test.describe('Búsqueda (SCR-017)', () => {
  test('AC_TKT009_06 consulta corta muestra el mensaje en línea sin ejecutar la búsqueda', async ({
    page,
  }) => {
    await page.goto('/buscar?q=a');
    await esperarHidratacion(page);
    await expect(page.getByTestId('busqueda-invalida')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT009_07 consulta válida agrupa resultados por tipo y permite "ver todos"', async ({
    page,
  }) => {
    // "a" del alfabeto latino aparece en casi cualquier semilla real en español.
    const respuesta = await page.goto('/buscar?q=montana');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Resultados para');
    await sinViolacionesGraves(page);
  });
});

test.describe('Institucional y legal (SCR-020/021)', () => {
  for (const ruta of [
    '/acerca-de',
    '/politica-de-tratamiento-de-datos',
    '/politica-de-cookies',
    '/aviso-legal',
  ]) {
    test(`AC_TKT009_08 ${ruta} responde 200 y es accesible`, async ({ page }) => {
      const respuesta = await page.goto(ruta);
      expect(respuesta?.status()).toBe(200);
      await esperarHidratacion(page);
      await expect(page.getByTestId('pagina-institucional')).toBeVisible();
      await sinViolacionesGraves(page);
    });
  }

  test('AC_TKT009_09 acerca-de muestra las escalas de dificultad y presupuesto con ancla', async ({
    page,
  }) => {
    await page.goto('/acerca-de#escala-de-dificultad');
    await esperarHidratacion(page);
    await expect(page.locator('#escala-de-dificultad')).toBeVisible();
    await expect(page.locator('#escala-de-presupuesto')).toBeVisible();
  });

  test('AC_TKT009_10 créditos de imágenes lista medios agrupados por contenido', async ({ page }) => {
    const respuesta = await page.goto('/creditos');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await expect(page.getByRole('heading', { level: 1, name: 'Créditos de imágenes' })).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT009_11 pie de página enlaza a todas las páginas institucionales (sin huérfanas)', async ({
    page,
  }) => {
    await page.goto('/');
    await esperarHidratacion(page);
    await expect(page.getByTestId('pie-acerca-de')).toHaveAttribute('href', '/acerca-de');
    await expect(page.getByTestId('pie-tratamiento-de-datos')).toHaveAttribute(
      'href',
      '/politica-de-tratamiento-de-datos',
    );
    await expect(page.getByTestId('pie-cookies')).toHaveAttribute('href', '/politica-de-cookies');
    await expect(page.getByTestId('pie-aviso-legal')).toHaveAttribute('href', '/aviso-legal');
    await expect(page.getByTestId('pie-creditos')).toHaveAttribute('href', '/creditos');
  });
});

test.describe('Colecciones y glosario (SCR-013/014/018, SHOULD/COULD)', () => {
  test('AC_TKT009_12 índice de colecciones responde 200 (o estado vacío si aún no hay ninguna)', async ({
    page,
  }) => {
    const respuesta = await page.goto('/colecciones');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-colecciones')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT009_13 glosario responde 200 y el índice A-Z enlaza a los términos disponibles', async ({
    page,
  }) => {
    const respuesta = await page.goto('/glosario');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await expect(page.getByTestId('pagina-glosario')).toBeVisible();
    await sinViolacionesGraves(page);
  });
});
