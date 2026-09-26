import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { Boton, VarianteBoton } from './boton';

@Component({
  imports: [Boton],
  template: `
    <button type="button" appBoton [variante]="variante()" [tamano]="tamano()" [cargando]="cargando()"
            [deshabilitadoEnfocable]="bloqueado()" (click)="clics = clics + 1">Publicar</button>
  `,
})
class Anfitrion {
  readonly variante = signal<VarianteBoton>('primary');
  readonly tamano = signal<'sm' | 'md' | 'lg'>('md');
  readonly cargando = signal(false);
  readonly bloqueado = signal(false);
  clics = 0;
}

describe('Boton (appBoton)', () => {
  async function crear() {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    return { fixture, boton: fixture.nativeElement.querySelector('button') as HTMLButtonElement };
  }

  it('aplica clases de variante y tamaño', async () => {
    const { fixture, boton } = await crear();
    expect(boton.className).toBe('bs-boton bs-boton--primary');
    fixture.componentInstance.variante.set('accent');
    fixture.componentInstance.tamano.set('lg');
    await fixture.whenStable();
    expect(boton.className).toBe('bs-boton bs-boton--accent bs-boton--lg');
    expect(boton.dataset['variante']).toBe('accent');
  });

  it('en carga marca aria-busy/aria-disabled y bloquea el clic (doble clic protegido)', async () => {
    const { fixture, boton } = await crear();
    fixture.componentInstance.cargando.set(true);
    await fixture.whenStable();
    expect(boton.getAttribute('aria-busy')).toBe('true');
    expect(boton.getAttribute('aria-disabled')).toBe('true');
    boton.click();
    expect(fixture.componentInstance.clics).toBe(0);
  });

  it('deshabilitado enfocable: sigue en el orden de foco pero no ejecuta la acción', async () => {
    const { fixture, boton } = await crear();
    boton.click();
    expect(fixture.componentInstance.clics).toBe(1);
    fixture.componentInstance.bloqueado.set(true);
    await fixture.whenStable();
    expect(boton.disabled).toBe(false);
    expect(boton.getAttribute('aria-disabled')).toBe('true');
    expect(boton.hasAttribute('aria-busy')).toBe(false);
    boton.click();
    expect(fixture.componentInstance.clics).toBe(1);
  });
});
