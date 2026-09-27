import { TestBed } from '@angular/core/testing';

import { Chip } from './chip';

describe('Chip', () => {
  it('es un botón con nombre accesible «Quitar filtro …» que emite quitar', async () => {
    const fixture = TestBed.createComponent(Chip);
    fixture.componentRef.setInput('etiqueta', 'Tipo: Senderismo');
    fixture.componentRef.setInput('testId', 'chip-tipo');
    let quitado = 0;
    fixture.componentInstance.quitar.subscribe(() => quitado++);
    await fixture.whenStable();

    const boton = fixture.nativeElement.querySelector('button') as HTMLButtonElement;
    expect(boton.getAttribute('aria-label')).toBe('Quitar filtro Tipo: Senderismo');
    expect(boton.dataset['testid']).toBe('chip-tipo');
    expect(boton.textContent).toContain('Tipo: Senderismo');
    boton.click();
    expect(quitado).toBe(1);
  });
});
