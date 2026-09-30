import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, TransferState, makeStateKey } from '@angular/core';
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

/**
 * CLS real medido en Inicio (QA, ciclo 1/3, ver el docstring de inicio.repositorio.ts): estas
 * pruebas viven en su propio `describe` (sin el `beforeEach`/`afterEach` de arriba) porque cada una
 * arma su propio TestBed con un `PLATFORM_ID`/`TransferState` distinto para simular SSR y cliente
 * por separado.
 */
describe('InicioRepositorio — TransferState (CLS de Inicio)', () => {
  it('en el servidor, guarda la respuesta de /publico/inicio en TransferState tras pedirla', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
        { provide: PLATFORM_ID, useValue: 'server' },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const transferencia = TestBed.inject(TransferState);
    const repo = TestBed.inject(InicioRepositorio);

    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/inicio').flush(INICIO_VACIO);
    await promesa;

    // Esto es justo lo que Angular serializa en el <script id="ng-state"> del HTML inicial.
    expect(transferencia.toJson()).toContain('publico-inicio');
    http.verify();
  });

  it('en el cliente, si ya hay un valor transferido lo reutiliza SIN una segunda petición HTTP (evita el colapso de layout)', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
        // PLATFORM_ID por defecto (navegador): simula la hidratación en el cliente.
        {
          provide: TransferState,
          useFactory: () => {
            const estado = new TransferState();
            estado.set(makeStateKey<InicioDto>('publico-inicio'), INICIO_VACIO);
            return estado;
          },
        },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const repo = TestBed.inject(InicioRepositorio);

    const resultado = await repo.obtener();

    http.expectNone('/api/v1/publico/inicio');
    expect(resultado).toEqual({ hero: null, destinos: [], itinerarios: [], guias: [], tipos: [] });
    http.verify();
  });

  it('sin valor transferido (segunda llamada, o cliente sin SSR previo) sí hace la petición HTTP normal', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const repo = TestBed.inject(InicioRepositorio);

    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/inicio').flush(INICIO_VACIO);
    await promesa;
    http.verify();
  });
});
