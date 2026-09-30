import { TestBed } from '@angular/core/testing';

import { BotonGuardar } from './boton-guardar';

describe('BotonGuardar', () => {
  async function crear(guardado = false, deshabilitado = false) {
    const fixture = TestBed.createComponent(BotonGuardar);
    fixture.componentRef.setInput('titulo', 'Patagonia');
    fixture.componentRef.setInput('guardado', guardado);
    fixture.componentRef.setInput('deshabilitado', deshabilitado);
    let veces = 0;
    fixture.componentInstance.alternar.subscribe(() => veces++);
    await fixture.whenStable();
    return { fixture, veces: () => veces, boton: fixture.nativeElement.querySelector('button') as HTMLButtonElement };
  }

  it('sin guardar: aria-pressed=false y nombre accesible «Guardar {título}»', async () => {
    const { boton } = await crear(false);
    expect(boton.getAttribute('aria-pressed')).toBe('false');
    expect(boton.getAttribute('aria-label')).toBe('Guardar Patagonia');
  });

  it('guardado: aria-pressed=true y nombre accesible «Quitar {título} de guardados»', async () => {
    const { boton } = await crear(true);
    expect(boton.getAttribute('aria-pressed')).toBe('true');
    expect(boton.getAttribute('aria-label')).toBe('Quitar Patagonia de guardados');
  });

  it('al pulsar emite alternar', async () => {
    const { boton, veces } = await crear(false);
    boton.click();
    expect(veces()).toBe(1);
  });

  it('deshabilitado (ALT-011): no emite alternar al pulsar', async () => {
    const { boton, veces } = await crear(false, true);
    expect(boton.getAttribute('aria-disabled')).toBe('true');
    boton.click();
    expect(veces()).toBe(0);
  });
});
