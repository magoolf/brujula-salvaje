import { expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

/**
 * TKT-056 (LCP / bundle inicial): lo que se carga bajo demanda sigue funcionando y las imágenes
 * piden el tamaño adecuado. Requiere la semilla (Bahía de Ha Long tiene galería).
 */
const FICHA = '/destinos/bahia-de-ha-long';

test.describe('TKT-056 carga diferida y tamaños de imagen', () => {
  test('AC_TKT056_01 el visor de galería (cargado al pulsar) abre, navega, es accesible y Esc lo cierra', async ({
    page,
  }) => {
    await page.goto(FICHA);
    await esperarHidratacion(page);

    const miniaturas = page.getByTestId('galeria-miniatura');
    expect(await miniaturas.count()).toBeGreaterThan(1);
    await miniaturas.first().click();

    const visor = page.getByTestId('visor-galeria');
    await expect(visor).toBeVisible();
    await expect(visor.locator('.posicion')).toHaveText(/^1 de \d+$/);
    await page.keyboard.press('ArrowRight');
    await expect(visor.locator('.posicion')).toHaveText(/^2 de \d+$/);
    await sinViolacionesGraves(page);

    await page.keyboard.press('Escape');
    await expect(visor).toBeHidden();
    await expect(miniaturas.first()).toBeFocused();
  });

  test('AC_TKT056_02 og:image de la ficha es un JPEG grande (compatible con redes sociales)', async ({
    request,
  }) => {
    const html = await (await request.get(FICHA)).text();
    const og = /<meta property="og:image" content="([^"]+)"/.exec(html)?.[1] ?? '';
    expect(og).toMatch(/^https?:\/\/[^/]+\/media\/publico\/.+-1200-[0-9a-f]+\.jpe?g$/);
  });

  test.describe('móvil (412 px, DPR 1,75, perfil de Lighthouse)', () => {
    test.use({ viewport: { width: 412, height: 823 }, deviceScaleFactor: 1.75 });

    for (const caso of [
      { ruta: '/', testId: 'cabecera-boton-menu', dialogo: 'menu-movil' },
      { ruta: FICHA, testId: 'galeria-miniatura', dialogo: 'visor-galeria' },
    ]) {
      test(`AC_TKT056_04 ${caso.dialogo}: su módulo se precarga en reposo tras hidratar (abrir no descarga JS; QA F-02)`, async ({
        page,
      }) => {
        await page.goto(caso.ruta);
        await esperarHidratacion(page);
        // requestIdleCallback con plazo máximo de 3 s: tras él la precarga ya se pidió.
        await page.waitForTimeout(3500);
        await page.waitForLoadState('networkidle');
        const scripts: string[] = [];
        page.on('request', (r) => {
          if (r.resourceType() === 'script') scripts.push(r.url());
        });
        await page.getByTestId(caso.testId).first().click();
        await expect(page.getByTestId(caso.dialogo)).toBeVisible();
        expect(scripts).toEqual([]);
      });
    }

    test('AC_TKT056_03 las tarjetas de tipo de Inicio piden el derivado de 400 px, no el de 800', async ({
      page,
    }) => {
      await page.goto('/');
      await esperarHidratacion(page);
      const imagen = page.locator('.rejilla--tipos app-tarjeta-contenido img').first();
      await imagen.scrollIntoViewIfNeeded();
      await expect
        .poll(() => imagen.evaluate((i: HTMLImageElement) => i.complete && i.currentSrc !== ''))
        .toBe(true);
      const ancho = await imagen.evaluate((i: HTMLImageElement) => i.getBoundingClientRect().width);
      expect(ancho).toBeLessThan(200);
      expect(await imagen.evaluate((i: HTMLImageElement) => i.currentSrc)).toMatch(/-400-[0-9a-f]+\./);
    });
  });
});
