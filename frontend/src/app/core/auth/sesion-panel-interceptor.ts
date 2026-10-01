import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { esNoAutenticado } from '../http/clasificar-error';
import { normalizarError } from '../http/normalizar-error';
import { RUTA_ACCESO_PANEL, esDestinoSeguro } from './destino-seguro';

/** API del panel protegida por sesión. */
const PREFIJO_API_PANEL = '/api/v1/panel/';
const PREFIJO_API_AUTH = '/api/v1/panel/auth/';

/**
 * Endpoints de autenticación que gestionan su propio 401: el login y la emisión del CSRF (sin
 * sesión todavía) y la consulta del estado de la sesión, que usan los guards del panel para decidir
 * a dónde ir (con el `siguiente` de la navegación en curso, no el de la URL actual).
 */
const AUTH_SIN_TRATAMIENTO_GLOBAL = new Set(['login', 'csrf', 'sesion']);

/**
 * Códigos 401 que NO significan sesión expirada sino un dato erróneo de la persona: la contraseña
 * de una reautenticación (DEC-AUTO-215, contrato: «el cliente NO debe tratar este 401 como sesión
 * expirada; distinguir por `code`») y el código del segundo factor (FEAT-030). Se muestran como
 * error del campo y no se pierde el formulario.
 */
const CODIGOS_401_DE_CAMPO = new Set(['credenciales_invalidas', 'mfa_invalido']);

/** Motivo que SCR-030 muestra tras la redirección (ALT-014). */
export const MOTIVO_SESION_EXPIRADA = 'expirada';

function gestionaSuPropio401(url: string): boolean {
  if (!url.startsWith(PREFIJO_API_AUTH)) return false;
  const operacion = url.slice(PREFIJO_API_AUTH.length).split(/[?#]/)[0];
  return AUTH_SIN_TRATAMIENTO_GLOBAL.has(operacion);
}

/**
 * Tratamiento GLOBAL del 401 (Skill_Frontend §12, decisión del proyecto; el 403 lo trata cada
 * feature con SCR-048). La autenticación es por cookie de sesión HttpOnly gestionada por Django
 * (ADR-API-001): este interceptor NO lee ni adjunta credenciales. Ante un 401 de sesión expirada o
 * ausente en la API del panel redirige a SCR-030 conservando un `siguiente` interno seguro
 * (ST-UNAUTHORIZED, AC-115, ALT-014) y propaga el error para que la feature conserve los datos del
 * formulario en la página.
 */
export const sesionPanelInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(PREFIJO_API_PANEL) || gestionaSuPropio401(req.url)) {
    return next(req);
  }
  const router = inject(Router);
  return next(req).pipe(
    catchError((error: unknown) => {
      if (esNoAutenticado(error) && !CODIGOS_401_DE_CAMPO.has(normalizarError(error).codigo ?? '')) {
        const actual = router.url;
        const queryParams: Record<string, string> = { motivo: MOTIVO_SESION_EXPIRADA };
        if (esDestinoSeguro(actual)) queryParams['siguiente'] = actual;
        void router.navigate([RUTA_ACCESO_PANEL], { queryParams });
      }
      return throwError(() => error);
    }),
  );
};
