import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { GlosarioRepositorio } from '../data/glosario.repositorio';
import { PaginaGlosario } from '../domain/modelos';
import { GlosarioStore } from './glosario.store';

const PAGINA: PaginaGlosario = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('GlosarioStore', () => {
  function crear(params: Record<string, string> = {}) {
    const queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    const listar = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        GlosarioStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: GlosarioRepositorio, useValue: { listar } },
      ],
    });
    return { store: TestBed.inject(GlosarioStore), listar };
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
