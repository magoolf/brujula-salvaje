import { ErrorHandler, Injectable, InjectionToken, inject } from '@angular/core';
import { Router } from '@angular/router';

import { normalizarError } from '../http/normalizar-error';
import { VERSION_APP } from './version-app';

/** Registro estructurado de un error no controlado. No contiene PII (Skill_Frontend §27.5). */
export interface RegistroError {
  readonly evento: 'error_no_controlado';
  readonly nombre: string;
  readonly mensaje: string;
  readonly traceId: string | null;
  readonly ruta: string;
  readonly version: string;
}

/** Destino del registro. Por defecto la consola (no hay analítica ni envío a terceros, CON-002). */
export const DESTINO_REGISTRO_ERRORES = new InjectionToken<(registro: RegistroError) => void>(
  'DESTINO_REGISTRO_ERRORES',
  { providedIn: 'root', factory: () => (registro) => console.error(registro) },
);

const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/g;
const QUERY = /\?[^\s#'"]*/g;
const DIGITOS_LARGOS = /\d{6,}/g;

/** Elimina datos potencialmente personales de un texto libre (query strings, correos, números largos). */
export function sanearTexto(texto: string, maximo = 300): string {
  return texto
    .replace(QUERY, '?[omitido]')
    .replace(EMAIL, '[correo]')
    .replace(DIGITOS_LARGOS, '[numero]')
    .slice(0, maximo);
}

/** Ruta sin query string ni fragmento (la búsqueda del visitante podría contener datos personales). */
export function rutaSinParametros(url: string): string {
  return url.split(/[?#]/)[0] || '/';
}

/**
 * ErrorHandler global (Skill_Frontend §27.5): registra traceId, ruta y versión de la app sin PII.
 * No muestra nada al usuario: las pantallas de error las gestionan las features y core/layout.
 */
@Injectable()
export class ManejadorErroresGlobal implements ErrorHandler {
  private readonly router = inject(Router, { optional: true });
  private readonly destino = inject(DESTINO_REGISTRO_ERRORES);

  handleError(error: unknown): void {
    const normalizado = normalizarError(error);
    const nombre = error instanceof Error ? error.name : typeof error;
    const mensaje = error instanceof Error ? sanearTexto(error.message) : '';
    this.destino({
      evento: 'error_no_controlado',
      nombre,
      mensaje,
      traceId: normalizado.traceId,
      ruta: rutaSinParametros(this.router?.url ?? '/'),
      version: VERSION_APP,
    });
  }
}
