import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { NAVEGACION_INSTITUCIONAL, NAVEGACION_PRINCIPAL } from '../navegacion';
import { PieSitio } from './pie-sitio';

describe('PieSitio (GI-02)', () => {
  it('footer con Explorar, Institucional (orden fijo) y la frase de privacidad enlazada a cookies', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(PieSitio);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('footer')).not.toBeNull();

    const explorar = raiz.querySelector('nav[aria-labelledby="pie-explorar"]') as HTMLElement;
    expect(explorar.querySelectorAll('a')).toHaveLength(NAVEGACION_PRINCIPAL.length);

    const institucional = Array.from(
      raiz.querySelectorAll('nav[aria-labelledby="pie-institucional"] a'),
    ).map((a) => a.getAttribute('href'));
    expect(institucional).toEqual(NAVEGACION_INSTITUCIONAL.map((e) => e.ruta));
    expect(institucional).not.toContain('/glosario');

    const privacidad = raiz.querySelector('[data-testid="pie-sin-cookies"]');
    expect(privacidad?.getAttribute('href')).toBe('/politica-de-cookies');
    expect(privacidad?.textContent).toBe('Sin cookies ni rastreadores en el sitio público');
  });
});
