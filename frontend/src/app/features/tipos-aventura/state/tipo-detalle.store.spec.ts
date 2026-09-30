import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { TiposAventuraRepositorio } from '../data/tipos-aventura.repositorio';
import { TipoDetalle } from '../domain/modelos';
import { TipoDetalleStore } from './tipo-detalle.store';

const TIPO = { slug: 'buceo', titulo: 'Buceo' } as TipoDetalle;

describe('TipoDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<TipoDetalle> = () => Promise.resolve(TIPO)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'buceo' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        TipoDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: TiposAventuraRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(TipoDetalleStore);
  }

  it('carga el tipo del slug actual y el descargo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.tipo()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('buceo');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
  });

  it('404 → esNoEncontrado', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 404, error: { code: 'no_encontrado' } })),
    );
    await vi.waitFor(() => expect(store.esNoEncontrado()).toBe(true));
  });

  it('410 → esRetirado con listado_padre por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/tipos-de-aventura', alternativas: [] });
  });

  it('recargar() vuelve a pedir el tipo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.tipo()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});
