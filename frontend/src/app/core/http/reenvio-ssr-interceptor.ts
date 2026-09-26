import { HttpInterceptorFn } from '@angular/common/http';
import { REQUEST, inject } from '@angular/core';

import { API_INTERNAL_URL, esRutaApi } from './api-interna';

/**
 * Cabeceras de la petición del visitante que el SSR reenvía SIN MODIFICAR a la API
 * (DEVOPS_HANDOFF §6.4, ADR-API-002 §9): la IP real para el throttling por IP, y la
 * correlación de trazas. El proxy ya las saneó (sobrescribe X-Forwarded-For y regenera
 * un traceparent inválido).
 */
export const CABECERAS_REENVIADAS: readonly string[] = ['x-forwarded-for', 'traceparent', 'x-request-id'];

/**
 * Solo actúa durante el renderizado en servidor: reescribe las rutas relativas de la API
 * (`/api/...`) hacia `API_INTERNAL_URL` y reenvía las cabeceras del visitante.
 * En el navegador `REQUEST` es null y la petición sigue intacta al mismo origen.
 */
export const reenvioSsrInterceptor: HttpInterceptorFn = (req, next) => {
  const peticionEntrante = inject(REQUEST, { optional: true });
  const base = inject(API_INTERNAL_URL);
  if (peticionEntrante === null || base === null || !esRutaApi(req.url)) {
    return next(req);
  }

  const cabeceras: Record<string, string> = {};
  for (const nombre of CABECERAS_REENVIADAS) {
    const valor = peticionEntrante.headers.get(nombre);
    if (valor !== null && !req.headers.has(nombre)) cabeceras[nombre] = valor;
  }
  return next(req.clone({ url: base + req.url, setHeaders: cabeceras }));
};
