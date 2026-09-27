import { InjectionToken } from '@angular/core';

/**
 * Prefijos de las rutas del backend servidas en el mismo origen por el proxy (ADR-API-001).
 * Excepción documentada a la Regla 02: core/http necesita reconocer las peticiones a la API para
 * aplicar infraestructura transversal (reenvío SSR, sesión); las URL concretas viven en data/ y en
 * el cliente generado (src/app/api).
 */
export const PREFIJOS_API: readonly string[] = ['/api/', '/health/'];

export function esRutaApi(url: string): boolean {
  return PREFIJOS_API.some((p) => url.startsWith(p));
}

/**
 * URL base con la que el SSR llama a la API dentro de la red de Compose (`API_INTERNAL_URL`,
 * DEVOPS_HANDOFF §6). En el navegador no se provee: las llamadas van al mismo origen.
 */
export const API_INTERNAL_URL = new InjectionToken<string | null>('API_INTERNAL_URL', {
  providedIn: 'root',
  factory: () => null,
});

/** Valida `API_INTERNAL_URL`: solo http(s) sin credenciales, query ni fragmento. */
export function validarUrlInterna(valor: string | undefined | null): string | null {
  if (valor === undefined || valor === null || valor.trim() === '') return null;
  let url: URL;
  try {
    url = new URL(valor.trim());
  } catch {
    return null;
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
  if (url.username !== '' || url.password !== '' || url.search !== '' || url.hash !== '')
    return null;
  return url.origin + url.pathname.replace(/\/+$/, '');
}
