import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ShellPublico } from './shell-publico';

describe('ShellPublico (GI-01..GI-03)', () => {
  it('SkipLink → cabecera → main#contenido-principal → pie, con landmarks', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(ShellPublico);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;

    expect(Array.from(raiz.children).map((e) => e.tagName.toLowerCase())).toEqual([
      'app-skip-link',
      'app-cabecera-sitio',
      'main',
      'app-pie-sitio',
    ]);
    const main = raiz.querySelector('main') as HTMLElement;
    expect(main.id).toBe('contenido-principal');
    expect(main.getAttribute('tabindex')).toBe('-1');
    expect(main.querySelector('router-outlet')).not.toBeNull();
    expect(raiz.querySelector('[data-testid="skip-link"]')?.getAttribute('href')).toBe(
      '#contenido-principal',
    );
    expect(raiz.querySelector('header')).not.toBeNull();
    expect(raiz.querySelector('footer')).not.toBeNull();
  });
});
