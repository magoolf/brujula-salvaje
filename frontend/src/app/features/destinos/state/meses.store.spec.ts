import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
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

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('DestinosDelMesStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({ mes: '1' }));
    const listar = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        DestinosDelMesStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { paramMap: ruta$ } },
        { provide: DestinosRepositorio, useValue: { listar } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(DestinosDelMesStore), ruta$, listar };
  }

  it('AC_TKT016_07 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, listar } = crearHidratado({ ['recurso:destinos-del-mes:1']: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(listar).not.toHaveBeenCalled();
  });

  it('AC_TKT016_07 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, listar } = crearHidratado({ ['recurso:destinos-del-mes:2']: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(listar).toHaveBeenCalledWith({ ...FILTROS_VACIOS, mes: 1 });
    listar.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ mes: '2' }));
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(listar).toHaveBeenLastCalledWith({ ...FILTROS_VACIOS, mes: 2 });
  });
});
