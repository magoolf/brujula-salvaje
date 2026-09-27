import { TestBed } from '@angular/core/testing';

import { Icono, aNodoPlano } from './icono';
import { ICONOS_LUCIDE } from './iconos-lucide';

describe('Icono', () => {
  it('renderiza el SVG decorativo del icono (aria-hidden, currentColor, sin innerHTML)', async () => {
    const fixture = TestBed.createComponent(Icono);
    fixture.componentRef.setInput('nombre', 'circle-alert');
    await fixture.whenStable();
    const svg = fixture.nativeElement.querySelector('svg') as SVGElement;
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.getAttribute('stroke')).toBe('currentColor');
    expect(svg.getAttribute('width')).toBe('20');
    expect(svg.dataset['testid']).toBe('icono-circle-alert');
    expect(svg.querySelectorAll('circle')).toHaveLength(1);
    expect(svg.querySelectorAll('line')).toHaveLength(2);
  });

  it('con etiqueta se expone como imagen con nombre accesible', async () => {
    const fixture = TestBed.createComponent(Icono);
    fixture.componentRef.setInput('nombre', 'search');
    fixture.componentRef.setInput('etiqueta', 'Buscar');
    fixture.componentRef.setInput('tamano', 24);
    await fixture.whenStable();
    const svg = fixture.nativeElement.querySelector('svg') as SVGElement;
    expect(svg.getAttribute('role')).toBe('img');
    expect(svg.getAttribute('aria-label')).toBe('Buscar');
    expect(svg.hasAttribute('aria-hidden')).toBe(false);
    expect(svg.querySelectorAll('path')).toHaveLength(1);
  });

  it('todos los iconos vendorizados tienen nodos válidos', () => {
    for (const nodos of Object.values(ICONOS_LUCIDE)) {
      for (const nodo of nodos) {
        expect(['path', 'circle', 'line']).toContain(aNodoPlano(nodo).tipo);
      }
    }
  });
});
