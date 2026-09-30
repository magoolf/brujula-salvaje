import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { DestinosRepositorio } from '../data/destinos.repositorio';
import { FILTROS_VACIOS } from '../domain/filtros';
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
