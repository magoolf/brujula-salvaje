import { TransferState, makeStateKey } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideClientHydration } from '@angular/platform-browser';
import { Router, provideRouter } from '@angular/router';

import { InicioRepositorio } from '../data/inicio.repositorio';
import { Inicio } from '../domain/modelos';
import { InicioStore } from './inicio.store';

const INICIO: Inicio = { hero: null, destinos: [], itinerarios: [], guias: [], tipos: [] };

describe('InicioStore', () => {
  it('carga el inicio', async () => {
    const obtener = vi.fn().mockResolvedValue(INICIO);
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: InicioRepositorio, useValue: { obtener } }],
    });
    const store = TestBed.inject(InicioStore);
    await vi.waitFor(() => expect(store.inicio()).toEqual(INICIO));
    expect(store.error()).toBeNull();
    expect(store.cargando()).toBe(false);

    store.recargar();
    await vi.waitFor(() => expect(obtener).toHaveBeenCalledTimes(2));
    await vi.waitFor(() => expect(store.cargando()).toBe(false));
  });

  it('normaliza un fallo a ErrorApi', async () => {
    const obtener = vi.fn().mockRejectedValue(new Error('fallo'));
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: InicioRepositorio, useValue: { obtener } }],
    });
    const store = TestBed.inject(InicioStore);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
  });

  it('sorprenderme() navega al destino aleatorio devuelto por el repositorio', async () => {
    const obtener = vi.fn().mockResolvedValue(INICIO);
    const destinoAleatorio = vi.fn().mockResolvedValue('patagonia');
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: InicioRepositorio, useValue: { obtener, destinoAleatorio } }],
    });
    const store = TestBed.inject(InicioStore);
    const router = TestBed.inject(Router);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    const error = await store.sorprenderme();
    expect(error).toBeNull();
    expect(navigate).toHaveBeenCalledWith(['/destinos', 'patagonia']);
  });

  it('sorprenderme() devuelve ErrorApi si el destino aleatorio falla', async () => {
    const obtener = vi.fn().mockResolvedValue(INICIO);
    const destinoAleatorio = vi.fn().mockRejectedValue(new Error('sin destinos'));
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: InicioRepositorio, useValue: { obtener, destinoAleatorio } }],
    });
    const store = TestBed.inject(InicioStore);
    const error = await store.sorprenderme();
    expect(error).not.toBeNull();
  });

  it('AC_TKT016_01 hidratación: nace resuelto con el valor del SSR (TransferState) sin pedirlo otra vez', () => {
    const obtener = vi.fn();
    const INICIO_SSR: Inicio = { ...INICIO, tipos: [] };
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideClientHydration(),
        { provide: InicioRepositorio, useValue: { obtener } },
      ],
    });
    TestBed.inject(TransferState).set(makeStateKey<Inicio>('recurso:inicio'), INICIO_SSR);
    const store = TestBed.inject(InicioStore);
    // Síncrono: el primer render del cliente ya ve los datos (no el esqueleto de «cargando»).
    expect(store.inicio()).toEqual(INICIO_SSR);
    expect(store.cargando()).toBe(false);
    TestBed.tick();
    expect(obtener).not.toHaveBeenCalled();
  });
});
