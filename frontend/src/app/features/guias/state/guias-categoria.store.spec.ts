import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
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

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('GuiasCategoriaStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ slug: 'seguridad' }));
    const categoria = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        GuiasCategoriaStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$, queryParamMap: new BehaviorSubject(convertToParamMap({})) } },
        { provide: GuiasRepositorio, useValue: { categoria, listarGuias: vi.fn().mockResolvedValue(GUIAS), listarCategorias: vi.fn().mockResolvedValue(OTRAS) } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(GuiasCategoriaStore), ruta$, categoria };
  }

  it('AC_TKT016_23 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, categoria } = crearHidratado({ ['recurso:guias-categoria:seguridad']: SSR });
    expect(store.categoria()).toEqual(SSR);
    TestBed.tick();
    expect(categoria).not.toHaveBeenCalled();
  });

  it('AC_TKT016_23 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, categoria } = crearHidratado({ ['recurso:guias-categoria:equipo']: SSR });
    await vi.waitFor(() => expect(store.categoria()).toEqual(RED));
    expect(categoria).toHaveBeenCalledWith('seguridad');
    categoria.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ slug: 'equipo' }));
    await vi.waitFor(() => expect(store.categoria()).toEqual({ origen: 'red-2' }));
    expect(categoria).toHaveBeenLastCalledWith('equipo');
  });
});
