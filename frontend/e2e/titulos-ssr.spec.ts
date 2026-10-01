import { expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * TKT-010, OBS-04 (QA ciclo 1): el <title> y og:title de las rutas públicas son iguales en el HTML
 * del SSR y en el cliente, tanto en la carga directa como al navegar dentro de la SPA (con la ruta
 * de layout de la primera versión, Inicio daba «Brújula Salvaje» en SSR y «Inicio — …» en cliente).
 */
const RUTAS: readonly { ruta: string; titulo: RegExp }[] = [
  { ruta: '/', titulo: /^Inicio — Brújula Salvaje$/ }, // mismo título que main en SSR y cliente
  { ruta: '/destinos', titulo: / — Brújula Salvaje$/ },
  { ruta: '/guias', titulo: / — Brújula Salvaje$/ },
  { ruta: '/acerca-de', titulo: / — Brújula Salvaje$/ },
];

function tituloDelHtml(html: string): string {
  return /<title>([^<]*)<\/title>/.exec(html)?.[1] ?? '';
}

function ogTitleDelHtml(html: string): string {
  return /<meta property="og:title" content="([^"]*)"/.exec(html)?.[1] ?? '';
}

test.describe('Títulos SSR = cliente (TKT-010 OBS-04)', () => {
  for (const { ruta, titulo } of RUTAS) {
    test(`TKT010_OBS04 ${ruta}: mismo título y og:title en SSR y en el cliente`, async ({ page, request }) => {
      const html = await (await request.get(ruta)).text();
      const tituloSsr = tituloDelHtml(html);
      const ogSsr = ogTitleDelHtml(html);
      expect(tituloSsr).toMatch(titulo);
      expect(ogSsr).not.toBe('');

      await page.goto(ruta);
      await esperarHidratacion(page);
      await expect(page).toHaveTitle(tituloSsr);
      // og:title lo fija cada página (Inicio usa solo la marca, igual que en main): debe coincidir.
      await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content', ogSsr);
    });
  }

  test('TKT010_OBS04 al volver a Inicio navegando en la SPA el título es el mismo que en SSR', async ({
    page,
    request,
  }) => {
    const tituloSsr = tituloDelHtml(await (await request.get('/')).text());
    await page.goto('/destinos');
    await esperarHidratacion(page);
    await page.getByTestId('cabecera-logo').click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page).toHaveTitle(tituloSsr);
  });
});
