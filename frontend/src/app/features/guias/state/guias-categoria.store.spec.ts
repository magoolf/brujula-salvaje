import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { GuiasRepositorio } from '../data/guias.repositorio';
import { PaginaCategorias, PaginaGuias } from '../domain/modelos';
import { GuiasCategoriaStore } from './guias-categoria.store';

const CATEGORIA = { slug: 'seguridad', nombre: 'Seguridad', descripcion: 'x' };
const GUIAS: PaginaGuias = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };
const OTRAS: PaginaCategorias = {
  resultados: [
    { slug: 'seguridad', nombre: 'Seguridad', descripcion: 'x', numeroGuias: 1, guiasRecientes: [] },
    { slug: 'equipo', nombre: 'Equipo', descripcion: 'x', numeroGuias: 2, guiasRecientes: [] },
  ],
  pagina: 1,
  totalPaginas: 1,
  total: 2,
  tamanoPagina: 24,
};

describe('GuiasCategoriaStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let categoria: ReturnType<typeof vi.fn>;
  let listarGuias: ReturnType<typeof vi.fn>;
  let listarCategorias: ReturnType<typeof vi.fn>;

  function crear(categoriaImpl = () => Promise.resolve(CATEGORIA)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'seguridad' }));
    categoria = vi.fn(categoriaImpl);
    listarGuias = vi.fn().mockResolvedValue(GUIAS);
    listarCategorias = vi.fn().mockResolvedValue(OTRAS);
    TestBed.configureTestingModule({
      providers: [
        GuiasCategoriaStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$, queryParamMap: new BehaviorSubject(convertToParamMap({})) } },
        { provide: GuiasRepositorio, useValue: { categoria, listarGuias, listarCategorias } },
      ],
    });
    return TestBed.inject(GuiasCategoriaStore);
  }

  it('carga la categoría, sus guías y filtra la categoría actual de "otras categorías"', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.categoria()).not.toBeNull());
    expect(categoria).toHaveBeenCalledWith('seguridad');
    await vi.waitFor(() => expect(store.guias()).not.toBeNull());
    await vi.waitFor(() => expect(store.otrasCategorias()).toEqual([expect.objectContaining({ slug: 'equipo' })]));
  });

  it('404 (categoría sin guías publicadas) → esNoEncontrado', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });
});
