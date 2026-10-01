/**
 * E2E del Selector de medios SCR-041 (TKT-022, AC_TKT022_04 y AC_TKT022_05): accesibilidad del
 * diálogo en los 3 motores (foco atrapado, Escape, teclado, semántica para lectores de pantalla) y
 * axe a 320 px y en escritorio.
 *
 * Su pantalla anfitriona real (SCR-036, TKT-023) aún no existe: se monta en el banco de pruebas
 * /panel/desarrollo/selector-medios, que solo se registra en desarrollo (DEC-DEV-022-01). Por eso
 * esta suite corre contra `ng serve` con la API reenviada al stack real (ver
 * e2e/proxy-selector.conf.mjs) y requiere, además de E2E_COMPOSE_PROJECT:
 *   E2E_SELECTOR_URL=http://127.0.0.1:4310
 * Sin ella, se omite con el motivo.
 */
import AxeBuilder from '@axe-core/playwright';
import { Locator, Page, expect, test } from '@playwright/test';

import { catalogarPorApi, pngValido, subirPorApi } from './medios-soporte';
import { PROYECTO_COMPOSE, crearCuenta, entrarPorApi, irA } from './panel-soporte';

const URL_SELECTOR = process.env['E2E_SELECTOR_URL'] ?? '';
const BANCO = '/panel/desarrollo/selector-medios';

test.use({ baseURL: URL_SELECTOR || undefined });
test.beforeEach(() => {
  test.skip(
    URL_SELECTOR === '' || PROYECTO_COMPOSE === '',
    'Requiere E2E_SELECTOR_URL (ng serve con e2e/proxy-selector.conf.mjs) y E2E_COMPOSE_PROJECT.',
  );
});

async function abrirBanco(page: Page): Promise<void> {
  await entrarPorApi(page, crearCuenta());
  await irA(page, BANCO);
  await expect(page.getByTestId('banco-selector')).toBeVisible();
}

function dialogo(page: Page, nombre: string): Locator {
  return page.getByRole('dialog', { name: nombre });
}

async function axeSinGraves(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page }).analyze();
  const graves = resultado.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
  expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)).toEqual([]);
}

/** El elemento activo está dentro del diálogo abierto. */
async function focoDentro(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const abierto = document.querySelector('dialog[open]');
    return abierto !== null && abierto.contains(document.activeElement);
  });
}

test.describe('Panel · selector de medios SCR-041 (TKT-022)', () => {
  test('AC_TKT022_04 diálogo modal: foco inicial, foco atrapado con Tab y Mayús+Tab, Escape devuelve el foco', async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await abrirBanco(page);
    const abrir = page.getByTestId('banco-abrir-varios');
    await abrir.focus();
    await page.keyboard.press('Enter');
    const selector = dialogo(page, 'Elegir imágenes');
    await expect(selector).toBeVisible();
    await expect(selector.getByLabel('Buscar', { exact: true })).toBeFocused();
    await expect(selector.getByTestId('selector-rejilla')).toBeVisible();

    // Recorre todo el diálogo con Tab (más pasos que controles) sin salir nunca de él.
    for (let i = 0; i < 70; i++) {
      await page.keyboard.press('Tab');
      expect(await focoDentro(page)).toBe(true);
    }
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press('Shift+Tab');
      expect(await focoDentro(page)).toBe(true);
    }
    // El resto de la página es inerte mientras el diálogo está abierto.
    await expect(page.getByTestId('banco-abrir-uno')).not.toBeFocused();

    await page.keyboard.press('Escape');
    await expect(selector).toBeHidden();
    await expect(abrir).toBeFocused();
    await expect(page.getByTestId('banco-estado')).toHaveText('Selección cancelada.');
  });

  test('AC_TKT022_04 teclado y lector de pantalla: casillas con Espacio, recuento en role=status, reordenar y añadir', async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await abrirBanco(page);
    await page.getByTestId('banco-abrir-varios').click();
    const selector = dialogo(page, 'Elegir imágenes');
    await expect(selector.getByRole('tablist', { name: 'Origen de las imágenes' })).toBeVisible();
    await expect(selector.getByRole('tab', { name: 'Biblioteca', selected: true })).toBeVisible();
    await expect(selector.getByRole('group', { name: 'Elegir imágenes' })).toBeVisible();
    const casillas = selector.getByRole('checkbox');
    await expect(casillas.first()).toBeVisible();
    const recuento = selector.getByRole('status').filter({ hasText: /seleccionad/ });
    await expect(recuento).toHaveText('Ninguna imagen seleccionada');

    await casillas.nth(0).focus();
    await page.keyboard.press('Space');
    await expect(casillas.nth(0)).toBeChecked();
    await page.keyboard.press('Tab');
    await expect(casillas.nth(1)).toBeFocused();
    await page.keyboard.press('Space');
    await expect(recuento).toHaveText('2 seleccionadas');
    await expect(selector.getByTestId('selector-anadir')).toHaveText('Añadir 2 imágenes');

    const elegidas = selector.getByRole('list', { name: 'Imágenes seleccionadas, en orden' }).getByRole('listitem');
    await expect(elegidas).toHaveCount(2);
    const ids = await elegidas.evaluateAll((items) => items.map((i) => i.getAttribute('data-testid') ?? ''));
    const primera = (await elegidas.nth(0).locator('.nombre').textContent()) ?? '';
    const segunda = (await elegidas.nth(1).locator('.nombre').textContent()) ?? '';
    await selector.getByTestId(ids[0]).getByRole('button', { name: `Bajar ${primera}` }).focus();
    await page.keyboard.press('Enter');
    await expect(elegidas.nth(0)).toHaveAttribute('data-testid', ids[1]);
    await expect(elegidas.nth(1)).toHaveAttribute('data-testid', ids[0]);
    await expect(selector.getByTestId('selector-anuncio')).toHaveText(`${primera} movida a la posición 2 de 2.`);
    // El foco sigue al botón pulsado en la nueva posición del elemento movido.
    await expect(selector.getByTestId(ids[0]).getByRole('button', { name: `Bajar ${primera}` })).toBeFocused();

    await selector.getByTestId('selector-anadir').focus();
    await page.keyboard.press('Enter');
    await expect(selector).toBeHidden();
    await expect(page.getByTestId('banco-estado')).toHaveText('Se eligieron 2 imágenes.');
    await expect(page.getByTestId('banco-resultado').getByRole('listitem')).toHaveText([segunda, primera]);
  });

  test('AC_TKT022_04 modo una imagen: radios en un radiogroup, flechas cambian la elección; no disponibles deshabilitadas', async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await abrirBanco(page);
    // Un medio pendiente de datos con un nombre único para encontrarlo.
    const pendiente = await subirPorApi(page, pngValido('pendiente-selector.png'));
    const marca = `selector${pendiente.id}`;
    await catalogarPorApi(page, pendiente.id, { titulo_interno: `Prueba ${marca}` });

    await page.getByTestId('banco-abrir-uno').click();
    const selector = dialogo(page, 'Elegir portada');
    const grupo = selector.getByRole('radiogroup', { name: 'Elegir portada' });
    await expect(grupo).toBeVisible();
    const radios = grupo.getByRole('radio');
    await radios.nth(0).focus();
    await page.keyboard.press('Space');
    await expect(radios.nth(0)).toBeChecked();
    await page.keyboard.press('ArrowRight');
    await expect(radios.nth(1)).toBeChecked();
    await expect(radios.nth(0)).not.toBeChecked();
    await expect(selector.getByRole('status').filter({ hasText: /seleccionad/ })).toHaveText('1 seleccionada');

    // «Todas»: el pendiente se ve, pero su radio está deshabilitado y explica por qué.
    await selector.getByLabel('Buscar', { exact: true }).fill(marca);
    await selector.getByLabel('Mostrar').selectOption('no');
    await selector.getByRole('button', { name: 'Buscar', exact: true }).click();
    const bloqueado = selector.getByRole('radio', { name: new RegExp(marca) });
    await expect(bloqueado).toBeDisabled();
    await expect(bloqueado).toHaveAccessibleDescription('Completa sus datos en Medios para usarla');

    await selector.getByTestId('selector-anadir').click();
    await expect(selector).toBeHidden();
    await expect(page.getByTestId('banco-estado')).toHaveText('Se eligió 1 imagen.');
  });

  test('AC_TKT022_04 pestañas con flechas y subida desde el diálogo: duplicado → «Usar la existente» la selecciona', async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await abrirBanco(page);
    const imagen = pngValido('existente-selector.png');
    const existente = await subirPorApi(page, imagen);
    await catalogarPorApi(page, existente.id, {
      titulo_interno: `Existente ${existente.id}`,
      texto_alternativo: 'Prueba del selector',
      autor_credito: 'Equipo E2E',
      licencia_id: 1,
    });

    await page.getByTestId('banco-abrir-varios').click();
    const selector = dialogo(page, 'Elegir imágenes');
    await selector.getByRole('tab', { name: 'Biblioteca' }).focus();
    await page.keyboard.press('ArrowRight');
    const pestanaSubir = selector.getByRole('tab', { name: 'Subir' });
    await expect(pestanaSubir).toBeFocused();
    await expect(pestanaSubir).toHaveAttribute('aria-selected', 'true');
    const panelSubir = selector.getByRole('tabpanel', { name: 'Subir' });
    await expect(panelSubir).toBeVisible();

    await panelSubir.getByTestId('subida-archivos').setInputFiles([{ ...imagen, name: 'de-nuevo.png' }]);
    await expect(panelSubir.getByTestId('subida-resumen')).toHaveText('0 aceptadas, 1 duplicada');
    await panelSubir.getByTestId('subida-usar-existente').click();
    await expect(selector.getByRole('tab', { name: 'Biblioteca' })).toBeFocused();
    await expect(selector.getByTestId('selector-anuncio')).toHaveText('Se seleccionó la imagen que ya estaba en la biblioteca.');
    await expect(selector.getByTestId(`selector-elegida-${existente.id}`)).toBeVisible();
    await expect(selector.getByRole('status').filter({ hasText: /seleccionad/ })).toHaveText('1 seleccionada');
  });

  for (const ancho of [320, 1280]) {
    test(`AC_TKT022_05 axe sin violaciones serious/critical en SCR-041 a ${ancho} px`, async ({ page }) => {
      test.setTimeout(90_000);
      await page.setViewportSize({ width: ancho, height: 900 });
      await abrirBanco(page);
      await page.getByTestId('banco-abrir-varios').click();
      const selector = dialogo(page, 'Elegir imágenes');
      await expect(selector.getByTestId('selector-rejilla')).toBeVisible();
      await selector.getByRole('checkbox').first().check();
      await axeSinGraves(page);
      await selector.getByRole('tab', { name: 'Subir' }).click();
      await selector.getByTestId('subida-archivos').setInputFiles([pngValido(`axe-selector-${ancho}.png`)]);
      await expect(selector.getByTestId('subida-resultados')).toBeVisible();
      await axeSinGraves(page);
      await page.keyboard.press('Escape');
      await page.getByTestId('banco-abrir-uno').click();
      await expect(dialogo(page, 'Elegir portada').getByRole('radiogroup')).toBeVisible();
      await axeSinGraves(page);
    });
  }
});
