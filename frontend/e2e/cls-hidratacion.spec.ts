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
  const red = { vio429: false };
  page.on('response', (r) => {
    if (r.url().includes('/api/') && r.status() === 429) red.vio429 = true;
  });
  for (let intento = 0; intento < REINTENTOS_LIMITE; intento++) {
    red.vio429 = false;
    const respuesta = await page.goto(ruta);
    expect(respuesta?.status()).toBe(200);
    await esperarHidratacion(page);
    // La ventana del defecto eran los 300-420 ms posteriores a la hidratación (sin conexión
    // rápida, hasta ~850 ms en la ficha). Se deja 1,5 s y la red en reposo.
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1_500);
    const medicion: Medicion = await page.evaluate(() => {
      const e = (window as unknown as Ventana).__tkt016;
      return { cls: e.cls, pie: e.pie, retirados: e.retirados };
    });
    const limiteEnPagina = TEXTO_LIMITE.test(await page.locator('main').innerText());
    if (!red.vio429 && !limiteEnPagina) return medicion;
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
}

const CASOS: readonly Caso[] = [
  { id: 'AC_TKT016_01', nombre: 'Inicio', ruta: () => '/' },
  { id: 'AC_TKT016_02', nombre: 'Explorar destinos', ruta: () => '/destinos' },
  {
    id: 'AC_TKT016_03',
    nombre: 'Ficha de destino',
    ruta: async (slug) => `/destinos/${await slug('destinos')}`,
  },
  { id: 'AC_TKT016_04', nombre: 'Cuándo ir', ruta: () => '/cuando-ir' },
  { id: 'AC_TKT016_07', nombre: 'Destinos del mes', ruta: () => '/cuando-ir/1' },
  { id: 'AC_TKT016_08', nombre: 'Mapa de destinos', ruta: () => '/destinos/mapa' },
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
  { id: 'AC_TKT016_24', nombre: 'Guardados', ruta: () => '/guardados' },
  {
    id: 'AC_TKT016_05',
    nombre: 'Créditos',
    ruta: () => '/creditos',
  },
  { id: 'AC_TKT016_06', nombre: 'Acerca de', ruta: () => '/acerca-de' },
  {
    id: 'AC_TKT016_18',
    nombre: 'Política de datos',
    ruta: () => '/politica-de-tratamiento-de-datos',
  },
  {
    id: 'AC_TKT016_19',
    nombre: 'Política de cookies',
    ruta: () => '/politica-de-cookies',
  },
  {
    id: 'AC_TKT016_20',
    nombre: 'Aviso legal',
    ruta: () => '/aviso-legal',
  },
  {
    id: 'AC_TKT016_21',
    nombre: 'Glosario',
    ruta: () => '/glosario',
  },
  {
    id: 'AC_TKT016_22',
    nombre: 'Búsqueda',
    ruta: () => '/buscar?q=volcan',
  },
  {
    id: 'AC_TKT016_25',
    nombre: 'Búsqueda por grupo',
    ruta: () => '/buscar?q=volcan&tipo=destinos',
  },
  {
    id: 'AC_TKT016_23',
    nombre: 'Categoría de guías',
    ruta: async (slug) => `/guias/categoria/${await slug('categorias-guia')}`,
  },
];

test.describe('TKT-016 CLS tras la hidratación ≤ 0,1 (Skill_UI_UX §47.2)', () => {
  for (const caso of CASOS) {
    test(`${caso.id} ${caso.nombre}: sin layout shift ni DOM del SSR recreado al hidratar`, async ({
      page,
    }) => {
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
      expect(retirados).toEqual([]);
    });
  }
});

/**
 * Las claves de TransferState incluyen los parámetros de la URL y Angular solo las consulta durante
 * la hidratación: tras ella, la navegación en el cliente (sin recargar la página) debe pedir y
 * pintar los datos de la nueva URL, nunca reutilizar los transferidos por el SSR de la anterior.
 */
test.describe('TKT-016 sin datos obsoletos al navegar en el cliente tras hidratar', () => {
  async function marcarDocumento(page: Page): Promise<void> {
    await page.evaluate(() => {
      (window as unknown as { __tkt016Doc: boolean }).__tkt016Doc = true;
    });
  }

  async function mismoDocumento(page: Page): Promise<boolean> {
    return page.evaluate(
      () => (window as unknown as { __tkt016Doc?: boolean }).__tkt016Doc === true,
    );
  }

  test('AC_TKT016_26 /buscar: una nueva consulta pide y pinta sus propios resultados', async ({
    page,
  }) => {
    await page.goto('/buscar?q=volcan');
    await esperarHidratacion(page);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('«volcan»');
    await marcarDocumento(page);

    const peticion = page.waitForResponse(
      (r) => r.url().includes('/api/v1/publico/busqueda') && r.url().includes('q=patagonia'),
    );
    const campo = page.getByTestId('busqueda-campo');
    await campo.getByTestId('campo-busqueda-entrada').fill('patagonia');
    await campo.getByTestId('campo-busqueda-enviar').click();
    const respuesta = await peticion;
    expect(respuesta.status()).toBe(200);
    const cuerpo = (await respuesta.json()) as { total: number };

    await expect(page).toHaveURL(/q=patagonia/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('«patagonia»');
    await expect(page.getByTestId('busqueda-total')).toContainText(String(cuerpo.total));
    expect(await mismoDocumento(page)).toBe(true);
  });

  test('AC_TKT016_27 ficha de destino: el enlace a otra ficha pinta la nueva, no la del SSR', async ({
    page,
  }) => {
    const listado = await getConReintento(page, '/api/v1/publico/destinos');
    const { resultados } = (await listado.json()) as { resultados: { slug: string }[] };
    const origen = resultados[0].slug;
    await page.goto(`/destinos/${origen}`);
    await esperarHidratacion(page);
    const tituloOrigen = await page.getByRole('heading', { level: 1 }).innerText();
    await marcarDocumento(page);

    const enlace = page
      .getByTestId('pagina-destino')
      .locator(
        `a[href^="/destinos/"]:not([href="/destinos/${origen}"]):not([href^="/destinos/mapa"])`,
      )
      .first();
    const destino = ((await enlace.getAttribute('href')) ?? '').replace('/destinos/', '');
    expect(destino).not.toBe('');
    const detalle = await getConReintento(page, `/api/v1/publico/destinos/${destino}`);
    const { titulo } = (await detalle.json()) as { titulo: string };
    expect(titulo).not.toBe(tituloOrigen);

    await enlace.click();
    await expect(page).toHaveURL(new RegExp(`/destinos/${destino}$`));
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(titulo);
    expect(await mismoDocumento(page)).toBe(true);
  });
});
