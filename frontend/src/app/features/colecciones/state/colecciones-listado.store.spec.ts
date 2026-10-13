import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ColeccionesRepositorio } from '../data/colecciones.repositorio';
import { PaginaColecciones } from '../domain/modelos';
import { ColeccionesListadoStore } from './colecciones-listado.store';

const PAGINA: PaginaColecciones = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('ColeccionesListadoStore', () => {
  function crear(params: Record<string, string> = {}) {
    const queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    const listar = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        ColeccionesListadoStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: ColeccionesRepositorio, useValue: { listar } },
      ],
    });
    return { store: TestBed.inject(ColeccionesListadoStore), listar };
  }

  it('pide la página 1 sin parámetros', async () => {
    const { store, listar } = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(listar).toHaveBeenCalledWith(1);
  });

  it('recargar() vuelve a pedir el listado', async () => {
    const { store, listar } = crear();
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
describe('ColeccionesListadoStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({}));
    const listar = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        ColeccionesListadoStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { queryParamMap: ruta$ } },
        { provide: ColeccionesRepositorio, useValue: { listar } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(ColeccionesListadoStore), ruta$, listar };
  }

  it('AC_TKT016_15 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, listar } = crearHidratado({ ['recurso:colecciones-listado:1']: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(listar).not.toHaveBeenCalled();
  });

  it('AC_TKT016_15 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, listar } = crearHidratado({ ['recurso:colecciones-listado:2']: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(listar).toHaveBeenCalledWith(1);
    listar.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ pagina: '2' }));
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(listar).toHaveBeenLastCalledWith(2);
  });
});
