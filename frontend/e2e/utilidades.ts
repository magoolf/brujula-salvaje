import AxeBuilder from '@axe-core/playwright';
import { Page, expect } from '@playwright/test';

/** Tecla de avance de foco. */
export function teclaTab(_browserName: string): string {
  return 'Tab';
}

/**
 * WebKit (motor de Playwright) no incluye los enlaces en el orden de tabulación por defecto
 * (preferencia «tabs to links» desactivada; en Windows ni Tab ni Alt+Tab los enfocan). En ese
 * motor las pruebas enfocan el enlace con focus() y verifican su activación por teclado (Enter).
 */
export function enlacesTabulables(browserName: string): boolean {
  return browserName !== 'webkit';
}

/** Atributo data-testid (o id) del elemento con foco. */
export async function focoActual(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const activo = document.activeElement as HTMLElement | null;
    return activo?.dataset['testid'] ?? activo?.id ?? null;
  });
}

/** Tabula hasta que el foco llegue al data-testid indicado (máximo `limite` pulsaciones). */
export async function tabularHasta(
  page: Page,
  browserName: string,
  testId: string,
  limite = 25,
): Promise<void> {
  for (let i = 0; i < limite; i++) {
    await page.keyboard.press(teclaTab(browserName));
    if ((await focoActual(page)) === testId) return;
  }
  throw new Error(`El foco no llegó a ${testId} tras ${limite} pulsaciones de Tab`);
}

/** axe (WCAG 2.2 AA): sin violaciones de impacto serious/critical (Skill_UI_UX §47.2). */
export async function sinViolacionesGraves(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
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

/** Espera a que la aplicación esté hidratada e interactiva (App marca html[data-app-lista]). */
export async function esperarHidratacion(page: Page): Promise<void> {
  await page.locator('html[data-app-lista="true"]').waitFor({ state: 'attached' });
}

/**
 * Empieza a acumular Cumulative Layout Shift (misma métrica que Lighthouse/CrUX: suma de
 * `value` de cada entrada `layout-shift` sin `hadRecentInput`) en `window`. Debe llamarse ANTES de
 * `page.goto()` (con `page.addInitScript`) para no perder los desplazamientos del arranque/
 * hidratación, que es justo la ventana donde ocurre el colapso de layout (Skill_UI_UX §47.2, CLS
 * ≤ 0.1).
 */
export async function empezarMedicionCls(page: Page): Promise<void> {
  await page.addInitScript(() => {
    (window as unknown as { __cls: number }).__cls = 0;
    try {
      new PerformanceObserver((lista) => {
        for (const entrada of lista.getEntries()) {
          const e = entrada as PerformanceEntry & { value: number; hadRecentInput: boolean };
          if (!e.hadRecentInput) {
            (window as unknown as { __cls: number }).__cls += e.value;
          }
        }
      }).observe({ type: 'layout-shift', buffered: true });
    } catch {
      // Motor sin soporte de layout-shift (p. ej. WebKit/Firefox de Playwright): sin datos de CLS.
    }
  });
}

/** Lee el CLS acumulado desde `empezarMedicionCls`. `null` si el motor no soporta `layout-shift`. */
export async function leerCls(page: Page): Promise<number | null> {
  return page.evaluate(() => (window as unknown as { __cls?: number }).__cls ?? null);
}

/**
 * Espera a que la ficha de destino termine de cargar sus datos (SCR-004). `esperarHidratacion`
 * solo indica que la aplicación arrancó (bootstrap), no que ESTA ruta ya resolvió su petición: justo
 * después de navegar, `<main>` puede seguir mostrando el esqueleto "Cargando destino…" (visto de
 * forma reproducible en este entorno). Se espera explícitamente el contenido real con un margen
 * mayor que el timeout por defecto, en vez de asumir que 5 s siempre alcanzan.
 */
export async function esperarFichaDestino(page: Page): Promise<void> {
  await page.getByTestId('pagina-destino').waitFor({ state: 'visible', timeout: 15_000 });
}
