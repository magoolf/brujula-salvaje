import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { ItinerariosRepositorio } from '../data/itinerarios.repositorio';
import { ItinerarioDetalle } from '../domain/modelos';
import { ItinerarioDetalleStore } from './itinerario-detalle.store';

const ITINERARIO = { slug: 'w-trek', titulo: 'W Trek' } as ItinerarioDetalle;

describe('ItinerarioDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<ItinerarioDetalle> = () => Promise.resolve(ITINERARIO)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'w-trek' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        ItinerarioDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: ItinerariosRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(ItinerarioDetalleStore);
  }

  it('carga el itinerario del slug actual y el descargo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.itinerario()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('w-trek');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
    expect(store.esNoEncontrado()).toBe(false);
    expect(store.esRetirado()).toBe(false);
  });

  it('recarga al cambiar el slug', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.itinerario()).not.toBeNull());
    paramMap$.next(convertToParamMap({ slug: 'otro' }));
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledWith('otro'));
  });

  it('404 → esNoEncontrado', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });

  it('410 → esRetirado con alternativas y listado_padre del ErrorApi', async () => {
    const store = crear(() =>
      Promise.reject(
        new HttpErrorResponse({
          status: 410,
          error: {
            code: 'retirado',
            listado_padre: '/itinerarios',
            alternativas: [{ tipo: 'ITINERARIO', slug: 'otro', titulo: 'Otro', origen: 'CURADO' }],
          },
        }),
      ),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({
      rutaListadoPadre: '/itinerarios',
      alternativas: [expect.objectContaining({ slug: 'otro' })],
    });
  });

  it('410 sin listado_padre usa /itinerarios por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/itinerarios', alternativas: [] });
  });

  it('recargar() vuelve a pedir el itinerario', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.itinerario()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});
