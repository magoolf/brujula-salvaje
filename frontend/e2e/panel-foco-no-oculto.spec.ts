/**
 * E2E TKT-070 (WCAG 2.4.11 Foco no oculto, origen QA TKT-042 OBS-QA042-01): en el editor del panel,
 * ni la barra superior sticky (HEADER.barra) ni la StatusBar sticky del editor tapan el destino de un
 * ancla ni el control enfocado al tabular.
 *
 * «Visible» se comprueba como lo ve el usuario: `elementFromPoint` en el centro y en las esquinas
 * (con margen por el radio del borde) del control enfocado devuelve el propio control o un
 * descendiente, nunca la barra. Solo Chromium (decisión humana). Requiere E2E_BASE_URL y
 * E2E_COMPOSE_PROJECT (ver panel-soporte.ts).
 */
import { Page, expect, test } from '@playwright/test';

import { crearBorrador, sufijo } from './panel-contenidos-soporte';
import { entrarComoEditorCompartido, irA, omitirSinStack } from './panel-soporte';
import { empezarMedicionCls, leerCls, sinViolacionesGraves } from './utilidades';

test.beforeEach(({ browserName }) => {
  omitirSinStack();
  test.skip(browserName !== 'chromium', 'TKT-070: E2E solo en Chromium (decisión humana).');
  test.setTimeout(240_000);
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});

const VIEWPORTS = [
  { nombre: 'móvil 375', ancho: 375, alto: 812 },
  { nombre: 'escritorio 1280', ancho: 1280, alto: 800 },
] as const;

const TIPOS = [
  { ruta: 'destinos', etiqueta: 'destino' },
  { ruta: 'guias', etiqueta: 'guía' },
] as const;

/** Máximo de pulsaciones de Tab por recorrido del formulario. */
const MAX_TABS = 140;

interface Comprobacion {
  readonly visible: boolean;
  readonly descripcion: string;
}

/**
 * Espera a que el desplazamiento se asiente: el Router desplaza al ancla tras un setTimeout/rAF y
 * FocoRuta tras el siguiente render; se espera a que `scrollY` no cambie durante varios fotogramas.
 */
async function esperarQuietud(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const fotograma = (): Promise<void> => new Promise((r) => requestAnimationFrame(() => r()));
    await new Promise((r) => setTimeout(r, 150));
    let ultimo = scrollY;
    let estables = 0;
    for (let i = 0; i < 120 && estables < 6; i++) {
      await fotograma();
      if (scrollY === ultimo) estables++;
      else {
        estables = 0;
        ultimo = scrollY;
      }
    }
  });
}

/** ¿El elemento con foco se ve (centro y esquinas) o lo tapa otro (la barra)? */
async function focoVisible(page: Page): Promise<Comprobacion> {
  return page.evaluate(() => {
    const activo = document.activeElement as HTMLElement | null;
    if (activo === null || activo === document.body) return { visible: true, descripcion: 'sin foco' };
    const describir = (e: Element | null): string =>
      e === null
        ? 'null'
        : `${e.tagName}${e.id ? '#' + e.id : ''}${(e as HTMLElement).dataset?.['testid'] ? '[' + (e as HTMLElement).dataset['testid'] + ']' : ''}${typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : ''}`;
    // Controles visualmente ocultos (p. ej. checkbox nativo bajo uno personalizado): se mide el
    // primer antecesor con tamaño real.
    let medido: HTMLElement = activo;
    while (medido.parentElement !== null) {
      const r = medido.getBoundingClientRect();
      if (r.width >= 4 && r.height >= 4) break;
      medido = medido.parentElement;
    }
    const r = medido.getBoundingClientRect();
    const barra = document.querySelector('[data-testid="panel-barra-superior"]')!.getBoundingClientRect();
    const margen = Math.min(8, r.width / 4, r.height / 4);
    const izquierda = Math.max(r.left + margen, 0);
    const derecha = Math.min(r.right - margen, innerWidth - 1);
    const arriba = r.top + margen;
    // Un control más alto que el viewport no cabe entero: se exige su parte superior y su centro visible.
    const cabe = r.height <= innerHeight - barra.bottom;
    const abajo = cabe ? r.bottom - margen : Math.min(r.bottom, innerHeight) - margen;
    const puntos: [number, number][] = [
      [(izquierda + derecha) / 2, (arriba + abajo) / 2],
      [izquierda, arriba],
      [derecha, arriba],
      [izquierda, abajo],
      [derecha, abajo],
    ];
    const tapados: string[] = [];
    for (const [x, y] of puntos) {
      const encima = y < 0 || y >= innerHeight ? null : document.elementFromPoint(x, y);
      const propio =
        encima !== null &&
        (medido.contains(encima) || activo.contains(encima) || (encima.closest('label') as HTMLLabelElement | null)?.control === activo);
      if (!propio) tapados.push(`(${Math.round(x)},${Math.round(y)})→${describir(encima)}`);
    }
    return {
      visible: tapados.length === 0,
      descripcion: `${describir(activo)} top=${Math.round(r.top)} bottom=${Math.round(r.bottom)} barra.bottom=${Math.round(barra.bottom)} ${tapados.join(' ')}`,
    };
  });
}

async function abrirEditor(page: Page, ruta: string): Promise<void> {
  await irA(page, ruta);
  await expect(page.getByTestId('editor-contenido')).toBeVisible({ timeout: 15_000 });
}

for (const vp of VIEWPORTS) {
  for (const tipo of TIPOS) {
    test(`AC_TKT070_01 / AC_TKT070_02 / AC_TKT070_03 editor de ${tipo.etiqueta} a ${vp.nombre}: anclas, secciones y Tab sin foco oculto`, async ({ page }) => {
      await page.setViewportSize({ width: vp.ancho, height: vp.alto });
      await entrarComoEditorCompartido(page);
      await empezarMedicionCls(page);
      const fallos: string[] = [];

      // (1a) ErrorSummary: Guardar vacío y seguir el enlace al campo.
      await abrirEditor(page, `/panel/contenido/${tipo.ruta}/nuevo`);
      await page.getByTestId('editor-guardar').click();
      await expect(page.getByTestId('editor-resumen-errores')).toBeFocused();
      await sinViolacionesGraves(page);
      const enlacesResumen = page.getByTestId('editor-resumen-enlace');
      const totalResumen = await enlacesResumen.count();
      expect(totalResumen).toBeGreaterThan(0);
      for (let i = 0; i < totalResumen; i++) {
        await enlacesResumen.nth(i).click();
        await esperarQuietud(page);
        const r = await focoVisible(page);
        if (!r.visible) fallos.push(`resumen[${i}]: ${r.descripcion}`);
      }

      // (2) Navegación de secciones: lista ≥ xl, «Ir a sección» < xl.
      const listaVisible = await page.getByTestId('editor-nav-identidad').isVisible();
      const ids = await page.locator('#editor-ir-seccion option').evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value));
      expect(ids.length).toBeGreaterThan(1);
      for (const id of [...ids.slice(1), ids[0]!]) {
        if (listaVisible) await page.getByTestId(`editor-nav-${id}`).click();
        else await page.locator('#editor-ir-seccion').selectOption(id);
        await esperarQuietud(page);
        await expect(page.locator(`#seccion-${id}-titulo`)).toBeFocused();
        const r = await focoVisible(page);
        if (!r.visible) fallos.push(`sección ${id}: ${r.descripcion}`);
      }

      // (3) Tab por todo el formulario desde el título de la vista.
      await page.locator('#editor-titulo').focus();
      await page.evaluate(() => scrollTo(0, 0));
      for (let i = 0; i < MAX_TABS; i++) {
        await page.keyboard.press('Tab');
        await esperarQuietud(page);
        const fuera = await page.evaluate(() => !document.querySelector('[data-testid="editor-contenido"]')?.contains(document.activeElement));
        if (fuera) break;
        const r = await focoVisible(page);
        if (!r.visible) fallos.push(`Tab ${i + 1}: ${r.descripcion}`);
      }

      // (1b) Enlaces de la lista de errores de «Publicar» de un borrador incompleto (muchos campos).
      const borrador = await crearBorrador(page, tipo.ruta, `Foco E2E ${sufijo()}`);
      await abrirEditor(page, `/panel/contenido/${tipo.ruta}/${borrador.id}`);
      await page.getByTestId('editor-accion-principal').click();
      const enlacesPublicar = page.getByTestId('publicacion-error-campo');
      await expect(enlacesPublicar.first()).toBeVisible({ timeout: 15_000 });
      const totalPublicar = await enlacesPublicar.count();
      for (let i = 0; i < totalPublicar; i++) {
        if (i > 0) {
          await page.getByTestId('editor-accion-principal').click();
          await expect(enlacesPublicar.nth(i)).toBeVisible({ timeout: 15_000 });
        }
        const texto = (await enlacesPublicar.nth(i).textContent())?.trim() ?? '';
        await enlacesPublicar.nth(i).click();
        await esperarQuietud(page);
        const r = await focoVisible(page);
        if (!r.visible) fallos.push(`publicar[${i}] «${texto}»: ${r.descripcion}`);
      }
      await sinViolacionesGraves(page);

      const cls = await leerCls(page);
      test.info().annotations.push({ type: 'cls', description: String(cls) });
      expect(fallos).toEqual([]);
      expect(cls ?? 0).toBeLessThanOrEqual(0.1);
    });
  }
}
