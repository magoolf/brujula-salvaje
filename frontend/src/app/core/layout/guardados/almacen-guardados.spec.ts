import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { AlmacenGuardados } from './almacen-guardados';

describe('AlmacenGuardados', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
  });

  it('está disponible en el navegador (jsdom) y lee/escribe JSON', () => {
    const almacen = TestBed.inject(AlmacenGuardados);
    expect(almacen.estaDisponible()).toBe(true);
    expect(almacen.leer()).toEqual([]);

    const elemento = { tipo: 'DESTINO' as const, slug: 'patagonia', titulo: 'Patagonia', pais: null };
    expect(almacen.escribir([elemento])).toBe(true);
    expect(almacen.leer()).toEqual([elemento]);
  });

  it('descarta entradas inválidas al leer (THREAT-026) sin lanzar', () => {
    localStorage.setItem('bs-guardados-v1', JSON.stringify([{ tipo: 'DESTINO' }, 'texto-suelto']));
    const almacen = TestBed.inject(AlmacenGuardados);
    expect(almacen.leer()).toEqual([]);
  });

  it('devuelve lista vacía si el contenido guardado no es JSON válido', () => {
    localStorage.setItem('bs-guardados-v1', '{no es json');
    const almacen = TestBed.inject(AlmacenGuardados);
    expect(almacen.leer()).toEqual([]);
  });

  it('devuelve lista vacía si el contenido guardado no es un array', () => {
    localStorage.setItem('bs-guardados-v1', JSON.stringify({ no: 'es un array' }));
    const almacen = TestBed.inject(AlmacenGuardados);
    expect(almacen.leer()).toEqual([]);
  });

  it('no está disponible fuera del navegador (SSR)', () => {
    TestBed.overrideProvider(PLATFORM_ID, { useValue: 'server' });
    const almacen = TestBed.inject(AlmacenGuardados);
    expect(almacen.estaDisponible()).toBe(false);
    expect(almacen.leer()).toEqual([]);
    expect(almacen.escribir([])).toBe(false);
  });
});
