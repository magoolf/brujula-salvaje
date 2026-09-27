import { HttpErrorResponse } from '@angular/common/http';

/**
 * Consultas sobre errores HTTP para la infraestructura de core/ (Regla 09: el tipo
 * `HttpErrorResponse` solo se usa dentro de core/http).
 */
export function esNoAutenticado(error: unknown): boolean {
  return error instanceof HttpErrorResponse && error.status === 401;
}
