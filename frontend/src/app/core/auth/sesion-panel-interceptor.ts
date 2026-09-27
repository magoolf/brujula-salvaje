import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { esNoAutenticado } from '../http/clasificar-error';
import { RUTA_ACCESO_PANEL, esDestinoSeguro } from './destino-seguro';

/** API del panel protegida por sesión; los endpoints de autenticación gestionan su propio 401. */
const PREFIJO_API_PANEL = '/api/v1/panel/';
const PREFIJO_API_AUTH = '/api/v1/panel/auth/';

/**
 * Tratamiento GLOBAL del 401 (Skill_Frontend §12, decisión del proyecto; el 403 lo trata cada
 * feature). La autenticación es por cookie de sesión HttpOnly gestionada por Django (ADR-API-001):
 * este interceptor NO lee ni adjunta credenciales. Ante un 401 de la API del panel redirige a
 * SCR-030 conservando un `siguiente` interno seguro (ST-UNAUTHORIZED, AC-115) y propaga el error
 * para que la feature conserve los datos del formulario.
 */
export const sesionPanelInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(PREFIJO_API_PANEL) || req.url.startsWith(PREFIJO_API_AUTH)) {
    return next(req);
  }
  const router = inject(Router);
  return next(req).pipe(
    catchError((error: unknown) => {
      if (esNoAutenticado(error)) {
        const actual = router.url;
        const queryParams = esDestinoSeguro(actual) ? { siguiente: actual } : {};
        void router.navigate([RUTA_ACCESO_PANEL], { queryParams });
      }
      return throwError(() => error);
    }),
  );
};
