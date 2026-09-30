import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { GlosarioRepositorio } from './glosario.repositorio';

describe('GlosarioRepositorio', () => {
  let http: HttpTestingController;
  let repo: GlosarioRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(GlosarioRepositorio);
  });

  afterEach(() => http.verify());

  it('listar() omite pagina en la página 1', async () => {
    const promesa = repo.listar(1);
    const peticion = http.expectOne('/api/v1/publico/glosario');
    expect(peticion.request.params.has('pagina')).toBe(false);
    peticion.flush({ anterior: null, pagina: 1, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 1, resultados: [] });
    await promesa;
  });

  it('listar() envía pagina cuando es mayor a 1', async () => {
    const promesa = repo.listar(2);
    const peticion = http.expectOne((r) => r.url === '/api/v1/publico/glosario' && r.params.get('pagina') === '2');
    peticion.flush({ anterior: null, pagina: 2, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 2, resultados: [] });
    await promesa;
  });
});
