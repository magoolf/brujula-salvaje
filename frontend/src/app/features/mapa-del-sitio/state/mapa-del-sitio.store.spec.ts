import { TestBed } from '@angular/core/testing';

import { MapaDelSitioRepositorio } from '../data/mapa-del-sitio.repositorio';
import { DatosMapaDelSitio } from '../domain/modelos';
import { MapaDelSitioStore } from './mapa-del-sitio.store';

const DATOS: DatosMapaDelSitio = {
  entradas: [{ tipo: 'COLECCION', slug: 'volcanes', titulo: 'Volcanes', agrupacion: null }],
  meses: [],
  terminos: [],
};

describe('MapaDelSitioStore', () => {
  function crear(obtener = vi.fn().mockResolvedValue(DATOS), transferidos: DatosMapaDelSitio | null = null) {
    TestBed.configureTestingModule({
      providers: [
        MapaDelSitioStore,
        { provide: MapaDelSitioRepositorio, useValue: { obtener, datosTransferidos: () => transferidos } },
      ],
    });
    return { store: TestBed.inject(MapaDelSitioStore), obtener };
  }

  it('AC_TKT019_02 expone las secciones construidas y el total de enlaces', async () => {
    const { store } = crear();
    expect(store.secciones()).toBeNull();
    expect(store.total()).toBe(0);
    await vi.waitFor(() => expect(store.secciones()).not.toBeNull());
    expect(store.secciones()?.find((s) => s.id === 'colecciones')?.grupos[0].enlaces).toEqual([
      { etiqueta: 'Volcanes', ruta: '/colecciones/volcanes' },
    ]);
    // colección + créditos
    expect(store.total()).toBe(2);
    expect(store.cargando()).toBe(false);
    expect(store.error()).toBeNull();
  });

  it('AC_TKT019_07 normaliza el error y recargar() vuelve a pedir', async () => {
    const obtener = vi.fn().mockRejectedValueOnce(new Error('caída')).mockResolvedValue(DATOS);
    const { store } = crear(obtener);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    expect(store.secciones()).toBeNull();
    store.recargar();
    await vi.waitFor(() => expect(store.secciones()).not.toBeNull());
    expect(obtener).toHaveBeenCalledTimes(2);
  });

  it('AC_TKT019_06 usa los datos del SSR desde el primer render (sin volver a «cargando», CLS)', () => {
    const { store } = crear(vi.fn().mockReturnValue(new Promise(() => undefined)), DATOS);
    expect(store.secciones()).not.toBeNull();
    expect(store.total()).toBe(2);
  });

  it('con datos del SSR, un error posterior muestra el error y no los datos', async () => {
    const { store } = crear(vi.fn().mockRejectedValue(new Error('caída')), DATOS);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    expect(store.secciones()).toBeNull();
  });
});
