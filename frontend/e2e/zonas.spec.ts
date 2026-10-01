import { Page, Request, expect, test } from '@playwright/test';

import { crearCuenta, entrarPorApi, irA, omitirSinStack } from './panel-soporte';

/**
 * Cruces de zona en la SPA (TKT-010, QA ciclo 2 HALLAZGO-ZONA): sitio público (ShellPublico) ↔
 * panel editorial (armazón propio). Un muestreador en la página (requestAnimationFrame +
 * MutationObserver) registra cada estado intermedio del DOM mientras se navega y la prueba falla si
 * en algún momento:
 * - una página pública aparece fuera de ShellPublico (contenido sin chrome);
 * - el armazón del panel aparece dentro de ShellPublico, o conviven ambos armazones;
 * - hay un número de <main> distinto de 1, o no hay ningún armazón (pantalla vacía);
 * - ShellPublico se queda sin página (chrome sin contenido);
 * y, por la red, si la página saliente se vuelve a montar (peticiones de la API pública al ir al
 * panel, o la misma petición repetida dentro de un paso).
 * Se añade latencia a la API (guards de sesión y datos) para ensanchar las ventanas de transición en
 * los tres motores.
 */

const LATENCIA_MS = 250;
const SESION = 'GET /api/v1/panel/auth/sesion';

/** Muestreador instalado antes de cargar la página (se ejecuta en el navegador). */
function instalarMuestreador(): void {
  interface Registro {
    paso: string;
    violaciones: string[];
    estados: string[];
  }
  const w = window as unknown as { __zonas: Registro };
  w.__zonas = { paso: '', violaciones: [], estados: [] };
  const PANEL = ['app-layout-acceso', 'app-shell-panel'];
  const NEUTROS = ['app-shell-publico', 'app-banner-sin-conexion', 'router-outlet', ...PANEL];

  const evaluar = (origen: string): void => {
    const registro = w.__zonas;
    if (registro.paso === '') return;
    const raiz = document.querySelector('app-root');
    if (raiz === null) return;
    const hijos = Array.from(raiz.children).map((e) => e.localName);
    const shell = raiz.querySelector(':scope > app-shell-publico');
    const panel = raiz.querySelector(':scope > app-layout-acceso, :scope > app-shell-panel');
    const mains = document.querySelectorAll('main').length;
    const fallos: string[] = [];
    const sueltos = hijos.filter((t) => !NEUTROS.includes(t));
    if (sueltos.length > 0) fallos.push(`contenido sin chrome (${sueltos.join(',')})`);
    if (document.querySelector('app-shell-publico :is(app-layout-acceso, app-shell-panel)')) {
      fallos.push('armazón del panel dentro de ShellPublico');
    }
    if (shell !== null && panel !== null) fallos.push('ShellPublico y armazón del panel a la vez');
    if (shell === null && panel === null) fallos.push('sin armazón (pantalla vacía)');
    if (mains !== 1) fallos.push(`${mains} <main>`);
    if (shell !== null && shell.querySelector('main > router-outlet + *') === null) {
      fallos.push('ShellPublico sin página');
    }
    const estado =
      `${location.pathname}${location.search} raiz=[${hijos.join(',')}] main=${mains}` +
      (fallos.length > 0 ? ` FALLO: ${fallos.join('; ')}` : '');
    if (registro.estados.at(-1) === estado) return;
    registro.estados.push(estado);
    if (fallos.length > 0) registro.violaciones.push(`[${registro.paso}] (${origen}) ${estado}`);
  };

  const iniciar = (): void => {
    const cuadro = (): void => {
      evaluar('frame');
      requestAnimationFrame(cuadro);
    };
    requestAnimationFrame(cuadro);
    new MutationObserver(() => evaluar('mutación')).observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
}

/** Navegación de la SPA sin recarga (historial + popstate, como Atrás/Adelante). */
async function navegarSpa(page: Page, url: string): Promise<void> {
  await page.evaluate((destino) => {
    history.pushState(null, '', destino);
    dispatchEvent(new PopStateEvent('popstate', { state: null }));
  }, url);
}

interface Contexto {
  readonly page: Page;
  readonly peticiones: string[];
}

async function prepararPagina(page: Page): Promise<Contexto> {
  const peticiones: string[] = [];
  page.on('request', (r: Request) => {
    const url = new URL(r.url());
    if (url.pathname.startsWith('/api/'))
      peticiones.push(`${r.method()} ${url.pathname}${url.search}`);
  });
  await page.addInitScript(instalarMuestreador);
  return { page, peticiones };
}

/**
 * Latencia artificial en la API (tras la carga inicial). Los fragmentos JS no se interceptan: en
 * Firefox, retener muchas descargas de módulos en paralelo con page.route llegó a bloquear una
 * navegación; el MutationObserver ya detecta cualquier estado que dure más de una microtarea.
 */
async function anadirLatencia(page: Page): Promise<void> {
  const retrasar = async (route: Parameters<Parameters<Page['route']>[1]>[0]): Promise<void> => {
    await new Promise((r) => setTimeout(r, LATENCIA_MS));
    await route.fallback();
  };
  await page.route(/\/api\/v1\//, retrasar);
}

/**
 * Ejecuta un paso, espera a que la vista de destino esté lista y devuelve las peticiones a la API
 * hechas durante el paso. Falla si el muestreador registró algún estado intermedio incorrecto.
 */
async function paso(
  ctx: Contexto,
  nombre: string,
  accion: () => Promise<unknown>,
  listo: () => Promise<void>,
): Promise<string[]> {
  const { page, peticiones } = ctx;
  const desde = peticiones.length;
  await page.evaluate((n) => {
    const w = window as unknown as { __zonas: { paso: string; estados: string[] } };
    w.__zonas.paso = n;
    w.__zonas.estados = [];
  }, nombre);
  await accion();
  await listo();
  // Deja asentarse la vista (peticiones de datos y cuadros posteriores a la navegación).
  await page.waitForTimeout(LATENCIA_MS * 3);
  const { violaciones, estados } = await page.evaluate(() => {
    const w = window as unknown as {
      __zonas: { paso: string; violaciones: string[]; estados: string[] };
    };
    const r = { violaciones: [...w.__zonas.violaciones], estados: [...w.__zonas.estados] };
    w.__zonas.paso = '';
    w.__zonas.violaciones = [];
    return r;
  });
  const hechas = peticiones.slice(desde);
  // Aserciones blandas: cada cruce se informa aunque falle uno anterior.
  expect.soft(violaciones, `${nombre}\nestados:\n  ${estados.join('\n  ')}`).toEqual([]);
  // La sesión se lee a propósito dos veces al entrar al panel sin sesión (sesionCompletaGuard y
  // accesoGuard, que siempre la relee): no es un remontaje y no cuenta como repetición.
  const datos = hechas.filter((p) => p !== SESION);
  const repetidas = datos.filter((p, i) => datos.indexOf(p) !== i);
  expect
    .soft(repetidas, `${nombre}: peticiones repetidas (página remontada)\n  ${hechas.join('\n  ')}`)
    .toEqual([]);
  return hechas;
}

const publicas = (peticiones: string[]): string[] =>
  peticiones.filter((p) => p.includes('/api/v1/publico/'));

async function enDestinos(page: Page): Promise<void> {
  await expect(page).toHaveURL(/\/destinos$/);
  await expect(page.locator('app-shell-publico main app-pagina-destinos h1')).toBeVisible();
}

async function enAcceso(page: Page): Promise<void> {
  await expect(page).toHaveURL(/\/panel\/acceso\?siguiente=/);
  await expect(page.locator('app-root > app-layout-acceso app-pagina-acceso h1')).toBeVisible();
}

test.describe('Cruces de zona sitio público ↔ panel en la SPA (TKT-010)', () => {
  test.beforeEach(() => {
    omitirSinStack();
    test.setTimeout(180_000);
  });

  test('AC_TKT010_10 sin sesión: ningún cuadro mezcla armazones, deja contenido sin chrome ni repite peticiones', async ({
    page,
  }) => {
    const ctx = await prepararPagina(page);
    await irA(page, '/');
    await anadirLatencia(page);

    await paso(
      ctx,
      'público / → /destinos',
      () => page.locator('app-cabecera-sitio a[href="/destinos"]').first().click(),
      () => enDestinos(page),
    );

    // (1) público → panel: /destinos no se vuelve a montar ni repite sus peticiones.
    const alPanel = await paso(
      ctx,
      '(1) /destinos → /panel',
      () => navegarSpa(page, '/panel'),
      () => enAcceso(page),
    );
    expect.soft(publicas(alPanel), 'al ir al panel no se piden datos públicos').toEqual([]);

    // (3) Atrás desde el panel a /destinos, Adelante y Atrás otra vez.
    const atras = await paso(
      ctx,
      '(3) Atrás → /destinos',
      () => page.goBack(),
      () => enDestinos(page),
    );
    expect
      .soft(publicas(atras).filter((p) => p.startsWith('GET /api/v1/publico/destinos')))
      .toHaveLength(1);
    const adelante = await paso(
      ctx,
      '(3) Adelante → panel',
      () => page.goForward(),
      () => enAcceso(page),
    );
    expect.soft(publicas(adelante)).toEqual([]);
    await paso(
      ctx,
      '(3) Atrás otra vez → /destinos',
      () => page.goBack(),
      () => enDestinos(page),
    );

    // (2) panel → público: /panel/acceso → /acerca-de (página aún no cargada: su fragmento se descarga).
    await paso(
      ctx,
      'público → /panel/acceso',
      () => navegarSpa(page, '/panel/acceso'),
      async () => {
        await expect(page).toHaveURL(/\/panel\/acceso$/);
        await expect(
          page.locator('app-root > app-layout-acceso app-pagina-acceso h1'),
        ).toBeVisible();
      },
    );
    const alSitio = await paso(
      ctx,
      '(2) /panel/acceso → /acerca-de',
      () => navegarSpa(page, '/acerca-de'),
      async () => {
        await expect(page).toHaveURL(/\/acerca-de$/);
        await expect(
          page.locator('app-shell-publico main app-pagina-institucional h1'),
        ).toBeVisible();
      },
    );
    expect.soft(alSitio.filter((p) => p.includes('/api/v1/panel/'))).toEqual([]);

    // Rutas límite.
    await paso(
      ctx,
      'límite /panelx (404 pública)',
      () => navegarSpa(page, '/panelx'),
      async () => {
        await expect(page).toHaveURL(/\/panelx$/);
        await expect(
          page.locator('app-shell-publico main [data-testid="pagina-no-encontrada"]'),
        ).toBeVisible();
      },
    );
    await paso(
      ctx,
      'límite /panel?x=1',
      () => navegarSpa(page, '/panel?x=1'),
      async () => {
        await expect(page).toHaveURL(/\/panel\/acceso\?siguiente=%2Fpanel%3Fx%3D1$/);
        await expect(
          page.locator('app-root > app-layout-acceso app-pagina-acceso h1'),
        ).toBeVisible();
      },
    );
    await paso(
      ctx,
      'límite /panelx desde el panel',
      () => navegarSpa(page, '/panelx'),
      async () => {
        await expect(
          page.locator('app-shell-publico main [data-testid="pagina-no-encontrada"]'),
        ).toBeVisible();
      },
    );
    await paso(
      ctx,
      'límite /panel/',
      () => navegarSpa(page, '/panel/'),
      async () => {
        await expect(page).toHaveURL(/\/panel\/acceso\?siguiente=%2Fpanel$/);
        await expect(
          page.locator('app-root > app-layout-acceso app-pagina-acceso h1'),
        ).toBeVisible();
      },
    );
    await expect(page.locator('app-shell-publico')).toHaveCount(0);
  });

  test('AC_TKT010_10 con sesión: 404 del panel y Tablero ↔ sitio sin estados intermedios incorrectos', async ({
    page,
  }) => {
    const cuenta = crearCuenta();
    const ctx = await prepararPagina(page);
    await irA(page, '/destinos');
    await entrarPorApi(page, cuenta);
    await anadirLatencia(page);

    await paso(
      ctx,
      '/destinos → 404 del panel',
      () => navegarSpa(page, '/panel/no-existe'),
      async () => {
        await expect(page).toHaveURL(/\/panel\/no-existe$/);
        await expect(page.locator('app-root > app-shell-panel main h1')).toHaveText(
          'No encontramos esta página del panel',
        );
      },
    );
    await paso(
      ctx,
      '404 del panel → Tablero',
      () => navegarSpa(page, '/panel'),
      async () => {
        await expect(
          page.locator('app-root > app-shell-panel [data-testid="pagina-tablero"]'),
        ).toBeVisible();
      },
    );
    const atrasPanel = await paso(
      ctx,
      'Tablero → 404 del panel (Atrás)',
      () => page.goBack(),
      async () => {
        await expect(page).toHaveURL(/\/panel\/no-existe$/);
        await expect(page.locator('app-root > app-shell-panel main h1')).toBeVisible();
      },
    );
    expect.soft(publicas(atrasPanel)).toEqual([]);
    const tableroAlSitio = await paso(
      ctx,
      'panel (ShellPanel) → /destinos',
      () => navegarSpa(page, '/destinos'),
      () => enDestinos(page),
    );
    expect.soft(tableroAlSitio.filter((p) => p.includes('/api/v1/panel/'))).toEqual([]);
    await paso(
      ctx,
      '/destinos → Tablero',
      () => navegarSpa(page, '/panel'),
      async () => {
        await expect(
          page.locator('app-root > app-shell-panel [data-testid="pagina-tablero"]'),
        ).toBeVisible();
      },
    );
    await paso(
      ctx,
      'Tablero → / (Atrás hasta el sitio)',
      () => navegarSpa(page, '/'),
      async () => {
        await expect(page.locator('app-shell-publico main app-pagina-inicio')).toBeVisible();
      },
    );
  });
});
