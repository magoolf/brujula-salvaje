import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { BusquedaRepositorio } from './busqueda.repositorio';

const GRUPO_VACIO = { resultados: [], total: 0 };

describe('BusquedaRepositorio', () => {
  let http: HttpTestingController;
  let repo: BusquedaRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(BusquedaRepositorio);
  });

  afterEach(() => http.verify());

  it('buscar() envía q como query param', async () => {
    const promesa = repo.buscar('patagonia');
    const peticion = http.expectOne((r) => r.url === '/api/v1/publico/busqueda' && r.params.get('q') === 'patagonia');
    peticion.flush({ total: 0, grupos: { destinos: GRUPO_VACIO, itinerarios: GRUPO_VACIO, guias: GRUPO_VACIO, tipos: GRUPO_VACIO } });
    const resultado = await promesa;
    expect(resultado.total).toBe(0);
  });

  it('buscarPorGrupo() llama a la ruta del grupo con q y pagina', async () => {
    const promesa = repo.buscarPorGrupo('destinos', 'patagonia', 2);
    const peticion = http.expectOne(
      (r) => r.url === '/api/v1/publico/busqueda/destinos' && r.params.get('q') === 'patagonia' && r.params.get('pagina') === '2',
    );
    peticion.flush({ anterior: null, pagina: 2, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 2, resultados: [] });
    const resultado = await promesa;
    expect(resultado.pagina).toBe(2);
  });
});
