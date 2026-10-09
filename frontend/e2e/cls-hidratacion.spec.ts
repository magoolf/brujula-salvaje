import { Page, expect, test } from '@playwright/test';

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
        if (previo && (previo.top !== r.top || previo.height !== r.height) && r.height > 0 && previo.height > 0) {
          const union = {
            top: Math.min(previo.top, r.top),
            bottom: Math.max(previo.bottom, r.bottom),
            left: Math.min(previo.left, r.left),
            right: Math.max(previo.right, r.right),
          };
          const impacto = areaVisible(union) / (innerWidth * innerHeight);
          const distancia = Math.min(Math.abs(r.top - previo.top), innerHeight) / Math.max(innerWidth, innerHeight);
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

async function medir(page: Page, ruta: string): Promise<Medicion> {
  await instrumentar(page);
  const respuesta = await page.goto(ruta);
  expect(respuesta?.status()).toBe(200);
  await esperarHidratacion(page);
  // La ventana del defecto eran los 300-420 ms posteriores a la hidratación (sin conexión rápida,
  // hasta ~850 ms en la ficha). Se deja 1,5 s y la red en reposo.
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1_500);
  return page.evaluate(() => {
    const e = (window as unknown as Ventana).__tkt016;
    return { cls: e.cls, pie: e.pie, retirados: e.retirados };
  });
}

interface Caso {
  id: string;
  nombre: string;
  ruta: (slugDestino: string) => string;
  /** Rutas cuyos stores están fuera de los archivos_permitidos de TKT-016 (Botón de Pánico). */
  pendiente?: string;
}

const PENDIENTE_INSTITUCIONAL =
  'TKT-016 Botón de Pánico parcial: el store de features/institucional/state (fuera de ' +
  'archivos_permitidos) necesita resource({ id }) como inicio/destinos; ver TKT-030.';

const CASOS: readonly Caso[] = [
  { id: 'AC_TKT016_01', nombre: 'Inicio', ruta: () => '/' },
  { id: 'AC_TKT016_02', nombre: 'Explorar destinos', ruta: () => '/destinos' },
  { id: 'AC_TKT016_03', nombre: 'Ficha de destino', ruta: (slug) => `/destinos/${slug}` },
  { id: 'AC_TKT016_04', nombre: 'Cuándo ir', ruta: () => '/cuando-ir' },
  { id: 'AC_TKT016_05', nombre: 'Créditos', ruta: () => '/creditos', pendiente: PENDIENTE_INSTITUCIONAL },
  { id: 'AC_TKT016_06', nombre: 'Acerca de', ruta: () => '/acerca-de', pendiente: PENDIENTE_INSTITUCIONAL },
];

test.describe('TKT-016 CLS tras la hidratación ≤ 0,1 (Skill_UI_UX §47.2)', () => {
  let slugDestino = '';

  test.beforeAll(async ({ request }) => {
    const respuesta = await request.get('/api/v1/publico/destinos');
    expect(respuesta.ok()).toBe(true);
    const cuerpo = (await respuesta.json()) as { resultados: { slug: string }[] };
    expect(cuerpo.resultados.length).toBeGreaterThan(0);
    slugDestino = cuerpo.resultados[0].slug;
  });

  for (const caso of CASOS) {
    test(`${caso.id} ${caso.nombre}: sin layout shift ni DOM del SSR recreado al hidratar`, async ({
      page,
    }) => {
      test.fixme(caso.pendiente !== undefined, caso.pendiente);
      const { cls, pie, retirados } = await medir(page, caso.ruta(slugDestino));
      test.info().annotations.push({
        type: 'medicion',
        description: `cls=${cls === null ? 'no soportado' : cls.toFixed(4)} pie=${pie.toFixed(4)}`,
      });
      if (cls !== null) expect(cls).toBeLessThanOrEqual(0.1);
      expect(pie).toBeLessThanOrEqual(0.1);
      expect(retirados).toEqual([]);
    });
  }
});
