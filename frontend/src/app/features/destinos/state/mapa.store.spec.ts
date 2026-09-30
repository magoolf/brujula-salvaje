import { TestBed } from '@angular/core/testing';

import { DestinosRepositorio } from '../data/destinos.repositorio';
import { PuntoMapa } from '../domain/modelos';
import { MapaStore } from './mapa.store';

const PUNTO: PuntoMapa = {
  slug: 'patagonia',
  titulo: 'Patagonia',
  pais: 'Argentina',
  region: { slug: 'suramerica', nombre: 'Suramérica' },
  dificultad: 3,
  latitud: -50,
  longitud: -73,
};

describe('MapaStore', () => {
  it('carga todos los puntos del mapa', async () => {
    const mapaCompleto = vi.fn().mockResolvedValue([PUNTO]);
    TestBed.configureTestingModule({
      providers: [{ provide: DestinosRepositorio, useValue: { mapaCompleto } }],
    });
    const store = TestBed.inject(MapaStore);
    await vi.waitFor(() => expect(store.puntos()).toHaveLength(1));
    expect(store.puntos()).toEqual([PUNTO]);
    expect(store.error()).toBeNull();
    expect(store.cargando()).toBe(false);

    store.recargar();
    await vi.waitFor(() => expect(mapaCompleto).toHaveBeenCalledTimes(2));
    await vi.waitFor(() => expect(store.cargando()).toBe(false));
  });

  it('normaliza un fallo a ErrorApi y puntos queda vacío', async () => {
    const mapaCompleto = vi.fn().mockRejectedValue(new Error('fallo'));
    TestBed.configureTestingModule({
      providers: [{ provide: DestinosRepositorio, useValue: { mapaCompleto } }],
    });
    const store = TestBed.inject(MapaStore);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    expect(store.puntos()).toEqual([]);
  });
});
