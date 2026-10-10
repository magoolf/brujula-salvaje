import { DOCUMENT } from '@angular/common';
import { EnvironmentInjector, createEnvironmentInjector, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import {
  ID_PRECARGA_PORTADA,
  PrecargaImagen,
  mantenerPrecargaImagen,
  precargaDe,
} from './precarga-portada';
import { SIZES_PORTADA } from './pagina-destino';

const DERIVADOS = [
  { url: '/m/d-400.avif', ancho: 400 },
  { url: '/m/d-800.avif', ancho: 800 },
  { url: '/m/d-400.webp', ancho: 400 },
  { url: '/m/d-400.jpeg', ancho: 400 },
  { url: '/m/d-800.jpeg', ancho: 800 },
];

describe('precargaDe (TKT-048)', () => {
  it('AC_TKT048_07: precarga el primer <source> (AVIF) con su type, srcset y sizes', () => {
    expect(precargaDe(DERIVADOS, SIZES_PORTADA)).toEqual({
      tipo: 'image/avif',
      srcset: '/m/d-400.avif 400w, /m/d-800.avif 800w',
      sizes: SIZES_PORTADA,
    });
  });

  it('AC_TKT048_07: solo JPEG -> precarga el respaldo sin type', () => {
    expect(precargaDe(DERIVADOS.slice(3), '100vw')).toEqual({
      tipo: null,
      srcset: '/m/d-400.jpeg 400w, /m/d-800.jpeg 800w',
      sizes: '100vw',
    });
  });

  it('sin derivados no hay precarga', () => {
    expect(precargaDe([], '100vw')).toBeNull();
  });

  it('el sizes de la portada sigue el contenedor (máx. 1184px) y no 100vw', () => {
    expect(SIZES_PORTADA.startsWith('(min-width: 80rem) 1184px')).toBe(true);
    expect(SIZES_PORTADA.endsWith('calc(100vw - 2rem)')).toBe(true);
  });
});

describe('mantenerPrecargaImagen (TKT-048)', () => {
  function enlaces(): HTMLLinkElement[] {
    return Array.from(
      TestBed.inject(DOCUMENT).head.querySelectorAll<HTMLLinkElement>(`link#${ID_PRECARGA_PORTADA}`),
    );
  }

  afterEach(() => enlaces().forEach((e) => e.remove()));

  it('AC_TKT048_07: crea un único <link rel=preload as=image fetchpriority=high>, lo actualiza y lo retira al destruirse', () => {
    const precarga = signal<PrecargaImagen | null>({
      tipo: 'image/avif',
      srcset: '/a-400.avif 400w',
      sizes: '100vw',
    });
    const inyector = createEnvironmentInjector([], TestBed.inject(EnvironmentInjector));
    inyector.runInContext(() => mantenerPrecargaImagen(precarga));
    TestBed.tick();

    expect(enlaces()).toHaveLength(1);
    const enlace = enlaces()[0];
    expect(enlace.getAttribute('rel')).toBe('preload');
    expect(enlace.getAttribute('as')).toBe('image');
    expect(enlace.getAttribute('fetchpriority')).toBe('high');
    expect(enlace.getAttribute('type')).toBe('image/avif');
    expect(enlace.getAttribute('imagesrcset')).toBe('/a-400.avif 400w');
    expect(enlace.getAttribute('imagesizes')).toBe('100vw');

    precarga.set({ tipo: null, srcset: '/b-400.jpeg 400w', sizes: '50vw' });
    TestBed.tick();
    expect(enlaces()).toHaveLength(1);
    expect(enlaces()[0]).toBe(enlace); // reutiliza el elemento (hidratación sin otra descarga)
    expect(enlace.hasAttribute('type')).toBe(false);
    expect(enlace.getAttribute('imagesrcset')).toBe('/b-400.jpeg 400w');

    precarga.set(null);
    TestBed.tick();
    expect(enlaces()).toHaveLength(0);

    precarga.set({ tipo: 'image/webp', srcset: '/c-400.webp 400w', sizes: '100vw' });
    TestBed.tick();
    expect(enlaces()).toHaveLength(1);
    inyector.destroy();
    expect(enlaces()).toHaveLength(0);
  });
});
