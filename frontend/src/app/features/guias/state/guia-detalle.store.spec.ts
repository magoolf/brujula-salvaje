import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { GuiasRepositorio } from '../data/guias.repositorio';
import { GuiaDetalle } from '../domain/modelos';
import { GuiaDetalleStore } from './guia-detalle.store';

const GUIA = { slug: 'primeros-auxilios', titulo: 'Primeros auxilios' } as GuiaDetalle;

describe('GuiaDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<GuiaDetalle> = () => Promise.resolve(GUIA)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'primeros-auxilios' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        GuiaDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: GuiasRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(GuiaDetalleStore);
  }

  it('carga la guía del slug actual y el descargo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.guia()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('primeros-auxilios');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
  });

  it('410 → esRetirado con listado_padre por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/guias', alternativas: [] });
  });

  it('recargar() vuelve a pedir la guía', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.guia()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('GuiaDetalleStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ slug: 'a' }));
    const detalle = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        GuiaDetalleStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$ } },
        { provide: GuiasRepositorio, useValue: { detalle, textoDescargo: vi.fn().mockResolvedValue('Descargo') } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(GuiaDetalleStore), ruta$, detalle };
  }

  it('AC_TKT016_14 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, detalle } = crearHidratado({ ['recurso:guia-detalle:a']: SSR });
    expect(store.guia()).toEqual(SSR);
    TestBed.tick();
    expect(detalle).not.toHaveBeenCalled();
  });

  it('AC_TKT016_14 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, detalle } = crearHidratado({ ['recurso:guia-detalle:b']: SSR });
    await vi.waitFor(() => expect(store.guia()).toEqual(RED));
    expect(detalle).toHaveBeenCalledWith('a');
    detalle.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ slug: 'b' }));
    await vi.waitFor(() => expect(store.guia()).toEqual({ origen: 'red-2' }));
    expect(detalle).toHaveBeenLastCalledWith('b');
  });
});
