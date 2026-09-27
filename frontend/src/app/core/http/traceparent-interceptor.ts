import { HttpInterceptorFn } from '@angular/common/http';

import { CABECERA_TRACEPARENT, esTraceparentValido, generarTraceparent } from './traceparent';

/**
 * Propaga la cabecera W3C `traceparent` en cada petición (Skill_Frontend §27.5).
 * Si la petición ya trae un `traceparent` válido (p. ej. reenviado por el SSR, ADR-API-002 §9),
 * se respeta sin modificarlo; si no, se genera uno nuevo.
 */
export const traceparentInterceptor: HttpInterceptorFn = (req, next) => {
  if (esTraceparentValido(req.headers.get(CABECERA_TRACEPARENT))) {
    return next(req);
  }
  return next(req.clone({ setHeaders: { [CABECERA_TRACEPARENT]: generarTraceparent() } }));
};
