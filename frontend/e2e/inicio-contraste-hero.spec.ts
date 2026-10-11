import { Locator, Page, TestInfo, expect, test } from '@playwright/test';

import { empezarMedicionCls, esperarHidratacion, leerCls, sinViolacionesGraves } from './utilidades';

/**
 * TKT-047 (QA TKT-041 F-01, WCAG 1.4.3): el contraste del texto del bloque principal de Inicio no
 * puede depender de la foto, que se cambia desde el panel. Se mide el contraste REAL por píxel: para
 * cada línea de texto del rótulo, el titular y el subtítulo se hacen dos capturas del mismo recorte
 * (texto visible y texto transparente, ambas sin text-shadow, que así no cuenta a favor) y se
 * compara el color del texto con el fondo efectivo (foto + scrim) bajo cada píxel de glifo.
 * No se usa la regla color-contrast de axe porque con imagen de fondo devuelve «incomplete».
 *
 * Fondos: imagen blanca pura e imagen de nieve con cielo claro (peores casos), inyectadas con
 * page.route sobre TODOS los derivados del hero (AVIF/WebP/JPEG del <picture>), y la foto de la
 * semilla. Anchos 320, 768 y 1280 px. Umbrales (Skill_UI_UX §47.2): 4,5:1 para el rótulo y el
 * subtítulo (texto normal), 3:1 para el titular (texto grande, ≥ 24 px).
 *
 * Solo Chromium (decisión humana: las E2E de QA se ejecutan en Chromium); requiere la semilla.
 */

type Fondo = 'blanca' | 'nieve' | 'semilla';

const ALTO_POR_ANCHO: Readonly<Record<number, number>> = { 320: 640, 768: 1024, 1280: 800 };
const ANCHOS = [320, 768, 1280] as const;
const FONDOS: readonly Fondo[] = ['blanca', 'nieve', 'semilla'];
const TEXTOS = [
  { clase: 'overline-marca', umbral: 4.5 },
  { clase: 'titular', umbral: 3 },
  { clase: 'subtitulo', umbral: 4.5 },
] as const;
/** Ancho de las imágenes inyectadas (16:9). */
const ANCHO_INYECTADA = 1600;

interface Recorte {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface MedidaLinea {
  linea: number;
  pixeles: number;
  minimo: number;
  p05: number;
  mediana: number;
}

test.skip(({ browserName }) => browserName !== 'chromium', 'Medición de contraste solo en Chromium');

/** PNG (base64) de 1600×900 generado con canvas: blanco puro o nieve con cielo claro. */
async function generarImagen(page: Page, fondo: Exclude<Fondo, 'semilla'>): Promise<Buffer> {
  const base64 = await page.evaluate(
    ({ tipo, ancho }) => {
      const alto = Math.round((ancho * 9) / 16);
      const lienzo = document.createElement('canvas');
      lienzo.width = ancho;
      lienzo.height = alto;
      const g = lienzo.getContext('2d');
      if (!g) throw new Error('Sin contexto 2D');
      if (tipo === 'blanca') {
        g.fillStyle = '#ffffff';
        g.fillRect(0, 0, ancho, alto);
      } else {
        const cielo = g.createLinearGradient(0, 0, 0, alto);
        cielo.addColorStop(0, '#d4e5f6');
        cielo.addColorStop(0.45, '#edf4fb');
        cielo.addColorStop(0.55, '#fafcfd');
        cielo.addColorStop(1, '#ffffff');
        g.fillStyle = cielo;
        g.fillRect(0, 0, ancho, alto);
        // Textura de nieve determinista (LCG): motas gris azulado muy claro en la mitad inferior.
        let semilla = 47;
        const siguiente = (): number => {
          semilla = (semilla * 1103515245 + 12345) % 2147483648;
          return semilla;
        };
        g.fillStyle = '#e3eaf1';
        for (let i = 0; i < 6000; i++) {
          g.fillRect(siguiente() % ancho, alto / 2 + (siguiente() % (alto / 2)), 3, 2);
        }
      }
      return lienzo.toDataURL('image/png').split(',')[1] ?? '';
    },
    { tipo: fondo, ancho: ANCHO_INYECTADA },
  );
  return Buffer.from(base64, 'base64');
}

/**
 * URLs absolutas de todos los derivados del <picture> del hero (sources + img), leídas del HTML del
 * SSR ANTES de navegar: así page.route intercepta la primera petición (y el preload, si lo hay) y
 * ninguna caché del navegador sirve la foto real.
 */
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
  if (fondo !== 'semilla') {
    const urls = await derivadosHero(page, base);
    expect(urls.size).toBeGreaterThan(0);
    await page.goto('about:blank');
    const cuerpo = await generarImagen(page, fondo);
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
  if (fondo !== 'semilla') {
    await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0)).toBe(true);
    expect(servidas).toBeGreaterThan(0);
    // La imagen pintada es la inyectada: su píxel superior izquierdo es el de la imagen generada.
    const esperado = fondo === 'blanca' ? [255, 255, 255] : [0xd4, 0xe5, 0xf6];
    const pixel = await img.evaluate((i: HTMLImageElement) => {
      const lienzo = document.createElement('canvas');
      lienzo.width = 16;
      lienzo.height = 9;
      const g = lienzo.getContext('2d');
      g?.drawImage(i, 0, 0, 16, 9);
      return Array.from(g?.getImageData(0, 0, 1, 1).data ?? []).slice(0, 3);
    });
    pixel.forEach((c, k) => expect(Math.abs(c - (esperado[k] ?? 0))).toBeLessThanOrEqual(6));
  } else {
    await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0)).toBe(true);
  }
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

/** Texto del bloque principal por su clase (rótulo, titular o subtítulo). */
function texto(page: Page, clase: string): Locator {
  return page.getByTestId('inicio-bloque-principal').locator(`.${clase}`);
}

/** Recortes (coordenadas del viewport) de cada línea de texto del elemento. */
async function lineasDeTexto(page: Page, clase: string): Promise<Recorte[]> {
  const el = texto(page, clase);
  await el.evaluate((e) => e.scrollIntoView({ block: 'center' }));
  await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => r())));
  return el.evaluate((e) => {
    const rango = document.createRange();
    rango.selectNodeContents(e);
    const lineas: { izq: number; der: number; arriba: number; abajo: number }[] = [];
    for (const r of Array.from(rango.getClientRects())) {
      if (r.width < 1 || r.height < 1) continue;
      const misma = lineas.find((l) => Math.abs(l.arriba - r.top) < r.height / 2);
      if (misma) {
        misma.izq = Math.min(misma.izq, r.left);
        misma.der = Math.max(misma.der, r.right);
        misma.abajo = Math.max(misma.abajo, r.bottom);
      } else {
        lineas.push({ izq: r.left, der: r.right, arriba: r.top, abajo: r.bottom });
      }
    }
    return lineas.map((l) => ({
      x: Math.max(0, Math.floor(l.izq)),
      y: Math.max(0, Math.floor(l.arriba)),
      width: Math.ceil(l.der - l.izq) + 1,
      height: Math.ceil(l.abajo - l.arriba) + 1,
    }));
  });
}

/** Contraste del color del texto contra el fondo efectivo bajo cada píxel de glifo, por línea. */
async function medirContraste(page: Page, clase: string): Promise<MedidaLinea[]> {
  const el = texto(page, clase);
  const recortes = await lineasDeTexto(page, clase);
  expect(recortes.length).toBeGreaterThan(0);
  const color = await el.evaluate((e) => getComputedStyle(e).color);
  await el.evaluate((e) => e.style.setProperty('text-shadow', 'none', 'important'));
  const conTexto: string[] = [];
  for (const clip of recortes) {
    conTexto.push((await page.screenshot({ clip, animations: 'disabled', caret: 'hide' })).toString('base64'));
  }
  await el.evaluate((e) => e.style.setProperty('color', 'transparent', 'important'));
  const sinTexto: string[] = [];
  for (const clip of recortes) {
    sinTexto.push((await page.screenshot({ clip, animations: 'disabled', caret: 'hide' })).toString('base64'));
  }
  await el.evaluate((e) => {
    e.style.removeProperty('color');
    e.style.removeProperty('text-shadow');
  });

  return page.evaluate(
    async ({ color, conTexto, sinTexto }) => {
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
      const [fr = 0, fg = 0, fb = 0] = (color.match(/[\d.]+/g) ?? []).map(Number);
      const lTexto = luminancia(fr, fg, fb);
      const medidas = [];
      for (let n = 0; n < conTexto.length; n++) {
        const a = await pixeles(conTexto[n] ?? '');
        const b = await pixeles(sinTexto[n] ?? '');
        const ratios: number[] = [];
        for (let i = 0; i + 3 < a.length && i + 3 < b.length; i += 4) {
          const diferencia =
            Math.abs((a[i] ?? 0) - (b[i] ?? 0)) +
            Math.abs((a[i + 1] ?? 0) - (b[i + 1] ?? 0)) +
            Math.abs((a[i + 2] ?? 0) - (b[i + 2] ?? 0));
          if (diferencia <= 30) continue; // no es glifo
          const lFondo = luminancia(b[i] ?? 0, b[i + 1] ?? 0, b[i + 2] ?? 0);
          ratios.push((Math.max(lTexto, lFondo) + 0.05) / (Math.min(lTexto, lFondo) + 0.05));
        }
        ratios.sort((x, y) => x - y);
        const cuantil = (p: number): number => ratios[Math.floor(p * (ratios.length - 1))] ?? 0;
        medidas.push({
          linea: n + 1,
          pixeles: ratios.length,
          minimo: Number((ratios[0] ?? 0).toFixed(2)),
          p05: Number(cuantil(0.05).toFixed(2)),
          mediana: Number(cuantil(0.5).toFixed(2)),
        });
      }
      return medidas;
    },
    { color, conTexto, sinTexto },
  );
}

async function verificarContraste(page: Page, testInfo: TestInfo, etiqueta: string): Promise<void> {
  const resultado: Record<string, MedidaLinea[]> = {};
  for (const { clase } of TEXTOS) resultado[clase] = await medirContraste(page, clase);
  // Evidencia para el PR / QA (antes de afirmar, para tener siempre las tres medidas): medidas por
  // línea y captura del bloque principal.
  console.log(`[TKT-047] ${etiqueta} ${JSON.stringify(resultado)}`);
  await testInfo.attach(`contraste-${etiqueta}.json`, {
    body: JSON.stringify(resultado, null, 1),
    contentType: 'application/json',
  });
  await page.evaluate(() => window.scrollTo(0, 0));
  const captura = testInfo.outputPath(`hero-${etiqueta}.png`);
  await page.getByTestId('inicio-bloque-principal').screenshot({ path: captura, animations: 'disabled' });
  await testInfo.attach(`hero-${etiqueta}.png`, { path: captura, contentType: 'image/png' });
  for (const { clase, umbral } of TEXTOS) {
    for (const m of resultado[clase] ?? []) {
      expect.soft(m.pixeles, `${clase} línea ${m.linea}: sin píxeles de glifo`).toBeGreaterThan(20);
      expect.soft(m.minimo, `${etiqueta} ${clase} línea ${m.linea} (umbral ${umbral}:1)`).toBeGreaterThanOrEqual(umbral);
    }
  }
}

test.describe('TKT-047 contraste del texto del bloque principal de Inicio', () => {
  for (const fondo of FONDOS) {
    for (const ancho of ANCHOS) {
      test(`AC_TKT047_01 rótulo y subtítulo ≥4,5:1 y titular ≥3:1 con imagen ${fondo} a ${ancho} px`, async ({
        page,
        baseURL,
      }, testInfo) => {
        await page.setViewportSize({ width: ancho, height: ALTO_POR_ANCHO[ancho] ?? 800 });
        await empezarMedicionCls(page);
        await abrirInicio(page, fondo, baseURL ?? '');
        if (fondo === 'semilla') {
          // Sin CLS nuevo: el cambio es solo de pintura (scrim, color, sombra).
          const cls = await leerCls(page);
          console.log(`[TKT-047] CLS semilla ${ancho}px: ${cls}`);
          expect(cls ?? 0).toBeLessThanOrEqual(0.1);
        }
        await verificarContraste(page, testInfo, `${fondo}-${ancho}`);
        await sinViolacionesGraves(page);
      });
    }
  }

  test('AC_TKT047_02 con prefers-contrast: more el scrim se refuerza y el texto sigue legible sobre blanco', async ({
    page,
    baseURL,
  }, testInfo) => {
    await page.emulateMedia({ contrast: 'more' });
    await page.setViewportSize({ width: 320, height: 640 });
    await abrirInicio(page, 'blanca', baseURL ?? '');
    // overlay.lightbox (#0E1412 al 95 %) en lugar de overlay.scrim (78 %).
    const fondoFranja = await page
      .getByTestId('inicio-franja-texto')
      .evaluate((e) => getComputedStyle(e).backgroundColor);
    expect(Number(/,\s*([\d.]+)\)$/.exec(fondoFranja)?.[1] ?? '0')).toBeGreaterThanOrEqual(0.9);
    await verificarContraste(page, testInfo, 'blanca-320-contraste-alto');
    await sinViolacionesGraves(page);
  });
});
