import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { PaginaEnPreparacion } from './pagina-en-preparacion';

describe('PaginaEnPreparacion (estado vacío de SCR-001)', () => {
  it('h1, CTA Explorar destinos, búsqueda, enlaces institucionales y JSON-LD WebSite', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(PaginaEnPreparacion);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const doc = TestBed.inject(DOCUMENT);

    expect(raiz.querySelector('h1')?.textContent).toBe('Contenido en preparación');
    expect(raiz.querySelector('[data-testid="preparacion-explorar"]')?.getAttribute('href')).toBe('/destinos');
    expect(raiz.querySelector('form[role="search"]')).not.toBeNull();
    expect(raiz.querySelector('[data-testid="preparacion-acerca-de"]')?.getAttribute('href')).toBe('/acerca-de');
    expect(doc.title).toBe('Inicio — Brújula Salvaje');
    expect(JSON.parse(doc.head.querySelector('#bs-json-ld')?.textContent ?? '{}')['@type']).toBe('WebSite');
    expect(doc.head.querySelector('#bs-canonica')?.getAttribute('href')).toMatch(/\/$/);
  });
});
