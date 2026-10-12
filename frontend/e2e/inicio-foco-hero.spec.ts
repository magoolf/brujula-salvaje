import { Page, TestInfo, expect, test } from '@playwright/test';

import {
  empezarMedicionCls,
  esperarHidratacion,
  leerCls,
  sinViolacionesGraves,
} from './utilidades';

/**
 * TKT-069 (WCAG 2.4.7 / 1.4.11; QA TKT-047 OBS-01): el indicador de foco de TODOS los controles
 * enfocables del bloque principal de Inicio (CTA, búsqueda grande y su botón) debe contrastar ≥3:1
 * con lo que tiene alrededor, que es la franja con scrim sobre la foto (la foto se cambia desde el
 * panel). tokens.json: focus.ring-inverse «sobre bg.inverse y sobre fotografías con scrim».
 *
 * Medición REAL por píxel, con el foco puesto por teclado (Tab, :focus-visible): para cada elemento
 * que pinta un anillo (el control enfocado o un ancestro con :focus-within, p. ej. la fila de la
 * búsqueda) se hacen dos capturas del mismo recorte, con el anillo y con `outline-style: none` en
 * ese elemento. Los píxeles que cambian son el anillo; el color de la captura sin anillo en esos
 * píxeles es el fondo adyacente real (foto + scrim). Se compara el color declarado del anillo
 * (outline-color calculado) con ese fondo, en los píxeles cubiertos por completo por el anillo (los
 * del borde antialiasado se descartan). Además se comprueba que la mayoría de los píxeles que cambian
 * son de ese color (la medida corresponde al anillo pintado y no a otra cosa).
 *
 * Fondos: la foto de la semilla y una imagen blanca pura (peor caso) inyectada con page.route sobre
 * todos los derivados del <picture> del hero. Anchos 375 y 1280 px. Fuera del hero el anillo sigue
 * siendo focus.ring (lagoon-600). Solo Chromium (decisión humana); requiere la semilla.
 */

type Fondo = 'blanca' | 'semilla';

const ANCHOS = [375, 1280] as const;
const ALTO_POR_ANCHO: Readonly<Record<number, number>> = { 375: 812, 1280: 800 };
const FONDOS: readonly Fondo[] = ['semilla', 'blanca'];
const UMBRAL = 3;
/** focus.ring (lagoon-600 #1D5E7A) y focus.ring-inverse (sunset-300 #F2A57C), tokens.css. */
const ANILLO_NORMAL = 'rgb(29, 94, 122)';
const ANILLO_INVERSO = 'rgb(242, 165, 124)';
/** Margen del recorte alrededor del portador: el anillo es de 3 px con separación de 2 px. */
const MARGEN = 10;

interface MedidaAnillo {
  control: string;
  portador: string;
  color: string;
  pixeles: number;
  coincidencia: number;
  minimo: number;
  p05: number;
  mediana: number;
}

test.skip(({ browserName }) => browserName !== 'chromium', 'Medición del foco solo en Chromium');

/** PNG (base64) blanco puro de 1600×900 generado con canvas. */
async function imagenBlanca(page: Page): Promise<Buffer> {
  const base64 = await page.evaluate(() => {
    const lienzo = document.createElement('canvas');
    lienzo.width = 1600;
    lienzo.height = 900;
    const g = lienzo.getContext('2d');
    if (!g) throw new Error('Sin contexto 2D');
    g.fillStyle = '#ffffff';
    g.fillRect(0, 0, lienzo.width, lienzo.height);
    return lienzo.toDataURL('image/png').split(',')[1] ?? '';
  });
  return Buffer.from(base64, 'base64');
}

/** URLs absolutas de todos los derivados del <picture> del hero, leídas del HTML del SSR. */
async function derivadosHero(page: Page, base: string): Promise<Set<string>> {
  const html = await (await page.request.get('/')).text();
  const picture = /<picture[^>]*inicio-imagen-principal[\s\S]*?<\/picture>/.exec(html)?.[0] ?? '';
  const urls = new Set<string>();
  for (const [, valor = ''] of picture.matchAll(/\s(?:srcset|src)="([^"]+)"/g)) {
    for (const parte of valor.replaceAll('&amp;', '&').split(',')) {
      const url = parte.trim().split(/\s+/)[0];
      if (url) urls.add(new URL(url, base).href);
    }
  }
  return urls;
}

async function abrirInicio(page: Page, fondo: Fondo, base: string): Promise<void> {
  const img = page.getByTestId('inicio-imagen-principal').locator('img');
  let servidas = 0;
  if (fondo === 'blanca') {
    const urls = await derivadosHero(page, base);
    expect(urls.size).toBeGreaterThan(0);
    await page.goto('about:blank');
    const cuerpo = await imagenBlanca(page);
    await page.route(
      (url) => urls.has(url.href),
      async (ruta) => {
        servidas++;
        await ruta.fulfill({ status: 200, contentType: 'image/png', body: cuerpo });
      },
    );
  }
  await page.goto('/');
  await esperarHidratacion(page);
  await expect
    .poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0))
    .toBe(true);
  if (fondo === 'blanca') {
    expect(servidas).toBeGreaterThan(0);
    const pixel = await img.evaluate((i: HTMLImageElement) => {
      const lienzo = document.createElement('canvas');
      lienzo.width = 16;
      lienzo.height = 9;
      const g = lienzo.getContext('2d');
      g?.drawImage(i, 0, 0, 16, 9);
      return Array.from(g?.getImageData(0, 0, 1, 1).data ?? []).slice(0, 3);
    });
    pixel.forEach((c) => expect(c).toBeGreaterThanOrEqual(249));
  }
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

/** ¿El elemento con foco está dentro del bloque principal? */
async function focoEnHero(page: Page): Promise<boolean> {
  return page.evaluate(
    () => document.activeElement?.closest('[data-testid="inicio-bloque-principal"]') != null,
  );
}

/** Descripción corta del elemento con foco (data-testid, id o etiqueta). */
async function descripcionFoco(page: Page): Promise<string> {
  return page.evaluate(() => {
    const e = document.activeElement as HTMLElement | null;
    return e?.dataset['testid'] ?? (e?.id || e?.tagName.toLowerCase() || 'ninguno');
  });
}

/**
 * Marca (data-tkt069-portador) los elementos que pintan anillo para el foco actual: el elemento
 * enfocado y sus ancestros con outline visible (:focus-within). Devuelve sus descripciones.
 */
async function marcarPortadores(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    document
      .querySelectorAll('[data-tkt069-portador]')
      .forEach((e) => e.removeAttribute('data-tkt069-portador'));
    const portadores: string[] = [];
    let e = document.activeElement as HTMLElement | null;
    let n = 0;
    while (e && e !== document.body) {
      const estilo = getComputedStyle(e);
      if (estilo.outlineStyle !== 'none' && parseFloat(estilo.outlineWidth) > 0) {
        e.setAttribute('data-tkt069-portador', String(n));
        portadores.push(
          `${String(n)}:${e.dataset['testid'] ?? e.className.toString().split(' ')[0] ?? e.tagName}`,
        );
        n++;
      }
      e = e.parentElement;
    }
    return portadores;
  });
}

/** Mide el contraste del anillo del portador `n` contra el fondo bajo cada píxel del anillo. */
async function medirPortador(
  page: Page,
  control: string,
  n: number,
  descripcion: string,
): Promise<MedidaAnillo> {
  const portador = page.locator(`[data-tkt069-portador="${String(n)}"]`);
  const { clip, color } = await portador.evaluate((e, margen) => {
    const r = e.getBoundingClientRect();
    const x = Math.max(0, Math.floor(r.left - margen));
    const y = Math.max(0, Math.floor(r.top - margen));
    return {
      clip: {
        x,
        y,
        width: Math.min(window.innerWidth, Math.ceil(r.right + margen)) - x,
        height: Math.min(window.innerHeight, Math.ceil(r.bottom + margen)) - y,
      },
      color: getComputedStyle(e).outlineColor,
    };
  }, MARGEN);
  const conAnillo = (
    await page.screenshot({ clip, animations: 'disabled', caret: 'hide' })
  ).toString('base64');
  await portador.evaluate((e) =>
    (e as HTMLElement).style.setProperty('outline-style', 'none', 'important'),
  );
  const sinAnillo = (
    await page.screenshot({ clip, animations: 'disabled', caret: 'hide' })
  ).toString('base64');
  await portador.evaluate((e) => (e as HTMLElement).style.removeProperty('outline-style'));

  const medida = await page.evaluate(
    async ({ color, conAnillo, sinAnillo }) => {
      const pixeles = async (b64: string): Promise<Uint8ClampedArray> => {
        const binario = atob(b64);
        const bytes = new Uint8Array(binario.length);
        for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i);
        const mapa = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
        const lienzo = new OffscreenCanvas(mapa.width, mapa.height);
        const g = lienzo.getContext('2d');
        if (!g) throw new Error('Sin contexto 2D');
        g.drawImage(mapa, 0, 0);
        return g.getImageData(0, 0, mapa.width, mapa.height).data;
      };
      const lineal = (c: number): number => {
        const v = c / 255;
        return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      const luminancia = (r: number, g: number, b: number): number =>
        0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b);
      const [ar = 0, ag = 0, ab = 0] = (color.match(/[\d.]+/g) ?? []).map(Number);
      const lAnillo = luminancia(ar, ag, ab);
      const a = await pixeles(conAnillo);
      const b = await pixeles(sinAnillo);
      const ratios: number[] = [];
      let coinciden = 0;
      let cambiados = 0;
      for (let i = 0; i + 3 < a.length && i + 3 < b.length; i += 4) {
        const diferencia =
          Math.abs((a[i] ?? 0) - (b[i] ?? 0)) +
          Math.abs((a[i + 1] ?? 0) - (b[i + 1] ?? 0)) +
          Math.abs((a[i + 2] ?? 0) - (b[i + 2] ?? 0));
        if (diferencia <= 30) continue; // no es anillo
        cambiados++;
        const distanciaAlColor =
          Math.abs((a[i] ?? 0) - ar) +
          Math.abs((a[i + 1] ?? 0) - ag) +
          Math.abs((a[i + 2] ?? 0) - ab);
        // Solo píxeles cubiertos por completo por el anillo: los del borde antialiasado mezclan el
        // anillo con el fondo y no representan ni uno ni otro.
        if (distanciaAlColor > 24) continue;
        coinciden++;
        const lFondo = luminancia(b[i] ?? 0, b[i + 1] ?? 0, b[i + 2] ?? 0);
        ratios.push((Math.max(lAnillo, lFondo) + 0.05) / (Math.min(lAnillo, lFondo) + 0.05));
      }
      ratios.sort((x, y) => x - y);
      const cuantil = (p: number): number => ratios[Math.floor(p * (ratios.length - 1))] ?? 0;
      return {
        pixeles: ratios.length,
        coincidencia: Number((cambiados ? coinciden / cambiados : 0).toFixed(2)),
        minimo: Number((ratios[0] ?? 0).toFixed(2)),
        p05: Number(cuantil(0.05).toFixed(2)),
        mediana: Number(cuantil(0.5).toFixed(2)),
      };
    },
    { color, conAnillo, sinAnillo },
  );
  return { control, portador: descripcion, color, ...medida };
}

/** Mide los anillos del elemento con foco actual. */
async function medirFocoActual(page: Page): Promise<MedidaAnillo[]> {
  const control = await descripcionFoco(page);
  await page.evaluate(() =>
    (document.activeElement as HTMLElement | null)?.scrollIntoView({ block: 'center' }),
  );
  await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => r())));
  const portadores = await marcarPortadores(page);
  expect(portadores.length, `${control}: sin anillo de foco visible`).toBeGreaterThan(0);
  const medidas: MedidaAnillo[] = [];
  for (let n = 0; n < portadores.length; n++) {
    medidas.push(await medirPortador(page, control, n, portadores[n] ?? ''));
  }
  return medidas;
}

/** Tabula desde el principio hasta entrar en el hero y mide cada control enfocable del hero. */
async function medirControlesDelHero(page: Page): Promise<MedidaAnillo[]> {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.locator('body').focus();
  let entradas = 0;
  while (!(await focoEnHero(page))) {
    await page.keyboard.press('Tab');
    if (++entradas > 60) throw new Error('El foco no llegó al bloque principal tras 60 Tab');
  }
  const medidas: MedidaAnillo[] = [];
  const vistos = new Set<string>();
  while (await focoEnHero(page)) {
    const control = await descripcionFoco(page);
    expect(vistos.has(control), `trampa de foco en ${control}`).toBe(false);
    vistos.add(control);
    medidas.push(...(await medirFocoActual(page)));
    await page.keyboard.press('Tab');
  }
  // Los controles del hero (HANDOFF_UI_UX SCR-001 focus_order: CTA → búsqueda).
  for (const esperado of [
    'inicio-cta-explorar',
    'inicio-cta-sorprendeme',
    'campo-busqueda-entrada',
    'campo-busqueda-enviar',
  ]) {
    expect([...vistos], `control del hero no alcanzado por teclado: ${esperado}`).toContain(
      esperado,
    );
  }
  return medidas;
}

/**
 * axe con la página arriba y sin las marcas de la medición. Tras recorrer el hero con Tab el control
 * enfocado puede quedar parcialmente bajo la cabecera fija y axe (target-size) lo cuenta como
 * objetivo tapado: es un efecto de la posición de desplazamiento de la prueba, no del producto.
 */
async function axeArriba(page: Page): Promise<void> {
  await page.evaluate(() => {
    document
      .querySelectorAll('[data-tkt069-portador]')
      .forEach((e) => e.removeAttribute('data-tkt069-portador'));
    window.scrollTo(0, 0);
  });
  await sinViolacionesGraves(page);
}

async function verificar(
  medidas: MedidaAnillo[],
  testInfo: TestInfo,
  etiqueta: string,
  colorEsperado: string,
): Promise<void> {
  console.log(`[TKT-069] ${etiqueta} ${JSON.stringify(medidas)}`);
  await testInfo.attach(`foco-${etiqueta}.json`, {
    body: JSON.stringify(medidas, null, 1),
    contentType: 'application/json',
  });
  for (const m of medidas) {
    const nombre = `${etiqueta} ${m.control} [${m.portador}]`;
    expect.soft(m.pixeles, `${nombre}: sin píxeles de anillo`).toBeGreaterThan(40);
    expect
      .soft(m.coincidencia, `${nombre}: los píxeles del anillo no son ${m.color}`)
      .toBeGreaterThanOrEqual(0.5);
    expect
      .soft(m.minimo, `${nombre}: contraste del anillo (umbral ${String(UMBRAL)}:1)`)
      .toBeGreaterThanOrEqual(UMBRAL);
  }
  // El anillo exterior de cada control del hero es focus.ring-inverse (el interior del botón de la
  // búsqueda, focus.ring-inner sobre el verde del botón, se mide pero no se fuerza su color).
  for (const m of medidas.filter((x) => !x.portador.includes('enviar'))) {
    expect.soft(m.color, `${etiqueta} ${m.control} [${m.portador}]`).toBe(colorEsperado);
  }
}

test.describe('TKT-069 anillo de foco de los controles del bloque principal de Inicio', () => {
  for (const fondo of FONDOS) {
    for (const ancho of ANCHOS) {
      test(`AC_TKT069_01 anillo de foco ≥3:1 en cada control del hero con imagen ${fondo} a ${String(ancho)} px`, async ({
        page,
        baseURL,
      }, testInfo) => {
        await page.setViewportSize({ width: ancho, height: ALTO_POR_ANCHO[ancho] ?? 800 });
        await empezarMedicionCls(page);
        await abrirInicio(page, fondo, baseURL ?? '');
        if (fondo === 'semilla') {
          const cls = await leerCls(page);
          console.log(`[TKT-069] CLS semilla ${String(ancho)}px: ${String(cls)}`);
          expect(cls ?? 0).toBeLessThanOrEqual(0.1);
        }
        const medidas = await medirControlesDelHero(page);
        await verificar(medidas, testInfo, `${fondo}-${String(ancho)}`, ANILLO_INVERSO);
        if (fondo === 'semilla') {
          // El foco no desplaza nada (solo outline): sin CLS tras recorrer el hero con Tab.
          expect((await leerCls(page)) ?? 0).toBeLessThanOrEqual(0.1);
        }
        await axeArriba(page);
      });
    }
  }

  test('AC_TKT069_02 fuera del hero el anillo sigue siendo focus.ring (lagoon-600) y contrasta ≥3:1', async ({
    page,
    baseURL,
  }, testInfo) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await abrirInicio(page, 'semilla', baseURL ?? '');
    // Antes del hero: primer control de la cabecera tras el salto al contenido.
    await page.locator('body').focus();
    const antes: MedidaAnillo[] = [];
    for (let i = 0; i < 60 && !(await focoEnHero(page)); i++) {
      await page.keyboard.press('Tab');
      const dentro = await focoEnHero(page);
      const enCabecera = await page.evaluate(
        () => document.activeElement?.closest('header') != null,
      );
      if (!dentro && enCabecera && antes.length === 0) antes.push(...(await medirFocoActual(page)));
    }
    expect(antes.length, 'sin control enfocable en la cabecera').toBeGreaterThan(0);
    // Después del hero: primer control de las secciones de contenido.
    while (await focoEnHero(page)) await page.keyboard.press('Tab');
    const despues = await medirFocoActual(page);
    const medidas = [...antes, ...despues];
    await verificar(medidas, testInfo, 'fuera-del-hero', ANILLO_NORMAL);
  });

  test('AC_TKT069_03 con prefers-contrast: more el anillo del hero sigue ≥3:1 sobre la imagen blanca', async ({
    page,
    baseURL,
  }, testInfo) => {
    await page.emulateMedia({ contrast: 'more' });
    await page.setViewportSize({ width: 375, height: 812 });
    await abrirInicio(page, 'blanca', baseURL ?? '');
    // La franja reforzada de TKT-047 (overlay.lightbox, ≥90 % de opacidad) sigue activa.
    const fondoFranja = await page
      .getByTestId('inicio-franja-texto')
      .evaluate((e) => getComputedStyle(e).backgroundColor);
    expect(Number(/,\s*([\d.]+)\)$/.exec(fondoFranja)?.[1] ?? '0')).toBeGreaterThanOrEqual(0.9);
    const medidas = await medirControlesDelHero(page);
    await verificar(medidas, testInfo, 'blanca-375-contraste-alto', ANILLO_INVERSO);
    await axeArriba(page);
  });
});
