import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { EstadoVacio } from './estado-vacio';

@Component({
  imports: [EstadoVacio],
  template: `
    <app-estado-vacio titulo="Ningún destino cumple estos filtros">
      Quita el último filtro para ver más resultados.
      <span estado-salidas><a href="/destinos">Limpiar filtros</a><a href="/">Ir al inicio</a></span>
    </app-estado-vacio>
  `,
})
class Anfitrion {}

describe('EstadoVacio', () => {
  it('muestra h2 vinculado a la sección, explicación y ≥2 rutas de salida', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const seccion = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="estado-vacio"]') as HTMLElement;
    const h2 = seccion.querySelector('h2') as HTMLElement;
    expect(h2.textContent).toBe('Ningún destino cumple estos filtros');
    expect(seccion.getAttribute('aria-labelledby')).toBe(h2.id);
    expect(seccion.querySelectorAll('.salidas a')).toHaveLength(2);
    expect(seccion.querySelector('[data-testid="ilustracion-brujula"]')?.getAttribute('aria-hidden')).toBe('true');
  });
});
