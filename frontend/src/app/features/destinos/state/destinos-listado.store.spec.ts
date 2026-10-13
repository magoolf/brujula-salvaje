import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { DestinosRepositorio } from '../data/destinos.repositorio';
import { FILTROS_VACIOS, filtrosDesdeQueryParams } from '../domain/filtros';
import { PaginaDestinos, FacetasDestinos } from '../domain/modelos';
import { DestinosListadoStore } from './destinos-listado.store';

const PAGINA: PaginaDestinos = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };
const FACETAS: FacetasDestinos = { tipos: [], regiones: [], dificultad: [], presupuesto: [], tramosDuracion: [] };

describe('DestinosListadoStore', () => {
  let queryParamMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let listar: ReturnType<typeof vi.fn>;
  let facetas: ReturnType<typeof vi.fn>;

  function crear(listarImpl: () => Promise<PaginaDestinos> = () => Promise.resolve(PAGINA)) {
    queryParamMap$ = new BehaviorSubject(convertToParamMap({}));
    listar = vi.fn(listarImpl);
    facetas = vi.fn().mockResolvedValue(FACETAS);
    TestBed.configureTestingModule({
      providers: [
        DestinosListadoStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: DestinosRepositorio, useValue: { listar, facetas } },
      ],
    });
    return TestBed.inject(DestinosListadoStore);
  }

  it('lee los filtros iniciales de la URL y carga listado + facetas', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(store.pagina()).toEqual(PAGINA);
    expect(store.facetas()).toEqual(FACETAS);
    expect(listar).toHaveBeenCalledWith(FILTROS_VACIOS);
  });

  it('vuelve a pedir el listado cuando cambian los query params (reactividad de la URL)', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(store.cargando()).toBe(false);
    expect(store.cargandoFacetas()).toBe(false);

    queryParamMap$.next(convertToParamMap({ tipo: ['buceo', 'senderismo'], pagina: '2' }));
    await vi.waitFor(() => expect(listar).toHaveBeenCalledTimes(2));
    expect(listar).toHaveBeenLastCalledWith({
      ...FILTROS_VACIOS,
      tipo: ['buceo', 'senderismo'],
      pagina: 2,
    });
  });

  it('normaliza un error de red a ErrorApi', async () => {
    const store = crear(() => Promise.reject(new Error('fallo de red')));
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    expect(store.error()?.categoria).toBe('desconocido');
  });

  it('recargar() vuelve a invocar el listado', async () => {
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
describe('DestinosListadoStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({}));
    const listar = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        DestinosListadoStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { queryParamMap: ruta$ } },
        { provide: DestinosRepositorio, useValue: { listar, facetas: vi.fn().mockResolvedValue(FACETAS) } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(DestinosListadoStore), ruta$, listar };
  }

  it('AC_TKT016_02 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, listar } = crearHidratado({ [`recurso:destinos-listado:${JSON.stringify(filtrosDesdeQueryParams({}))}`]: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(listar).not.toHaveBeenCalled();
  });

  it('AC_TKT016_02 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, listar } = crearHidratado({ [`recurso:destinos-listado:${JSON.stringify(filtrosDesdeQueryParams({ pagina: '2' }))}`]: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(listar).toHaveBeenCalledWith(filtrosDesdeQueryParams({}));
    listar.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ pagina: '2' }));
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(listar).toHaveBeenLastCalledWith(filtrosDesdeQueryParams({ pagina: '2' }));
  });
});
