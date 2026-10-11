import { Page, expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * TKT-021 (REQ-052, LCP ≤ 2,5 s en los listados). Causa raíz medida con Lighthouse móvil
 * (devtools, Slow 4G, CPU x4): el elemento LCP de los listados es la imagen de la PRIMERA tarjeta,
 * decorativa (`alt=""`), que `app-imagen-responsiva` retiene hasta hidratar y confirmar con su
 * IntersectionObserver (TKT-018), así que el SSR la entregaba sin `src` y la petición salía ~4,5 s
 * tarde ("load delay"). La primera imagen visible de cada listado se marca prioritaria (eager +
 * fetchpriority=high, con `src`/`srcset`/`sizes` ya en el HTML del servidor); el resto de la rejilla
 * sigue diferida, sin la ráfaga de peticiones que motivó TKT-018.
 *
 * Requiere la semilla (`manage.py cargar_semilla` + `regenerar_derivados`).
 */
interface CasoListado {
  readonly ruta: string;
  /** Imágenes prioritarias esperadas (primera fila visible en móvil). */
  readonly prioritarias: number;
  /** En móvil (412 px) la primera imagen queda por encima del pliegue. */
  readonly visibleEnMovil: boolean;
  /**
   * `fetchpriority=high` (LCP también en móvil) o solo carga inmediata (`cargaInmediata`: en móvil
   * queda bajo el pliegue y no debe competir con fuentes y CSS; el navegador la prioriza si se ve).
   */
  readonly altaPrioridad: boolean;
}

const LISTADOS: readonly CasoListado[] = [
  // En móvil los filtros van antes que la rejilla: el LCP es el h1; en escritorio, la 1.ª tarjeta.
  { ruta: '/destinos', prioritarias: 1, visibleEnMovil: false, altaPrioridad: false },
  { ruta: '/guias', prioritarias: 1, visibleEnMovil: true, altaPrioridad: true },
  { ruta: '/itinerarios', prioritarias: 1, visibleEnMovil: true, altaPrioridad: true },
  // Rejilla de meses: 2 columnas en móvil.
  { ruta: '/cuando-ir', prioritarias: 2, visibleEnMovil: true, altaPrioridad: true },
  { ruta: '/cuando-ir/7', prioritarias: 1, visibleEnMovil: true, altaPrioridad: true },
];

interface AtributosImagen {
  readonly loading: string | null;
  readonly fetchpriority: string | null;
  readonly src: string | null;
  readonly srcset: string | null;
  readonly sizes: string | null;
}

/** Atributos de las `<img>` de las imágenes responsivas, en orden de documento. */
function leerImagenes(page: Page): Promise<AtributosImagen[]> {
  return page.locator('app-imagen-responsiva img').evaluateAll((imgs) =>
    imgs.map((img) => ({
      loading: img.getAttribute('loading'),
      fetchpriority: img.getAttribute('fetchpriority'),
      src: img.getAttribute('src'),
      srcset: img.getAttribute('srcset'),
      sizes: img.getAttribute('sizes'),
    })),
  );
}

test.describe('TKT-021 imagen LCP de los listados', () => {
  test.describe('HTML del servidor (sin JavaScript)', () => {
    test.use({ javaScriptEnabled: false });

    for (const caso of LISTADOS) {
      test(`AC_TKT021_01 ${caso.ruta}: la primera imagen llega del SSR (eager) y el resto sigue diferido`, async ({
        page,
      }) => {
        const respuesta = await page.goto(caso.ruta);
        expect(respuesta?.status()).toBe(200);
        const imagenes = await leerImagenes(page);
        expect(imagenes.length).toBeGreaterThan(caso.prioritarias);

        const prioritarias = imagenes.slice(0, caso.prioritarias);
        for (const img of prioritarias) {
          expect(img.loading).toBe('eager');
          expect(img.fetchpriority).toBe(caso.altaPrioridad ? 'high' : null);
          expect(img.src).toMatch(/^\/media\/publico\//);
          expect(img.srcset).toMatch(/ \d+w/);
          expect(img.sizes).not.toBeNull();
        }

        // TKT-018: las demás tarjetas no emiten red en el SSR (ni prioridad alta).
        for (const img of imagenes.slice(caso.prioritarias)) {
          expect(img.fetchpriority).toBeNull();
          expect(img.loading).toBe('lazy');
          expect(img.src).toBeNull();
        }
      });
    }
  });

  test.describe('móvil (412 px, DPR 1,75, perfil de Lighthouse)', () => {
    test.use({ viewport: { width: 412, height: 823 }, deviceScaleFactor: 1.75 });

    for (const caso of LISTADOS.filter((c) => c.visibleEnMovil)) {
      test(`AC_TKT021_02 ${caso.ruta}: la imagen priorizada está en el primer viewport y pide un derivado acorde a su ancho`, async ({
        page,
      }) => {
        await page.goto(caso.ruta);
        await esperarHidratacion(page);
        const imagen = page.locator('app-imagen-responsiva img[fetchpriority="high"]').first();
        await expect
          .poll(() => imagen.evaluate((i: HTMLImageElement) => i.complete && i.currentSrc !== ''))
          .toBe(true);
        const caja = await imagen.evaluate((i: HTMLImageElement) => {
          const r = i.getBoundingClientRect();
          return { top: r.top, ancho: r.width };
        });
        expect(caja.top).toBeLessThan(823);
        // `sizes` correcto: el derivado elegido no supera el doble de lo necesario (ancho x DPR).
        const anchoDerivado = await imagen.evaluate((i: HTMLImageElement) => {
          const m = /-(\d+)-[0-9a-f]+\.[a-z]+$/.exec(i.currentSrc);
          return m ? Number(m[1]) : i.naturalWidth;
        });
        expect(anchoDerivado).toBeLessThanOrEqual(Math.max(400, caja.ancho * 1.75 * 2));
      });
    }
  });
});
