import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Modos de renderizado (DEVOPS_HANDOFF §6.5, RSK-UX-001): las rutas públicas se renderizan por
 * petición (RenderMode.Server) para llevar el nonce CSP de cada respuesta y el código HTTP real
 * (404/410/500); el panel es solo cliente (noindex, sin SSR de datos de sesión).
 * No se usa RenderMode.Prerender: una página prerenderizada no puede llevar nonce por petición.
 */
export const serverRoutes: ServerRoute[] = [
  { path: 'panel/**', renderMode: RenderMode.Client },
  { path: '**', renderMode: RenderMode.Server },
];
