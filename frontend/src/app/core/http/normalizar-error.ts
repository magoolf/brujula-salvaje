import { HttpErrorResponse } from '@angular/common/http';

import {
  CategoriaErrorApi,
  ErrorApi,
  MENSAJE_ERROR_GENERICO,
  MENSAJE_SIN_CONEXION,
} from './error-api.model';

/**
 * Normalización de errores HTTP → ErrorApi (Skill_Frontend §10, Regla 09: `HttpErrorResponse`
 * solo aparece en core/http). Acepta RFC 9457 (application/problem+json) y, por robustez, el
 * formato por defecto de DRF (`{detail}` o `{campo: [mensajes]}`).
 */
export function normalizarError(error: unknown): ErrorApi {
  if (error instanceof HttpErrorResponse) {
    return normalizarRespuesta(error.status, error.error);
  }
  return crearError('desconocido', null, null, MENSAJE_ERROR_GENERICO, {}, null, {});
}

const MIEMBROS_ESTANDAR = new Set([
  'type',
  'title',
  'status',
  'detail',
  'instance',
  'code',
  'errors',
  'trace_id',
]);
const TRACE_ID = /^[0-9a-f]{32}$/;

/** Función pura (sin Angular) para normalizar un estado HTTP y su cuerpo. */
export function normalizarRespuesta(estado: number, cuerpo: unknown): ErrorApi {
  const categoria = categoriaPorEstado(estado);
  if (categoria === 'sin_conexion') {
    return crearError(categoria, null, null, MENSAJE_SIN_CONEXION, {}, null, {});
  }

  const datos = aObjeto(cuerpo);
  const codigo = textoONulo(datos['code']);
  const tipoUri = textoONulo(datos['type']);
  const traceId = textoONulo(datos['trace_id']);
  const campos = extraerCampos(datos);

  // En errores del servidor nunca se muestra el detalle recibido (ST-ERROR, THREAT-028).
  const mensaje =
    categoria === 'servidor'
      ? MENSAJE_ERROR_GENERICO
      : (textoONulo(datos['detail']) ?? textoONulo(datos['title']) ?? MENSAJE_ERROR_GENERICO);

  const extra: Record<string, unknown> = {};
  if (esProblema(datos)) {
    for (const [clave, valor] of Object.entries(datos)) {
      if (!MIEMBROS_ESTANDAR.has(clave)) extra[clave] = valor;
    }
  }

  return crearError(
    categoria,
    codigo,
    tipoUri,
    mensaje,
    campos,
    traceId !== null && TRACE_ID.test(traceId) ? traceId : null,
    extra,
  );
}

export function categoriaPorEstado(estado: number): CategoriaErrorApi {
  if (estado === 0) return 'sin_conexion';
  if (estado >= 500) return 'servidor';
  switch (estado) {
    case 400:
      return 'validacion';
    case 401:
      return 'no_autenticado';
    case 403:
      return 'permiso_denegado';
    case 404:
      return 'no_encontrado';
    case 409:
      return 'conflicto';
    case 410:
      return 'retirado';
    case 422:
      return 'regla_negocio';
    case 429:
      return 'limite_tasa';
    default:
      return 'desconocido';
  }
}

/** Último segmento de la URI `type` (`https://…/errors/validacion` → `validacion`). */
export function tipoDesdeUri(tipoUri: string | null): string | null {
  if (tipoUri === null || tipoUri === 'about:blank') return null;
  const sinFragmento = tipoUri.split(/[?#]/)[0].replace(/\/+$/, '');
  const segmento = sinFragmento.substring(sinFragmento.lastIndexOf('/') + 1);
  return segmento.length > 0 ? segmento : null;
}

function crearError(
  categoria: CategoriaErrorApi,
  codigo: string | null,
  tipoUri: string | null,
  mensaje: string,
  campos: Record<string, readonly string[]>,
  traceId: string | null,
  extra: Record<string, unknown>,
): ErrorApi {
  return {
    tipo: tipoDesdeUri(tipoUri) ?? codigo ?? categoria,
    categoria,
    codigo,
    mensaje,
    campos,
    traceId,
    extra,
  };
}

function esProblema(datos: Record<string, unknown>): boolean {
  return 'type' in datos || 'title' in datos || 'code' in datos || 'trace_id' in datos;
}

function extraerCampos(datos: Record<string, unknown>): Record<string, readonly string[]> {
  // RFC 9457 del contrato: `errors` por campo.
  if ('errors' in datos) return mensajesPorCampo(aObjeto(datos['errors']));
  // DRF sin Problem Details: el propio cuerpo es el mapa de campos.
  if (!esProblema(datos) && !('detail' in datos)) return mensajesPorCampo(datos);
  return {};
}

function mensajesPorCampo(origen: Record<string, unknown>): Record<string, readonly string[]> {
  const campos: Record<string, readonly string[]> = {};
  for (const [campo, valor] of Object.entries(origen)) {
    const mensajes = (Array.isArray(valor) ? valor : [valor]).filter(
      (m): m is string => typeof m === 'string' && m.length > 0,
    );
    if (mensajes.length > 0) campos[campo] = mensajes;
  }
  return campos;
}

function aObjeto(valor: unknown): Record<string, unknown> {
  if (typeof valor === 'string') {
    try {
      return aObjeto(JSON.parse(valor));
    } catch {
      return {};
    }
  }
  return typeof valor === 'object' && valor !== null && !Array.isArray(valor)
    ? (valor as Record<string, unknown>)
    : {};
}

function textoONulo(valor: unknown): string | null {
  return typeof valor === 'string' && valor.trim().length > 0 ? valor : null;
}
