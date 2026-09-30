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
