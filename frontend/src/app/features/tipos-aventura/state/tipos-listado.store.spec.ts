import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { TiposAventuraRepositorio } from '../data/tipos-aventura.repositorio';
import { PaginaTipos } from '../domain/modelos';
import { TiposListadoStore } from './tipos-listado.store';

const PAGINA: PaginaTipos = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('TiposListadoStore', () => {
  let queryParamMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let listar: ReturnType<typeof vi.fn>;

  function crear(params: Record<string, string> = {}) {
    queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    listar = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        TiposListadoStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: TiposAventuraRepositorio, useValue: { listar } },
      ],
    });
    return TestBed.inject(TiposListadoStore);
  }

  it('pide la página 1 sin parámetros', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(listar).toHaveBeenCalledWith(1);
  });

  it('reacciona a cambios de página en la URL', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    queryParamMap$.next(convertToParamMap({ pagina: '3' }));
    await vi.waitFor(() => expect(listar).toHaveBeenLastCalledWith(3));
  });

  it('página inválida cae a 1', async () => {
    crear({ pagina: 'abc' });
    await vi.waitFor(() => expect(listar).toHaveBeenCalledWith(1));
  });

  it('recargar() vuelve a pedir el listado', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(listar).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('TiposListadoStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({}));
    const listar = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        TiposListadoStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { queryParamMap: ruta$ } },
        { provide: TiposAventuraRepositorio, useValue: { listar } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(TiposListadoStore), ruta$, listar };
  }

  it('AC_TKT016_11 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, listar } = crearHidratado({ ['recurso:tipos-listado:1']: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(listar).not.toHaveBeenCalled();
  });

  it('AC_TKT016_11 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, listar } = crearHidratado({ ['recurso:tipos-listado:2']: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(listar).toHaveBeenCalledWith(1);
    listar.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ pagina: '2' }));
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(listar).toHaveBeenLastCalledWith(2);
  });
});
