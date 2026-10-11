import { APIResponse, Page, expect, test } from '@playwright/test';

import { apiEscribir } from './panel-contenidos-soporte';
import { PROYECTO_COMPOSE, entrarComoEditorCompartido } from './panel-soporte';
import {
  empezarMedicionCls,
  esperarHidratacion,
  focoActual,
  leerCls,
  sinViolacionesGraves,
} from './utilidades';

/**
 * TKT-042 (QA TKT-019 OBS-01/OBS-02): anclas internas y fragmentos.
 * - OBS-01: con `<base href="/">` un `href="#x"` relativo resuelve a `/#x` (Inicio). El índice
 *   alfabético del glosario debe quedarse en /glosario y llevar la vista y el foco a la letra.
 * - OBS-02: la navegación EN CLIENTE a /glosario#termino (guías, tipos de aventura, itinerarios,
 *   mapa del sitio) debe dejar el término visible y con el foco aunque el glosario pinte sus datos
 *   después de terminar la navegación.
 * Contra datos reales (semilla) cuando `E2E_BASE_URL` apunta al stack de Compose. Los contenidos con
 * términos se descubren con la API pública, de forma independiente al código de las páginas.
 * Solo Chromium por decisión humana (velocidad); el proyecto `chromium` de playwright.config.
 */

interface Pagina<T> {
  readonly total_paginas: number;
  readonly resultados: readonly T[];
}

interface ConSlug {
  readonly slug: string;
}

interface Detalle {
  readonly terminos: readonly ConSlug[];
}

const RUTA_GLOSARIO = '/glosario';

/** GET que respeta el limitador real (429 + Retry-After) del entorno compartido. */
async function getConReintento(page: Page, url: string): Promise<APIResponse> {
  for (let intento = 0; intento < 8; intento++) {
    const respuesta = await page.request.get(url, { maxRedirects: 0 });
    if (respuesta.status() !== 429) return respuesta;
    const espera = Number(respuesta.headers()['retry-after'] ?? '1');
    await page.waitForTimeout(Math.min(Math.max(espera, 1), 10) * 1000);
  }
  throw new Error(`Límite de tasa persistente en ${url}`);
}

async function json<T>(page: Page, url: string): Promise<T> {
  const respuesta = await getConReintento(page, url);
  expect(respuesta.status(), url).toBe(200);
  return (await respuesta.json()) as T;
}

/** Slugs de la primera página del glosario, en el orden en que se pintan. */
async function terminosPagina1(page: Page): Promise<string[]> {
  const pagina = await json<Pagina<ConSlug>>(page, '/api/v1/publico/glosario');
  return pagina.resultados.map((t) => t.slug);
}

/**
 * Primer contenido publicado del tipo dado que enlaza a un término de la página 1 del glosario
 * (los enlaces de las fichas no llevan `?pagina=`). Devuelve el slug del contenido y el término
 * enlazado más abajo en el glosario (el que más desplazamiento exige).
 */
async function buscarContenidoConTermino(
  page: Page,
  api: string,
): Promise<{ slug: string; termino: string } | null> {
  const enGlosario = await terminosPagina1(page);
  const listado = await json<Pagina<ConSlug>>(page, api);
  for (const item of listado.resultados) {
    const detalle = await json<Detalle>(page, `${api}/${item.slug}`);
    const validos = detalle.terminos
      .map((t) => t.slug)
      .filter((s) => enGlosario.includes(s))
      .sort((a, b) => enGlosario.indexOf(b) - enGlosario.indexOf(a));
    if (validos.length > 0) return { slug: item.slug, termino: validos[0] };
  }
  return null;
}

/** Campos de ContenidoPanelMeta (y GuiaPanel.palabras) que no admite el PUT del panel. */
const CAMPOS_SOLO_LECTURA = new Set([
  'id',
  'tipo',
  'estado_editorial',
  'slug_bloqueado',
  'creado_en',
  'actualizado_en',
  'creado_por',
  'actualizado_por',
  'requisitos_publicacion',
  'referencias',
  'palabras',
  'motivo_retiro',
  'primera_publicacion_en',
  'publicado_actualizado_en',
  'retirado_en',
  'url_publica',
]);

interface ItemPanel {
  readonly id: number;
  readonly slug: string | null;
}

/**
 * Como `buscarContenidoConTermino`, pero si la semilla no relaciona ningún contenido de ese tipo con
 * el glosario (tipos de aventura e itinerarios de la semilla actual), lo prepara por la API del
 * panel en el stack bajo prueba: añade el último término de la página 1 al primer contenido
 * publicado y vuelve a publicarlo. Requiere el stack de Compose (E2E_COMPOSE_PROJECT).
 */
async function contenidoConTermino(
  page: Page,
  api: string,
  tipoPanel: string,
): Promise<{ slug: string; termino: string }> {
  const existente = await buscarContenidoConTermino(page, api);
  if (existente !== null) return existente;
  test.skip(
    PROYECTO_COMPOSE === '',
    `La semilla no relaciona ${tipoPanel} con el glosario y sin E2E_COMPOSE_PROJECT no se puede preparar.`,
  );
  const enGlosario = await terminosPagina1(page);
  const termino = enGlosario[enGlosario.length - 1];
  await entrarComoEditorCompartido(page);
  const glosario = await json<Pagina<ItemPanel>>(page, `/api/v1/panel/contenidos/glosario?q=${termino}`);
  const idTermino = glosario.resultados.find((t) => t.slug === termino)?.id;
  expect(idTermino, `término ${termino} en el panel`).toBeDefined();
  const publicados = await json<Pagina<ItemPanel>>(
    page,
    `/api/v1/panel/contenidos/${tipoPanel}?estado=PUBLICADO`,
  );
  const id = publicados.resultados[0].id;
  // PUT es un reemplazo completo: se reenvía el contenido tal cual (sin los campos de solo lectura)
  // añadiendo el término, para no vaciar checklist, días, etc. Un contenido PUBLICADO se actualiza
  // en el sitio al guardarlo.
  const actual = await json<Record<string, unknown>>(page, `/api/v1/panel/contenidos/${tipoPanel}/${id}`);
  const cuerpo = Object.fromEntries(Object.entries(actual).filter(([k]) => !CAMPOS_SOLO_LECTURA.has(k)));
  const previos = Array.isArray(actual['terminos_ids']) ? (actual['terminos_ids'] as number[]) : [];
  cuerpo['terminos_ids'] = [...new Set([...previos, idTermino as number])];
  await apiEscribir(page, 'put', `/contenidos/${tipoPanel}/${id}`, cuerpo);
  await page.context().clearCookies();
  await expect
    .poll(async () => (await buscarContenidoConTermino(page, api))?.termino ?? null, {
      timeout: 30_000,
    })
    .toBe(termino);
  return (await buscarContenidoConTermino(page, api)) as { slug: string; termino: string };
}

/** Marca el documento actual: si sigue marcado tras navegar, la navegación fue en cliente. */
async function marcarDocumento(page: Page): Promise<void> {
  await page.evaluate(() => {
    (window as unknown as { __tkt042: boolean }).__tkt042 = true;
  });
}

async function mismoDocumento(page: Page): Promise<boolean> {
  return page.evaluate(() => (window as unknown as { __tkt042?: boolean }).__tkt042 === true);
}

/** Tras llegar al término: misma vista del glosario, ancla en la URL, término visible y enfocado. */
async function esperarEnTermino(page: Page, slug: string): Promise<void> {
  await expect.poll(() => new URL(page.url()).pathname).toBe(RUTA_GLOSARIO);
  await expect.poll(() => new URL(page.url()).hash).toBe(`#${slug}`);
  const termino = page.locator(`[id="${slug}"]`);
  await expect(termino).toBeInViewport({ timeout: 15_000 });
  await expect(termino).toBeFocused();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Glosario');
}

test.describe('Anclas internas y fragmentos (TKT-042)', () => {
  test.describe.configure({ timeout: 120_000 });

  test('AC_TKT042_01 el índice del glosario se queda en /glosario y lleva vista y foco a la letra', async ({
    page,
  }) => {
    await empezarMedicionCls(page);
    await page.goto(RUTA_GLOSARIO);
    await esperarHidratacion(page);
    await page.waitForLoadState('networkidle');
    const indice = page.getByRole('navigation', { name: 'Índice alfabético' });
    const enlaces = indice.getByRole('link');
    await expect(enlaces.first()).toBeVisible();

    // Hrefs completos: con <base href="/"> un «#letra-x» relativo iría a /#letra-x (Inicio).
    const hrefs = await enlaces.evaluateAll((as) => as.map((a) => a.getAttribute('href') ?? ''));
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) expect(href).toMatch(/^\/glosario#letra-[A-ZÑ]$/);

    // La última letra disponible es la que más desplazamiento exige.
    const ultima = enlaces.last();
    const letra = (await ultima.textContent())?.trim() ?? '';
    await marcarDocumento(page);
    await ultima.click();
    await expect.poll(() => new URL(page.url()).pathname).toBe(RUTA_GLOSARIO);
    await expect.poll(() => new URL(page.url()).hash).toBe(`#letra-${letra}`);
    const seccion = page.locator(`[id="letra-${letra}"]`);
    await expect(seccion).toBeInViewport();
    await expect(seccion).toBeFocused();
    expect(await mismoDocumento(page)).toBe(true);

    // Teclado: Enter sobre la primera letra.
    await page.evaluate(() => window.scrollTo(0, 0));
    const primera = enlaces.first();
    const letraPrimera = (await primera.textContent())?.trim() ?? '';
    await primera.focus();
    await page.keyboard.press('Enter');
    await expect.poll(() => new URL(page.url()).hash).toBe(`#letra-${letraPrimera}`);
    await expect(page.locator(`[id="letra-${letraPrimera}"]`)).toBeFocused();
    await expect.poll(() => new URL(page.url()).pathname).toBe(RUTA_GLOSARIO);

    // Sin CLS por los saltos (Skill_UI_UX §47.2: CLS ≤ 0.1).
    const cls = await leerCls(page);
    expect(cls).not.toBeNull();
    expect(cls as number).toBeLessThanOrEqual(0.1);
    await sinViolacionesGraves(page);
  });

  test('AC_TKT042_02 carga directa de /glosario#termino deja el término en la vista', async ({
    page,
  }) => {
    const terminos = await terminosPagina1(page);
    const slug = terminos[terminos.length - 1];
    await page.goto(`${RUTA_GLOSARIO}#${slug}`);
    await esperarHidratacion(page);
    await expect(page.locator(`[id="${slug}"]`)).toBeInViewport({ timeout: 15_000 });
    await expect.poll(() => new URL(page.url()).pathname).toBe(RUTA_GLOSARIO);
  });

  const ORIGENES = [
    { nombre: 'una guía', api: '/api/v1/publico/guias', panel: 'guias', ruta: '/guias/' },
    {
      nombre: 'un tipo de aventura',
      api: '/api/v1/publico/tipos-aventura',
      panel: 'tipos-aventura',
      ruta: '/tipos-de-aventura/',
    },
    {
      nombre: 'un itinerario',
      api: '/api/v1/publico/itinerarios',
      panel: 'itinerarios',
      ruta: '/itinerarios/',
    },
  ] as const;

  for (const origen of ORIGENES) {
    test(`AC_TKT042_03 navegación en cliente desde ${origen.nombre} a /glosario#termino`, async ({
      page,
    }) => {
      const { slug, termino } = await contenidoConTermino(page, origen.api, origen.panel);
      await page.goto(`${origen.ruta}${slug}`);
      await esperarHidratacion(page);
      // data-app-lista llega con el primer render; la vista diferida se hidrata después.
      await page.waitForLoadState('networkidle');
      const enlace = page.locator(`a[href="${RUTA_GLOSARIO}#${termino}"]`).first();
      await expect(enlace).toBeVisible({ timeout: 15_000 });
      await marcarDocumento(page);
      await enlace.click();
      await esperarEnTermino(page, termino);
      expect(await mismoDocumento(page)).toBe(true);
    });
  }

  test('AC_TKT042_04 navegación en cliente desde el mapa del sitio a un término del glosario', async ({
    page,
  }) => {
    const terminos = await terminosPagina1(page);
    const slug = terminos[terminos.length - 1];
    await page.goto('/mapa-del-sitio');
    await esperarHidratacion(page);
    await page.waitForLoadState('networkidle');
    const enlace = page
      .getByTestId('pagina-mapa-del-sitio')
      .locator(`a[href="${RUTA_GLOSARIO}#${slug}"]`)
      .first();
    await expect(enlace).toBeVisible({ timeout: 15_000 });
    await marcarDocumento(page);
    await enlace.click();
    await esperarEnTermino(page, slug);
    expect(await mismoDocumento(page)).toBe(true);
    await sinViolacionesGraves(page);
  });

  test('AC_TKT042_05 el skip link global sigue llevando el foco al contenido principal', async ({
    page,
  }) => {
    await page.goto(RUTA_GLOSARIO);
    await esperarHidratacion(page);
    await page.keyboard.press('Tab');
    expect(await focoActual(page)).toBe('skip-link');
    await page.keyboard.press('Enter');
    expect(await focoActual(page)).toBe('contenido-principal');
    await expect.poll(() => new URL(page.url()).pathname).toBe(RUTA_GLOSARIO);
  });

  test('AC_TKT042_06 sin enlaces con href="#…" relativos salvo el skip link', async ({ page }) => {
    const { slug: guia } = await contenidoConTermino(page, '/api/v1/publico/guias', 'guias');
    for (const ruta of [RUTA_GLOSARIO, '/mapa-del-sitio', `/guias/${guia}`, '/acerca-de']) {
      await page.goto(ruta);
      await esperarHidratacion(page);
      const relativos = await page
        .locator('a[href^="#"]:not([data-testid="skip-link"])')
        .evaluateAll((as) => as.map((a) => a.outerHTML.slice(0, 120)));
      expect(relativos, ruta).toEqual([]);
    }
  });
});
