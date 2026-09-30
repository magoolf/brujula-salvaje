import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { DestinosRepositorio } from './destinos.repositorio';
import { FILTROS_VACIOS } from '../domain/filtros';

const PAGINA_VACIA = {
  anterior: null,
  pagina: 1,
  siguiente: null,
  tamano_pagina: 24,
  total: 0,
  total_paginas: 1,
  resultados: [],
};

describe('DestinosRepositorio', () => {
  let http: HttpTestingController;
  let repo: DestinosRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(DestinosRepositorio);
  });

  afterEach(() => http.verify());

  it('listar() serializa los filtros como query params repetidos y mapea la respuesta', async () => {
    const promesa = repo.listar({ ...FILTROS_VACIOS, tipo: ['buceo', 'senderismo'], pagina: 2 });
    const peticion = http.expectOne(
      (r) => r.url === '/api/v1/publico/destinos' && r.params.getAll('tipo')?.join(',') === 'buceo,senderismo',
    );
    expect(peticion.request.params.get('pagina')).toBe('2');
    peticion.flush(PAGINA_VACIA);
    const resultado = await promesa;
    expect(resultado).toEqual({ resultados: [], pagina: 1, totalPaginas: 1, total: 0, tamanoPagina: 24 });
  });

  it('facetas() llama al endpoint de facetas', async () => {
    const promesa = repo.facetas();
    http
      .expectOne('/api/v1/publico/facetas/destinos')
      .flush({ dificultad: [], presupuesto: [], regiones: [], tipos: [], tramos_duracion: [] });
    const resultado = await promesa;
    expect(resultado.tipos).toEqual([]);
  });

  it('detalle() llama al slug correcto', async () => {
    const promesa = repo.detalle('patagonia');
    const peticion = http.expectOne('/api/v1/publico/destinos/patagonia');
    peticion.flush({
      clima: 'x',
      como_llegar: 'x',
      descripcion_experta: 'x',
      dificultad: 1,
      duracion_max_dias: 1,
      duracion_min_dias: 1,
      fuentes: [],
      galeria: [],
      guias_relacionadas: [],
      itinerarios: [],
      itinerarios_afines: [],
      itinerarios_total: 0,
      latitud: 0,
      longitud: 0,
      meses_mejor_epoca: [],
      metadatos: {
        autoria: 'x',
        fecha_ultima_revision: '2026-01-01',
        publicado_actualizado_en: '2026-01-01',
        seo_descripcion: 'x',
        seo_titulo: 'x',
      },
      nivel_presupuesto: 1,
      pais: { codigo_iso2: 'CO', nombre: 'Colombia', region: { continente: 'AMERICA', nombre: 'S', slug: 's' }, slug: 'colombia' },
      portada: null,
      relacionados: [],
      resumen: 'x',
      seguridad_riesgos: 'x',
      slug: 'patagonia',
      sostenibilidad: 'x',
      terminos: [],
      tipo_principal: { slug: 't', nombre: 'T' },
      tipos: [],
      titulo: 'Patagonia',
    });
    const resultado = await promesa;
    expect(resultado.slug).toBe('patagonia');
  });

  it('mapaCompleto() recorre todas las páginas y fusiona los resultados', async () => {
    const promesa = repo.mapaCompleto();
    const primera = http.expectOne((r) => r.url === '/api/v1/publico/destinos/mapa' && r.params.get('pagina') === null);
    primera.flush({
      anterior: null,
      pagina: 1,
      siguiente: '/x?pagina=2',
      tamano_pagina: 1,
      total: 2,
      total_paginas: 2,
      resultados: [{ dificultad: 1, latitud: 1, longitud: 1, pais: { slug: 'p', nombre: 'P' }, region: { slug: 'r', nombre: 'R' }, slug: 'a', titulo: 'A' }],
    });
    // La segunda petición se dispara tras resolverse la primera Promise (varios microtasks después).
    const segunda = await vi.waitFor(() =>
      http.expectOne((r) => r.url === '/api/v1/publico/destinos/mapa' && r.params.get('pagina') === '2'),
    );
    segunda.flush({
      anterior: '/x',
      pagina: 2,
      siguiente: null,
      tamano_pagina: 1,
      total: 2,
      total_paginas: 2,
      resultados: [{ dificultad: 1, latitud: 2, longitud: 2, pais: { slug: 'p', nombre: 'P' }, region: { slug: 'r', nombre: 'R' }, slug: 'b', titulo: 'B' }],
    });
    const resultado = await promesa;
    expect(resultado.map((p) => p.slug)).toEqual(['a', 'b']);
  });

  it('meses() y textoDescargo() llaman a publico-general', async () => {
    const promesaMeses = repo.meses();
    http.expectOne('/api/v1/publico/meses').flush({ meses: [] });
    expect(await promesaMeses).toEqual([]);

    const promesaDescargo = repo.textoDescargo();
    http.expectOne('/api/v1/publico/configuracion').flush({
      nombre_marca: 'Brújula Salvaje',
      responsable: { definido: false },
      texto_descargo: 'Descargo de prueba',
    });
    expect(await promesaDescargo).toBe('Descargo de prueba');
  });
});
