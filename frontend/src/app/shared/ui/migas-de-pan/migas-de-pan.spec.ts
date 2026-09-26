import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MigasDePan } from './migas-de-pan';

describe('MigasDePan (GI-03)', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  it('nav etiquetada con ol; el último elemento es la página actual sin enlace; versión compacta al padre', async () => {
    const fixture = TestBed.createComponent(MigasDePan);
    fixture.componentRef.setInput('migas', [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Destinos', ruta: '/destinos' },
      { etiqueta: 'Patagonia' },
    ]);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const nav = raiz.querySelector('nav');
    expect(nav?.getAttribute('aria-label')).toBe('Migas de pan');
    const items = raiz.querySelectorAll('ol > li');
    expect(items).toHaveLength(3);
    expect(items[2].querySelector('a')).toBeNull();
    expect(items[2].querySelector('[aria-current="page"]')?.textContent).toBe('Patagonia');
    expect(items[1].querySelector('a')?.getAttribute('href')).toBe('/destinos');
    const padre = raiz.querySelector('[data-testid="migas-de-pan-padre"]');
    expect(padre?.getAttribute('href')).toBe('/destinos');
    expect(padre?.textContent).toContain('Destinos');
  });

  it('sin nivel padre enlazable no muestra la versión compacta', async () => {
    const fixture = TestBed.createComponent(MigasDePan);
    fixture.componentRef.setInput('migas', [{ etiqueta: 'Inicio' }]);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="migas-de-pan-padre"]')).toBeNull();
  });
});
