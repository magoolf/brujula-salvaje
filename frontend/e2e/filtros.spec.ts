import { expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * FLOW-002/FEAT-004: el estado de filtros vive en la URL (compartible, funciona con recarga
 * completa sin JS). Contra datos reales (facetas reales de la semilla).
 */
test.describe('Filtros de Explorar destinos en la URL (FEAT-004)', () => {
  test('AC_TKT008_04 activar un filtro de tipo actualiza la URL, el recuento y es persistente al recargar', async ({
    page,
  }) => {
    await page.goto('/destinos');
    await esperarHidratacion(page);

    const totalInicial = await page.getByTestId('destinos-recuento').textContent();

    const primeraOpcionTipo = page
      .getByTestId('filtros-destinos')
      .locator('fieldset')
      .first()
      .locator('a.opcion')
      .first();
    const etiquetaTipo = (await primeraOpcionTipo.textContent())?.trim();
    await primeraOpcionTipo.click();

    await expect(page).toHaveURL(/[?&]tipo=/);
    await expect(page.getByTestId('filtros-activos')).toContainText(etiquetaTipo ?? '');
    const totalFiltrado = await page.getByTestId('destinos-recuento').textContent();
    expect(totalFiltrado).not.toBe(totalInicial);

    // La URL filtrada es compartible: recargar conserva el filtro.
    await page.reload();
    await esperarHidratacion(page);
    await expect(page.getByTestId('filtros-activos')).toContainText(etiquetaTipo ?? '');
    await expect(page.getByTestId('destinos-recuento')).toHaveText(totalFiltrado ?? '');

    // Metadatos: no se indexa una URL filtrada, pero sí se sigue rastreando (DEC-AUTO-047).
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');

    // Quitar el filtro por la ficha activa vuelve al total original.
    await page.getByTestId('filtros-activos').locator('a').first().click();
    await expect(page).not.toHaveURL(/[?&]tipo=/);
    await expect(page.getByTestId('destinos-recuento')).toHaveText(totalInicial ?? '');
  });

  test('AC_TKT008_05 sin resultados: ofrece quitar el último filtro y explorar por tipo', async ({
    page,
  }) => {
    // Combinación verificada sin coincidencias contra la semilla real de TKT-007 (AC-018).
    await page.goto('/destinos?dificultad_min=5&dificultad_max=5&presupuesto=1&duracion=1-3');
    await esperarHidratacion(page);
    const vacio = page.getByTestId('destinos-vacio');
    await expect(vacio.getByRole('heading', { level: 2 })).toHaveText(
      'Ningún destino cumple estos filtros',
    );
    await expect(vacio.getByRole('link', { name: /Limpiar filtros/ })).toBeVisible();
  });
});
