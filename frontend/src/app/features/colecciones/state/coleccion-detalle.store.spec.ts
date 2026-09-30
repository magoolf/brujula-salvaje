import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ColeccionesRepositorio } from '../data/colecciones.repositorio';
import { ColeccionDetalle } from '../domain/modelos';
import { ColeccionDetalleStore } from './coleccion-detalle.store';

const COLECCION = { slug: 'mejores-treks', titulo: 'Los mejores treks' } as ColeccionDetalle;

describe('ColeccionDetalleStore', () => {
  function crear(detalleImpl: () => Promise<ColeccionDetalle> = () => Promise.resolve(COLECCION)) {
    const paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'mejores-treks' }));
    const detalle = vi.fn(detalleImpl);
    TestBed.configureTestingModule({
      providers: [
        ColeccionDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: ColeccionesRepositorio, useValue: { detalle } },
      ],
    });
    return { store: TestBed.inject(ColeccionDetalleStore), detalle };
  }

  it('carga la colección del slug actual', async () => {
    const { store, detalle } = crear();
    await vi.waitFor(() => expect(store.coleccion()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('mejores-treks');
  });

  it('404 → esNoEncontrado', async () => {
    const { store } = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });

  it('410 → esRetirado con listado_padre por defecto', async () => {
    const { store } = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/colecciones', alternativas: [] });
  });
});
