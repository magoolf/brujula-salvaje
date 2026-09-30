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
