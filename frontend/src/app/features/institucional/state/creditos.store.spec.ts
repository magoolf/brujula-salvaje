import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { InstitucionalRepositorio } from '../data/institucional.repositorio';
import { PaginaCreditos } from '../domain/modelos';
import { CreditosStore } from './creditos.store';

const PAGINA: PaginaCreditos = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('CreditosStore', () => {
  function crear(params: Record<string, string> = {}) {
    const queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    const creditos = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        CreditosStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: InstitucionalRepositorio, useValue: { creditos } },
      ],
    });
    return { store: TestBed.inject(CreditosStore), creditos };
  }

  it('pide la página 1 sin parámetros', async () => {
    const { store, creditos } = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(creditos).toHaveBeenCalledWith(1);
  });

  it('recargar() vuelve a pedir los créditos', async () => {
    const { store, creditos } = crear();
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(creditos).toHaveBeenCalledTimes(2));
  });
});
