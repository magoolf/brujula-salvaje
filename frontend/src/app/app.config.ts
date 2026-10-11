import { DOCUMENT, isPlatformBrowser, registerLocaleData } from '@angular/common';
import localeEsCo from '@angular/common/locales/es-CO';
import {
  ApplicationConfig,
  ErrorHandler,
  InjectionToken,
  LOCALE_ID,
  PLATFORM_ID,
  RendererFactory2,
  inject,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import {
  Title,
  provideClientHydration,
  withNoHttpTransferCache,
  withNoIncrementalHydration,
} from '@angular/platform-browser';
import {
  NavigationEnd,
  NavigationError,
  Router,
  TitleStrategy,
  provideRouter,
  withComponentInputBinding,
  withInMemoryScrolling,
  withNavigationErrorHandler,
} from '@angular/router';
import { filter, take } from 'rxjs';

import { routes } from './app.routes';
import { proveerHttp } from './core/http/proveer-http';
import { ID_CONTENIDO_PRINCIPAL } from './core/layout/navegacion';
import { ManejadorErroresGlobal } from './core/observabilidad/manejador-errores.handler';
import { EstrategiaTitulo } from './core/seo/estrategia-titulo';
import { LOCALE, NOMBRE_MARCA, SEPARADOR_TITULO } from './core/seo/marca';

registerLocaleData(localeEsCo, LOCALE);

// ---------------------------------------------------------------------------------------------
// TKT-025: errores de navegación por carga de un chunk diferido.
//
// Las rutas son `loadComponent`/`loadChildren`: si el `import()` del chunk falla (red transitoria,
// 429 del limitador del borde, o un 404 —servido como HTML, error de MIME— porque un despliegue
// retiró los chunks del build anterior), la navegación termina en NavigationError. El navegador
// cachea el fallo del módulo en su mapa de módulos, así que reintentar la navegación en la SPA no
// sirve: hace falta un documento nuevo. Política (DEC-AUTO-1230):
// - error de chunk, en el navegador y con conexión: UNA recarga completa hacia la URL destino;
// - guarda anti-bucle en sessionStorage (URL + instante): si la misma URL vuelve a fallar dentro de
//   VENTANA_ANTI_BUCLE_MS no se recarga otra vez, sino que se muestra un estado de error accesible
//   dentro del shell (role=alert, h1 enfocado, «Reintentar» como enlace real a la URL destino);
// - sin sessionStorage utilizable (modo privado estricto, cuota) no hay guarda posible: no se
//   recarga (preferimos no recargar a arriesgar un bucle) y se muestra el estado de error;
// - sin conexión no se recarga (cambiaría la página por la de error del navegador): la página
//   actual sigue visible y el aviso GI-04 (BannerSinConexion) ya informa;
// - cualquier otro error de navegación no se toca; en el servidor (SSR) no se hace nada.
// ---------------------------------------------------------------------------------------------

/** Clave de sessionStorage de la guarda anti-bucle (valor: JSON `{ url, instante }`). */
export const CLAVE_RECARGA_CHUNK = 'bs-recarga-chunk';

/** Ventana durante la que una segunda recarga hacia la misma URL se considera un bucle. */
export const VENTANA_ANTI_BUCLE_MS = 120_000;

/**
 * Mensajes de un `import()` dinámico fallido por motor (y el nombre del error de chunk de webpack,
 * por si una dependencia lo propaga). El error de MIME (404 servido como text/html) llega al
 * `import()` como el mismo «Failed to fetch…» en Chromium y «error loading…» en Firefox; WebKit lo
 * notifica con su propio mensaje de MIME.
 */
const PATRONES_ERROR_CHUNK: readonly RegExp[] = [
  /Failed to fetch dynamically imported module/i, // Chromium
  /error loading dynamically imported module/i, // Firefox
  /Importing a module script failed/i, // WebKit
  /Loading chunk [\w-]+ failed/i, // webpack ChunkLoadError
  /Expected a JavaScript(?:-or-Wasm)? module script but the server responded with a MIME type/i,
  /is not a valid JavaScript MIME type/i, // WebKit, error de MIME
];

/** `true` si el error es el fallo de carga de un chunk diferido (no cualquier error de ruta). */
export function esErrorCargaChunk(error: unknown): boolean {
  if (typeof error === 'string') return PATRONES_ERROR_CHUNK.some((p) => p.test(error));
  if (typeof error !== 'object' || error === null) return false;
  const { name, message } = error as { name?: unknown; message?: unknown };
  if (name === 'ChunkLoadError') return true;
  return typeof message === 'string' && PATRONES_ERROR_CHUNK.some((p) => p.test(message));
}

/** Subconjunto de `Window` que usa la recarga (sustituible en pruebas). */
export interface EntornoRecarga {
  readonly location: {
    readonly href: string;
    readonly origin: string;
    assign(url: string): void;
    replace(url: string): void;
  };
  readonly navigator: { readonly onLine: boolean };
  /** Su lectura puede lanzar (SecurityError con el almacenamiento bloqueado). */
  readonly sessionStorage: Pick<Storage, 'getItem' | 'setItem'>;
}

/** Entorno del navegador; `null` en el servidor. */
export const ENTORNO_RECARGA = new InjectionToken<EntornoRecarga | null>('ENTORNO_RECARGA', {
  providedIn: 'root',
  factory: () => (isPlatformBrowser(inject(PLATFORM_ID)) ? inject(DOCUMENT).defaultView : null),
});

export type ResultadoRecarga = 'recargando' | 'sin-conexion' | 'ya-recargada' | 'sin-guarda';

/**
 * Recarga por completo hacia `urlDestino` (ruta interna del router, p. ej. `/destinos?q=1`) salvo
 * que ya se haya recargado hacia ella dentro de la ventana anti-bucle. Si el navegador ya muestra
 * esa URL (carga inicial, atrás/adelante) se usa `replace` para no duplicar la entrada del
 * historial; si no (clic en la SPA), `assign`, como haría la navegación que falló.
 */
export function recargarUnaVez(
  entorno: EntornoRecarga,
  urlDestino: string,
  ahora: number,
): ResultadoRecarga {
  if (!entorno.navigator.onLine) return 'sin-conexion';
  const destino = new URL(urlDestino, entorno.location.origin);
  // El router solo produce rutas del propio origen; se comprueba igualmente antes de navegar.
  if (destino.origin !== entorno.location.origin) return 'sin-guarda';
  try {
    const almacen = entorno.sessionStorage;
    const previa = JSON.parse(almacen.getItem(CLAVE_RECARGA_CHUNK) ?? 'null') as {
      url?: unknown;
      instante?: unknown;
    } | null;
    if (
      previa?.url === destino.href &&
      typeof previa.instante === 'number' &&
      ahora - previa.instante >= 0 &&
      ahora - previa.instante < VENTANA_ANTI_BUCLE_MS
    ) {
      return 'ya-recargada';
    }
    almacen.setItem(CLAVE_RECARGA_CHUNK, JSON.stringify({ url: destino.href, instante: ahora }));
  } catch {
    return 'sin-guarda';
  }
  if (destino.href === new URL(entorno.location.href).href) {
    entorno.location.replace(destino.href);
  } else {
    entorno.location.assign(destino.href);
  }
  return 'recargando';
}

/** Título del documento del estado de error de carga. */
export const TITULO_ERROR_CARGA = 'No pudimos cargar la página';

/** data-testid del estado de error de carga (E2E). */
export const TESTID_ERROR_CARGA = 'error-carga-ruta';

/**
 * Estado de error accesible dentro del shell (fallo persistente). Se inserta al principio del
 * contenido principal (o de la raíz, en el panel, que no tiene el `<main>` público) con el
 * Renderer y solo texto (nunca HTML); si la navegación fallida era la inicial, el outlet queda vacío
 * y este estado es lo único que se ve entre cabecera y pie. Sustituye a uno anterior y se retira en
 * la siguiente navegación que termine bien.
 */
function mostrarErrorCarga(urlDestino: string): void {
  const documento = inject(DOCUMENT);
  const renderer = inject(RendererFactory2).createRenderer(null, null);
  const router = inject(Router);
  const contenedor =
    documento.getElementById(ID_CONTENIDO_PRINCIPAL) ?? documento.querySelector('app-root');
  if (contenedor === null) return;

  documento.querySelector(`[data-testid="${TESTID_ERROR_CARGA}"]`)?.remove();

  const seccion = renderer.createElement('section') as HTMLElement;
  renderer.addClass(seccion, 'bs-contenedor');
  renderer.setAttribute(seccion, 'role', 'alert');
  renderer.setAttribute(seccion, 'data-testid', TESTID_ERROR_CARGA);

  const titulo = renderer.createElement('h1') as HTMLElement;
  renderer.setAttribute(titulo, 'tabindex', '-1');
  renderer.appendChild(titulo, renderer.createText(TITULO_ERROR_CARGA));

  const texto = renderer.createElement('p') as HTMLElement;
  renderer.appendChild(
    texto,
    renderer.createText('Hubo un problema de conexión. Vuelve a intentarlo en unos segundos.'),
  );

  // Enlace real (no routerLink): carga un documento nuevo, con un mapa de módulos limpio.
  const reintentar = renderer.createElement('a') as HTMLAnchorElement;
  renderer.setAttribute(reintentar, 'href', urlDestino);
  renderer.setAttribute(reintentar, 'data-testid', `${TESTID_ERROR_CARGA}-reintentar`);
  renderer.addClass(reintentar, 'bs-boton');
  renderer.addClass(reintentar, 'bs-boton--primary');
  renderer.appendChild(reintentar, renderer.createText('Reintentar'));

  renderer.appendChild(seccion, titulo);
  renderer.appendChild(seccion, texto);
  renderer.appendChild(seccion, reintentar);
  renderer.insertBefore(contenedor, seccion, contenedor.firstChild);

  inject(Title).setTitle(`${TITULO_ERROR_CARGA}${SEPARADOR_TITULO}${NOMBRE_MARCA}`);
  titulo.focus();

  router.events
    .pipe(
      filter((e) => e instanceof NavigationEnd),
      take(1),
    )
    .subscribe(() => seccion.remove());
}

/**
 * Manejador de `withNavigationErrorHandler` (se ejecuta en el contexto de inyección). Solo actúa
 * ante errores de carga de chunk en el navegador; nunca devuelve RedirectCommand, así que el resto
 * de errores siguen su curso normal (ErrorHandler global).
 */
export function manejarErrorNavegacion(evento: NavigationError): void {
  if (!isPlatformBrowser(inject(PLATFORM_ID)) || !esErrorCargaChunk(evento.error)) return;
  const entorno = inject(ENTORNO_RECARGA);
  if (entorno === null) return;
  const resultado = recargarUnaVez(entorno, evento.url, Date.now());
  if (resultado === 'ya-recargada' || resultado === 'sin-guarda') {
    // Ruta relativa al propio origen para el enlace «Reintentar» (sin esquema ni host).
    const destino = new URL(evento.url, entorno.location.origin);
    mostrarErrorCarga(destino.pathname + destino.search + destino.hash);
  }
}

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
      withNavigationErrorHandler(manejarErrorNavegacion),
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
