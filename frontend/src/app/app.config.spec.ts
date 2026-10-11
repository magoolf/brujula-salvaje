import { Component, PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import {
  NavigationError,
  Router,
  Routes,
  provideRouter,
  withNavigationErrorHandler,
} from '@angular/router';

import {
  CLAVE_RECARGA_CHUNK,
  ENTORNO_RECARGA,
  EntornoRecarga,
  TESTID_ERROR_CARGA,
  TITULO_ERROR_CARGA,
  VENTANA_ANTI_BUCLE_MS,
  destinoMismoOrigen,
  esErrorCargaChunk,
  manejarErrorNavegacion,
  recargarUnaVez,
} from './app.config';
import { ID_CONTENIDO_PRINCIPAL } from './core/layout/navegacion';

const ORIGEN = 'http://localhost';

/** Mensajes reales de un import() dinámico fallido por motor. */
const ERROR_CHROMIUM = new TypeError(
  'Failed to fetch dynamically imported module: http://localhost/chunk-ABC123.js',
);
const ERROR_FIREFOX = new TypeError(
  'error loading dynamically imported module: http://localhost/chunk-ABC123.js',
);
const ERROR_WEBKIT = new TypeError('Importing a module script failed.');

class AlmacenFalso {
  readonly datos = new Map<string, string>();
  getItem(clave: string): string | null {
    return this.datos.get(clave) ?? null;
  }
  setItem(clave: string, valor: string): void {
    this.datos.set(clave, valor);
  }
}

function entornoFalso(opciones: { href?: string; enLinea?: boolean } = {}) {
  const almacen = new AlmacenFalso();
  const assign = vi.fn<(url: string) => void>();
  const replace = vi.fn<(url: string) => void>();
  const entorno: EntornoRecarga = {
    location: { href: opciones.href ?? `${ORIGEN}/`, origin: ORIGEN, assign, replace },
    navigator: { onLine: opciones.enLinea ?? true },
    sessionStorage: almacen,
  };
  return { entorno, almacen, assign, replace };
}

describe('TKT-025 esErrorCargaChunk', () => {
  it('AC_TKT025_01 detecta los mensajes de chunk de Chromium, Firefox y WebKit', () => {
    expect(esErrorCargaChunk(ERROR_CHROMIUM)).toBe(true);
    expect(esErrorCargaChunk(ERROR_FIREFOX)).toBe(true);
    expect(esErrorCargaChunk(ERROR_WEBKIT)).toBe(true);
  });

  it('AC_TKT025_01 detecta el error de MIME (404 servido como HTML), ChunkLoadError y mensajes en texto', () => {
    expect(
      esErrorCargaChunk(
        new TypeError(
          'Failed to load module script: Expected a JavaScript-or-Wasm module script but the server responded with a MIME type of "text/html".',
        ),
      ),
    ).toBe(true);
    expect(
      esErrorCargaChunk(new TypeError("'text/html' is not a valid JavaScript MIME type.")),
    ).toBe(true);
    const webpack = new Error('Loading chunk 42 failed.');
    expect(esErrorCargaChunk(webpack)).toBe(true);
    expect(esErrorCargaChunk({ name: 'ChunkLoadError', message: '' })).toBe(true);
    expect(esErrorCargaChunk('Failed to fetch dynamically imported module: x.js')).toBe(true);
  });

  it('AC_TKT025_04 ignora errores no relacionados', () => {
    expect(esErrorCargaChunk(new Error('Cannot match any routes'))).toBe(false);
    expect(esErrorCargaChunk(new TypeError('Failed to fetch'))).toBe(false);
    expect(esErrorCargaChunk('boom')).toBe(false);
    expect(esErrorCargaChunk({ message: 42 })).toBe(false);
    expect(esErrorCargaChunk(null)).toBe(false);
    expect(esErrorCargaChunk(undefined)).toBe(false);
    expect(esErrorCargaChunk(404)).toBe(false);
  });
});

describe('TKT-025 recargarUnaVez', () => {
  it('AC_TKT025_02 recarga a la URL destino (assign) y deja la guarda', () => {
    const { entorno, almacen, assign, replace } = entornoFalso();
    expect(recargarUnaVez(entorno, '/destinos?q=selva#mapa', 1000)).toBe('recargando');
    expect(assign).toHaveBeenCalledExactlyOnceWith(`${ORIGEN}/destinos?q=selva#mapa`);
    expect(replace).not.toHaveBeenCalled();
    expect(JSON.parse(almacen.getItem(CLAVE_RECARGA_CHUNK) ?? '')).toEqual({
      url: `${ORIGEN}/destinos?q=selva#mapa`,
      instante: 1000,
    });
  });

  it('AC_TKT025_02 si el navegador ya muestra la URL destino (carga inicial) usa replace', () => {
    const { entorno, assign, replace } = entornoFalso({ href: `${ORIGEN}/destinos` });
    expect(recargarUnaVez(entorno, '/destinos', 1000)).toBe('recargando');
    expect(replace).toHaveBeenCalledExactlyOnceWith(`${ORIGEN}/destinos`);
    expect(assign).not.toHaveBeenCalled();
  });

  it('AC_TKT025_03 una sola vez: la misma URL dentro de la ventana no vuelve a recargar', () => {
    const { entorno, assign } = entornoFalso();
    recargarUnaVez(entorno, '/destinos', 1000);
    expect(recargarUnaVez(entorno, '/destinos', 1000 + VENTANA_ANTI_BUCLE_MS - 1)).toBe(
      'ya-recargada',
    );
    expect(assign).toHaveBeenCalledOnce();
  });

  it('AC_TKT025_03 otra URL, o la misma pasada la ventana, sí recargan (cada una una vez)', () => {
    const { entorno, assign } = entornoFalso();
    recargarUnaVez(entorno, '/destinos', 1000);
    expect(recargarUnaVez(entorno, '/guias', 2000)).toBe('recargando');
    expect(recargarUnaVez(entorno, '/guias', 2000 + VENTANA_ANTI_BUCLE_MS - 1)).toBe(
      'ya-recargada',
    );
    expect(recargarUnaVez(entorno, '/guias', 2000 + VENTANA_ANTI_BUCLE_MS)).toBe('recargando');
    expect(assign).toHaveBeenCalledTimes(3);
  });

  it('AC_TKT025_03 sin almacenamiento utilizable no recarga (no hay guarda contra el bucle)', () => {
    const { entorno, assign, replace } = entornoFalso();
    const bloqueado: EntornoRecarga = {
      ...entorno,
      get sessionStorage(): EntornoRecarga['sessionStorage'] {
        throw new DOMException('Bloqueado', 'SecurityError');
      },
    };
    expect(recargarUnaVez(bloqueado, '/destinos', 1000)).toBe('sin-guarda');

    const lleno = entornoFalso();
    vi.spyOn(lleno.almacen, 'setItem').mockImplementation(() => {
      throw new DOMException('Cuota', 'QuotaExceededError');
    });
    expect(recargarUnaVez(lleno.entorno, '/destinos', 1000)).toBe('sin-guarda');

    const corrupto = entornoFalso();
    corrupto.almacen.setItem(CLAVE_RECARGA_CHUNK, '{no es json');
    expect(recargarUnaVez(corrupto.entorno, '/destinos', 1000)).toBe('sin-guarda');

    for (const llamada of [assign, replace, lleno.assign, corrupto.assign]) {
      expect(llamada).not.toHaveBeenCalled();
    }
  });

  it('sin conexión no recarga ni toca la guarda; una URL de otro origen nunca se navega', () => {
    const offline = entornoFalso({ enLinea: false });
    expect(recargarUnaVez(offline.entorno, '/destinos', 1000)).toBe('sin-conexion');
    expect(offline.almacen.datos.size).toBe(0);
    expect(offline.assign).not.toHaveBeenCalled();

    const externo = entornoFalso();
    expect(recargarUnaVez(externo.entorno, '//malicioso.example/x', 1000)).toBe('url-no-valida');
    expect(externo.assign).not.toHaveBeenCalled();
  });
});

/** Rutas hostiles: dot-segments que normalizan a `//host`, host vacío y barra invertida. */
const BARRA_INVERTIDA = String.raw`/\evil.com`;
const RUTAS_HOSTILES = ['/.//evil.com', '//', BARRA_INVERTIDA, '/%2e%2e//evil.com'];

describe('TKT-025 SEC-025-01/02 destino de la recarga y del enlace «Reintentar»', () => {
  it('SEC_025_01 nunca devuelve una URL de otro origen ni una ruta protocol-relative', () => {
    for (const ruta of RUTAS_HOSTILES) {
      const destino = destinoMismoOrigen(ruta, ORIGEN);
      if (destino !== null) {
        expect(destino.origin, ruta).toBe(ORIGEN);
        expect(destino.href.startsWith(`${ORIGEN}/`), ruta).toBe(true);
      }
    }
    // Dot-segments: se conserva en el propio origen como URL absoluta (no como `//evil.com`).
    expect(destinoMismoOrigen('/.//evil.com', ORIGEN)?.href).toBe(`${ORIGEN}//evil.com`);
    expect(destinoMismoOrigen('/%2e%2e//evil.com', ORIGEN)?.href).toBe(`${ORIGEN}//evil.com`);
    // Barra invertida = barra: otro origen → rechazada.
    expect(BARRA_INVERTIDA).toHaveLength(10);
    expect(destinoMismoOrigen(BARRA_INVERTIDA, ORIGEN)).toBeNull();
    expect(destinoMismoOrigen('https://evil.com/x', ORIGEN)).toBeNull();
    expect(destinoMismoOrigen('/destinos?q=1#a', ORIGEN)?.href).toBe(`${ORIGEN}/destinos?q=1#a`);
  });

  it('SEC_025_02 una URL que no se puede analizar no lanza: no recarga', () => {
    expect(destinoMismoOrigen('//', ORIGEN)).toBeNull();
    const { entorno, assign, replace, almacen } = entornoFalso();
    expect(() => recargarUnaVez(entorno, '//', 1000)).not.toThrow();
    expect(recargarUnaVez(entorno, '//', 1000)).toBe('url-no-valida');
    expect(assign).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(almacen.datos.size).toBe(0);
  });

  it('SEC_025_01 recargarUnaVez solo navega a URLs absolutas del propio origen', () => {
    for (const ruta of RUTAS_HOSTILES) {
      const { entorno, assign, replace } = entornoFalso();
      recargarUnaVez(entorno, ruta, 1000);
      for (const url of [...assign.mock.calls, ...replace.mock.calls].map(([u]) => u)) {
        expect(new URL(url).origin, ruta).toBe(ORIGEN);
        expect(url.startsWith(`${ORIGEN}/`), ruta).toBe(true);
      }
    }
  });
});

@Component({ template: '<h1>Destino cargado</h1>' })
class PaginaOk {}

const RUTAS: Routes = [
  { path: 'ok', component: PaginaOk },
  { path: 'diferida', loadComponent: () => Promise.reject(ERROR_CHROMIUM) },
  { path: 'rota', loadComponent: () => Promise.reject(new Error('fallo del componente')) },
];

describe('TKT-025 manejarErrorNavegacion (withNavigationErrorHandler)', () => {
  let principal: HTMLElement;

  function configurar(entorno: EntornoRecarga, plataforma = 'browser'): Router {
    TestBed.configureTestingModule({
      providers: [
        provideRouter(RUTAS, withNavigationErrorHandler(manejarErrorNavegacion)),
        { provide: ENTORNO_RECARGA, useValue: entorno },
        { provide: PLATFORM_ID, useValue: plataforma },
      ],
    });
    return TestBed.inject(Router);
  }

  async function navegar(router: Router, url: string): Promise<void> {
    await router.navigateByUrl(url).catch(() => undefined);
  }

  function estadoError(): HTMLElement | null {
    return document.querySelector(`[data-testid="${TESTID_ERROR_CARGA}"]`);
  }

  beforeEach(() => {
    principal = document.createElement('main');
    principal.id = ID_CONTENIDO_PRINCIPAL;
    principal.append(document.createElement('router-outlet'));
    document.body.append(principal);
  });

  afterEach(() => principal.remove());

  it('AC_TKT025_02 un error de chunk recarga una vez hacia la URL destino de la navegación', async () => {
    const { entorno, assign } = entornoFalso();
    const router = configurar(entorno);
    await navegar(router, '/diferida?pagina=2');
    expect(assign).toHaveBeenCalledExactlyOnceWith(`${ORIGEN}/diferida?pagina=2`);
    expect(estadoError()).toBeNull();
  });

  it('AC_TKT025_03 si tras la recarga vuelve a fallar: sin bucle, estado de error accesible dentro del shell', async () => {
    const { entorno, assign } = entornoFalso();
    const router = configurar(entorno);
    await navegar(router, '/diferida');
    await navegar(router, '/diferida');
    await navegar(router, '/diferida');
    expect(assign).toHaveBeenCalledOnce();

    const estado = estadoError();
    expect(estado).not.toBeNull();
    expect(document.querySelectorAll(`[data-testid="${TESTID_ERROR_CARGA}"]`)).toHaveLength(1);
    expect(estado?.parentElement).toBe(principal);
    expect(estado?.getAttribute('role')).toBe('alert');
    const h1 = estado?.querySelector('h1');
    expect(h1?.textContent).toBe(TITULO_ERROR_CARGA);
    expect(document.activeElement).toBe(h1);
    const reintentar = estado?.querySelector('a');
    expect(reintentar?.getAttribute('href')).toBe(`${ORIGEN}/diferida`);
    expect(reintentar?.hasAttribute('routerlink')).toBe(false);
    expect(TestBed.inject(Title).getTitle()).toBe(`${TITULO_ERROR_CARGA} — Brújula Salvaje`);

    // La siguiente navegación que termina bien retira el estado de error.
    await navegar(router, '/ok');
    expect(estadoError()).toBeNull();
  });

  it('SEC_025_01/02 con una URL destino no válida no recarga y «Reintentar» apunta a una URL segura', async () => {
    const { entorno, assign, replace } = entornoFalso();
    configurar(entorno);
    const evento = new NavigationError(1, '//', ERROR_CHROMIUM);
    TestBed.runInInjectionContext(() => manejarErrorNavegacion(evento));
    expect(assign).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(estadoError()?.querySelector('a')?.getAttribute('href')).toBe('/');

    const puntos = entornoFalso();
    puntos.almacen.setItem(
      CLAVE_RECARGA_CHUNK,
      JSON.stringify({ url: `${ORIGEN}//evil.com`, instante: Date.now() }),
    );
    TestBed.resetTestingModule();
    configurar(puntos.entorno);
    TestBed.runInInjectionContext(() =>
      manejarErrorNavegacion(new NavigationError(2, '/.//evil.com', ERROR_CHROMIUM)),
    );
    expect(puntos.assign).not.toHaveBeenCalled();
    expect(estadoError()?.querySelector('a')?.getAttribute('href')).toBe(`${ORIGEN}//evil.com`);
  });

  it('AC_TKT025_04 otros errores de navegación no recargan ni muestran el estado de error', async () => {
    const { entorno, assign, replace, almacen } = entornoFalso();
    const router = configurar(entorno);
    await navegar(router, '/rota');
    expect(assign).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(almacen.datos.size).toBe(0);
    expect(estadoError()).toBeNull();
  });

  it('AC_TKT025_05 en el servidor no hace nada (ni window/location ni DOM)', async () => {
    const { entorno, assign, replace, almacen } = entornoFalso();
    const router = configurar(entorno, 'server');
    await navegar(router, '/diferida');
    await navegar(router, '/diferida');
    expect(assign).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(almacen.datos.size).toBe(0);
    expect(estadoError()).toBeNull();
  });

  it('AC_TKT025_05 el entorno por defecto es null en el servidor', () => {
    TestBed.configureTestingModule({ providers: [{ provide: PLATFORM_ID, useValue: 'server' }] });
    expect(TestBed.inject(ENTORNO_RECARGA)).toBeNull();
  });

  it('sin conexión la navegación falla sin recargar y sin estado de error (avisa GI-04)', async () => {
    const { entorno, assign } = entornoFalso({ enLinea: false });
    const router = configurar(entorno);
    await navegar(router, '/diferida');
    expect(assign).not.toHaveBeenCalled();
    expect(estadoError()).toBeNull();
  });

  it('en el panel (sin <main> público) el estado de error va en la raíz de la aplicación', async () => {
    principal.remove();
    const raiz = document.createElement('app-root');
    document.body.append(raiz);
    try {
      const { entorno, almacen } = entornoFalso();
      almacen.setItem(
        CLAVE_RECARGA_CHUNK,
        JSON.stringify({ url: `${ORIGEN}/diferida`, instante: Date.now() }),
      );
      const router = configurar(entorno);
      await navegar(router, '/diferida');
      expect(estadoError()?.parentElement).toBe(raiz);
    } finally {
      raiz.remove();
    }
  });
});
