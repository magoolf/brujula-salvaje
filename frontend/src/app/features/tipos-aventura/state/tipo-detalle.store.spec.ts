import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { TiposAventuraRepositorio } from '../data/tipos-aventura.repositorio';
import { TipoDetalle } from '../domain/modelos';
import { TipoDetalleStore } from './tipo-detalle.store';

const TIPO = { slug: 'buceo', titulo: 'Buceo' } as TipoDetalle;

describe('TipoDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<TipoDetalle> = () => Promise.resolve(TIPO)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'buceo' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        TipoDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: TiposAventuraRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(TipoDetalleStore);
  }

  it('carga el tipo del slug actual y el descargo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.tipo()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('buceo');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
  });

  it('404 → esNoEncontrado', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });

  it('410 → esRetirado con listado_padre por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/tipos-de-aventura', alternativas: [] });
  });

  it('recargar() vuelve a pedir el tipo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.tipo()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('TipoDetalleStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ slug: 'a' }));
    const detalle = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        TipoDetalleStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$ } },
        { provide: TiposAventuraRepositorio, useValue: { detalle, textoDescargo: vi.fn().mockResolvedValue('Descargo') } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(TipoDetalleStore), ruta$, detalle };
  }

  it('AC_TKT016_12 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, detalle } = crearHidratado({ ['recurso:tipo-detalle:a']: SSR });
    expect(store.tipo()).toEqual(SSR);
    TestBed.tick();
    expect(detalle).not.toHaveBeenCalled();
  });

  it('AC_TKT016_12 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, detalle } = crearHidratado({ ['recurso:tipo-detalle:b']: SSR });
    await vi.waitFor(() => expect(store.tipo()).toEqual(RED));
    expect(detalle).toHaveBeenCalledWith('a');
    detalle.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ slug: 'b' }));
    await vi.waitFor(() => expect(store.tipo()).toEqual({ origen: 'red-2' }));
    expect(detalle).toHaveBeenLastCalledWith('b');
  });
});
