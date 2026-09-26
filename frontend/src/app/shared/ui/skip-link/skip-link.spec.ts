import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { SkipLink } from './skip-link';

@Component({
  imports: [SkipLink],
  template: `<app-skip-link destino="principal-prueba" /><main id="principal-prueba"><h1>Título</h1></main>`,
})
class Anfitrion {}

describe('SkipLink', () => {
  it('es un ancla al contenido principal que mueve el foco al activarse', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    document.body.appendChild(fixture.nativeElement);
    await fixture.whenStable();
    const enlace = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="skip-link"]') as HTMLAnchorElement;
    const principal = (fixture.nativeElement as HTMLElement).querySelector('main') as HTMLElement;
    principal.scrollIntoView = vi.fn();

    expect(enlace.getAttribute('href')).toBe('#principal-prueba');
    expect(enlace.textContent).toBe('Saltar al contenido principal');
    const evento = new MouseEvent('click', { cancelable: true, bubbles: true });
    enlace.dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(true);
    expect(principal.getAttribute('tabindex')).toBe('-1');
    expect(document.activeElement).toBe(principal);
    fixture.nativeElement.remove();
  });

  it('si el destino no existe deja la navegación nativa', async () => {
    const fixture = TestBed.createComponent(SkipLink);
    fixture.componentRef.setInput('destino', 'no-existe');
    await fixture.whenStable();
    const evento = new MouseEvent('click', { cancelable: true });
    (fixture.nativeElement as HTMLElement).querySelector('a')?.dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(false);
  });
});
