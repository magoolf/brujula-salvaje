import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { ColeccionesRepositorio } from './colecciones.repositorio';

describe('ColeccionesRepositorio', () => {
  let http: HttpTestingController;
  let repo: ColeccionesRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(ColeccionesRepositorio);
  });

  afterEach(() => http.verify());

  it('listar() omite pagina en la página 1', async () => {
    const promesa = repo.listar(1);
    const peticion = http.expectOne('/api/v1/publico/colecciones');
    expect(peticion.request.params.has('pagina')).toBe(false);
    peticion.flush({ anterior: null, pagina: 1, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 1, resultados: [] });
    await promesa;
  });

  it('detalle() llama al slug correcto', async () => {
    const promesa = repo.detalle('mejores-treks');
    const peticion = http.expectOne('/api/v1/publico/colecciones/mejores-treks');
    peticion.flush({
      descripcion: 'x',
      elementos: [],
      metadatos: { autoria: 'x', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
      portada: null,
      resumen: 'x',
      slug: 'mejores-treks',
      titulo: 'Los mejores treks',
    });
    const resultado = await promesa;
    expect(resultado.slug).toBe('mejores-treks');
  });
});
