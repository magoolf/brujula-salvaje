import {
  provideHttpClient,
  withFetch,
  withInterceptors,
  withXsrfConfiguration,
} from '@angular/common/http';
import { EnvironmentProviders, Provider } from '@angular/core';

import { provideApiConfiguration } from '../../api/api-configuration';
import { sesionPanelInterceptor } from '../auth/sesion-panel-interceptor';
import { reenvioSsrInterceptor } from './reenvio-ssr-interceptor';
import { traceparentInterceptor } from './traceparent-interceptor';

/** Nombres de la cookie y la cabecera CSRF de Django (Skill_Frontend §27.4, ADR-API-001). */
export const XSRF_COOKIE = 'csrftoken';
export const XSRF_CABECERA = 'X-CSRFToken';

/**
 * Infraestructura HTTP transversal (Skill_Frontend §27.4 y §27.5):
 * - fetch (compatible con SSR);
 * - XSRF alineado con Django: cookie `csrftoken` → cabecera `X-CSRFToken` (mismo origen);
 * - `traceparent` W3C en cada petición;
 * - reenvío al backend interno durante el SSR;
 * - tratamiento global del 401 del panel (Skill_Frontend §12).
 * El cliente generado usa rutas absolutas desde la raíz (`/api/v1/...`), así que su rootUrl es ''.
 */
export function proveerHttp(): (Provider | EnvironmentProviders)[] {
  return [
    provideHttpClient(
      withFetch(),
      withXsrfConfiguration({ cookieName: XSRF_COOKIE, headerName: XSRF_CABECERA }),
      withInterceptors([reenvioSsrInterceptor, traceparentInterceptor, sesionPanelInterceptor]),
    ),
    provideApiConfiguration(''),
  ];
}
