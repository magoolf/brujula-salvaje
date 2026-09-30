import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { TiposAventuraRepositorio } from './tipos-aventura.repositorio';

describe('TiposAventuraRepositorio', () => {
  let http: HttpTestingController;
  let repo: TiposAventuraRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(TiposAventuraRepositorio);
  });

  afterEach(() => http.verify());

  it('listar() omite el parámetro pagina en la página 1', async () => {
    const promesa = repo.listar(1);
    const peticion = http.expectOne('/api/v1/publico/tipos-aventura');
    expect(peticion.request.params.has('pagina')).toBe(false);
    peticion.flush({ anterior: null, pagina: 1, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 1, resultados: [] });
    await promesa;
  });

  it('listar() envía la página cuando es mayor a 1', async () => {
    const promesa = repo.listar(2);
    const peticion = http.expectOne((r) => r.url === '/api/v1/publico/tipos-aventura' && r.params.get('pagina') === '2');
    peticion.flush({ anterior: null, pagina: 2, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 2, resultados: [] });
    await promesa;
  });

  it('detalle() llama al slug correcto', async () => {
    const promesa = repo.detalle('buceo');
    const peticion = http.expectOne('/api/v1/publico/tipos-aventura/buceo');
    peticion.flush({
      checklist: [],
      descripcion: 'x',
      destinos: [],
      destinos_total: 0,
      fuentes: [],
      guias_relacionadas: [],
      metadatos: { autoria: 'x', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
      nivel_exigencia: 1,
      portada: null,
      relacionados: [],
      resumen: 'x',
      slug: 'buceo',
      terminos: [],
      titulo: 'Buceo',
    });
    const resultado = await promesa;
    expect(resultado.slug).toBe('buceo');
  });

  it('textoDescargo() llama a publico-general', async () => {
    const promesa = repo.textoDescargo();
    http.expectOne('/api/v1/publico/configuracion').flush({
      nombre_marca: 'Brújula Salvaje',
      responsable: { definido: false },
      texto_descargo: 'Descargo de prueba',
    });
    expect(await promesa).toBe('Descargo de prueba');
  });
});
