import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { Enlace } from './enlace';

@Component({
  imports: [Enlace],
  template: `
    <a appEnlace href="/acerca-de" id="inline">Metodología</a>
    <a appEnlace variante="external" href="https://ejemplo.org" id="externo">Fuente</a>
    <a appEnlace variante="nav" href="/destinos" id="nav">Destinos</a>
  `,
})
class Anfitrion {}

describe('Enlace (appEnlace)', () => {
  it('aplica la variante y rel seguro en enlaces externos', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('#inline')?.className).toBe('bs-enlace bs-enlace--inline');
    expect(raiz.querySelector('#inline')?.hasAttribute('rel')).toBe(false);
    expect(raiz.querySelector('#externo')?.getAttribute('rel')).toBe('noopener noreferrer');
    expect(raiz.querySelector('#nav')?.className).toBe('bs-enlace bs-enlace--nav');
  });
});
