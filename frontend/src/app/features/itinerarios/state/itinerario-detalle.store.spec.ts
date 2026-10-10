import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ItinerariosRepositorio } from '../data/itinerarios.repositorio';
import { ItinerarioDetalle } from '../domain/modelos';
import { ItinerarioDetalleStore } from './itinerario-detalle.store';

const ITINERARIO = { slug: 'w-trek', titulo: 'W Trek' } as ItinerarioDetalle;

describe('ItinerarioDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<ItinerarioDetalle> = () => Promise.resolve(ITINERARIO)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'w-trek' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        ItinerarioDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: ItinerariosRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(ItinerarioDetalleStore);
  }

  it('carga el itinerario del slug actual y el descargo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.itinerario()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('w-trek');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
    expect(store.esNoEncontrado()).toBe(false);
    expect(store.esRetirado()).toBe(false);
  });

  it('recarga al cambiar el slug', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.itinerario()).not.toBeNull());
    paramMap$.next(convertToParamMap({ slug: 'otro' }));
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledWith('otro'));
  });

  it('404 → esNoEncontrado', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });

  it('410 → esRetirado con alternativas y listado_padre del ErrorApi', async () => {
    const store = crear(() =>
      Promise.reject(
        new HttpErrorResponse({
          status: 410,
          error: {
            code: 'retirado',
            listado_padre: '/itinerarios',
            alternativas: [{ tipo: 'ITINERARIO', slug: 'otro', titulo: 'Otro', origen: 'CURADO' }],
          },
        }),
      ),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({
      rutaListadoPadre: '/itinerarios',
      alternativas: [expect.objectContaining({ slug: 'otro' })],
    });
  });

  it('410 sin listado_padre usa /itinerarios por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/itinerarios', alternativas: [] });
  });

  it('recargar() vuelve a pedir el itinerario', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.itinerario()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('ItinerarioDetalleStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ slug: 'a' }));
    const detalle = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        ItinerarioDetalleStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$ } },
        { provide: ItinerariosRepositorio, useValue: { detalle, textoDescargo: vi.fn().mockResolvedValue('Descargo') } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(ItinerarioDetalleStore), ruta$, detalle };
  }

  it('AC_TKT016_10 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, detalle } = crearHidratado({ ['recurso:itinerario-detalle:a']: SSR });
    expect(store.itinerario()).toEqual(SSR);
    TestBed.tick();
    expect(detalle).not.toHaveBeenCalled();
  });

  it('AC_TKT016_10 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, detalle } = crearHidratado({ ['recurso:itinerario-detalle:b']: SSR });
    await vi.waitFor(() => expect(store.itinerario()).toEqual(RED));
    expect(detalle).toHaveBeenCalledWith('a');
    detalle.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ slug: 'b' }));
    await vi.waitFor(() => expect(store.itinerario()).toEqual({ origen: 'red-2' }));
    expect(detalle).toHaveBeenLastCalledWith('b');
  });
});
