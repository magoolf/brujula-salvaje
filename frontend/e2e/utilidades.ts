import AxeBuilder from '@axe-core/playwright';
import { Page, expect } from '@playwright/test';

/** WebKit no enfoca enlaces con Tab por defecto (preferencia del sistema); Alt+Tab sí. */
export function teclaTab(browserName: string): string {
  return browserName === 'webkit' ? 'Alt+Tab' : 'Tab';
}

/** Atributo data-testid (o id) del elemento con foco. */
export async function focoActual(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const activo = document.activeElement as HTMLElement | null;
    return activo?.dataset['testid'] ?? activo?.id ?? null;
  });
}

/** Tabula hasta que el foco llegue al data-testid indicado (máximo `limite` pulsaciones). */
export async function tabularHasta(page: Page, browserName: string, testId: string, limite = 25): Promise<void> {
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
  const graves = resultado.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  expect(graves.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
}

/** Espera a que la aplicación esté hidratada e interactiva (App marca html[data-app-lista]). */
export async function esperarHidratacion(page: Page): Promise<void> {
  await page.locator('html[data-app-lista="true"]').waitFor({ state: 'attached' });
}
