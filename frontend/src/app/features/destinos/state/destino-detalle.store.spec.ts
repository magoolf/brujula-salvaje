import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { DestinosRepositorio } from '../data/destinos.repositorio';
import { DestinoDetalle } from '../domain/modelos';
import { DestinoDetalleStore } from './destino-detalle.store';

const DESTINO = { slug: 'patagonia', titulo: 'Patagonia' } as DestinoDetalle;

describe('DestinoDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<DestinoDetalle> = () => Promise.resolve(DESTINO)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'patagonia' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        DestinoDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: DestinosRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(DestinoDetalleStore);
  }

  it('carga el destino del slug actual y el descargo de responsabilidad', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.destino()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('patagonia');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
    expect(store.esNoEncontrado()).toBe(false);
    expect(store.esRetirado()).toBe(false);
    expect(store.retirado()).toBeNull();
    expect(store.cargando()).toBe(false);
  });

  it('recarga al cambiar el slug (navegación entre fichas)', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.destino()).not.toBeNull());
    paramMap$.next(convertToParamMap({ slug: 'otro' }));
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledWith('otro'));
  });

  it('404 → esNoEncontrado, sin datos de retirado', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
    expect(store.esRetirado()).toBe(false);
  });

  it('410 → esRetirado, expone alternativas y listado_padre desde el ErrorApi', async () => {
    const store = crear(() =>
      Promise.reject(
        new HttpErrorResponse({
          status: 410,
          error: {
            code: 'retirado',
            listado_padre: '/destinos',
            alternativas: [{ tipo: 'DESTINO', slug: 'otro', titulo: 'Otro', origen: 'CURADO' }],
          },
        }),
      ),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({
      rutaListadoPadre: '/destinos',
      alternativas: [expect.objectContaining({ slug: 'otro' })],
    });
  });

  it('410 sin listado_padre en el ErrorApi: usa /destinos por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/destinos', alternativas: [] });
  });

  it('recargar() vuelve a pedir el destino', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.destino()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('DestinoDetalleStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ slug: 'a' }));
    const detalle = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        DestinoDetalleStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$ } },
        { provide: DestinosRepositorio, useValue: { detalle, textoDescargo: vi.fn().mockResolvedValue('Descargo') } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(DestinoDetalleStore), ruta$, detalle };
  }

  it('AC_TKT016_03 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, detalle } = crearHidratado({ ['recurso:destino-detalle:a']: SSR });
    expect(store.destino()).toEqual(SSR);
    TestBed.tick();
    expect(detalle).not.toHaveBeenCalled();
  });

  it('AC_TKT016_03 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, detalle } = crearHidratado({ ['recurso:destino-detalle:b']: SSR });
    await vi.waitFor(() => expect(store.destino()).toEqual(RED));
    expect(detalle).toHaveBeenCalledWith('a');
    detalle.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ slug: 'b' }));
    await vi.waitFor(() => expect(store.destino()).toEqual({ origen: 'red-2' }));
    expect(detalle).toHaveBeenLastCalledWith('b');
  });
});
