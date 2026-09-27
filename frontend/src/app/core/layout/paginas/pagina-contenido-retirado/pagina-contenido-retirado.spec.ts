import { Component } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { RESPONSE_INIT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { PaginaContenidoRetirado } from './pagina-contenido-retirado';

@Component({
  imports: [PaginaContenidoRetirado],
  template: `
    <app-pagina-contenido-retirado
      rutaListadoPadre="/destinos"
      etiquetaListadoPadre="Ver todos los destinos"
    >
      <article>Alternativa 1</article>
    </app-pagina-contenido-retirado>
  `,
})
class Anfitrion {}

describe('PaginaContenidoRetirado (SCR-024)', () => {
  it('HTTP 410, noindex, alternativas proyectadas y listado padre', async () => {
    const respuesta: { status?: number } = {};
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: RESPONSE_INIT, useValue: respuesta }],
    });
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;

    expect(respuesta.status).toBe(410);
    expect(TestBed.inject(DOCUMENT).title).toBe('Contenido no disponible — Brújula Salvaje');
    expect(raiz.querySelector('h1')?.textContent).toBe('Este contenido ya no está disponible');
    expect(raiz.textContent).toContain('Lo retiramos de Brújula Salvaje.');
    expect(raiz.querySelector('.rejilla article')?.textContent).toBe('Alternativa 1');
    const padre = raiz.querySelector('[data-testid="retirado-listado-padre"]');
    expect(padre?.getAttribute('href')).toBe('/destinos');
    expect(padre?.textContent?.trim()).toBe('Ver todos los destinos');
  });
});
