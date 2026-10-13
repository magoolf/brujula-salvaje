import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ColeccionesRepositorio } from '../data/colecciones.repositorio';
import { ColeccionDetalle } from '../domain/modelos';
import { ColeccionDetalleStore } from './coleccion-detalle.store';

const COLECCION = { slug: 'mejores-treks', titulo: 'Los mejores treks' } as ColeccionDetalle;

describe('ColeccionDetalleStore', () => {
  function crear(detalleImpl: () => Promise<ColeccionDetalle> = () => Promise.resolve(COLECCION)) {
    const paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'mejores-treks' }));
    const detalle = vi.fn(detalleImpl);
    TestBed.configureTestingModule({
      providers: [
        ColeccionDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: ColeccionesRepositorio, useValue: { detalle } },
      ],
    });
    return { store: TestBed.inject(ColeccionDetalleStore), detalle };
  }

  it('carga la colección del slug actual', async () => {
    const { store, detalle } = crear();
    await vi.waitFor(() => expect(store.coleccion()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('mejores-treks');
  });

  it('404 → esNoEncontrado', async () => {
    const { store } = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });

  it('410 → esRetirado con listado_padre por defecto', async () => {
    const { store } = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/colecciones', alternativas: [] });
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('ColeccionDetalleStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ slug: 'a' }));
    const detalle = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        ColeccionDetalleStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$ } },
        { provide: ColeccionesRepositorio, useValue: { detalle } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(ColeccionDetalleStore), ruta$, detalle };
  }

  it('AC_TKT016_16 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, detalle } = crearHidratado({ ['recurso:coleccion-detalle:a']: SSR });
    expect(store.coleccion()).toEqual(SSR);
    TestBed.tick();
    expect(detalle).not.toHaveBeenCalled();
  });

  it('AC_TKT016_16 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, detalle } = crearHidratado({ ['recurso:coleccion-detalle:b']: SSR });
    await vi.waitFor(() => expect(store.coleccion()).toEqual(RED));
    expect(detalle).toHaveBeenCalledWith('a');
    detalle.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ slug: 'b' }));
    await vi.waitFor(() => expect(store.coleccion()).toEqual({ origen: 'red-2' }));
    expect(detalle).toHaveBeenLastCalledWith('b');
  });
});
