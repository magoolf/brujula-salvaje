import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { Insignia, VarianteInsignia } from './insignia';

@Component({
  imports: [Insignia],
  template: `<app-insignia [variante]="variante()">{{ texto() }}</app-insignia>`,
})
class Anfitrion {
  readonly variante = signal<VarianteInsignia>('publicado');
  readonly texto = signal('Publicado');
}

describe('Insignia', () => {
  it('muestra texto legible e icono de forma distinta por estado (no solo color)', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const insignia = fixture.nativeElement.querySelector('[data-testid="insignia"]') as HTMLElement;
    expect(insignia.textContent?.trim()).toBe('Publicado');
    expect(insignia.dataset['variante']).toBe('publicado');
    expect(insignia.querySelector('[data-testid="icono-circle-check"]')).not.toBeNull();

    fixture.componentInstance.variante.set('neutral');
    fixture.componentInstance.texto.set('12');
    await fixture.whenStable();
    expect(insignia.querySelector('svg')).toBeNull();
  });
});
