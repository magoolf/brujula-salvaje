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
 * El SSR reenvía la IP del cliente (X-Forwarded-For), así que el rastreo de AC_TKT019_04 consume
 * el mismo cupo «publico-lectura» del ejecutor de pruebas. Si el backend responde 429 al SSR, la
 * página sale con 200 y su estado de error (comportamiento correcto): se espera y se reintenta.
 */
const REINTENTOS_LIMITE = 8;
const ESPERA_LIMITE_MS = 10_000;

/** HTML del SSR del mapa con contenido (reintenta mientras el SSR muestre el estado de error). */
async function htmlSsrMapa(page: Page): Promise<string> {
  let html = '';
  for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
    const respuesta = await getConReintento(page, RUTA);
    expect(respuesta.status()).toBe(200);
    html = await respuesta.text();
    if (!html.includes('data-testid="estado-error"')) return html;
    await page.waitForTimeout(ESPERA_LIMITE_MS);
  }
  return html;
}

async function abrirMapa(page: Page): Promise<void> {
  for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
    const respuesta = await page.goto(RUTA);
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    const total = page.getByTestId('mapa-total');
    const error = page.getByTestId('estado-error');
    await expect(total.or(error).first()).toBeVisible({ timeout: 15_000 });
    if (await total.isVisible()) return;
    await page.waitForTimeout(ESPERA_LIMITE_MS);
  }
  await expect(page.getByTestId('mapa-total')).toBeVisible({ timeout: 15_000 });
}

test.describe('Mapa del sitio (SCR-022)', () => {
  // Margen para las esperas por límite de tasa (htmlSsrMapa / abrirMapa).
  test.describe.configure({ timeout: 180_000 });

  test('AC_TKT019_01 responde 200 con SSR, título, canónica y h1', async ({ page }) => {
    const html = await htmlSsrMapa(page);
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
    await indice.getByRole('link', { name: 'Glosario' }).click();
    await expect(page).toHaveURL(/#seccion-glosario$/);
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
    test.setTimeout(300_000);
    await abrirMapa(page);
    const todos = [...(await hrefs(page, 'mapa-enlace')), ...(await hrefs(page, 'mapa-enlace-seccion'))];
    const rutas = [...new Set(todos.map((h) => h.split('#')[0]))];
    expect(rutas.length).toBeGreaterThan(20);

    const rotas: string[] = [];
    for (const ruta of rutas) {
      const respuesta = await getConReintento(page, ruta);
      if (respuesta.status() !== 200) rotas.push(`${ruta} → ${respuesta.status()}`);
    }
    expect(rotas).toEqual([]);

    // Cada término enlazado existe como ancla en su página del glosario.
    const anclasPorPagina = new Map<string, string[]>();
    for (const href of todos.filter((h) => h.startsWith('/glosario') && h.includes('#'))) {
      const [ruta, ancla] = href.split('#');
      anclasPorPagina.set(ruta, [...(anclasPorPagina.get(ruta) ?? []), ancla]);
    }
    for (const [ruta, anclas] of anclasPorPagina) {
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
