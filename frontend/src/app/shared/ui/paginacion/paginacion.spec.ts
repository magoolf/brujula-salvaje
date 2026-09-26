import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Paginacion } from './paginacion';
import { ElementoPagina, calcularPaginas, normalizarPagina, normalizarTotal } from './paginas';

function comoTexto(elementos: readonly ElementoPagina[]): string {
  return elementos.map((e) => (e.tipo === 'pagina' ? String(e.numero) : '…')).join(' ');
}

describe('calcularPaginas', () => {
  it.each([
    [5, 12, '1 … 4 5 6 … 12'],
    [1, 12, '1 2 … 12'],
    [12, 12, '1 … 11 12'],
    [3, 12, '1 2 3 4 … 12'],
    [1, 1, '1'],
    [2, 3, '1 2 3'],
    [5, 9, '1 … 4 5 6 … 9'],
    [4, 7, '1 2 3 4 5 6 7'],
    [3, 5, '1 2 3 4 5'],
  ])('página %i de %i → %s', (actual, total, esperado) => {
    expect(comoTexto(calcularPaginas(actual, total))).toBe(esperado);
  });

  it('normaliza entradas fuera de rango o no numéricas', () => {
    expect(normalizarTotal(0)).toBe(1);
    expect(normalizarTotal(Number.NaN)).toBe(1);
    expect(normalizarPagina(99, 5)).toBe(5);
    expect(normalizarPagina(-3, 5)).toBe(1);
    expect(normalizarPagina(Number.POSITIVE_INFINITY, 5)).toBe(1);
    expect(comoTexto(calcularPaginas(50, 3))).toBe('1 2 3');
  });
});

describe('Paginacion', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  async function crear(actual: number, total: number) {
    const fixture = TestBed.createComponent(Paginacion);
    fixture.componentRef.setInput('paginaActual', actual);
    fixture.componentRef.setInput('totalPaginas', total);
    await fixture.whenStable();
    return fixture.nativeElement as HTMLElement;
  }

  it('enlaces reales con ?pagina=, actual con aria-current y la página 1 sin parámetro', async () => {
    const raiz = await crear(2, 5);
    expect(raiz.querySelector('nav')?.getAttribute('aria-label')).toBe('Paginación');
    expect(raiz.querySelector('[aria-current="page"]')?.textContent?.trim()).toBe('2');
    expect(raiz.querySelector('[data-testid="paginacion-anterior"]')?.getAttribute('href')).toBe('/');
    expect(raiz.querySelector('[data-testid="paginacion-siguiente"]')?.getAttribute('href')).toBe('/?pagina=3');
    expect(raiz.querySelector('.resumen')?.textContent).toContain('Página 2 de 5');
  });

  it('en los extremos los controles quedan inactivos', async () => {
    const raiz = await crear(1, 3);
    expect(raiz.querySelector('[data-testid="paginacion-anterior"]')).toBeNull();
    expect(raiz.querySelectorAll('[aria-disabled="true"]')).toHaveLength(1);
    const ultima = await crear(3, 3);
    expect(ultima.querySelector('[data-testid="paginacion-siguiente"]')).toBeNull();
  });

  it('con una sola página no se renderiza', async () => {
    const raiz = await crear(1, 1);
    expect(raiz.querySelector('nav')).toBeNull();
  });
});
