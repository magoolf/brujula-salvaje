import { ImagenVista } from '../domain/modelos';
import { SIZES_IMAGEN_PRINCIPAL, planImagenPrincipal } from './imagen-principal';

function imagen(urls: readonly string[]): ImagenVista {
  return {
    // Como los mappers: el `src` es el primer derivado de la lista (un AVIF pequeño).
    src: urls[0],
    alt: 'Fitz Roy al amanecer',
    ancho: 1920,
    alto: 1080,
    derivados: urls.map((url) => ({ url, ancho: Number(/-(\d+)\./.exec(url)?.[1]) })),
  };
}

describe('planImagenPrincipal (TKT-048)', () => {
  it('AC_TKT048_06: AVIF y WebP en <source> con srcset por ancho y JPEG de respaldo', () => {
    const plan = planImagenPrincipal(
      imagen([
        '/m/h-400.avif',
        '/m/h-800.avif',
        '/m/h-400.webp',
        '/m/h-800.webp',
        '/m/h-400.jpeg',
        '/m/h-800.jpeg',
      ]),
    );

    expect(plan).not.toBeNull();
    expect(plan?.alt).toBe('Fitz Roy al amanecer');
    expect(plan?.fuentes.map((f) => [f.tipo, f.srcset])).toEqual([
      ['image/avif', '/m/h-400.avif 400w, /m/h-800.avif 800w'],
      ['image/webp', '/m/h-400.webp 400w, /m/h-800.webp 800w'],
    ]);
    expect(plan?.srcset).toBe('/m/h-400.jpeg 400w, /m/h-800.jpeg 800w');
    // El `src` del <img> nunca es un AVIF: un navegador sin AVIF lo descargaría sin poder pintarlo.
    expect(plan?.src).toBe('/m/h-400.jpeg');
    expect(SIZES_IMAGEN_PRINCIPAL).toBe('100vw');
  });

  it('AC_TKT048_06: sin JPEG, el respaldo es el formato menos exigente y no se repite en <source>', () => {
    const plan = planImagenPrincipal(imagen(['/m/h-400.avif', '/m/h-400.webp', '/m/h-800.webp']));

    expect(plan?.fuentes.map((f) => f.tipo)).toEqual(['image/avif']);
    expect(plan?.srcset).toBe('/m/h-400.webp 400w, /m/h-800.webp 800w');
    expect(plan?.src).toBe('/m/h-400.webp');
  });

  it('sin imagen no hay plan', () => {
    expect(planImagenPrincipal(null)).toBeNull();
  });
});
