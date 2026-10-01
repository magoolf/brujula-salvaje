/**
 * DATA: el contrato solo comunica el tiempo de bloqueo (429 acceso_bloqueado_temporalmente /
 * limite_tasa) en la cabecera `Retry-After`, que la normalización común (core/http) no conserva.
 * Este adaptador copia ese valor como miembro de extensión del Problem Details
 * (`reintentar_en_segundos`), de modo que llega a `ErrorApi.extra` sin que STATE/UI conozcan
 * cabeceras ni códigos HTTP (Reglas 09 y 13). Se reconoce por su forma (sin importar
 * HttpErrorResponse, Regla 09) y se devuelve el MISMO error para que `normalizarError` lo trate igual.
 */
export const CAMPO_ESPERA = 'reintentar_en_segundos';

interface ErrorConCabeceras {
  headers: { get(nombre: string): string | null };
  error: unknown;
}

function tieneCabeceras(error: unknown): error is ErrorConCabeceras {
  if (typeof error !== 'object' || error === null || !('headers' in error)) return false;
  const cabeceras = (error as { headers: unknown }).headers;
  return (
    typeof cabeceras === 'object' &&
    cabeceras !== null &&
    typeof (cabeceras as { get?: unknown }).get === 'function'
  );
}

/** Retry-After en segundos (entero ≥ 1) o null si falta o no es numérico. */
export function leerRetryAfter(valor: string | null): number | null {
  if (valor === null || !/^\d+$/.test(valor.trim())) return null;
  const segundos = Number(valor.trim());
  return segundos > 0 ? segundos : null;
}

export function anotarEspera(error: unknown): unknown {
  if (!tieneCabeceras(error)) return error;
  const segundos = leerRetryAfter(error.headers.get('Retry-After'));
  if (segundos === null) return error;
  error.error = { ...aObjeto(error.error), [CAMPO_ESPERA]: segundos };
  return error;
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
