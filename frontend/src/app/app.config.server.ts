import { ApplicationConfig, CSP_NONCE, REQUEST, inject, mergeApplicationConfig } from '@angular/core';
import { provideServerRendering, withRoutes } from '@angular/ssr';

import { appConfig } from './app.config';
import { serverRoutes } from './app.routes.server';
import { API_INTERNAL_URL, validarUrlInterna } from './core/http/api-interna';
import { CABECERA_NONCE_CSP, nonceDesdePeticion } from './core/http/nonce-csp';

/**
 * Configuración del SSR (DEVOPS_HANDOFF §6.5):
 * - CSP_NONCE desde la cabecera `x-csp-nonce` que envía el proxy (validada).
 * - API_INTERNAL_URL para que el SSR llame al backend por la red interna de Compose.
 */
const serverConfig: ApplicationConfig = {
  providers: [
    provideServerRendering(withRoutes(serverRoutes)),
    {
      provide: CSP_NONCE,
      useFactory: () => nonceDesdePeticion(inject(REQUEST, { optional: true })?.headers.get(CABECERA_NONCE_CSP)),
    },
    {
      provide: API_INTERNAL_URL,
      useFactory: () => validarUrlInterna(process.env['API_INTERNAL_URL']),
    },
  ],
};

export const config = mergeApplicationConfig(appConfig, serverConfig);
