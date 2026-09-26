import { TestBed } from '@angular/core/testing';

import { ImagenResponsiva, construirSrcset } from './imagen-responsiva';

describe('construirSrcset', () => {
  it('ordena por ancho, elimina duplicados e inválidos y codifica la URL', () => {
    expect(
      construirSrcset([
        { url: '/media/publico/a 960.webp', ancho: 960 },
        { url: '/media/publico/a-320.webp', ancho: 320 },
        { url: '/media/publico/dup.webp', ancho: 320 },
        { url: '', ancho: 480 },
        { url: '/x.webp', ancho: 0 },
      ]),
    ).toBe('/media/publico/a-320.webp 320w, /media/publico/a%20960.webp 960w');
    expect(construirSrcset([])).toBe('');
  });
});

describe('ImagenResponsiva', () => {
  async function crear(entradas: Record<string, unknown>) {
    const fixture = TestBed.createComponent(ImagenResponsiva);
    for (const [clave, valor] of Object.entries(entradas))
      fixture.componentRef.setInput(clave, valor);
    await fixture.whenStable();
    return fixture;
  }

  it('lazy por defecto, dimensiones reservadas y srcset + sizes', async () => {
    const fixture = await crear({
      src: '/media/publico/a-640.webp',
      alt: 'Glaciar',
      ancho: 640,
      alto: 480,
      derivados: [{ url: '/media/publico/a-320.webp', ancho: 320 }],
      sizes: '50vw',
    });
    const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
    expect(img.getAttribute('loading')).toBe('lazy');
    expect(img.getAttribute('decoding')).toBe('async');
    expect(img.hasAttribute('fetchpriority')).toBe(false);
    expect(img.getAttribute('width')).toBe('640');
    expect(img.getAttribute('height')).toBe('480');
    expect(img.getAttribute('srcset')).toBe('/media/publico/a-320.webp 320w');
    expect(img.getAttribute('sizes')).toBe('50vw');
    expect(img.alt).toBe('Glaciar');
    expect(
      ((fixture.nativeElement as HTMLElement).querySelector('.marco') as HTMLElement).style
        .aspectRatio,
    ).toBe('640 / 480');
  });

  it('imagen LCP: eager + fetchpriority=high, sin srcset si no hay derivados', async () => {
    const fixture = await crear({
      src: '/h.webp',
      alt: 'Portada',
      ancho: 1600,
      alto: 900,
      prioritaria: true,
      relacion: '16 / 9',
    });
    const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
    expect(img.getAttribute('loading')).toBe('eager');
    expect(img.getAttribute('fetchpriority')).toBe('high');
    expect(img.hasAttribute('srcset')).toBe(false);
    expect(img.hasAttribute('sizes')).toBe(false);
  });

  it('si falla la carga conserva el marco y muestra el texto alternativo (ALT-009)', async () => {
    const fixture = await crear({
      src: '/roto.webp',
      alt: 'Laguna al amanecer',
      ancho: 4,
      alto: 3,
    });
    (fixture.nativeElement as HTMLElement).querySelector('img')?.dispatchEvent(new Event('error'));
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('img')).toBeNull();
    expect(raiz.querySelector('[data-testid="imagen-fallida"]')?.textContent).toBe(
      'Laguna al amanecer',
    );
  });

  it('imagen decorativa que falla no muestra texto', async () => {
    const fixture = await crear({ src: '/roto.webp', alt: '', ancho: 4, alto: 3 });
    (fixture.nativeElement as HTMLElement).querySelector('img')?.dispatchEvent(new Event('error'));
    await fixture.whenStable();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('[data-testid="imagen-fallida"]'),
    ).toBeNull();
  });
});
