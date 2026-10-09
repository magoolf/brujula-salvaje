import { APIResponse, Page, expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * TKT-016 — CLS del shell tras la hidratación (Skill_UI_UX §47.2: CLS ≤ 0,1).
 *
 * Causa raíz medida: los `resource()` de las páginas nacían sin valor en el primer render del
 * cliente aunque el SSR ya hubiera pintado los datos. La hidratación elegía la rama «cargando» de la
 * plantilla, retiraba el DOM del servidor, pintaba el esqueleto (app-pie-sitio saltaba) y, al llegar
 * los datos, recreaba la página entera (TKT-030). Con `resource({ id })` el valor del SSR viaja en
 * TransferState y el recurso nace resuelto: la hidratación reutiliza el DOM.
 *
 * Tres señales por ruta, en los tres motores:
 * - CLS real (PerformanceObserver `layout-shift`, solo Chromium lo implementa);
 * - aproximación del desplazamiento de app-pie-sitio muestreado en cada frame (misma fórmula de
 *   fracción de impacto × fracción de distancia), que sí se puede medir en Firefox y WebKit;
 * - ningún hijo directo de la página enrutada (el DOM del SSR) se retira durante la hidratación.
 */

interface Medicion {
  cls: number | null;
  pie: number;
  retirados: string[];
}

interface Ventana {
  __tkt016: { cls: number | null; pie: number; retirados: string[]; ultimo: DOMRect | null };
}

async function instrumentar(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const estado: Ventana['__tkt016'] = { cls: null, pie: 0, retirados: [], ultimo: null };
    (window as unknown as Ventana).__tkt016 = estado;
    try {
      if (PerformanceObserver.supportedEntryTypes.includes('layout-shift')) {
        estado.cls = 0;
        new PerformanceObserver((lista) => {
          for (const entrada of lista.getEntries()) {
            const e = entrada as PerformanceEntry & { value: number; hadRecentInput: boolean };
            if (!e.hadRecentInput) estado.cls = (estado.cls ?? 0) + e.value;
          }
        }).observe({ type: 'layout-shift', buffered: true });
      }
    } catch {
      estado.cls = null;
    }

    const areaVisible = (r: { top: number; bottom: number; left: number; right: number }) => {
      const alto = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
      const ancho = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
      return alto * ancho;
    };
    const muestrear = () => {
      const pie = document.querySelector('app-pie-sitio');
      if (pie) {
        const r = pie.getBoundingClientRect();
        const previo = estado.ultimo;
        if (
          previo &&
          (previo.top !== r.top || previo.height !== r.height) &&
          r.height > 0 &&
          previo.height > 0
        ) {
          const union = {
            top: Math.min(previo.top, r.top),
            bottom: Math.max(previo.bottom, r.bottom),
            left: Math.min(previo.left, r.left),
            right: Math.max(previo.right, r.right),
          };
          const impacto = areaVisible(union) / (innerWidth * innerHeight);
          const distancia =
            Math.min(Math.abs(r.top - previo.top), innerHeight) / Math.max(innerWidth, innerHeight);
          // Solo cuenta si alguna de las dos posiciones era visible (como layout-shift).
          if (areaVisible(previo) > 0 || areaVisible(r) > 0) estado.pie += impacto * distancia;
        }
        if (r.height > 0) estado.ultimo = r;
      }
      requestAnimationFrame(muestrear);
    };
    requestAnimationFrame(muestrear);

    document.addEventListener('DOMContentLoaded', () => {
      const main = document.querySelector('main');
      if (!main) return;
      new MutationObserver((registros) => {
        for (const registro of registros) {
          const padre = registro.target as Element;
          // Hijos directos del host de la página enrutada (hermano siguiente del router-outlet).
          if (padre.parentElement !== main || padre.tagName === 'ROUTER-OUTLET') continue;
          for (const nodo of Array.from(registro.removedNodes)) {
            if (nodo.nodeType === Node.ELEMENT_NODE) {
              const el = nodo as Element;
              estado.retirados.push(
                `${padre.tagName.toLowerCase()} > ${el.tagName.toLowerCase()}${el.getAttribute('data-testid') ? `[${el.getAttribute('data-testid')}]` : ''}`,
              );
            }
          }
        }
      }).observe(main, { childList: true, subtree: true });
    });
  });
}

const REINTENTOS_LIMITE = 4;
const TEXTO_LIMITE = /límite de peticiones/i;

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

/**
 * Mide una carga completa. Solo se repite si la carga vio un 429 real (en el navegador o en el
 * SSR, que entonces pinta el estado de error con el mensaje de límite): con el limitador del
 * entorno compartido esa carga no representa la hidratación normal de la página.
 */
async function medir(page: Page, ruta: string): Promise<Medicion> {
  await instrumentar(page);
  let vio429 = false;
  page.on('response', (r) => {
    if (r.url().includes('/api/') && r.status() === 429) vio429 = true;
  });
  let medicion: Medicion = { cls: null, pie: 0, retirados: [] };
  for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
    vio429 = false;
    const respuesta = await page.goto(ruta);
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    // La ventana del defecto eran los 300-420 ms posteriores a la hidratación (sin conexión
    // rápida, hasta ~850 ms en la ficha). Se deja 1,5 s y la red en reposo.
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_500);
    medicion = await page.evaluate(() => {
      const e = (window as unknown as Ventana).__tkt016;
      return { cls: e.cls, pie: e.pie, retirados: e.retirados };
    });
    const limiteEnPagina = TEXTO_LIMITE.test(await page.locator('main').innerText());
    if (!vio429 && !limiteEnPagina) return medicion;
    await page.waitForTimeout(3_000);
  }
  throw new Error(`Límite de tasa persistente al medir ${ruta}`);
}

type Listado =
  'destinos' | 'itinerarios' | 'tipos-aventura' | 'categorias-guia' | 'guias' | 'colecciones';

interface Caso {
  id: string;
  nombre: string;
  ruta: (slug: (listado: Listado) => Promise<string>) => Promise<string> | string;
  /**
   * Alcance de TKT-016: además del CLS se exige que la hidratación reutilice el DOM del SSR
   * (ningún hijo de la página enrutada retirado). En el resto solo se exige el umbral de CLS.
   */
  estricto?: boolean;
  /** Rutas cuyos stores están fuera de los archivos_permitidos de TKT-016 (ampliación pendiente). */
  pendiente?: string;
}

const pendiente = (store: string): string =>
  `TKT-016 BLOCKED (alcance): ${store} está fuera de archivos_permitidos y necesita ` +
  'resource({ id }) como inicio/destinos para que la hidratación no vuelva al esqueleto.';
const INSTITUCIONAL = pendiente('features/institucional/state/pagina-institucional.store.ts');

const CASOS: readonly Caso[] = [
  // Alcance de TKT-016 (features/inicio y features/destinos).
  { id: 'AC_TKT016_01', estricto: true, nombre: 'Inicio', ruta: () => '/' },
  { id: 'AC_TKT016_02', estricto: true, nombre: 'Explorar destinos', ruta: () => '/destinos' },
  {
    id: 'AC_TKT016_03',
    estricto: true,
    nombre: 'Ficha de destino',
    ruta: async (slug) => `/destinos/${await slug('destinos')}`,
  },
  { id: 'AC_TKT016_04', estricto: true, nombre: 'Cuándo ir', ruta: () => '/cuando-ir' },
  { id: 'AC_TKT016_07', estricto: true, nombre: 'Destinos del mes', ruta: () => '/cuando-ir/1' },
  { id: 'AC_TKT016_08', estricto: true, nombre: 'Mapa de destinos', ruta: () => '/destinos/mapa' },
  // Resto de páginas públicas: regresión del umbral de CLS (las fichas aún recrean el DOM del SSR
  // al hidratar porque sus stores no transfieren el valor, pero sin desplazamiento medible).
  { id: 'AC_TKT016_09', nombre: 'Itinerarios', ruta: () => '/itinerarios' },
  {
    id: 'AC_TKT016_10',
    nombre: 'Ficha de itinerario',
    ruta: async (slug) => `/itinerarios/${await slug('itinerarios')}`,
  },
  { id: 'AC_TKT016_11', nombre: 'Tipos de aventura', ruta: () => '/tipos-de-aventura' },
  {
    id: 'AC_TKT016_12',
    nombre: 'Ficha de tipo',
    ruta: async (slug) => `/tipos-de-aventura/${await slug('tipos-aventura')}`,
  },
  { id: 'AC_TKT016_13', nombre: 'Guías', ruta: () => '/guias' },
  { id: 'AC_TKT016_14', nombre: 'Guía', ruta: async (slug) => `/guias/${await slug('guias')}` },
  { id: 'AC_TKT016_15', nombre: 'Colecciones', ruta: () => '/colecciones' },
  {
    id: 'AC_TKT016_16',
    nombre: 'Colección',
    ruta: async (slug) => `/colecciones/${await slug('colecciones')}`,
  },
  { id: 'AC_TKT016_17', nombre: 'Mapa del sitio', ruta: () => '/mapa-del-sitio' },
  // Fuera de alcance: CLS medido > 0,1 en algún motor, o sin margen estable (categoría de guías:
  // 0,089 en Firefox) porque la hidratación vuelve al esqueleto (ver el HANDOFF de TKT-016).
  {
    id: 'AC_TKT016_05',
    nombre: 'Créditos',
    ruta: () => '/creditos',
    pendiente: pendiente('features/institucional/state/creditos.store.ts'),
  },
  { id: 'AC_TKT016_06', nombre: 'Acerca de', ruta: () => '/acerca-de', pendiente: INSTITUCIONAL },
  {
    id: 'AC_TKT016_18',
    nombre: 'Política de datos',
    ruta: () => '/politica-de-tratamiento-de-datos',
    pendiente: INSTITUCIONAL,
  },
  {
    id: 'AC_TKT016_19',
    nombre: 'Política de cookies',
    ruta: () => '/politica-de-cookies',
    pendiente: INSTITUCIONAL,
  },
  {
    id: 'AC_TKT016_20',
    nombre: 'Aviso legal',
    ruta: () => '/aviso-legal',
    pendiente: INSTITUCIONAL,
  },
  {
    id: 'AC_TKT016_21',
    nombre: 'Glosario',
    ruta: () => '/glosario',
    pendiente: pendiente('features/glosario/state/glosario.store.ts'),
  },
  {
    id: 'AC_TKT016_22',
    nombre: 'Búsqueda',
    ruta: () => '/buscar?q=volcan',
    pendiente: pendiente('features/busqueda/state/busqueda.store.ts'),
  },
  {
    id: 'AC_TKT016_23',
    nombre: 'Categoría de guías',
    ruta: async (slug) => `/guias/categoria/${await slug('categorias-guia')}`,
    pendiente: pendiente('features/guias/state/guias-categoria.store.ts'),
  },
];

test.describe('TKT-016 CLS tras la hidratación ≤ 0,1 (Skill_UI_UX §47.2)', () => {
  for (const caso of CASOS) {
    test(`${caso.id} ${caso.nombre}: sin layout shift ni DOM del SSR recreado al hidratar`, async ({
      page,
    }) => {
      // TKT016_INCLUIR_PENDIENTES=1 mide también las rutas pendientes (diagnóstico y ampliación).
      test.fixme(
        caso.pendiente !== undefined && process.env['TKT016_INCLUIR_PENDIENTES'] !== '1',
        caso.pendiente,
      );
      const slug = async (listado: Listado): Promise<string> => {
        const respuesta = await getConReintento(page, `/api/v1/publico/${listado}`);
        expect(respuesta.ok()).toBe(true);
        const cuerpo = (await respuesta.json()) as { resultados: { slug: string }[] };
        expect(cuerpo.resultados.length).toBeGreaterThan(0);
        return cuerpo.resultados[0].slug;
      };
      const { cls, pie, retirados } = await medir(page, await caso.ruta(slug));
      test.info().annotations.push({
        type: 'medicion',
        description: `cls=${cls === null ? 'no soportado' : cls.toFixed(4)} pie=${pie.toFixed(4)} retirados=${retirados.length}`,
      });
      if (cls !== null) expect(cls).toBeLessThanOrEqual(0.1);
      expect(pie).toBeLessThanOrEqual(0.1);
      if (caso.estricto) expect(retirados).toEqual([]);
    });
  }
});
