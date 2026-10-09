import { HttpEventType, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { ApiConfiguration } from '../../../api/api-configuration';
import { Licencia } from '../../../api/models/licencia';
import { MedioPanel } from '../../../api/models/medio-panel';
import { FILTROS_VACIOS } from '../domain/medios';
import {
  aCatalogacionDto,
  mapLicencia,
  mapMedio,
  mapPaginaUsos,
  mapResultadoSubida,
  paramsListado,
} from './medios.mapper';
import { PanelMediosRepositorio, nuevaClaveIdempotencia } from './panel-medios.repositorio';

const BASE = '/api/v1/panel';

export const MEDIO_DTO: MedioPanel = {
  id: 7,
  estado: 'PENDIENTE_METADATOS',
  titulo_interno: null,
  texto_alternativo: null,
  pie_de_foto: null,
  autor_credito: null,
  fuente_url: null,
  licencia: null,
  formato_origen: 'PNG',
  ancho_px: 1600,
  alto_px: 1000,
  peso_bytes: 2048,
  derivados: [{ formato: 'WEBP', ancho: 320, alto: 200, url: '/api/v1/panel/medios/7/archivo?ancho=320&formato=WEBP' }],
  numero_usos: 0,
  en_uso_publicado: false,
  subido_por: { id: 3, etiqueta: '#3' },
  subido_en: '2026-09-30T10:00:00Z',
  actualizado_en: '2026-09-30T11:00:00Z',
  pendientes_catalogacion: ['texto_alternativo', 'autor_credito', 'licencia'],
};

function pagina<T>(resultados: T[], extra: Record<string, unknown> = {}) {
  return {
    resultados,
    pagina: 1,
    total_paginas: 1,
    total: resultados.length,
    tamano_pagina: 48,
    anterior: null,
    siguiente: null,
    ...extra,
  };
}

describe('medios.mapper (contrato → dominio)', () => {
  it('traduce un medio, con y sin licencia', () => {
    const medio = mapMedio(MEDIO_DTO);
    expect(medio).toMatchObject({
      id: 7,
      estado: 'PENDIENTE_METADATOS',
      tituloInterno: null,
      licencia: null,
      anchoPx: 1600,
      subidoPor: '#3',
      pendientes: ['texto_alternativo', 'autor_credito', 'licencia'],
    });
    expect(medio.derivados[0]).toEqual({
      formato: 'WEBP',
      ancho: 320,
      alto: 200,
      url: '/api/v1/panel/medios/7/archivo?ancho=320&formato=WEBP',
    });
    expect(medio.subidoEn.toISOString()).toBe('2026-09-30T10:00:00.000Z');
    const conLicencia = mapMedio({
      ...MEDIO_DTO,
      licencia: { id: 2, codigo: 'CC0', nombre: 'CC0', compatible_publicacion: true },
      derivados: [{ formato: 'JPEG', ancho: 640, url: '/x' }],
      titulo_interno: undefined,
    });
    expect(conLicencia.licencia).toEqual({ id: 2, codigo: 'CC0', nombre: 'CC0', compatiblePublicacion: true });
    expect(conLicencia.derivados[0].alto).toBeNull();
    expect(conLicencia.tituloInterno).toBeNull();
  });

  it('licencias con campos opcionales, usos y resultados de subida', () => {
    const completa: Licencia = { id: 1, codigo: 'A', nombre: 'Lic A', compatible_publicacion: true, activo: true };
    expect(mapLicencia(completa)).toEqual({ id: 1, codigo: 'A', nombre: 'Lic A', compatiblePublicacion: true, activa: true });
    expect(mapLicencia({ id: 2 })).toEqual({ id: 2, codigo: '', nombre: 'Licencia 2', compatiblePublicacion: false, activa: false });
    expect(mapLicencia({ id: 3, codigo: 'B' }).nombre).toBe('B');

    const usos = mapPaginaUsos(
      pagina([{ tipo_contenido: 'DESTINO', contenido_id: 4, titulo: 'Patagonia', rol: 'PORTADA', estado_editorial: 'PUBLICADO' },
        { tipo_contenido: 'CONFIG_INICIO', contenido_id: 1, titulo: 'Inicio', rol: 'HERO' }]),
    );
    expect(usos.usos).toEqual([
      { tipoContenido: 'DESTINO', contenidoId: 4, titulo: 'Patagonia', estadoEditorial: 'PUBLICADO', rol: 'PORTADA' },
      { tipoContenido: 'CONFIG_INICIO', contenidoId: 1, titulo: 'Inicio', estadoEditorial: null, rol: 'HERO' },
    ]);

    const resultados = mapResultadoSubida({
      resultados: [
        { nombre_archivo: 'a.png', resultado: 'ACEPTADO', medio: MEDIO_DTO },
        { nombre_archivo: 'b.png', resultado: 'DUPLICADO', medio_existente_id: 9 },
        { nombre_archivo: 'c.png', resultado: 'RECHAZADO', motivo: { code: 'archivo_corrupto', detalle: 'x' } },
      ],
    });
    expect(resultados.map((r) => [r.resultado, r.medio?.id ?? null, r.medioExistenteId, r.motivo, r.local])).toEqual([
      ['ACEPTADO', 7, null, null, false],
      ['DUPLICADO', null, 9, null, false],
      ['RECHAZADO', null, null, 'archivo_corrupto', false],
    ]);
  });

  it('AC_TKT022_02 parámetros del listado y cuerpo de la catalogación (solo campos presentes)', () => {
    expect(paramsListado(FILTROS_VACIOS)).toEqual({
      estado: undefined,
      licencia: undefined,
      en_uso: undefined,
      q: undefined,
      pagina: undefined,
    });
    expect(paramsListado({ estado: 'DISPONIBLE', licencia: 'CC0', enUso: false, q: 'río', pagina: 3 })).toEqual({
      estado: 'DISPONIBLE',
      licencia: 'CC0',
      en_uso: false,
      q: 'río',
      pagina: 3,
    });
    expect(aCatalogacionDto({})).toEqual({});
    expect(
      aCatalogacionDto({
        tituloInterno: null,
        textoAlternativo: 'Alt',
        pieDeFoto: null,
        autorCredito: 'Ana',
        fuenteUrl: null,
        licenciaId: 2,
      }),
    ).toEqual({
      titulo_interno: null,
      texto_alternativo: 'Alt',
      pie_de_foto: null,
      autor_credito: 'Ana',
      fuente_url: null,
      licencia_id: 2,
    });
  });
});

describe('PanelMediosRepositorio (cliente generado)', () => {
  let http: HttpTestingController;
  let repo: PanelMediosRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(PanelMediosRepositorio);
  });

  afterEach(() => http.verify());

  it('AC_TKT022_02 listar con filtros, obtener, usos, catalogar, retirar y reactivar', async () => {
    const listado = repo.listar({ estado: 'RETIRADO', licencia: null, enUso: true, q: 'lago', pagina: 2 });
    const peticion = http.expectOne((r) => r.url === `${BASE}/medios`);
    expect(peticion.request.params.get('estado')).toBe('RETIRADO');
    expect(peticion.request.params.get('en_uso')).toBe('true');
    expect(peticion.request.params.get('q')).toBe('lago');
    expect(peticion.request.params.get('pagina')).toBe('2');
    expect(peticion.request.params.has('licencia')).toBe(false);
    peticion.flush(pagina([MEDIO_DTO], { pagina: 2, total_paginas: 3, total: 100 }));
    expect(await listado).toMatchObject({ pagina: 2, totalPaginas: 3, total: 100 });

    const obtener = repo.obtener(7);
    http.expectOne(`${BASE}/medios/7`).flush(MEDIO_DTO);
    expect((await obtener).id).toBe(7);

    const usos = repo.usos(7, 2);
    const peticionUsos = http.expectOne((r) => r.url === `${BASE}/medios/7/usos`);
    expect(peticionUsos.request.params.get('pagina')).toBe('2');
    peticionUsos.flush(pagina([]));
    expect((await usos).total).toBe(0);
    const usosPrimera = repo.usos(7);
    const primera = http.expectOne((r) => r.url === `${BASE}/medios/7/usos`);
    expect(primera.request.params.has('pagina')).toBe(false);
    primera.flush(pagina([]));
    await usosPrimera;

    const catalogar = repo.catalogar(7, { textoAlternativo: 'Alt', fuenteUrl: null });
    const put = http.expectOne(`${BASE}/medios/7`);
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual({ texto_alternativo: 'Alt', fuente_url: null });
    put.flush({ ...MEDIO_DTO, estado: 'DISPONIBLE' });
    expect((await catalogar).estado).toBe('DISPONIBLE');

    const retirar = repo.retirar(7);
    http.expectOne(`${BASE}/medios/7/retirar`).flush({ ...MEDIO_DTO, estado: 'RETIRADO' });
    expect((await retirar).estado).toBe('RETIRADO');
    const reactivar = repo.reactivar(7);
    http.expectOne(`${BASE}/medios/7/reactivar`).flush(MEDIO_DTO);
    expect((await reactivar).estado).toBe('PENDIENTE_METADATOS');
  });

  it('lee todas las páginas del catálogo de licencias', async () => {
    const licencias = repo.licencias();
    http
      .expectOne((r) => r.url === `${BASE}/taxonomias/licencias` && !r.params.has('pagina'))
      .flush(pagina([{ id: 1, codigo: 'A', nombre: 'A', activo: true }], { total_paginas: 2, siguiente: '/x?pagina=2' }));
    await new Promise((r) => setTimeout(r, 0));
    http
      .expectOne((r) => r.url === `${BASE}/taxonomias/licencias` && r.params.get('pagina') === '2')
      .flush(pagina([{ id: 2, codigo: 'B', nombre: 'B', activo: false }], { pagina: 2, total_paginas: 2 }));
    expect((await licencias).map((l) => l.id)).toEqual([1, 2]);
  });

  it('AC_TKT022_01 subida multipart con Idempotency-Key, progreso y resultado por archivo', async () => {
    const progreso: [number, number | null][] = [];
    const archivo = new File([new Uint8Array([1, 2, 3])], 'a.png', { type: 'image/png' });
    const resultado = firstValueFrom(repo.subir([archivo], 'clave-1', (c, t) => progreso.push([c, t])));
    const peticion = http.expectOne(`${BASE}/medios`);
    expect(peticion.request.method).toBe('POST');
    expect(peticion.request.headers.get('Idempotency-Key')).toBe('clave-1');
    expect(peticion.request.reportProgress).toBe(true);
    const cuerpo = peticion.request.body as FormData;
    expect((cuerpo.getAll('archivos')[0] as File).name).toBe('a.png');
    peticion.event({ type: HttpEventType.UploadProgress, loaded: 50, total: 100 });
    peticion.event({ type: HttpEventType.UploadProgress, loaded: 100 });
    peticion.flush({ resultados: [{ nombre_archivo: 'a.png', resultado: 'ACEPTADO', medio: MEDIO_DTO }] });
    expect((await resultado)[0].medio?.id).toBe(7);
    expect(progreso).toEqual([
      [50, 100],
      [100, null],
    ]);

    const vacio = firstValueFrom(repo.subir([archivo], 'clave-2', () => undefined));
    http.expectOne(`${BASE}/medios`).flush(null);
    expect(await vacio).toEqual([]);
  });

  it('clave de idempotencia UUID v4 sin necesitar un contexto seguro', () => {
    const clave = nuevaClaveIdempotencia();
    expect(clave).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(nuevaClaveIdempotencia()).not.toBe(clave);
    const fijo = { getRandomValues: (b: Uint8Array) => b.fill(255) } as unknown as Crypto;
    expect(nuevaClaveIdempotencia(fijo)).toBe('ffffffff-ffff-4fff-bfff-ffffffffffff');
  });
});
