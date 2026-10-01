import { randomBytes } from 'node:crypto';

import { Page, expect, test } from '@playwright/test';

import {
  CuentaPrueba,
  crearCuenta,
  entrarPorApi,
  entrarPorUi,
  irA,
  loginApi,
  omitirSinStack,
  siguienteCodigo,
} from './panel-soporte';
import { enlacesTabulables, focoActual, sinViolacionesGraves } from './utilidades';

/**
 * E2E del panel editorial, TKT-010 (FLOW-010; SCR-030..034 y SCR-048) contra el stack real de
 * Compose (backend Django + PostgreSQL). Ver panel-soporte.ts para la creación de cuentas y el
 * límite de tasa del login.
 */
test.describe('Panel editorial — acceso, armazón y tablero (TKT-010)', () => {
  test.beforeEach(() => {
    omitirSinStack();
    test.setTimeout(300_000);
  });

  async function nuevaContrasena(): Promise<string> {
    return `una frase nueva ${randomBytes(6).toString('hex')}`;
  }

  async function sesionApi(page: Page): Promise<number> {
    return (await page.request.get('/api/v1/panel/auth/sesion')).status();
  }

  test('AC_TKT010_01 login sin MFA ni pendientes → Tablero; cerrar sesión → SCR-030 y la sesión deja de valer', async ({
    page,
  }) => {
    const cuenta = crearCuenta();
    await irA(page, '/panel/acceso');
    await expect(page.locator('h1')).toHaveText('Acceso al panel editorial');
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page).toHaveURL(/\/panel$/);
    await expect(page.getByTestId('pagina-tablero')).toBeVisible();
    await expect(page.getByTestId('panel-usuario-nombre')).toHaveText(cuenta.nombre);

    await page.getByTestId('panel-cerrar-sesion').click();
    await expect(page).toHaveURL(/\/panel\/acceso\?motivo=cerrada$/);
    await expect(page.getByTestId('acceso-motivo')).toContainText('Cerraste sesión.');
    expect(await sesionApi(page)).toBe(401);
    await irA(page, '/panel');
    await expect(page).toHaveURL(/\/panel\/acceso\?siguiente=%2Fpanel$/);
  });

  test('AC_TKT010_02 login fallido → mensaje genérico; 5 fallos → bloqueo temporal con tiempo, sin filtrar información', async ({
    page,
  }) => {
    await irA(page, '/panel/acceso');
    await entrarPorUi(page, `e2e.no.existe.${randomBytes(4).toString('hex')}`, 'lo-que-sea-2026');
    await expect(page.getByTestId('acceso-error')).toHaveText(/Usuario o contraseña incorrectos\./);
    // OBS-A11Y-01 (QA c2): el foco va al resumen del error, ya renderizado (no al botón ni a <main>).
    const resumenConError = page.locator('div.resumen:has([data-testid="acceso-error"])');
    await expect(resumenConError).toBeFocused();

    const cuenta = crearCuenta();
    await entrarPorUi(page, cuenta.usuario, 'equivocada-2026');
    await expect(page.getByTestId('acceso-error')).toHaveText(/Usuario o contraseña incorrectos\./);
    await expect(resumenConError).toBeFocused();
    await expect(page.getByTestId('acceso-contrasena')).toHaveValue('');
    await expect(page.getByTestId('acceso-usuario')).toHaveValue(cuenta.usuario);

    for (let i = 0; i < 3; i++) {
      expect((await loginApi(page, cuenta.usuario, 'equivocada-2026')).status()).toBe(401);
    }
    await entrarPorUi(page, cuenta.usuario, 'equivocada-2026');
    await expect(page.getByTestId('acceso-error')).toContainText(
      'Por seguridad, el acceso está bloqueado temporalmente.',
    );
    await expect(page.getByTestId('acceso-error')).toContainText(/en \d+ minutos?\./);
    // Bloqueada, ni la contraseña correcta entra (y el mensaje no revela nada más).
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page.getByTestId('acceso-error')).toContainText('bloqueado temporalmente');
    await expect(page).toHaveURL(/\/panel\/acceso/);
  });

  test('AC_TKT010_03 cuenta con MFA → SCR-031; código inválido muestra error; código válido entra', async ({
    page,
  }) => {
    const cuenta = crearCuenta({ conMfa: true });
    await irA(page, '/panel/acceso');
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page).toHaveURL(/\/panel\/acceso\/verificacion$/);
    await expect(page.locator('h1')).toHaveText('Verificación en dos pasos');

    await page.getByTestId('mfa-codigo').fill('000000');
    await page.getByTestId('mfa-verificar').click();
    await expect(page.getByTestId('mfa-codigo-error')).toHaveText(/El código no es válido\./);

    await page.getByTestId('mfa-codigo').fill(await siguienteCodigo(cuenta));
    await page.getByTestId('mfa-verificar').click();
    await expect(page).toHaveURL(/\/panel$/);
    await expect(page.getByTestId('pagina-tablero')).toBeVisible();
  });

  test('AC_TKT010_04 cambio obligatorio → SCR-032 bloqueante; contraseña débil → error de campo; luego continúa', async ({
    page,
  }) => {
    const cuenta = crearCuenta({ debeCambiar: true });
    await entrarPorApi(page, cuenta);
    await irA(page, '/panel');
    await expect(page).toHaveURL(/\/panel\/cuenta$/);
    await expect(page.getByTestId('panel-layout-acceso')).toBeVisible();
    await expect(page.getByTestId('panel-navegacion')).toHaveCount(0);
    await expect(page.getByTestId('cuenta-obligatorio')).toContainText(
      'Debes cambiar tu contraseña temporal para continuar.',
    );
    // Mientras tanto no se puede ir a otra pantalla del panel.
    await irA(page, '/panel');
    await expect(page).toHaveURL(/\/panel\/cuenta$/);

    await page.getByTestId('cuenta-actual').fill(cuenta.contrasena);
    await page.getByTestId('cuenta-nueva').fill('corta');
    await page.getByTestId('cuenta-confirmacion').fill('corta');
    await page.getByTestId('cuenta-guardar-contrasena').click();
    await expect(page.getByTestId('cuenta-nueva-error')).toContainText('Usa al menos 12 caracteres');

    // Débil según el servidor (contiene el usuario, RULE-017) → mensaje bajo el campo.
    const debil = `${cuenta.usuario}-2026`;
    await page.getByTestId('cuenta-nueva').fill(debil);
    await page.getByTestId('cuenta-confirmacion').fill(debil);
    await page.getByTestId('cuenta-guardar-contrasena').click();
    await expect(page.getByTestId('cuenta-nueva-error')).toContainText('no puede contener tu usuario');
    await expect(page).toHaveURL(/\/panel\/cuenta$/);

    const nueva = await nuevaContrasena();
    await page.getByTestId('cuenta-nueva').fill(nueva);
    await page.getByTestId('cuenta-confirmacion').fill(nueva);
    await page.getByTestId('cuenta-guardar-contrasena').click();
    await expect(page).toHaveURL(/\/panel$/);
    await expect(page.getByTestId('pagina-tablero')).toBeVisible();
  });

  test('AC_TKT010_05 sin autorización → SCR-033 bloqueante; «No autorizo» cierra sesión; «Autorizo» continúa', async ({
    page,
  }) => {
    const cuenta = crearCuenta({ autorizada: false });
    await entrarPorApi(page, cuenta);
    await irA(page, '/panel');
    await expect(page).toHaveURL(/\/panel\/autorizacion$/);
    await expect(page.getByTestId('autorizacion-resumen')).toBeVisible();
    await expect(page.getByTestId('autorizacion-politica')).toHaveAttribute('target', '_blank');

    await page.getByTestId('autorizacion-no-autorizo').click();
    await expect(page.getByTestId('autorizacion-confirmacion')).toBeVisible();
    await page.getByTestId('autorizacion-confirmar-no-autorizo').click();
    await expect(page).toHaveURL(/\/panel\/acceso\?motivo=cerrada$/);
    expect(await sesionApi(page)).toBe(401);

    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page).toHaveURL(/\/panel\/autorizacion$/);
    await page.getByTestId('autorizacion-autorizo').click();
    await expect(page).toHaveURL(/\/panel$/);
    await expect(page.getByTestId('pagina-tablero')).toBeVisible();
  });

  test('AC_TKT010_06 Mi cuenta: activar MFA (reautenticación sin expulsión), regenerar códigos y desactivar', async ({
    page,
  }) => {
    const cuenta: CuentaPrueba = crearCuenta();
    await entrarPorApi(page, cuenta);
    await irA(page, '/panel/cuenta');
    await expect(page.getByTestId('mfa-estado')).toContainText('desactivada');

    // DEC-AUTO-215: contraseña errónea = error del campo; ni redirección ni pérdida de sesión.
    await page.getByTestId('mfa-empezar').click();
    await page.getByTestId('mfa-reautenticacion').fill('equivocada-2026');
    await page.getByTestId('mfa-reautenticar').click();
    await expect(page.getByTestId('mfa-reautenticacion-error')).toHaveText(/La contraseña no es correcta\./);
    await expect(page).toHaveURL(/\/panel\/cuenta$/);
    await expect(page.getByTestId('panel-navegacion')).toBeVisible();
    expect(await sesionApi(page)).toBe(200);

    await page.getByTestId('mfa-reautenticacion').fill(cuenta.contrasena);
    await page.getByTestId('mfa-reautenticar').click();
    await expect(page.getByTestId('codigo-qr')).toBeVisible();
    await expect(page.getByTestId('codigo-qr')).toHaveAttribute(
      'aria-label',
      'Código QR para configurar tu aplicación autenticadora',
    );
    const clave = ((await page.getByTestId('mfa-clave').textContent()) ?? '').replace(/\s+/g, '');
    expect(clave).toMatch(/^[A-Z2-7]{16,64}$/);
    cuenta.secreto = clave;

    await page.getByTestId('mfa-continuar').click();
    await page.getByTestId('mfa-confirmar-codigo').fill(await siguienteCodigo(cuenta));
    await page.getByTestId('mfa-activar').click();
    await expect(page.getByTestId('mfa-codigos')).toBeVisible();
    await expect(page.getByTestId('mfa-codigos')).toContainText('Paso 3 de 3');
    const primeros = await page.getByTestId('mfa-lista-codigos').locator('li').allTextContents();
    expect(primeros.length).toBeGreaterThan(0);
    await page.getByTestId('mfa-codigos-guardados').click();
    await expect(page.getByTestId('mfa-estado')).toContainText('activada');

    await page.getByTestId('mfa-regenerar-codigo').fill(await siguienteCodigo(cuenta));
    await page.getByTestId('mfa-regenerar').click();
    await expect(page.getByTestId('mfa-lista-codigos')).toBeVisible();
    const nuevos = (await page.getByTestId('mfa-lista-codigos').locator('li').allTextContents()).map((c) =>
      c.trim(),
    );
    expect(nuevos).not.toEqual(primeros.map((c) => c.trim()));
    await page.getByTestId('mfa-codigos-guardados').click();

    await page.getByTestId('mfa-desactivar').click();
    await expect(page.getByTestId('mfa-dialogo-desactivar')).toBeVisible();
    await page.getByTestId('mfa-desactivar-contrasena').fill(cuenta.contrasena);
    await page.getByTestId('mfa-desactivar-codigo').fill(nuevos[0]);
    await page.getByTestId('mfa-confirmar-desactivar').click();
    await expect(page.getByTestId('mfa-desactivado')).toBeVisible();
    await expect(page.getByTestId('mfa-estado')).toContainText('desactivada');
  });

  test('AC_TKT010_07 ruta del panel sin sesión → SCR-030 con siguiente y retorno; siguiente externo → Tablero', async ({
    page,
    browser,
  }) => {
    const cuenta = crearCuenta();
    await irA(page, '/panel/cuenta');
    await expect(page).toHaveURL(/\/panel\/acceso\?siguiente=%2Fpanel%2Fcuenta$/);
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page).toHaveURL(/\/panel\/cuenta$/);

    const contexto = await browser.newContext();
    const otra = await contexto.newPage();
    await irA(otra, '/panel/acceso?siguiente=https%3A%2F%2Fevil.example%2Fpanel');
    await entrarPorUi(otra, cuenta.usuario, cuenta.contrasena);
    await expect(otra).toHaveURL(/^http:\/\/[^/]+\/panel$/);
    await contexto.close();

    // FALLO-03 (QA ciclo 1): segmentos de punto codificados no sacan del panel.
    const contexto2 = await browser.newContext();
    const tercera = await contexto2.newPage();
    await irA(tercera, `/panel/acceso?siguiente=${encodeURIComponent('/panel/%2e%2e/destinos')}`);
    await entrarPorUi(tercera, cuenta.usuario, cuenta.contrasena);
    await expect(tercera).toHaveURL(/^http:\/\/[^/]+\/panel$/);
    await contexto2.close();
  });

  test('AC_TKT010_08 rol: Editor sin accesos de Administrador (API 403 y SCR-048); el Administrador sí', async ({
    page,
    browser,
  }) => {
    const editor = crearCuenta();
    await entrarPorApi(page, editor);
    await irA(page, '/panel');
    await expect(page.getByTestId('panel-usuario-rol')).toHaveText('Editor');
    await expect(page.getByTestId('panel-navegacion').locator('a')).toHaveText(['Tablero', 'Mi cuenta']);
    expect((await page.request.get('/api/v1/panel/cuentas')).status()).toBe(403);
    await irA(page, '/panel/acceso-denegado');
    await expect(page.getByTestId('acceso-denegado')).toBeVisible();
    await expect(page.locator('h1')).toHaveText('No tienes permiso para ver esta sección');
    await page.getByTestId('acceso-denegado-tablero').click();
    await expect(page).toHaveURL(/\/panel$/);

    const contexto = await browser.newContext();
    const admin = await contexto.newPage();
    const cuentaAdmin = crearCuenta({ rol: 'ADMINISTRADOR', conMfa: true });
    await entrarPorApi(admin, cuentaAdmin);
    await irA(admin, '/panel/cuenta');
    await expect(admin.getByTestId('panel-usuario-rol')).toHaveText('Administrador');
    await expect(admin.getByTestId('mfa-obligatorio')).toBeVisible();
    expect((await admin.request.get('/api/v1/panel/cuentas')).status()).toBe(200);
    await contexto.close();
  });

  test('AC_TKT010_09 Tablero con datos reales de /api/v1/panel/tablero, alerta solo para Administrador', async ({
    page,
    browser,
  }) => {
    const admin = crearCuenta({ rol: 'ADMINISTRADOR', conMfa: true });
    await entrarPorApi(page, admin);
    const respuesta = await page.request.get('/api/v1/panel/tablero');
    expect(respuesta.status()).toBe(200);
    const tablero = (await respuesta.json()) as {
      conteos: { tipo: string; borrador: number; publicado: number; retirado: number }[];
      recientes: { titulo: string }[];
      alertas: { code: string }[];
    };
    await irA(page, '/panel');
    await expect(page.getByTestId('tablero-conteos')).toBeVisible();
    for (const conteo of tablero.conteos) {
      const fila = page.getByTestId(`tablero-conteo-${conteo.tipo}`).locator('td');
      await expect(fila).toHaveText([
        String(conteo.borrador),
        String(conteo.publicado),
        String(conteo.retirado),
        String(conteo.borrador + conteo.publicado + conteo.retirado),
      ]);
    }
    if (tablero.recientes.length > 0) {
      await expect(page.getByTestId('tablero-recientes')).toContainText(tablero.recientes[0].titulo);
    }
    for (const alerta of tablero.alertas) {
      await expect(page.getByTestId(`tablero-alerta-${alerta.code}`)).toBeVisible();
    }
    // Ningún acceso rápido a secciones aún no implementadas (RULE-030).
    await expect(page.getByTestId('tablero-accesos')).toHaveCount(0);

    const contexto = await browser.newContext();
    const editorPagina = await contexto.newPage();
    await entrarPorApi(editorPagina, crearCuenta());
    const delEditor = (await (await editorPagina.request.get('/api/v1/panel/tablero')).json()) as {
      alertas: { code: string }[];
    };
    expect(delEditor.alertas.map((a) => a.code)).not.toContain('responsable_sin_definir');
    await irA(editorPagina, '/panel');
    await expect(editorPagina.getByTestId('tablero-conteos')).toBeVisible();
    await expect(editorPagina.getByTestId('tablero-alerta-responsable_sin_definir')).toHaveCount(0);
    await contexto.close();
  });

  test('AC_TKT010_10 axe sin violaciones serious/critical en SCR-030, 031, 032, 033, 034 y 048; noindex', async ({
    page,
  }) => {
    await irA(page, '/panel/acceso');
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'noindex, nofollow');
    await sinViolacionesGraves(page);

    const cuenta = crearCuenta({ conMfa: true, debeCambiar: true, autorizada: false });
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page).toHaveURL(/\/panel\/acceso\/verificacion$/);
    await sinViolacionesGraves(page);

    await page.getByTestId('mfa-codigo').fill(await siguienteCodigo(cuenta));
    await page.getByTestId('mfa-verificar').click();
    await expect(page.getByTestId('cuenta-obligatorio')).toBeVisible();
    await sinViolacionesGraves(page);

    const nueva = await nuevaContrasena();
    await page.getByTestId('cuenta-actual').fill(cuenta.contrasena);
    await page.getByTestId('cuenta-nueva').fill(nueva);
    await page.getByTestId('cuenta-confirmacion').fill(nueva);
    await page.getByTestId('cuenta-guardar-contrasena').click();
    await expect(page).toHaveURL(/\/panel\/autorizacion$/);
    await expect(page.getByTestId('autorizacion-resumen')).toBeVisible();
    await sinViolacionesGraves(page);

    await page.getByTestId('autorizacion-autorizo').click();
    await expect(page.getByTestId('tablero-conteos')).toBeVisible();
    await sinViolacionesGraves(page);

    await irA(page, '/panel/cuenta');
    await expect(page.getByTestId('mfa-estado')).toBeVisible();
    await sinViolacionesGraves(page);

    await irA(page, '/panel/acceso-denegado');
    await expect(page.getByTestId('acceso-denegado')).toBeVisible();
    await sinViolacionesGraves(page);
  });

  test('AC_TKT010_10 teclado: saltos al contenido y a la navegación; Enter envía el acceso', async ({
    page,
    browserName,
  }) => {
    const cuenta = crearCuenta();
    await irA(page, '/panel/acceso');
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena, 'enter');
    await expect(page).toHaveURL(/\/panel$/);
    await expect(page.getByTestId('pagina-tablero')).toBeVisible();

    await irA(page, '/panel');
    await expect(page.getByTestId('pagina-tablero')).toBeVisible();
    if (enlacesTabulables(browserName)) {
      await page.keyboard.press('Tab');
      expect(await focoActual(page)).toBe('panel-saltar-contenido');
      await page.keyboard.press('Tab');
      expect(await focoActual(page)).toBe('panel-saltar-navegacion');
    } else {
      await page.getByTestId('panel-saltar-navegacion').focus();
    }
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('panel-navegacion')).toBeFocused();

    await page.getByTestId('panel-saltar-contenido').focus();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('panel-contenido')).toBeFocused();
  });

  test('AC_TKT010_10 operable a 320 px: sin scroll horizontal y con el menú en cajón', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 720 });
    const cuenta = crearCuenta();
    await irA(page, '/panel/acceso');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await entrarPorUi(page, cuenta.usuario, cuenta.contrasena);
    await expect(page.getByTestId('tablero-conteos')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await expect(page.getByTestId('panel-navegacion')).toBeHidden();

    // OBS-06 (QA ciclo 1): cajón modal < lg — foco dentro, Escape cierra y devuelve el foco.
    const menu = page.getByTestId('panel-menu');
    const cajon = page.getByTestId('panel-cajon');
    await menu.click();
    await expect(cajon).toBeVisible();
    await expect(menu).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByTestId('panel-cajon-nav-tablero')).toBeFocused();
    await sinViolacionesGraves(page);
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab');
      const dentro = await page.evaluate(
        () => document.activeElement?.closest('[data-testid="panel-cajon"]') !== null,
      );
      // El foco no sale al contenido inerte (puede pasar por la interfaz del navegador).
      const enContenido = await page.evaluate(
        () => document.activeElement?.closest('[data-testid="panel-contenido"]') !== null,
      );
      expect(dentro || !enContenido).toBe(true);
    }
    await page.keyboard.press('Escape');
    await expect(cajon).toBeHidden();
    await expect(menu).toBeFocused();
    await expect(menu).toHaveAttribute('aria-expanded', 'false');

    await menu.click();
    await page.getByTestId('panel-cajon-nav-cuenta').click();
    await expect(page).toHaveURL(/\/panel\/cuenta$/);
    await expect(cajon).toBeHidden();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await sinViolacionesGraves(page);
  });

  test('AC_TKT010_11 aviso 2 min antes de expirar por inactividad y «Seguir conectado» renueva la sesión', async ({
    page,
  }) => {
    const cuenta = crearCuenta();
    await entrarPorApi(page, cuenta);
    await irA(page, '/panel');
    await expect(page.getByTestId('tablero-conteos')).toBeVisible();

    // La sesión expira 30 min después del último uso (medido por el servidor). Solo se adelanta la
    // hora del navegador (Date); los temporizadores siguen corriendo, porque el planificador de
    // detección de cambios zoneless de Angular depende de ellos.
    const consulta = page.waitForResponse((r) => r.url().endsWith('/api/v1/panel/auth/sesion'));
    await page.clock.setFixedTime(Date.now() + 28.5 * 60_000);
    expect((await consulta).status()).toBe(200);
    const aviso = page.getByTestId('aviso-expiracion');
    await expect(aviso).toBeVisible();
    await expect(aviso).toHaveAttribute('role', 'alertdialog');
    await expect(aviso).toContainText('Tu sesión está por expirar');
    await expect(page.getByTestId('aviso-expiracion-cuenta')).toHaveText(/^[0-2]:\d\d$/);
    await expect(page.getByTestId('aviso-expiracion-seguir')).toBeFocused();

    const renovar = page.waitForResponse((r) => r.url().endsWith('/api/v1/panel/auth/sesion/renovar'));
    await page.getByTestId('aviso-expiracion-seguir').click();
    const respuesta = await renovar;
    expect(respuesta.status()).toBe(200);
    const renovada = (await respuesta.json()) as { expira_inactividad_en: string };
    expect(new Date(renovada.expira_inactividad_en).getTime()).toBeGreaterThan(Date.now() + 29 * 60_000);
    // Vuelve la hora real: con la inactividad renovada no hay aviso.
    await page.clock.setFixedTime(Date.now());
    await expect(aviso).toBeHidden();
    expect(await sesionApi(page)).toBe(200);
  });
});
