import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { GuiasRepositorio } from '../data/guias.repositorio';
import { GuiaDetalle } from '../domain/modelos';
import { GuiaDetalleStore } from './guia-detalle.store';

const GUIA = { slug: 'primeros-auxilios', titulo: 'Primeros auxilios' } as GuiaDetalle;

describe('GuiaDetalleStore', () => {
  let paramMap$: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let detalle: ReturnType<typeof vi.fn>;
  let textoDescargo: ReturnType<typeof vi.fn>;

  function crear(detalleImpl: () => Promise<GuiaDetalle> = () => Promise.resolve(GUIA)) {
    paramMap$ = new BehaviorSubject(convertToParamMap({ slug: 'primeros-auxilios' }));
    detalle = vi.fn(detalleImpl);
    textoDescargo = vi.fn().mockResolvedValue('Descargo de prueba');
    TestBed.configureTestingModule({
      providers: [
        GuiaDetalleStore,
        { provide: ActivatedRoute, useValue: { paramMap: paramMap$ } },
        { provide: GuiasRepositorio, useValue: { detalle, textoDescargo } },
      ],
    });
    return TestBed.inject(GuiaDetalleStore);
  }

  it('carga la guía del slug actual y el descargo', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.guia()).not.toBeNull());
    expect(detalle).toHaveBeenCalledWith('primeros-auxilios');
    await vi.waitFor(() => expect(store.descargo()).toBe('Descargo de prueba'));
  });

  it('410 → esRetirado con listado_padre por defecto', async () => {
    const store = crear(() =>
      Promise.reject(new HttpErrorResponse({ status: 410, error: { code: 'retirado' } })),
    );
    await vi.waitFor(() => expect(store.esRetirado()).toBe(true));
    expect(store.retirado()).toEqual({ rutaListadoPadre: '/guias', alternativas: [] });
  });

  it('recargar() vuelve a pedir la guía', async () => {
    const store = crear();
    await vi.waitFor(() => expect(store.guia()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(detalle).toHaveBeenCalledTimes(2));
  });
});
