import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
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

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('CreditosStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject(convertToParamMap({}));
    const creditos = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        CreditosStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { queryParamMap: ruta$ } },
        { provide: InstitucionalRepositorio, useValue: { creditos } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(CreditosStore), ruta$, creditos };
  }

  it('AC_TKT016_05 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, creditos } = crearHidratado({ ['recurso:creditos:1']: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(creditos).not.toHaveBeenCalled();
  });

  it('AC_TKT016_05 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, creditos } = crearHidratado({ ['recurso:creditos:2']: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(creditos).toHaveBeenCalledWith(1);
    creditos.mockResolvedValue({ origen: 'red-2' });
    ruta$.next(convertToParamMap({ pagina: '2' }));
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(creditos).toHaveBeenLastCalledWith(2);
  });
});
