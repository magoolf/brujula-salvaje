import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MedidorDificultad } from '../medidor-dificultad/medidor-dificultad';
import { MedidorPresupuesto } from '../medidor-presupuesto/medidor-presupuesto';
import { normalizarNivel, segmentos, textoAccesible } from './medidor';

describe('medidor (lógica pura)', () => {
  it('normalizarNivel acota y redondea', () => {
    expect(normalizarNivel(3, 5)).toBe(3);
    expect(normalizarNivel(7, 5)).toBe(5);
    expect(normalizarNivel(0, 4)).toBe(1);
    expect(normalizarNivel(2.6, 4)).toBe(3);
    expect(normalizarNivel(Number.NaN, 5)).toBeNull();
    expect(normalizarNivel(null, 5)).toBeNull();
  });

  it('segmentos llenos hasta el nivel', () => {
    expect(segmentos(2, 4).map((s) => s.lleno)).toEqual([true, true, false, false]);
    expect(segmentos(null, 3).every((s) => !s.lleno)).toBe(true);
  });

  it('texto accesible con y sin etiqueta', () => {
    expect(textoAccesible('Dificultad', 3, 5, 'Exigente')).toBe('Dificultad 3 de 5: Exigente');
    expect(textoAccesible('Presupuesto', 2, 4, ' ')).toBe('Presupuesto 2 de 4');
    expect(textoAccesible('Dificultad', null, 5, null)).toBe('Dificultad sin dato');
  });
});

describe('MedidorDificultad / MedidorPresupuesto', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  it('dificultad completa: 5 segmentos, texto accesible y enlace a la escala', async () => {
    const fixture = TestBed.createComponent(MedidorDificultad);
    fixture.componentRef.setInput('valor', 3);
    fixture.componentRef.setInput('etiqueta', 'Exigente');
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('[data-testid="medidor-dificultad"]')).not.toBeNull();
    expect(raiz.querySelectorAll('.segmento')).toHaveLength(5);
    expect(raiz.querySelectorAll('.segmento--lleno')).toHaveLength(3);
    expect(raiz.querySelector('.bs-solo-lectores')?.textContent).toBe('Dificultad 3 de 5: Exigente');
    expect(raiz.querySelector('.segmentos')?.getAttribute('aria-hidden')).toBe('true');
    expect(raiz.querySelector('a')?.getAttribute('href')).toBe('/acerca-de#escala-de-dificultad');
  });

  it('presupuesto compacto: 4 segmentos, sin enlace ni símbolos de moneda', async () => {
    const fixture = TestBed.createComponent(MedidorPresupuesto);
    fixture.componentRef.setInput('valor', 2);
    fixture.componentRef.setInput('compacto', true);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelectorAll('.segmento')).toHaveLength(4);
    expect(raiz.querySelector('a')).toBeNull();
    expect(raiz.textContent).toContain('2/4');
    expect(raiz.textContent).not.toMatch(/[$€]/);
  });

  it('sin valor muestra un guion y «sin dato»', async () => {
    const fixture = TestBed.createComponent(MedidorPresupuesto);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Presupuesto sin dato');
  });
});
