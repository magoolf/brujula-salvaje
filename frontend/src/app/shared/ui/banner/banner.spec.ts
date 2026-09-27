import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { Banner, VarianteBanner } from './banner';

@Component({
  imports: [Banner],
  template: `
    <app-banner
      [variante]="variante()"
      titulo="Guardado"
      [permitirCerrar]="cerrable()"
      (cerrado)="cierres = cierres + 1"
    >
      Guardaste el borrador.
      <a banner-accion href="/panel">Ver en el sitio</a>
    </app-banner>
  `,
})
class Anfitrion {
  readonly variante = signal<VarianteBanner>('success');
  readonly cerrable = signal(true);
  cierres = 0;
}

describe('Banner (InlineAlert)', () => {
  it('role=status en éxito, con acción proyectada y descartable', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const banner = raiz.querySelector('[data-testid="banner"]') as HTMLElement;
    expect(banner.getAttribute('role')).toBe('status');
    expect(banner.textContent).toContain('Guardado');
    expect(banner.querySelector('.acciones a')?.textContent).toBe('Ver en el sitio');

    (raiz.querySelector('button[aria-label="Cerrar aviso"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(raiz.querySelector('[data-testid="banner"]')).toBeNull();
    expect(fixture.componentInstance.cierres).toBe(1);
  });

  it('role=alert en error y no descartable aunque se pida', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    fixture.componentInstance.variante.set('error');
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('[data-testid="banner"]')?.getAttribute('role')).toBe('alert');
    expect(raiz.querySelector('button[aria-label="Cerrar aviso"]')).toBeNull();
    fixture.componentInstance.variante.set('warning');
    await fixture.whenStable();
    expect(raiz.querySelector('[data-testid="banner"]')?.getAttribute('role')).toBe('status');
  });
});
