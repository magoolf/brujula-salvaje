import { expect, test } from '@playwright/test';

import { esperarHidratacion } from './utilidades';

/**
 * AC-TKT002-03: el SSR sirve / con el shell y aplica el nonce CSP recibido en `x-csp-nonce`
 * (simulando el proxy, DEVOPS_HANDOFF §5.3) a todo script ejecutable en línea; /healthz → 200.
 * La CSP del proxy es la de infra/proxy/snippets/security-headers-html.conf.
 */
const NONCE = '0123456789abcdef0123456789abcdef';
const CSP = `default-src 'self'; script-src 'self' 'nonce-${NONCE}'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; media-src 'self'; manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`;

/** Tipos de <script> que el navegador ejecuta (sin type, JS clásico o módulo). */
function esEjecutable(tipo: string | null): boolean {
  return (
    tipo === null ||
    tipo === '' ||
    tipo === 'module' ||
    /^(text|application)\/(x-)?(java|ecma)script$/i.test(tipo)
  );
}

test.describe('SSR, CSP con nonce y healthz', () => {
  test('AC_TKT002_03 /healthz responde 200 sin depender de la API', async ({ request }) => {
    const respuesta = await request.get('/healthz');
    expect(respuesta.status()).toBe(200);
    expect(await respuesta.json()).toEqual({ status: 'ok' });
    expect(respuesta.headers()['cache-control']).toBe('no-store');
  });

  test('AC_TKT002_03 / se sirve renderizado con el shell y todo script en línea ejecutable lleva el nonce', async ({
    request,
    page,
  }) => {
    const respuesta = await request.get('/', { headers: { 'x-csp-nonce': NONCE } });
    expect(respuesta.status()).toBe(200);
    expect(respuesta.headers()['x-powered-by']).toBeUndefined();
    const html = await respuesta.text();

    // Contenido principal en la respuesta inicial (CON-007) con el shell completo.
    expect(html).toContain('<html lang="es"');
    for (const marca of [
      'data-testid="skip-link"',
      'data-testid="cabecera-sitio"',
      'id="contenido-principal"',
      'data-testid="pie-sitio"',
      'Contenido en preparación',
    ]) {
      expect(html).toContain(marca);
    }

    await page.setContent(html);
    const scripts = await page
      .locator('script')
      .evaluateAll((nodos) =>
        nodos.map((s) => ({
          tipo: s.getAttribute('type'),
          src: s.getAttribute('src'),
          nonce: s.getAttribute('nonce') ?? (s as HTMLScriptElement).nonce,
        })),
      );
    const enLineaEjecutables = scripts.filter((s) => s.src === null && esEjecutable(s.tipo));
    expect(enLineaEjecutables.filter((s) => s.nonce !== NONCE)).toEqual([]);
    const estilosEnLinea = await page
      .locator('style')
      .evaluateAll((nodos) =>
        nodos.map((s) => s.getAttribute('nonce') ?? (s as HTMLStyleElement).nonce),
      );
    expect(estilosEnLinea.every((n) => n === NONCE)).toBe(true);
    // Sin manejadores de eventos en línea (on*=) en el HTML servido.
    expect(html).not.toMatch(/<[^>]+\son[a-z]+\s*=/i);
  });

  test('AC_TKT002_03 un nonce con formato inválido no se refleja en el HTML', async ({
    request,
  }) => {
    const html = await (
      await request.get('/', { headers: { 'x-csp-nonce': '"><script>alert(1)</script>' } })
    ).text();
    expect(html).not.toContain('alert(1)');
  });

  test('AC_TKT002_03 con la CSP estricta del proxy la app hidrata sin violaciones y es interactiva', async ({
    page,
  }) => {
    // Simula el proxy: añade x-csp-nonce a la petición del documento y la CSP a su respuesta.
    await page.route('**/*', async (ruta) => {
      if (ruta.request().resourceType() !== 'document') return ruta.continue();
      const respuesta = await ruta.fetch({
        headers: { ...ruta.request().headers(), 'x-csp-nonce': NONCE },
      });
      await ruta.fulfill({
        response: respuesta,
        headers: { ...respuesta.headers(), 'content-security-policy': CSP },
      });
    });
    const violaciones: string[] = [];
    await page.exposeFunction('registrarViolacionCsp', (texto: string) => violaciones.push(texto));
    await page.addInitScript(() => {
      document.addEventListener('securitypolicyviolation', (e) => {
        (window as unknown as { registrarViolacionCsp: (t: string) => void }).registrarViolacionCsp(
          `${e.violatedDirective} ${e.blockedURI}`,
        );
      });
    });

    await page.goto('/');
    await esperarHidratacion(page);
    // Interactividad tras hidratar: la búsqueda valida en el cliente (sin navegar).
    const campo = page.getByTestId('cabecera-busqueda').getByRole('searchbox');
    await campo.fill('x');
    await campo.press('Enter');
    await expect(
      page.getByTestId('cabecera-busqueda').getByTestId('campo-busqueda-error'),
    ).toBeVisible();
    expect(violaciones).toEqual([]);
  });
});
