import { DOCUMENT } from '@angular/common';
import { RESPONSE_INIT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { PaginaNoEncontrada } from './pagina-no-encontrada';

describe('PaginaNoEncontrada (SCR-023)', () => {
  it('HTTP 404 real, noindex, h1 único, búsqueda y rutas de salida', async () => {
    const respuesta: { status?: number } = {};
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: RESPONSE_INIT, useValue: respuesta }],
    });
    const fixture = TestBed.createComponent(PaginaNoEncontrada);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const doc = TestBed.inject(DOCUMENT);

    expect(respuesta.status).toBe(404);
    expect(doc.title).toBe('Página no encontrada — Brújula Salvaje');
    expect(doc.head.querySelector('meta[name="robots"]')?.getAttribute('content')).toBe(
      'noindex, nofollow',
    );
    expect(raiz.querySelectorAll('h1')).toHaveLength(1);
    expect(raiz.querySelector('h1')?.textContent).toBe('No encontramos esta página');
    expect(raiz.querySelector('form[role="search"]')).not.toBeNull();
    const salidas = Array.from(raiz.querySelectorAll('nav[aria-label="Rutas de salida"] a')).map(
      (a) => a.getAttribute('href'),
    );
    expect(salidas).toEqual(['/', '/destinos', '/guias']);
  });
});
