import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { BusquedaRepositorio } from '../data/busqueda.repositorio';
import { BusquedaAgrupadaVista, PaginaResultados } from '../domain/modelos';
import { BusquedaStore } from './busqueda.store';

const GRUPO_VACIO = { resultados: [], total: 0 };
const AGRUPADA: BusquedaAgrupadaVista = {
  total: 0,
  grupos: { destinos: GRUPO_VACIO, itinerarios: GRUPO_VACIO, guias: GRUPO_VACIO, tipos: GRUPO_VACIO },
};
const PAGINA: PaginaResultados = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('BusquedaStore', () => {
  let queryParamMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let buscar: ReturnType<typeof vi.fn>;
  let buscarPorGrupo: ReturnType<typeof vi.fn>;

  function crear(params: Record<string, string> = {}) {
    queryParamMap$ = new BehaviorSubject(convertToParamMap(params));
    buscar = vi.fn().mockResolvedValue(AGRUPADA);
    buscarPorGrupo = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        BusquedaStore,
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParamMap$ } },
        { provide: BusquedaRepositorio, useValue: { buscar, buscarPorGrupo } },
      ],
    });
    return TestBed.inject(BusquedaStore);
  }

  it('sin q: no valida ni llama a la API', () => {
    const store = crear();
    expect(store.validacion()).toBeNull();
    expect(buscar).not.toHaveBeenCalled();
    expect(buscarPorGrupo).not.toHaveBeenCalled();
  });

  it('q válida sin tipo: llama a buscar() agrupado', async () => {
    const store = crear({ q: 'patagonia' });
    await vi.waitFor(() => expect(store.agrupada()).not.toBeNull());
    expect(buscar).toHaveBeenCalledWith('patagonia');
    expect(buscarPorGrupo).not.toHaveBeenCalled();
  });

  it('q válida con tipo: llama a buscarPorGrupo()', async () => {
    const store = crear({ q: 'patagonia', tipo: 'destinos', pagina: '2' });
    await vi.waitFor(() => expect(store.grupo()).not.toBeNull());
    expect(buscarPorGrupo).toHaveBeenCalledWith('destinos', 'patagonia', 2);
    expect(buscar).not.toHaveBeenCalled();
  });

  it('q corta (AC-020): validación inválida, ninguna petición', () => {
    const store = crear({ q: 'a' });
    expect(store.validacion()).toEqual({ valida: false, mensaje: expect.any(String) });
    expect(buscar).not.toHaveBeenCalled();
  });

  it('q larga (>100): validación inválida, ninguna petición', () => {
    const store = crear({ q: 'a'.repeat(101) });
    expect(store.validacion()?.valida).toBe(false);
    expect(buscar).not.toHaveBeenCalled();
  });
});
