import { HttpErrorResponse, HttpHeaders } from '@angular/common/http';

import { MENSAJE_ERROR_GENERICO, MENSAJE_SIN_CONEXION } from './error-api.model';
import { categoriaPorEstado, normalizarError, normalizarRespuesta, tipoDesdeUri } from './normalizar-error';

/** Ejemplo literal de contracts/openapi.yaml → components.responses.Validacion (400). */
const PROBLEMA_VALIDACION = {
  type: 'https://brujulasalvaje.example/errors/validacion',
  title: 'Datos inválidos',
  status: 400,
  detail: 'Revisa los campos marcados.',
  code: 'validacion',
  errors: { resumen: ['Máximo 300 caracteres.'] },
  trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
};

/** Ejemplo literal de contracts/openapi.yaml → components.responses.ReglaNegocio (422). */
const PROBLEMA_PUBLICACION = {
  type: 'https://brujulasalvaje.example/errors/publicacion_invalida',
  title: 'No se puede publicar',
  status: 422,
  detail: 'Faltan requisitos de publicación.',
  code: 'publicacion_invalida',
  errors: {
    galeria_ids: ['Se necesitan al menos 3 medios DISPONIBLES.'],
    descripcion_experta: ['Mínimo 600 palabras.'],
  },
  trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
};

function respuestaHttp(status: number, error: unknown): HttpErrorResponse {
  return new HttpErrorResponse({
    status,
    error,
    url: '/api/v1/panel/contenidos/destinos',
    headers: new HttpHeaders({ 'Content-Type': 'application/problem+json' }),
  });
}

describe('normalizarError (RFC 9457 → ErrorApi)', () => {
  it('AC_TKT002_04 mapea el problem+json de validación del contrato: type→tipo, detail→mensaje, errors→campos, trace_id→traceId', () => {
    const error = normalizarError(respuestaHttp(400, PROBLEMA_VALIDACION));

    expect(error).toEqual({
      tipo: 'validacion',
      categoria: 'validacion',
      codigo: 'validacion',
      mensaje: 'Revisa los campos marcados.',
      campos: { resumen: ['Máximo 300 caracteres.'] },
      traceId: '4bf92f3577b34da6a3ce929d0e0e4736',
      extra: {},
    });
  });

  it('AC_TKT002_04 mapea el problem+json 422 del contrato con varios campos', () => {
    const error = normalizarError(respuestaHttp(422, PROBLEMA_PUBLICACION));

    expect(error.tipo).toBe('publicacion_invalida');
    expect(error.categoria).toBe('regla_negocio');
    expect(error.campos).toEqual(PROBLEMA_PUBLICACION.errors);
    expect(error.traceId).toBe(PROBLEMA_PUBLICACION.trace_id);
  });

  it('AC_TKT002_04 usa title cuando no hay detail', () => {
    const { detail: _omitido, ...sinDetalle } = PROBLEMA_VALIDACION;
    expect(normalizarError(respuestaHttp(400, sinDetalle)).mensaje).toBe('Datos inválidos');
  });

  it('AC_TKT002_04 acepta el cuerpo como texto JSON (fetch sin content-type JSON)', () => {
    const error = normalizarError(respuestaHttp(400, JSON.stringify(PROBLEMA_VALIDACION)));
    expect(error.tipo).toBe('validacion');
    expect(error.campos['resumen']).toEqual(['Máximo 300 caracteres.']);
  });

  it('conserva los miembros de extensión (410 con alternativas y listado_padre)', () => {
    const error = normalizarRespuesta(410, {
      type: 'https://brujulasalvaje.example/errors/retirado',
      title: 'Contenido retirado',
      status: 410,
      code: 'retirado',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
      alternativas: [{ slug: 'patagonia' }],
      listado_padre: '/destinos',
    });
    expect(error.categoria).toBe('retirado');
    expect(error.extra).toEqual({ alternativas: [{ slug: 'patagonia' }], listado_padre: '/destinos' });
  });

  it('nunca muestra el detalle de un 5xx (sin datos técnicos)', () => {
    const error = normalizarRespuesta(500, {
      type: 'https://brujulasalvaje.example/errors/error_interno',
      title: 'Error interno',
      status: 500,
      detail: 'Traceback (most recent call last)…',
      code: 'error_interno',
      trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
    });
    expect(error.mensaje).toBe(MENSAJE_ERROR_GENERICO);
    expect(error.categoria).toBe('servidor');
    expect(error.traceId).toBe('4bf92f3577b34da6a3ce929d0e0e4736');
  });

  it('status 0 → sin_conexion con mensaje de GI-04', () => {
    const error = normalizarError(new HttpErrorResponse({ status: 0, error: new ProgressEvent('error') }));
    expect(error.categoria).toBe('sin_conexion');
    expect(error.tipo).toBe('sin_conexion');
    expect(error.mensaje).toBe(MENSAJE_SIN_CONEXION);
  });

  it('normaliza el formato por defecto de DRF ({campo: [mensajes]} y {detail})', () => {
    const porCampo = normalizarRespuesta(400, { nombre: ['Obligatorio.'], slug: 'Inválido.', vacio: [] });
    expect(porCampo.campos).toEqual({ nombre: ['Obligatorio.'], slug: ['Inválido.'] });
    expect(porCampo.tipo).toBe('validacion');

    const conDetalle = normalizarRespuesta(403, { detail: 'No tienes permiso.' });
    expect(conDetalle.mensaje).toBe('No tienes permiso.');
    expect(conDetalle.campos).toEqual({});
    expect(conDetalle.categoria).toBe('permiso_denegado');
  });

  it('descarta un trace_id con formato inválido', () => {
    expect(normalizarRespuesta(404, { code: 'no_encontrado', trace_id: 'no-es-hex' }).traceId).toBeNull();
  });

  it('errores que no son HTTP → desconocido con mensaje genérico', () => {
    const error = normalizarError(new Error('fallo'));
    expect(error).toMatchObject({ categoria: 'desconocido', tipo: 'desconocido', mensaje: MENSAJE_ERROR_GENERICO });
  });

  it('cuerpos no objeto o JSON inválido no rompen la normalización', () => {
    expect(normalizarRespuesta(400, 'no es json').mensaje).toBe(MENSAJE_ERROR_GENERICO);
    expect(normalizarRespuesta(400, ['x']).campos).toEqual({});
    expect(normalizarRespuesta(400, null).tipo).toBe('validacion');
  });

  it('categoriaPorEstado cubre el catálogo de estados del contrato', () => {
    expect([400, 401, 403, 404, 409, 410, 422, 429, 503, 418].map(categoriaPorEstado)).toEqual([
      'validacion',
      'no_autenticado',
      'permiso_denegado',
      'no_encontrado',
      'conflicto',
      'retirado',
      'regla_negocio',
      'limite_tasa',
      'servidor',
      'desconocido',
    ]);
  });

  it('tipoDesdeUri extrae el último segmento y trata about:blank como ausente', () => {
    expect(tipoDesdeUri('https://x.example/errors/limite_tasa/')).toBe('limite_tasa');
    expect(tipoDesdeUri('https://x.example/errors/duplicado#frag')).toBe('duplicado');
    expect(tipoDesdeUri('about:blank')).toBeNull();
    expect(tipoDesdeUri(null)).toBeNull();
    expect(normalizarRespuesta(409, { type: 'about:blank', code: 'duplicado' }).tipo).toBe('duplicado');
  });
});
