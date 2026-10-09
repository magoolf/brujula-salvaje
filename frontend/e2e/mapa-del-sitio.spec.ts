import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { resolve } from 'node:path';

import { APIResponse, Page, expect, test } from '@playwright/test';

import { PROYECTO_COMPOSE, omitirSinStack } from './panel-soporte';
import {
  empezarMedicionCls,
  esperarHidratacion,
  leerCls,
  sinViolacionesGraves,
} from './utilidades';

/**
 * TKT-019 · SCR-022 Mapa del sitio HTML (FEAT-025, MUST, RULE-030, OBJ-001, AC-025), FLOW-017.
 * Contra datos reales (semilla) cuando `E2E_BASE_URL` apunta al stack de Compose. El oráculo de
 * «lo publicado» es la API pública (/api/v1/publico/indice, /meses, /glosario), consultada aquí de
 * forma independiente al código de la página.
 */

const RUTA = '/mapa-del-sitio';

const SECCIONES = [
  'General',
  'Destinos',
  'Itinerarios',
  'Tipos de aventura',
  'Guías',
  'Colecciones',
  '¿Dónde ir cada mes?',
  'Glosario',
  'Institucional',
];

interface Pagina<T> {
  readonly total_paginas: number;
  readonly resultados: readonly T[];
}

interface EntradaIndice {
  readonly tipo: string;
  readonly slug: string;
  readonly titulo: string;
}

interface Termino {
  readonly slug: string;
  readonly termino: string;
}

/** Ruta pública esperada de cada tipo del índice (oráculo independiente del dominio). */
function rutaEsperada(entrada: EntradaIndice): string {
  const prefijos: Record<string, string> = {
    DESTINO: '/destinos/',
    ITINERARIO: '/itinerarios/',
    TIPO: '/tipos-de-aventura/',
    GUIA: '/guias/',
    CATEGORIA_GUIA: '/guias/categoria/',
    COLECCION: '/colecciones/',
    PAGINA: '/',
  };
  return `${prefijos[entrada.tipo]}${entrada.slug}`;
}

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

async function todas<T>(page: Page, url: string): Promise<T[]> {
  const primera = (await (await getConReintento(page, url)).json()) as Pagina<T>;
  const resultados = [...primera.resultados];
  for (let n = 2; n <= primera.total_paginas; n++) {
    const pagina = (await (await getConReintento(page, `${url}?pagina=${n}`)).json()) as Pagina<T>;
    resultados.push(...pagina.resultados);
  }
  return resultados;
}

async function hrefs(page: Page, testId: string): Promise<string[]> {
  return page
    .getByTestId(testId)
    .evaluateAll((enlaces) => enlaces.map((a) => a.getAttribute('href') ?? ''));
}

/**
 * El SSR reenvía la IP del cliente (X-Forwarded-For): cada página SSR consume varias peticiones del
 * cupo «publico-lectura» (120/min) del ejecutor, compartido con el resto de la suite. Por eso:
 * - el recorrido de AC_TKT019_04 comprueba por SSR solo una muestra (una ruta por patrón); que cada
 *   enlace de contenido exista lo garantiza el oráculo de la API (AC_TKT019_03 y AC_TKT019_05);
 * - solo se reintenta ante un 429 real: visto en /api/ desde el navegador o, en el SSR (donde el
 *   429 queda en el servidor), por el estado de error con el mensaje de límite de peticiones.
 *   Cualquier otro estado de error o un 404 es un fallo.
 */
const REINTENTOS_LIMITE = 6;
const ESPERA_LIMITE_MS = 10_000;
const MARCA_ERROR = 'data-testid="estado-error"';
const MARCA_404 = 'data-testid="pagina-no-encontrada"';
const TEXTO_LIMITE = /límite de peticiones/i;

function esLimiteEnSsr(html: string): boolean {
  return html.includes(MARCA_ERROR) && TEXTO_LIMITE.test(html);
}

/** HTML del SSR de `ruta`; reintenta solo si el SSR recibió un 429 del backend. */
async function htmlSsr(page: Page, ruta: string): Promise<{ estado: number; html: string }> {
  let resultado = { estado: 0, html: '' };
  for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
    const respuesta = await getConReintento(page, ruta);
    resultado = { estado: respuesta.status(), html: await respuesta.text() };
    if (!esLimiteEnSsr(resultado.html)) return resultado;
    await page.waitForTimeout(ESPERA_LIMITE_MS);
  }
  return resultado;
}

/** Abre el mapa en el navegador; reintenta solo ante un 429 real (navegador o SSR). */
async function abrirMapa(page: Page): Promise<void> {
  let vio429 = false;
  const alResponder = (r: { url(): string; status(): number }): void => {
    if (r.url().includes('/api/') && r.status() === 429) vio429 = true;
  };
  page.on('response', alResponder);
  try {
    for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
      const respuesta = await page.goto(RUTA);
      expect(respuesta?.status()).toBe(200);
      await esperarHidratacion(page);
      const total = page.getByTestId('mapa-total');
      const error = page.getByTestId('estado-error');
      await expect(total.or(error).first()).toBeVisible({ timeout: 15_000 });
      if (await total.isVisible()) return;
      const limite = vio429 || TEXTO_LIMITE.test(await error.innerText());
      expect(limite, 'estado de error sin 429: fallo real').toBe(true);
      vio429 = false;
      await page.waitForTimeout(ESPERA_LIMITE_MS);
    }
    await expect(page.getByTestId('mapa-total')).toBeVisible({ timeout: 15_000 });
  } finally {
    page.off('response', alResponder);
  }
}

/** Patrón de ruta: el último segmento de las rutas de detalle pasa a `:x` (sin query ni ancla). */
function patron(ruta: string): string {
  const camino = ruta.split(/[?#]/)[0];
  const segmentos = camino.split('/').filter(Boolean);
  return segmentos.length < 2 ? camino : `/${[...segmentos.slice(0, -1), ':x'].join('/')}`;
}

/** Tras usar el índice: misma página, ancla en la URL, h2 en la vista y con el foco. */
async function esperarEnSeccion(page: Page, id: string, titulo: string): Promise<void> {
  await expect.poll(() => new URL(page.url()).pathname).toBe(RUTA);
  await expect.poll(() => new URL(page.url()).hash).toBe(`#seccion-${id}`);
  const h2 = page.getByRole('heading', { level: 2, name: titulo, exact: true });
  await expect(h2).toBeInViewport();
  await expect(h2).toBeFocused();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mapa del sitio');
}

test.describe('Mapa del sitio (SCR-022)', () => {
  // Margen para las esperas por límite de tasa (htmlSsr / abrirMapa).
  test.describe.configure({ timeout: 180_000 });

  test('AC_TKT019_01 responde 200 con SSR, título, canónica y h1', async ({ page }) => {
    const { estado, html } = await htmlSsr(page, RUTA);
    expect(estado).toBe(200);
    expect(html).not.toContain(MARCA_ERROR);
    // CON-007: el contenido llega en el HTML inicial (no solo tras hidratar).
    expect(html).toContain('data-testid="mapa-total"');
    expect(html).toMatch(/href="\/destinos\/[a-z0-9-]+"/);

    await abrirMapa(page);
    await expect(page).toHaveTitle(/^Mapa del sitio — /);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', /\/mapa-del-sitio$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mapa del sitio');
  });

  test('AC_TKT019_02 lista todas las secciones con su índice interno', async ({ page }) => {
    await abrirMapa(page);
    await expect(
      page.getByTestId('pagina-mapa-del-sitio').getByRole('heading', { level: 2 }),
    ).toHaveText(SECCIONES);
    const indice = page.getByRole('navigation', { name: 'Secciones del mapa del sitio' });
    await expect(indice.getByRole('link')).toHaveText(SECCIONES);
    // Con <base href="/"> un «#seccion-x» relativo iría a /#seccion-x (Inicio): sigue en el mapa.
    await expect(indice.getByRole('link', { name: 'Glosario' })).toHaveAttribute(
      'href',
      '/mapa-del-sitio#seccion-glosario',
    );
    await indice.getByRole('link', { name: 'Glosario' }).click();
    await esperarEnSeccion(page, 'glosario', 'Glosario');

    // Teclado: Enter sobre otro enlace del índice.
    await page.evaluate(() => window.scrollTo(0, 0));
    await indice.getByRole('link', { name: 'Colecciones' }).focus();
    await page.keyboard.press('Enter');
    await esperarEnSeccion(page, 'colecciones', 'Colecciones');
  });

  test('AC_TKT019_03 enlaza cada contenido publicado (destinos, itinerarios, tipos, guías, colecciones, meses, glosario, institucional)', async ({
    page,
  }) => {
    const entradas = await todas<EntradaIndice>(page, '/api/v1/publico/indice');
    const terminos = await todas<Termino>(page, '/api/v1/publico/glosario');
    const meses = (
      (await (await getConReintento(page, '/api/v1/publico/meses')).json()) as {
        meses: { mes: number }[];
      }
    ).meses;
    // La semilla real publica contenido de todas las secciones.
    for (const tipo of ['DESTINO', 'ITINERARIO', 'TIPO', 'GUIA', 'COLECCION', 'PAGINA']) {
      expect(entradas.some((e) => e.tipo === tipo), `semilla sin ${tipo}`).toBe(true);
    }

    await abrirMapa(page);
    const enlaces = new Set(await hrefs(page, 'mapa-enlace'));

    const faltan = entradas.map(rutaEsperada).filter((ruta) => !enlaces.has(ruta));
    expect(faltan).toEqual([]);
    for (const mes of meses) expect(enlaces).toContain(`/cuando-ir/${mes.mes}`);
    for (const termino of terminos) {
      expect([...enlaces].some((h) => h.startsWith('/glosario') && h.endsWith(`#${termino.slug}`))).toBe(true);
    }
    expect(enlaces).toContain('/creditos');

    // Destinos agrupados por región (h3) y guías por categoría (h3 con enlace a la categoría).
    await expect(page.getByTestId('mapa-seccion-destinos').getByRole('heading', { level: 3 }).first()).toBeVisible();
    const categoria = entradas.find((e) => e.tipo === 'CATEGORIA_GUIA');
    if (categoria) {
      await expect(
        page.getByTestId('mapa-seccion-guias').getByRole('heading', { level: 3, name: categoria.titulo }),
      ).toBeVisible();
    }
  });

  test('AC_TKT019_04 todos los enlaces resuelven (sin 404) y las anclas del glosario existen', async ({
    page,
  }) => {
    await abrirMapa(page);
    const todos = [...(await hrefs(page, 'mapa-enlace')), ...(await hrefs(page, 'mapa-enlace-seccion'))];
    const rutas = [...new Set(todos.map((h) => h.split('#')[0]))];
    expect(rutas.length).toBeGreaterThan(20);

    // Una ruta por patrón (/destinos/:x, /guias/categoria/:x, /cuando-ir/:x, /glosario, páginas
    // de un segmento…): cubre cada ruta del Router sin agotar el cupo compartido (ver arriba).
    const muestra = new Map<string, string>();
    for (const ruta of rutas) if (!muestra.has(patron(ruta))) muestra.set(patron(ruta), ruta);
    expect(muestra.size).toBeLessThan(rutas.length);

    const rotas: string[] = [];
    for (const ruta of muestra.values()) {
      const { estado, html } = await htmlSsr(page, ruta);
      if (estado !== 200) rotas.push(`${ruta} → ${estado}`);
      else if (html.includes(MARCA_404)) rotas.push(`${ruta} → página 404`);
      else if (html.includes(MARCA_ERROR)) rotas.push(`${ruta} → estado de error`);
    }
    expect(rotas).toEqual([]);

    // Cada término enlazado existe como ancla en su página del glosario.
    const anclasPorPagina = new Map<string, string[]>();
    for (const href of todos.filter((h) => h.startsWith('/glosario') && h.includes('#'))) {
      const [ruta, ancla] = href.split('#');
      anclasPorPagina.set(ruta, [...(anclasPorPagina.get(ruta) ?? []), ancla]);
    }
    for (const [ruta, anclas] of anclasPorPagina) {
      const { html } = await htmlSsr(page, ruta);
      expect(html, `${ruta} con error`).not.toContain(MARCA_ERROR);
      await page.goto(ruta);
      await esperarHidratacion(page);
      await expect(page.getByTestId('pagina-glosario').locator('dl').first()).toBeVisible({ timeout: 15_000 });
      for (const ancla of anclas) {
        await expect(page.locator(`[id="${ancla}"]`)).toHaveCount(1);
      }
    }
  });

  test('AC_TKT019_05 ningún contenido retirado ni borrador aparece', async ({ page }) => {
    omitirSinStack();
    test.setTimeout(180_000);
    const sufijo = randomBytes(4).toString('hex');
    const retirado = { slug: `e2e-retirado-${sufijo}`, titulo: `E2E Retirado ${sufijo}` };
    const borrador = { slug: `e2e-borrador-${sufijo}`, titulo: `E2E Borrador ${sufijo}` };
    // Contenido real no publicado, creado con el ORM del backend (mismo patrón que crearCuenta).
    // Las filas retiradas no se pueden borrar (trg_contenido_guardas): sufijo aleatorio.
    const script = `
from django.utils import timezone
from apps.contenido.models import Contenido, TipoAventura
ahora = timezone.now()
r = Contenido.objects.create(tipo="TIPO", slug=${JSON.stringify(retirado.slug)}, titulo=${JSON.stringify(retirado.titulo)},
    estado_editorial="RETIRADO", primera_publicacion_en=ahora, publicado_actualizado_en=ahora,
    fecha_ultima_revision=ahora.date(), retirado_en=ahora, motivo_retiro="E2E TKT-019")
TipoAventura.objects.create(contenido=r)
b = Contenido.objects.create(tipo="TIPO", slug=${JSON.stringify(borrador.slug)}, titulo=${JSON.stringify(borrador.titulo)},
    estado_editorial="BORRADOR")
TipoAventura.objects.create(contenido=b)
print("E2E_OK")
`;
    const salida = execFileSync(
      'docker',
      ['compose', '-p', PROYECTO_COMPOSE, 'exec', '-T', 'backend', 'python', 'manage.py', 'shell'],
      { cwd: resolve(__dirname, '..', '..'), input: script, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] },
    );
    expect(salida).toContain('E2E_OK');

    try {
      const entradas = await todas<EntradaIndice>(page, '/api/v1/publico/indice');
      await abrirMapa(page);
      const html = await page.content();
      for (const c of [retirado, borrador]) {
        expect(html).not.toContain(c.slug);
        expect(html).not.toContain(c.titulo);
      }
      // Todo enlace a contenido del mapa pertenece a lo publicado según la API pública.
      const publicadas = new Set(entradas.map(rutaEsperada));
      const contenido = (await hrefs(page, 'mapa-enlace')).filter(
        (h) => !h.startsWith('/cuando-ir/') && !h.startsWith('/glosario') && h !== '/creditos',
      );
      expect(contenido.filter((h) => !publicadas.has(h))).toEqual([]);
    } finally {
      // El borrador (nunca publicado) sí se puede borrar; el retirado queda reservado (RULE-008).
      execFileSync(
        'docker',
        ['compose', '-p', PROYECTO_COMPOSE, 'exec', '-T', 'backend', 'python', 'manage.py', 'shell'],
        {
          cwd: resolve(__dirname, '..', '..'),
          input: `from apps.contenido.models import Contenido\nContenido.objects.filter(slug=${JSON.stringify(borrador.slug)}, estado_editorial="BORRADOR").delete()\n`,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'pipe'],
        },
      );
    }
  });

  test('AC_TKT019_06 es accesible (axe), estable (CLS) y alcanzable desde el pie del sitio', async ({
    page,
    browserName,
  }) => {
    await empezarMedicionCls(page);
    await abrirMapa(page);
    await sinViolacionesGraves(page);
    const cls = await leerCls(page);
    if (browserName === 'chromium') expect(cls).not.toBeNull();
    if (cls !== null) expect(cls).toBeLessThanOrEqual(0.1);

    await page.goto('/acerca-de');
    await esperarHidratacion(page);
    await page.getByRole('contentinfo').getByRole('link', { name: 'Mapa del sitio' }).click();
    await expect(page).toHaveURL(/\/mapa-del-sitio$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Mapa del sitio');
  });
});
