import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { DestinosRepositorio } from '../data/destinos.repositorio';
import { FILTROS_VACIOS } from '../domain/filtros';
import { MesResumen, PaginaDestinos } from '../domain/modelos';
import { DestinosDelMesStore, MesesIndiceStore } from './meses.store';

const MESES: readonly MesResumen[] = [
  { mes: 1, nombre: 'Enero', slug: 'enero', numeroDestinos: 0, destacado: null },
];
const PAGINA: PaginaDestinos = { resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 };

describe('MesesIndiceStore', () => {
  it('carga los 12 meses', async () => {
    const meses = vi.fn().mockResolvedValue(MESES);
    TestBed.configureTestingModule({ providers: [{ provide: DestinosRepositorio, useValue: { meses } }] });
    const store = TestBed.inject(MesesIndiceStore);
    await vi.waitFor(() => expect(store.meses()).toEqual(MESES));
    expect(store.error()).toBeNull();
  });

  it('normaliza un fallo a ErrorApi', async () => {
    const meses = vi.fn().mockRejectedValue(new Error('fallo'));
    TestBed.configureTestingModule({ providers: [{ provide: DestinosRepositorio, useValue: { meses } }] });
    const store = TestBed.inject(MesesIndiceStore);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
  });
});

describe('DestinosDelMesStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let listar: ReturnType<typeof vi.fn>;

  function crear(mes: string) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ mes }));
    listar = vi.fn().mockResolvedValue(PAGINA);
    TestBed.configureTestingModule({
      providers: [
        DestinosDelMesStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: DestinosRepositorio, useValue: { listar } },
      ],
    });
    return TestBed.inject(DestinosDelMesStore);
  }

  it('mes válido: pide los destinos de ese mes', async () => {
    const store = crear('7');
    expect(store.mes()).toBe(7);
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(listar).toHaveBeenCalledWith({ ...FILTROS_VACIOS, mes: 7 });
    expect(store.cargando()).toBe(false);
    expect(store.error()).toBeNull();
  });

  it('normaliza un fallo de red a ErrorApi', async () => {
    paramMap$ = new BehaviorSubject(convertToParamMap({ mes: '3' }));
    listar = vi.fn().mockRejectedValue(new Error('fallo'));
    TestBed.configureTestingModule({
      providers: [
        DestinosDelMesStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: DestinosRepositorio, useValue: { listar } },
      ],
    });
    const store = TestBed.inject(DestinosDelMesStore);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    expect(store.pagina()).toBeNull();
  });

  it('mes inválido (fuera de 1-12 o no numérico): mes() es null y no se llama a la API', async () => {
    const store = crear('13');
    expect(store.mes()).toBeNull();
    await Promise.resolve();
    expect(listar).not.toHaveBeenCalled();
    expect(store.pagina()).toBeNull();
  });
});
