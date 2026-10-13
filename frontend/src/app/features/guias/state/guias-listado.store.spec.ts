import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { GuiasRepositorio } from '../data/guias.repositorio';
import { PaginaCategorias } from '../domain/modelos';
import { GuiasListadoStore } from './guias-listado.store';

const PAGINA: PaginaCategorias = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('GuiasListadoStore', () => {
  let queryParamMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let listarCategorias: ReturnType<typeof vi.fn>;

  function crear(params: Record<string, string> = {}) {
    queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    listarCategorias = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        GuiasListadoStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: GuiasRepositorio, useValue: { listarCategorias } },
      ],
    });
    return TestBed.inject(GuiasListadoStore);
  }

  it('pide la página 1 sin parámetros', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(listarCategorias).toHaveBeenCalledWith(1);
  });

  it('recargar() vuelve a pedir el listado', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(listarCategorias).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('GuiasListadoStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({}));
    const listarCategorias = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        GuiasListadoStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { queryParamMap: ruta$ } },
        { provide: GuiasRepositorio, useValue: { listarCategorias } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(GuiasListadoStore), ruta$, listarCategorias };
  }

  it('AC_TKT016_13 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, listarCategorias } = crearHidratado({ ['recurso:guias-listado:1']: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(listarCategorias).not.toHaveBeenCalled();
  });

  it('AC_TKT016_13 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, listarCategorias } = crearHidratado({ ['recurso:guias-listado:2']: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(listarCategorias).toHaveBeenCalledWith(1);
    listarCategorias.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ pagina: '2' }));
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(listarCategorias).toHaveBeenLastCalledWith(2);
  });
});
