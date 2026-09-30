import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { GuiasRepositorio } from './guias.repositorio';

describe('GuiasRepositorio', () => {
  let http: HttpTestingController;
  let repo: GuiasRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(GuiasRepositorio);
  });

  afterEach(() => http.verify());

  it('listarCategorias() llama al endpoint de categorías', async () => {
    const promesa = repo.listarCategorias(1);
    http.expectOne('/api/v1/publico/categorias-guia').flush({ anterior: null, pagina: 1, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 1, resultados: [] });
    await promesa;
  });

  it('categoria() llama al slug correcto', async () => {
    const promesa = repo.categoria('seguridad');
    http.expectOne('/api/v1/publico/categorias-guia/seguridad').flush({ slug: 'seguridad', nombre: 'Seguridad', descripcion: 'x' });
    const resultado = await promesa;
    expect(resultado.nombre).toBe('Seguridad');
  });

  it('listarGuias() envía la categoría como query param', async () => {
    const promesa = repo.listarGuias('seguridad', 2);
    const peticion = http.expectOne(
      (r) => r.url === '/api/v1/publico/guias' && r.params.get('categoria') === 'seguridad' && r.params.get('pagina') === '2',
    );
    peticion.flush({ anterior: null, pagina: 2, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 2, resultados: [] });
    await promesa;
  });

  it('listarGuias() sin categoría no envía el parámetro', async () => {
    const promesa = repo.listarGuias(null, 1);
    const peticion = http.expectOne('/api/v1/publico/guias');
    expect(peticion.request.params.has('categoria')).toBe(false);
    peticion.flush({ anterior: null, pagina: 1, siguiente: null, tamano_pagina: 24, total: 0, total_paginas: 1, resultados: [] });
    await promesa;
  });

  it('detalle() llama al slug correcto', async () => {
    const promesa = repo.detalle('primeros-auxilios');
    const peticion = http.expectOne('/api/v1/publico/guias/primeros-auxilios');
    peticion.flush({
      categoria: { slug: 's', nombre: 'S', descripcion: 'x' },
      cuerpo: 'x',
      destinos_relacionados: [],
      fuentes: [],
      metadatos: { autoria: 'x', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
      minutos_lectura: null,
      portada: null,
      relacionados: [],
      remite_a_metodologia: false,
      resumen: 'x',
      slug: 'primeros-auxilios',
      terminos: [],
      tipos_relacionados: [],
      titulo: 'Primeros auxilios',
    });
    const resultado = await promesa;
    expect(resultado.slug).toBe('primeros-auxilios');
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
