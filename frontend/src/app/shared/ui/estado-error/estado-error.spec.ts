import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { EstadoError } from './estado-error';

describe('EstadoError (ST-ERROR)', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  it('mensaje comprensible, Reintentar y enlace a Inicio; sin role=alert por defecto', async () => {
    const fixture = TestBed.createComponent(EstadoError);
    let reintentos = 0;
    fixture.componentInstance.reintentar.subscribe(() => reintentos++);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const bloque = raiz.querySelector('[data-testid="estado-error"]') as HTMLElement;
    expect(bloque.hasAttribute('role')).toBe(false);
    expect(bloque.textContent).toContain('No pudimos cargar esta sección');
    expect(raiz.querySelector('a')?.getAttribute('href')).toBe('/');
    (raiz.querySelector('[data-testid="estado-error-reintentar"]') as HTMLButtonElement).click();
    expect(reintentos).toBe(1);
  });

  it('tras una acción del usuario se anuncia (role=alert) y muestra «Reintentando…»', async () => {
    const fixture = TestBed.createComponent(EstadoError);
    fixture.componentRef.setInput('anunciar', true);
    fixture.componentRef.setInput('reintentando', true);
    fixture.componentRef.setInput('rutaSalida', '/panel');
    fixture.componentRef.setInput('etiquetaSalida', 'Ir al tablero');
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('[data-testid="estado-error"]')?.getAttribute('role')).toBe('alert');
    const boton = raiz.querySelector(
      '[data-testid="estado-error-reintentar"]',
    ) as HTMLButtonElement;
    expect(boton.textContent).toContain('Reintentando…');
    expect(boton.getAttribute('aria-busy')).toBe('true');
    expect(raiz.querySelector('a')?.textContent).toBe('Ir al tablero');
  });
});
