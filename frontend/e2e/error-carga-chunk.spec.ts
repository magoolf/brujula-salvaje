import { Page, Request, Route, expect, test } from '@playwright/test';

import { esperarHidratacion, sinViolacionesGraves } from './utilidades';

/**
 * TKT-025: un fallo al cargar el chunk diferido de una ruta (red, 429 del limitador del borde, 404
 * con HTML tras un despliegue) no deja la página en blanco. Se navega desde el shell de Inicio a
 * Destinos con el chunk de Destinos fallando:
 * - fallo transitorio → UNA recarga completa hacia /destinos y la ruta se muestra entera;
 * - fallo persistente → una sola recarga (sin bucle) y estado de error accesible con el shell.
 * Solo se ejecuta en Chromium (decisión humana: E2E/QA solo en Chromium).
 */
const DESTINO = '/destinos';

type Fallo = (ruta: Route) => Promise<void>;

const FALLOS: Record<string, Fallo> = {
  'red abortada': (ruta) => ruta.abort('failed'),
  '429 del limitador': (ruta) =>
    ruta.fulfill({ status: 429, contentType: 'text/plain', body: 'Too Many Requests' }),
  '404 con HTML tras un despliegue (error de MIME)': (ruta) =>
    ruta.fulfill({
      status: 404,
      contentType: 'text/html',
      body: '<!doctype html><title>404</title>',
    }),
};

/**
 * Abre Inicio, espera a la hidratación y a la precarga en reposo, y desde ese momento intercepta
 * todo JavaScript que Inicio no haya cargado (los chunks propios de la ruta destino): `debeFallar`
 * decide en cada petición si falla. Devuelve las cargas de documento hacia el destino.
 */
async function prepararDesdeInicio(
  page: Page,
  fallo: Fallo,
  debeFallar: () => boolean,
): Promise<Request[]> {
  const cargados = new Set<string>();
  page.on('request', (r) => {
    if (r.resourceType() === 'script') cargados.add(r.url());
  });
  await page.goto('/');
  await esperarHidratacion(page);
  await page.waitForLoadState('networkidle');
  const permitidos = new Set(cargados);
  await page.route('**/*.js', (ruta) =>
    permitidos.has(ruta.request().url()) || !debeFallar() ? ruta.continue() : fallo(ruta),
  );
  const documentos: Request[] = [];
  page.on('request', (r) => {
    if (r.isNavigationRequest() && new URL(r.url()).pathname === DESTINO) documentos.push(r);
  });
  return documentos;
}

async function shellIntacto(page: Page): Promise<void> {
  await expect(page.getByTestId('cabecera-sitio')).toBeVisible();
  await expect(page.getByTestId('contenido-principal')).toBeVisible();
  await expect(page.getByTestId('pie-sitio')).toBeVisible();
}

test.describe('TKT-025 error de carga de chunk diferido', () => {
  test.skip(
    ({ browserName }) => browserName !== 'chromium',
    'E2E solo en Chromium (decisión humana)',
  );

  for (const [nombre, fallo] of Object.entries(FALLOS)) {
    test(`AC_TKT025_06 fallo transitorio (${nombre}): una recarga y la ruta destino se muestra con el shell`, async ({
      page,
    }) => {
      let fallar = true;
      const documentos = await prepararDesdeInicio(page, fallo, () => fallar);
      // El chunk solo falla hasta la recarga: el documento nuevo lo obtiene sin problema.
      page.on('request', (r) => {
        if (r.isNavigationRequest()) fallar = false;
      });

      await page.getByTestId('nav-destinos').first().click();

      await expect(page).toHaveURL(DESTINO);
      await expect(page.getByTestId('pagina-destinos')).toBeVisible();
      await expect(
        page.getByRole('heading', { level: 1, name: 'Explorar destinos' }),
      ).toBeVisible();
      await esperarHidratacion(page);
      await shellIntacto(page);
      await expect(page.getByTestId('error-carga-ruta')).toHaveCount(0);
      expect(documentos).toHaveLength(1);
      await sinViolacionesGraves(page);
    });
  }

  test('AC_TKT025_07 fallo persistente: una sola recarga, sin bucle, estado de error accesible con el shell intacto', async ({
    page,
  }) => {
    const documentos = await prepararDesdeInicio(page, FALLOS['red abortada'], () => true);

    await page.getByTestId('nav-destinos').first().click();

    const estado = page.getByTestId('error-carga-ruta');
    await expect(estado).toBeVisible();
    await expect(estado).toHaveAttribute('role', 'alert');
    const titulo = estado.getByRole('heading', { level: 1, name: 'No pudimos cargar la página' });
    await expect(titulo).toBeVisible();
    await expect(titulo).toBeFocused();
    await expect(estado.getByRole('link', { name: 'Reintentar' })).toHaveAttribute('href', DESTINO);
    await expect(page).toHaveTitle('No pudimos cargar la página — Brújula Salvaje');
    await shellIntacto(page);

    // Sin bucle: tras unos segundos sigue habiendo una única recarga hacia el destino.
    await page.waitForTimeout(3000);
    expect(documentos).toHaveLength(1);
    await expect(estado).toBeVisible();
    await sinViolacionesGraves(page);

    // El shell sigue operativo: navegar a Inicio (ya cargado) retira el estado de error.
    await page.getByTestId('cabecera-logo').click();
    await expect(page).toHaveURL('/');
    await expect(estado).toHaveCount(0);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });
});
