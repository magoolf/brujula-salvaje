import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { InstitucionalRepositorio } from './institucional.repositorio';

describe('InstitucionalRepositorio', () => {
  let http: HttpTestingController;
  let repo: InstitucionalRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(InstitucionalRepositorio);
  });

  afterEach(() => http.verify());

  it('pagina() llama al slug correcto', async () => {
    const promesa = repo.pagina('aviso-legal');
    const peticion = http.expectOne('/api/v1/publico/paginas/aviso-legal');
    peticion.flush({
      cuerpo: 'x',
      metadatos: { autoria: 'x', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
      slug: 'aviso-legal',
      titulo: 'Aviso legal',
      version_documento: '1.0',
      vigente_desde: '2026-01-01',
    });
    const resultado = await promesa;
    expect(resultado.slug).toBe('aviso-legal');
  });

  it('escalas() llama al endpoint de escalas', async () => {
    const promesa = repo.escalas();
    http.expectOne('/api/v1/publico/escalas').flush({ dificultad: [], presupuesto: [] });
    expect(await promesa).toEqual({ dificultad: [], presupuesto: [] });
  });

  it('configuracion() llama al endpoint de configuración', async () => {
    const promesa = repo.configuracion();
    http.expectOne('/api/v1/publico/configuracion').flush({
      nombre_marca: 'Brújula Salvaje',
      responsable: { definido: false },
      texto_descargo: 'x',
    });
    const resultado = await promesa;
    expect(resultado.nombreMarca).toBe('Brújula Salvaje');
  });

  it('creditos() omite pagina en la página 1', async () => {
    const promesa = repo.creditos(1);
    const peticion = http.expectOne('/api/v1/publico/creditos');
    expect(peticion.request.params.has('pagina')).toBe(false);
    peticion.flush({ anterior: null, pagina: 1, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 1, resultados: [] });
    await promesa;
  });
});
