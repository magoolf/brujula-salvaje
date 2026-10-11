import { APIResponse, Page, expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * TKT-030 (QA TKT-020 F-QA020-04) — la hidratación reutiliza las imágenes que pintó el SSR.
 *
 * Defecto original: tras hidratar, el cliente retiraba y volvía a crear los subárboles del SSR con
 * imágenes (/destinos 24 IMG en DIV.resultados, ficha 13, itinerario 7, Inicio 24+1). Causa raíz:
 * los `resource()` de las páginas nacían sin valor en el primer render del cliente aunque el SSR ya
 * hubiera pintado los datos; la hidratación elegía la rama «cargando» del `@if`, retiraba el DOM del
 * servidor y, al llegar la respuesta repetida de la API, lo volvía a crear. TKT-016 lo corrigió con
 * `resource({ id })` (el valor viaja en TransferState). Esta prueba lo fija con una señal más
 * estricta que cls-hidratacion.spec.ts (que no cuenta las retiradas bajo
 * `app-imagen-responsiva > .marco` ni las reasignaciones con HTML idéntico): la IDENTIDAD de cada
 * nodo `<img>`.
 *
 * Medición independiente del momento de la hidratación (TKT-056 la retrasa hasta el FCP): un
 * MutationObserver instalado antes de que el documento empiece a analizarse (addInitScript) registra
 * en un WeakSet cada `<img>` insertado, también los que inserta el analizador del HTML del SSR. Si
 * la hidratación recreara una imagen, el total de imágenes insertadas superaría al de imágenes
 * presentes al final y aparecerían nodos `<img>` retirados.
 *
 * Solo Chromium (decisión humana: las E2E de rendimiento e hidratación se ejecutan en Chromium).
 */

interface Ventana {
  __tkt030: { insertadas: number; retiradas: string[]; vistas: WeakSet<Element> };
}

interface Medicion {
  insertadas: number;
  retiradas: string[];
  finales: number;
  originalesConectadas: number;
  api: string[];
  consola: string[];
}

async function instrumentar(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const estado: Ventana['__tkt030'] = { insertadas: 0, retiradas: [], vistas: new WeakSet() };
    (window as unknown as Ventana).__tkt030 = estado;
    const imagenesDe = (nodo: Node): Element[] => {
      if (nodo.nodeType !== Node.ELEMENT_NODE) return [];
      const el = nodo as Element;
      return [...(el.tagName === 'IMG' ? [el] : []), ...Array.from(el.querySelectorAll('img'))];
    };
    new MutationObserver((registros) => {
      for (const registro of registros) {
        for (const nodo of Array.from(registro.addedNodes)) {
          for (const img of imagenesDe(nodo)) {
            if (!estado.vistas.has(img)) {
              estado.vistas.add(img);
              estado.insertadas++;
            }
          }
        }
        for (const nodo of Array.from(registro.removedNodes)) {
          for (const img of imagenesDe(nodo)) {
            const padre = registro.target as Element;
            estado.retiradas.push(
              `${padre.tagName.toLowerCase()}.${padre.className} > img[src=${img.getAttribute('src') ?? ''}]`,
            );
          }
        }
      }
    }).observe(document, { childList: true, subtree: true });
  });
}

const REINTENTOS_LIMITE = 4;

/** GET que respeta el limitador real (429 + Retry-After) del entorno compartido. */
async function getConReintento(page: Page, url: string): Promise<APIResponse> {
  for (let intento = 0; intento < 8; intento++) {
    const respuesta = await page.request.get(url);
    if (respuesta.status() !== 429) return respuesta;
    const espera = Number(respuesta.headers()['retry-after'] ?? '1');
    await page.waitForTimeout(Math.min(Math.max(espera, 1), 10) * 1000);
  }
  throw new Error(`Límite de tasa persistente en ${url}`);
}

async function primerSlug(page: Page, listado: string): Promise<string> {
  const respuesta = await getConReintento(page, `/api/v1/publico/${listado}`);
  expect(respuesta.ok()).toBe(true);
  const cuerpo = (await respuesta.json()) as { resultados: { slug: string }[] };
  expect(cuerpo.resultados.length).toBeGreaterThan(0);
  return cuerpo.resultados[0].slug;
}

/** Carga completa de `ruta`; se repite solo si la carga vio un 429 real (no es la hidratación normal). */
async function medir(page: Page, ruta: string): Promise<Medicion> {
  await instrumentar(page);
  const registro = { vio429: false, api: [] as string[], consola: [] as string[] };
  page.on('request', (r) => {
    const { pathname, search } = new URL(r.url());
    if (pathname.startsWith('/api/')) registro.api.push(`${r.method()} ${pathname}${search}`);
  });
  page.on('response', (r) => {
    if (r.url().includes('/api/') && r.status() === 429) registro.vio429 = true;
  });
  page.on('console', (m) => {
    if (/NG0\d{3}/.test(m.text())) registro.consola.push(m.text().slice(0, 300));
  });
  for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
    registro.vio429 = false;
    registro.api = [];
    registro.consola = [];
    const respuesta = await page.goto(ruta);
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_000);
    const dom = await page.evaluate(() => {
      const estado = (window as unknown as Ventana).__tkt030;
      const finales = Array.from(document.querySelectorAll('img'));
      return {
        insertadas: estado.insertadas,
        retiradas: estado.retiradas,
        finales: finales.length,
        originalesConectadas: finales.filter((img) => estado.vistas.has(img)).length,
      };
    });
    if (!registro.vio429) {
      return { ...dom, api: [...registro.api], consola: [...registro.consola] };
    }
    await page.waitForTimeout(3_000);
  }
  throw new Error(`Límite de tasa persistente al medir ${ruta}`);
}

interface Caso {
  id: string;
  nombre: string;
  ruta: (page: Page) => Promise<string>;
  /** Solo medición (anotación), sin aserción: Inicio pertenece a otro ticket (TKT-047). */
  soloMedicion?: boolean;
}

const CASOS: readonly Caso[] = [
  { id: 'AC_TKT030_01', nombre: 'Explorar destinos', ruta: async () => '/destinos' },
  {
    id: 'AC_TKT030_02',
    nombre: 'Ficha de destino',
    ruta: async (page) => `/destinos/${await primerSlug(page, 'destinos')}`,
  },
  {
    id: 'AC_TKT030_03',
    nombre: 'Ficha de itinerario',
    ruta: async (page) => `/itinerarios/${await primerSlug(page, 'itinerarios')}`,
  },
  { id: 'AC_TKT030_04', nombre: 'Itinerarios', ruta: async () => '/itinerarios' },
  {
    id: 'AC_TKT030_05',
    nombre: 'Ficha de tipo de aventura',
    ruta: async (page) => `/tipos-de-aventura/${await primerSlug(page, 'tipos-aventura')}`,
  },
  {
    id: 'AC_TKT030_06',
    nombre: 'Guía',
    ruta: async (page) => `/guias/${await primerSlug(page, 'guias')}`,
  },
  {
    id: 'AC_TKT030_07',
    nombre: 'Colección',
    ruta: async (page) => `/colecciones/${await primerSlug(page, 'colecciones')}`,
  },
  { id: 'AC_TKT030_08', nombre: 'Inicio (medición)', ruta: async () => '/', soloMedicion: true },
];

test.describe('TKT-030 la hidratación reutiliza las imágenes del SSR', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'Solo Chromium (decisión humana)');

  for (const caso of CASOS) {
    test(`${caso.id} ${caso.nombre}: ningún <img> del SSR se retira ni se recrea, sin repetir la API ni errores NG0`, async ({
      page,
    }) => {
      const m = await medir(page, await caso.ruta(page));
      test.info().annotations.push({
        type: 'medicion',
        description: `img finales=${m.finales} insertadas=${m.insertadas} originalesConectadas=${m.originalesConectadas} retiradas=${m.retiradas.length} api=${m.api.length} ng0=${m.consola.length}`,
      });
      if (caso.soloMedicion) return;
      expect(m.finales).toBeGreaterThan(0);
      expect(m.retiradas).toEqual([]);
      expect(m.insertadas).toBe(m.finales);
      expect(m.originalesConectadas).toBe(m.finales);
      expect(m.api).toEqual([]);
      expect(m.consola).toEqual([]);
    });
  }

  test('AC_TKT030_09 /destinos tras hidratar: ordenar y filtrar siguen pidiendo y pintando datos nuevos', async ({
    page,
  }) => {
    await page.goto('/destinos');
    await esperarHidratacion(page);
    await page.evaluate(() => {
      (window as unknown as { __tkt030Doc: boolean }).__tkt030Doc = true;
    });
    const rejilla = page.getByTestId('destinos-rejilla');
    const titulos = () => rejilla.getByRole('heading').allInnerTexts();
    const antes = await titulos();

    // Ordenar por dificultad: la API se vuelve a pedir con el nuevo orden.
    const porOrden = page.waitForResponse(
      (r) => r.url().includes('/api/v1/publico/destinos?') && r.url().includes('orden=dificultad_desc'),
    );
    await page.getByTestId('orden-dificultad_desc').click();
    expect((await porOrden).status()).toBe(200);
    await expect(page).toHaveURL(/orden=dificultad_desc/);
    await expect.poll(titulos).not.toEqual(antes);

    // Filtrar por región: la API se vuelve a pedir y el recuento coincide con su respuesta.
    const region = page.getByRole('group', { name: 'Región' }).getByRole('link').first();
    const porRegion = page.waitForResponse(
      (r) => r.url().includes('/api/v1/publico/destinos?') && r.url().includes('region='),
    );
    await region.click();
    const respuesta = await porRegion;
    expect(respuesta.status()).toBe(200);
    const { total } = (await respuesta.json()) as { total: number };
    await expect(page).toHaveURL(/region=/);
    await expect(page.getByTestId('destinos-recuento')).toContainText(String(total));
    await expect(rejilla.getByTestId('tarjeta-destino')).toHaveCount(Math.min(total, 24));

    // Navegación en el cliente (sin recargar el documento).
    expect(
      await page.evaluate(() => (window as unknown as { __tkt030Doc?: boolean }).__tkt030Doc === true),
    ).toBe(true);
  });
});
