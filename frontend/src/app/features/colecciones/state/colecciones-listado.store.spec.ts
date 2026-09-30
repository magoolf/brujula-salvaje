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
