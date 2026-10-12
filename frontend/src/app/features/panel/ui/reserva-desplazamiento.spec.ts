import { ViewportScroller } from '@angular/common';
import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { HOLGURA_FOCO_PX, ReservaDesplazamiento, bordeFijado } from './reserva-desplazamiento';

/** Elemento con una altura simulada (jsdom no maqueta). */
function elementoDeAlto(alto: () => number): HTMLElement {
  const elemento = document.createElement('div');
  elemento.getBoundingClientRect = () => ({ height: alto() }) as DOMRect;
  document.body.appendChild(elemento);
  return elemento;
}

describe('ReservaDesplazamiento (TKT-070, WCAG 2.4.11)', () => {
  const estilo = document.documentElement.style;

  afterEach(() => {
    estilo.removeProperty('scroll-padding-top');
    estilo.removeProperty('scroll-padding-bottom');
    document.body.replaceChildren();
  });

  it('AC_TKT070_01 reserva la altura de la barra arriba (scroll-padding, variable y offset del Router) y la retira al cancelar', () => {
    const reserva = TestBed.inject(ReservaDesplazamiento);
    const scroller = TestBed.inject(ViewportScroller);
    const offset = vi.spyOn(scroller, 'setOffset');

    const cancelar = reserva.observar('barra', elementoDeAlto(() => 64.4), () => 'arriba');

    expect(estilo.getPropertyValue('scroll-padding-top')).toBe(`${65 + HOLGURA_FOCO_PX}px`);
    expect(estilo.getPropertyValue('--panel-alto-barra')).toBe('65px');
    const ultimo = offset.mock.lastCall?.[0];
    expect(typeof ultimo === 'function' ? ultimo() : ultimo).toEqual([0, 65 + HOLGURA_FOCO_PX]);

    cancelar();
    expect(estilo.getPropertyValue('scroll-padding-top')).toBe('');
    expect(estilo.getPropertyValue('--panel-alto-barra')).toBe('');
    expect(offset).toHaveBeenLastCalledWith([0, 0]);
  });

  it('AC_TKT070_03 suma las reservas por borde y vuelve a medir al redimensionar la ventana', () => {
    const reserva = TestBed.inject(ReservaDesplazamiento);
    let altoEstado = 120;
    let borde: 'arriba' | 'abajo' | null = 'abajo';
    const cancelarBarra = reserva.observar('barra', elementoDeAlto(() => 60), () => 'arriba');
    const cancelarEstado = reserva.observar('estado', elementoDeAlto(() => altoEstado), () => borde);

    expect(estilo.getPropertyValue('scroll-padding-top')).toBe(`${60 + HOLGURA_FOCO_PX}px`);
    expect(estilo.getPropertyValue('scroll-padding-bottom')).toBe(`${120 + HOLGURA_FOCO_PX}px`);

    // Cambio de punto de corte: la barra de estado pasa a fijarse arriba bajo la del panel.
    borde = 'arriba';
    altoEstado = 90;
    window.dispatchEvent(new Event('resize'));
    expect(reserva.total('arriba')).toBe(150);
    expect(estilo.getPropertyValue('scroll-padding-top')).toBe(`${150 + HOLGURA_FOCO_PX}px`);
    expect(estilo.getPropertyValue('scroll-padding-bottom')).toBe('');

    // En su columna (≥ xl) no tapa nada: deja de reservar.
    borde = null;
    window.dispatchEvent(new Event('resize'));
    expect(reserva.total('arriba')).toBe(60);

    cancelarEstado();
    cancelarBarra();
    expect(estilo.getPropertyValue('scroll-padding-top')).toBe('');
  });

  it('no reserva nada en el servidor', () => {
    TestBed.configureTestingModule({ providers: [{ provide: PLATFORM_ID, useValue: 'server' }] });
    const reserva = TestBed.inject(ReservaDesplazamiento);
    reserva.observar('barra', elementoDeAlto(() => 60), () => 'arriba')();
    expect(reserva.total('arriba')).toBe(0);
    expect(estilo.getPropertyValue('scroll-padding-top')).toBe('');
  });

  it('bordeFijado lee el borde pegado del estilo calculado', () => {
    const elemento = document.createElement('div');
    document.body.appendChild(elemento);
    expect(bordeFijado(elemento)).toBeNull();
    elemento.style.position = 'sticky';
    elemento.style.bottom = '0px';
    expect(bordeFijado(elemento)).toBe('abajo');
    elemento.style.top = '56px';
    expect(bordeFijado(elemento)).toBe('arriba');
    elemento.style.position = 'static';
    expect(bordeFijado(elemento)).toBeNull();
  });
});
