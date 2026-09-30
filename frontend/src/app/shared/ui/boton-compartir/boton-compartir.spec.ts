import { TestBed } from '@angular/core/testing';

import { BotonCompartir } from './boton-compartir';

describe('BotonCompartir', () => {
  async function crear(compartiendo = false) {
    const fixture = TestBed.createComponent(BotonCompartir);
    fixture.componentRef.setInput('titulo', 'Patagonia');
    fixture.componentRef.setInput('compartiendo', compartiendo);
    let veces = 0;
    fixture.componentInstance.compartir.subscribe(() => veces++);
    await fixture.whenStable();
    return { boton: fixture.nativeElement.querySelector('button') as HTMLButtonElement, veces: () => veces };
  }

  it('tiene nombre accesible «Compartir {título}» y emite compartir al pulsar', async () => {
    const { boton, veces } = await crear();
    expect(boton.getAttribute('aria-label')).toBe('Compartir Patagonia');
    boton.click();
    expect(veces()).toBe(1);
  });

  it('mientras comparte, el botón queda deshabilitado', async () => {
    const { boton } = await crear(true);
    expect(boton.disabled).toBe(true);
  });
});
