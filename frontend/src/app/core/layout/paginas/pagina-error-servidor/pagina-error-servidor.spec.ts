import { DOCUMENT } from '@angular/common';
import { RESPONSE_INIT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { PaginaErrorServidor } from './pagina-error-servidor';

describe('PaginaErrorServidor (SCR-025)', () => {
  it('HTTP 500, sin detalles técnicos, Reintentar recarga e Ir al inicio', async () => {
    const respuesta: { status?: number } = {};
    TestBed.configureTestingModule({ providers: [provideRouter([]), { provide: RESPONSE_INIT, useValue: respuesta }] });
    const fixture = TestBed.createComponent(PaginaErrorServidor);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const doc = TestBed.inject(DOCUMENT);

    expect(respuesta.status).toBe(500);
    expect(doc.title).toBe('Error del servidor — Brújula Salvaje');
    expect(raiz.querySelector('h1')?.textContent).toBe('Tuvimos un problema de nuestro lado');
    expect(raiz.querySelector('[data-testid="error-servidor-inicio"]')?.getAttribute('href')).toBe('/');

    const ubicacion = doc.defaultView?.location as Location;
    const recargar = vi.fn();
    vi.spyOn(doc, 'defaultView', 'get').mockReturnValue({ location: { ...ubicacion, reload: recargar } } as unknown as Window & typeof globalThis);
    (raiz.querySelector('[data-testid="error-servidor-reintentar"]') as HTMLButtonElement).click();
    expect(recargar).toHaveBeenCalledOnce();
  });
});
