import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { ItinerariosRepositorio } from './itinerarios.repositorio';

const PAGINA_VACIA = {
  anterior: null,
  pagina: 1,
  siguiente: null,
  tamano_pagina: 24,
  total: 0,
  total_paginas: 1,
  resultados: [],
};

describe('ItinerariosRepositorio', () => {
  let http: HttpTestingController;
  let repo: ItinerariosRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(ItinerariosRepositorio);
  });

  afterEach(() => http.verify());

  it('listar() envía orden y página solo si no son el valor por defecto', async () => {
    const promesa = repo.listar({ orden: 'duracion_asc', pagina: 2 });
    const peticion = http.expectOne(
      (r) => r.url === '/api/v1/publico/itinerarios' && r.params.get('orden') === 'duracion_asc',
    );
    expect(peticion.request.params.get('pagina')).toBe('2');
    peticion.flush(PAGINA_VACIA);
    const resultado = await promesa;
    expect(resultado.resultados).toEqual([]);
  });

  it('listar() con orden por defecto no envía el parámetro', async () => {
    const promesa = repo.listar({ orden: 'titulo', pagina: 1 });
    const peticion = http.expectOne('/api/v1/publico/itinerarios');
    expect(peticion.request.params.has('orden')).toBe(false);
    expect(peticion.request.params.has('pagina')).toBe(false);
    peticion.flush(PAGINA_VACIA);
    await promesa;
  });

  it('detalle() llama al slug correcto', async () => {
    const promesa = repo.detalle('w-trek');
    const peticion = http.expectOne('/api/v1/publico/itinerarios/w-trek');
    peticion.flush({
      desnivel_acumulado_m: null,
      destino: { dificultad: 1, pais: { slug: 'p', nombre: 'P' }, portada: null, region: { slug: 'r', nombre: 'R' }, slug: 'd', titulo: 'D' },
      dias: [],
      dificultad: 1,
      distancia_total_km: null,
      duracion_dias: 1,
      fuentes: [],
      galeria: [],
      metadatos: { autoria: 'x', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
      portada: null,
      relacionados: [],
      resumen: 'x',
      riesgos_seguridad: 'x',
      slug: 'w-trek',
      terminos: [],
      tipos: [],
      titulo: 'W Trek',
    });
    const resultado = await promesa;
    expect(resultado.slug).toBe('w-trek');
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
