import AxeBuilder from '@axe-core/playwright';
import { Page, expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * TKT-049 (QA TKT-041 OBS-C2-04) — los rótulos de la navegación principal de la cabecera (GI-01)
 * no se parten entre 1024 y 1440 px, en chromium, firefox y webkit (proyectos de
 * playwright.config.ts).
 *
 * - ≥ xl (80rem = 1280 px): variante completa. Cada enlace ocupa UNA sola línea (las cajas de
 *   línea de su texto, `Range.getClientRects()`, comparten fila), su texto no se recorta, los
 *   enlaces no se solapan, el objetivo táctil sigue en size.target (44 px), el foco es visible y
 *   ni la fila de la cabecera ni la página desbordan en horizontal.
 * - < xl (1024 y 1279 px): variante compacta. La navegación en línea no se muestra y el menú
 *   móvil (cajón CDK Dialog) sigue abriéndose con la navegación completa.
 * - axe (WCAG 2.2 AA) sobre la cabecera: 0 violaciones serious/critical en cada anchura.
 */

const ALTO = 800;
const XL = 1280;
const ANCHURAS = [1024, 1279, 1280, 1366, 1440] as const;
const OBJETIVO_TACTIL = 44; // --bs-size-target (docs/03_diseno/tokens.json)
const IDS_NAVEGACION = [
  'nav-destinos',
  'nav-tipos-de-aventura',
  'nav-itinerarios',
  'nav-guias',
  'nav-colecciones',
  'nav-cuando-ir',
  'nav-guardados',
];

interface MedidaEnlace {
  id: string;
  texto: string;
  lineas: number;
  recortado: boolean;
  izquierda: number;
  derecha: number;
  ancho: number;
  alto: number;
}

/** Mide cada enlace de la navegación principal dentro de la página. */
async function medirEnlaces(page: Page): Promise<MedidaEnlace[]> {
  return page.evaluate((ids) => {
    return ids.map((id) => {
      const enlace = document.querySelector<HTMLElement>(`[data-testid="${id}"]`);
      if (!enlace) throw new Error(`No existe ${id}`);
      const rango = document.createRange();
      rango.selectNodeContents(enlace);
      // Una caja por fragmento de línea: si el texto se parte, aparecen cajas con otro «top».
      const filas = new Set<number>();
      for (const caja of Array.from(rango.getClientRects())) {
        if (caja.width > 0 && caja.height > 0) filas.add(Math.round(caja.top));
      }
      const caja = enlace.getBoundingClientRect();
      return {
        id,
        texto: (enlace.textContent ?? '').trim(),
        lineas: filas.size,
        recortado: enlace.scrollWidth > enlace.clientWidth + 1,
        izquierda: caja.left,
        derecha: caja.right,
        ancho: caja.width,
        alto: caja.height,
      };
    });
  }, IDS_NAVEGACION);
}

/** Sin desbordamiento horizontal de la página ni de la fila de la cabecera. */
async function expectSinDesbordamiento(page: Page): Promise<void> {
  const medida = await page.evaluate(() => {
    const raiz = document.documentElement;
    const cabecera = document.querySelector<HTMLElement>('[data-testid="cabecera-sitio"]');
    const fila = cabecera?.querySelector<HTMLElement>('.fila');
    const cajaFila = fila?.getBoundingClientRect();
    const hijos = fila
      ? Array.from(fila.children)
          .map((h) => h.getBoundingClientRect())
          .filter((c) => c.width > 0)
          .map((c) => ({ izquierda: c.left, derecha: c.right }))
      : [];
    return {
      pagina: raiz.scrollWidth - raiz.clientWidth,
      fila: fila ? fila.scrollWidth - fila.clientWidth : -1,
      filaIzquierda: cajaFila?.left ?? 0,
      filaDerecha: cajaFila?.right ?? 0,
      hijos,
      ancho: window.innerWidth,
    };
  });
  expect(medida.pagina, 'la página desborda en horizontal').toBeLessThanOrEqual(0);
  expect(medida.fila, 'la fila de la cabecera desborda').toBeLessThanOrEqual(0);
  expect(medida.filaDerecha).toBeLessThanOrEqual(medida.ancho);
  for (const hijo of medida.hijos) {
    expect(hijo.izquierda).toBeGreaterThanOrEqual(medida.filaIzquierda - 1);
    expect(hijo.derecha).toBeLessThanOrEqual(medida.filaDerecha + 1);
  }
}

async function axeCabecera(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .include('[data-testid="cabecera-sitio"]')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  const graves = resultado.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  );
  expect(
    graves.map(
      (v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`,
    ),
  ).toEqual([]);
}

test.describe('TKT-049 rótulos de la navegación principal (GI-01) entre 1024 y 1440 px', () => {
  for (const ancho of ANCHURAS) {
    if (ancho >= XL) {
      test(`TKT049 a ${ancho} px cada enlace ocupa una sola línea, sin recortes ni desbordamiento`, async ({
        page,
      }) => {
        await page.setViewportSize({ width: ancho, height: ALTO });
        await page.goto('/');
        await esperarHidratacion(page);
        await page.evaluate(() => document.fonts.ready);

        const navegacion = page
          .getByTestId('cabecera-sitio')
          .locator('nav[aria-label="Principal"]');
        await expect(navegacion).toBeVisible();
        await expect(page.getByTestId('cabecera-boton-menu')).toBeHidden();

        const medidas = await medirEnlaces(page);
        expect(medidas.map((m) => m.id)).toEqual(IDS_NAVEGACION);
        for (const m of medidas) {
          expect(m.texto.length, `${m.id} sin texto`).toBeGreaterThan(0);
          expect(m.lineas, `«${m.texto}» se parte en ${m.lineas} líneas`).toBe(1);
          expect(m.recortado, `«${m.texto}» queda recortado`).toBe(false);
          expect(m.alto, `${m.id} por debajo del objetivo táctil`).toBeGreaterThanOrEqual(
            OBJETIVO_TACTIL,
          );
          expect(m.ancho).toBeGreaterThanOrEqual(24);
        }
        for (let i = 1; i < medidas.length; i++) {
          expect(
            medidas[i].izquierda,
            `${medidas[i].id} se solapa con ${medidas[i - 1].id}`,
          ).toBeGreaterThanOrEqual(medidas[i - 1].derecha);
        }

        await expectSinDesbordamiento(page);
        await expect(page.getByTestId('cabecera-busqueda')).toBeVisible();

        // El foco por teclado sigue siendo visible (anillo de foco global del design system).
        await page.keyboard.press('Shift');
        await page.getByTestId('nav-tipos-de-aventura').focus();
        const contorno = await page.getByTestId('nav-tipos-de-aventura').evaluate((el) => {
          const estilo = getComputedStyle(el);
          return { estilo: estilo.outlineStyle, grosor: parseFloat(estilo.outlineWidth) };
        });
        expect(contorno.estilo).not.toBe('none');
        expect(contorno.grosor).toBeGreaterThan(0);

        await axeCabecera(page);
      });
    } else {
      test(`TKT049 a ${ancho} px (< xl) la navegación va en el menú móvil, sin desbordamiento`, async ({
        page,
      }) => {
        await page.setViewportSize({ width: ancho, height: ALTO });
        await page.goto('/');
        await esperarHidratacion(page);

        await expect(
          page.getByTestId('cabecera-sitio').locator('nav[aria-label="Principal"]'),
        ).toBeHidden();
        const botonMenu = page.getByTestId('cabecera-boton-menu');
        await expect(botonMenu).toBeVisible();
        const caja = await botonMenu.boundingBox();
        expect(caja?.width ?? 0).toBeGreaterThanOrEqual(OBJETIVO_TACTIL);
        expect(caja?.height ?? 0).toBeGreaterThanOrEqual(OBJETIVO_TACTIL);
        await expectSinDesbordamiento(page);
        await axeCabecera(page);

        await botonMenu.click();
        const dialogo = page.getByRole('dialog');
        await expect(dialogo).toBeVisible();
        for (const etiqueta of [
          'Destinos',
          'Tipos de aventura',
          'Itinerarios',
          'Guías',
          'Colecciones',
          'Cuándo ir',
          'Guardados',
        ]) {
          await expect(dialogo.getByRole('link', { name: etiqueta, exact: true })).toBeVisible();
        }
        await page.keyboard.press('Escape');
        await expect(dialogo).toBeHidden();
        await expect(botonMenu).toBeFocused();
      });
    }
  }
});
