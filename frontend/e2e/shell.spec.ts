import { expect, test } from '@playwright/test';

import {
  enlacesTabulables,
  esperarHidratacion,
  focoActual,
  sinViolacionesGraves,
  tabularHasta,
  teclaTab,
} from './utilidades';

/**
 * AC-TKT002-06: shell navegable con teclado, skip link funcional, 404 accesible y axe sin
 * violaciones serious/critical, en chromium, firefox y webkit (proyectos de playwright.config.ts).
 */
test.describe('Shell global (GI-01..GI-04)', () => {
  test('AC_TKT002_06 el primer Tab enfoca el skip link visible y Enter lleva el foco al contenido principal', async ({
    page,
    browserName,
  }) => {
    await page.goto('/');
    await esperarHidratacion(page);

    const salto = page.getByTestId('skip-link');
    if (enlacesTabulables(browserName)) {
      await page.keyboard.press(teclaTab(browserName));
    } else {
      test
        .info()
        .annotations.push({
          type: 'webkit',
          description: 'Enlaces fuera del orden de Tab en WebKit: foco con focus()',
        });
      await salto.focus();
    }
    await expect(salto).toBeFocused();
    await expect(salto).toBeVisible();
    await expect(salto).toHaveText('Saltar al contenido principal');
    const caja = await salto.boundingBox();
    expect(caja?.y ?? -1).toBeGreaterThanOrEqual(0);

    await page.keyboard.press('Enter');
    await expect(page.locator('main#contenido-principal')).toBeFocused();
  });

  test('AC_TKT002_06 la navegación principal se recorre y activa con el teclado; el foco va al h1 de la vista', async ({
    page,
    browserName,
  }) => {
    await page.goto('/');
    await esperarHidratacion(page);

    if (enlacesTabulables(browserName)) {
      await tabularHasta(page, browserName, 'cabecera-logo');
      for (const id of ['nav-destinos', 'nav-tipos-de-aventura', 'nav-itinerarios', 'nav-guias']) {
        await page.keyboard.press(teclaTab(browserName));
        expect(await focoActual(page)).toBe(id);
      }
    } else {
      test
        .info()
        .annotations.push({
          type: 'webkit',
          description: 'Enlaces fuera del orden de Tab en WebKit: foco con focus()',
        });
      // El orden del DOM (= orden visual) sigue siendo logo → navegación principal.
      const orden = await page
        .locator('header a')
        .evaluateAll((a) => a.map((e) => e.getAttribute('data-testid')));
      expect(orden).toEqual([
        'cabecera-logo',
        'nav-destinos',
        'nav-tipos-de-aventura',
        'nav-itinerarios',
        'nav-guias',
      ]);
      await page.getByTestId('nav-guias').focus();
    }
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/guias$/);
    // /guias aún no existe (TKT-010): el comodín muestra SCR-023 y el foco va a su h1.
    const h1 = page.getByRole('heading', { level: 1 });
    await expect(h1).toHaveText('No encontramos esta página');
    await expect(h1).toBeFocused();
    await expect(page.getByTestId('nav-guias')).toHaveAttribute('aria-current', 'page');
  });

  test('AC_TKT002_06 la búsqueda valida en línea sin navegar', async ({ page }) => {
    await page.goto('/');
    await esperarHidratacion(page);
    const campo = page.getByTestId('cabecera-busqueda').getByRole('searchbox');
    await campo.fill('a');
    await campo.press('Enter');
    await expect(
      page.getByTestId('cabecera-busqueda').getByTestId('campo-busqueda-error'),
    ).toHaveText('Escribe al menos 2 caracteres.');
    await expect(campo).toHaveAttribute('aria-invalid', 'true');
    await expect(page).toHaveURL(/\/$/);
  });

  test('AC_TKT002_06 en móvil el menú es un diálogo modal operable con teclado y Esc devuelve el foco', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');
    await esperarHidratacion(page);

    const botonMenu = page.getByTestId('cabecera-boton-menu');
    await botonMenu.focus();
    await page.keyboard.press('Enter');
    const dialogo = page.getByRole('dialog', { name: 'Menú' });
    await expect(dialogo).toBeVisible();
    await expect(dialogo.getByRole('link', { name: 'Destinos' })).toBeVisible();
    expect(await dialogo.evaluate((d) => d.contains(document.activeElement))).toBe(true);

    await page.keyboard.press('Escape');
    await expect(dialogo).toBeHidden();
    await expect(botonMenu).toBeFocused();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT002_06 axe: / sin violaciones serious/critical', async ({ page }) => {
    const respuesta = await page.goto('/');
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('contentinfo')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT002_06 0 peticiones a dominios de terceros (fuentes e iconos autoalojados)', async ({
    page,
    baseURL,
  }) => {
    const origen = new URL(baseURL ?? 'http://127.0.0.1').origin;
    const externas: string[] = [];
    page.on('request', (r) => {
      const url = new URL(r.url());
      if (url.protocol.startsWith('http') && url.origin !== origen) externas.push(r.url());
    });
    await page.goto('/');
    await esperarHidratacion(page);
    await page.waitForLoadState('networkidle');
    expect(externas).toEqual([]);
  });
});

test.describe('Página 404 (SCR-023)', () => {
  test('AC_TKT002_06 una ruta inexistente responde HTTP 404 con la página accesible', async ({
    page,
  }) => {
    const respuesta = await page.goto('/esta-ruta/no-existe');
    expect(respuesta?.status()).toBe(404);
    await esperarHidratacion(page);
    await expect(page).toHaveTitle('Página no encontrada — Brújula Salvaje');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('No encontramos esta página');
    await expect(page.getByTestId('no-encontrada-inicio')).toHaveAttribute('href', '/');
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      'content',
      'noindex, nofollow',
    );
    await sinViolacionesGraves(page);
  });

  test('AC_TKT002_06 desde la 404 se vuelve al inicio con el teclado', async ({ page }) => {
    await page.goto('/no-existe');
    await esperarHidratacion(page);
    await page.getByTestId('no-encontrada-inicio').focus();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Contenido en preparación');
  });
});
