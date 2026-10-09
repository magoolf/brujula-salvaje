import { registerLocaleData } from '@angular/common';
import localeEsCo from '@angular/common/locales/es-CO';
import {
  ApplicationConfig,
  ErrorHandler,
  LOCALE_ID,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import {
  provideClientHydration,
  withNoHttpTransferCache,
  withNoIncrementalHydration,
} from '@angular/platform-browser';
import {
  TitleStrategy,
  provideRouter,
  withComponentInputBinding,
  withInMemoryScrolling,
} from '@angular/router';

import { routes } from './app.routes';
import { proveerHttp } from './core/http/proveer-http';
import { ManejadorErroresGlobal } from './core/observabilidad/manejador-errores.handler';
import { EstrategiaTitulo } from './core/seo/estrategia-titulo';
import { LOCALE } from './core/seo/marca';

registerLocaleData(localeEsCo, LOCALE);

/**
 * Configuración de la aplicación (Skill_Frontend: Angular 22 zoneless por defecto — sin
 * provideZoneChangeDetection ni zone.js —, standalone, Signals).
 */
export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    { provide: ErrorHandler, useClass: ManejadorErroresGlobal },
    { provide: LOCALE_ID, useValue: LOCALE },
    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled', anchorScrolling: 'enabled' }),
    ),
    { provide: TitleStrategy, useClass: EstrategiaTitulo },
    // Sin hidratación incremental ni event replay (activos por defecto en Angular 22): su contrato
    // de eventos se inyecta en el build como <script> en línea
    // SIN nonce y la CSP estricta lo bloquearía (AC-TKT002-03). Enlaces y búsqueda funcionan sin JS.
    //
    // Sin caché de transferencia HTTP (TKT-016, QA F-04): cada store público transfiere ya su valor
    // con `resource({ id })` (y el mapa del sitio con su propia clave), así que la caché HTTP solo
    // duplicaba cada respuesta en ng-state (p. ej. /destinos 130 → 70 KB) y exponía la URL interna
    // del backend usada por el SSR. La E2E cls-hidratacion verifica que ninguna ruta pública repite
    // peticiones a la API al hidratar.
    provideClientHydration(withNoIncrementalHydration(), withNoHttpTransferCache()),
    ...proveerHttp(),
  ],
};
