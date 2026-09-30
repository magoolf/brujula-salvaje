import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ItinerariosRepositorio } from '../data/itinerarios.repositorio';
import { PaginaItinerarios } from '../domain/modelos';
import { ItinerariosListadoStore } from './itinerarios-listado.store';

const PAGINA: PaginaItinerarios = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('ItinerariosListadoStore', () => {
  let queryParamMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let listar: ReturnType<typeof vi.fn>;

  function crear(params: Record<string, string> = {}) {
    queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    listar = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        ItinerariosListadoStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: ItinerariosRepositorio, useValue: { listar } },
      ],
    });
    return TestBed.inject(ItinerariosListadoStore);
  }

  it('deriva los filtros por defecto de la URL vacía y pide el listado', async () => {
    const store = crear();
    expect(store.filtros()).toEqual({ orden: 'titulo', pagina: 1 });
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(listar).toHaveBeenCalledWith({ orden: 'titulo', pagina: 1 });
  });

  it('reacciona a cambios en los query params', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    queryParamMap$.next(convertToParamMap({ orden: 'duracion_desc', pagina: '2' }));
    await vi.waitFor(() =>
      expect(listar).toHaveBeenLastCalledWith({ orden: 'duracion_desc', pagina: 2 }),
    );
  });

  it('recargar() vuelve a pedir el listado', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(listar).toHaveBeenCalledTimes(2));
  });
});
