import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { Inicio as InicioDto } from '../../../api/models/inicio';
import { InicioRepositorio } from './inicio.repositorio';

const INICIO_VACIO: InicioDto = { hero: null, destinos: [], itinerarios: [], guias: [], tipos: [] };

describe('InicioRepositorio', () => {
  let http: HttpTestingController;
  let repo: InicioRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(InicioRepositorio);
  });

  afterEach(() => http.verify());

  it('obtener() mapea la respuesta de /publico/inicio', async () => {
    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/inicio').flush(INICIO_VACIO);
    expect(await promesa).toEqual({ hero: null, destinos: [], itinerarios: [], guias: [], tipos: [] });
  });

  it('destinoAleatorio() devuelve el slug del destino sorpresa', async () => {
    const promesa = repo.destinoAleatorio();
    http.expectOne('/api/v1/publico/destinos/aleatorio').flush({ slug: 'patagonia' });
    expect(await promesa).toBe('patagonia');
  });
});
