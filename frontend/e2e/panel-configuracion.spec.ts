/**
 * E2E de configuración editorial y administración del panel (TKT-024): SCR-042 Destacados de
 * inicio (FLOW-014), SCR-043 Taxonomías, SCR-047 Configuración del sitio, SCR-044/045 Cuentas del
 * equipo (FLOW-015) y SCR-046 Auditoría (FLOW-016), contra el stack real de Compose, con axe en
 * cada pantalla. Hereda de TKT-010 el E2E de AC_TKT010_08 sobre una ruta real solo-Admin.
 * Los cambios en datos compartidos (destacados, configuración) se restauran al terminar el caso.
 * Requiere E2E_BASE_URL y E2E_COMPOSE_PROJECT (ver panel-soporte.ts).
 */
import { Page, expect, test } from '@playwright/test';

import { apiEscribir, apiGet, sufijo } from './panel-contenidos-soporte';
import {
  entrarComoAdminCompartido,
  entrarComoEditorCompartido,
  esperarTransiciones,
  expectPanel,
  irA,
  loginApi,
  omitirSinStack,
} from './panel-soporte';
import { sinViolacionesGraves } from './utilidades';

test.beforeEach(() => {
  omitirSinStack();
  test.setTimeout(150_000);
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});

async function axe(page: Page): Promise<void> {
  await esperarTransiciones(page);
  await sinViolacionesGraves(page);
}

interface ConfigInicioApi {
  hero_titular: string;
  hero_subtitulo: string;
  hero_medio_id: number;
  destinos_ids: number[];
  itinerarios_ids: number[];
  guias_ids: number[];
}

interface ConfiguracionApi {
  nombre_marca: string;
  lema: string | null;
  texto_descargo: string;
  responsable_nombre: string | null;
  responsable_identificacion: string | null;
  responsable_domicilio: string | null;
  responsable_canal_atencion: string | null;
}

function entradaInicio(c: ConfigInicioApi): ConfigInicioApi {
  return {
    hero_titular: c.hero_titular,
    hero_subtitulo: c.hero_subtitulo,
    hero_medio_id: c.hero_medio_id,
    destinos_ids: c.destinos_ids,
    itinerarios_ids: c.itinerarios_ids,
    guias_ids: c.guias_ids,
  };
}

function entradaConfiguracion(c: ConfiguracionApi): ConfiguracionApi {
  return {
    nombre_marca: c.nombre_marca,
    lema: c.lema,
    texto_descargo: c.texto_descargo,
    responsable_nombre: c.responsable_nombre,
    responsable_identificacion: c.responsable_identificacion,
    responsable_domicilio: c.responsable_domicilio,
    responsable_canal_atencion: c.responsable_canal_atencion,
  };
}

test.describe('Panel · configuración y administración (TKT-024)', () => {
  test('AC_TKT010_08 / AC_TKT024_11 un Editor en rutas solo-Admin ve SCR-048 conservando la URL; el Administrador accede', async ({ page }) => {
    await entrarComoEditorCompartido(page);
    for (const ruta of ['/panel/usuarios', '/panel/auditoria', '/panel/configuracion']) {
      await irA(page, ruta);
      await expectPanel(page.getByTestId('acceso-denegado')).toBeVisible();
      await expect(page).toHaveURL(new RegExp(`${ruta}$`));
    }
    await expect(page.getByTestId('panel-nav-usuarios')).toHaveCount(0);
    await expect(page.getByTestId('panel-nav-inicio')).toBeVisible();
    await expect(page.getByTestId('panel-nav-taxonomias')).toBeVisible();
    await axe(page);

    await page.context().clearCookies();
    await entrarComoAdminCompartido(page);
    await irA(page, '/panel/usuarios');
    await expectPanel(page.getByTestId('cuentas-tabla')).toBeVisible();
    await expect(page.getByTestId('acceso-denegado')).toHaveCount(0);
    await expect(page.getByTestId('panel-nav-usuarios')).toHaveAttribute('aria-current', 'page');
  });

  test('AC_TKT024_02 / AC_TKT024_03 FLOW-014: destacados con mínimos, reordenación, «Ver inicio» y aviso al salir', async ({ page }) => {
    await entrarComoEditorCompartido(page);
    const original = await apiGet<ConfigInicioApi>(page, '/inicio');
    try {
      await irA(page, '/panel/inicio');
      await expectPanel(page.getByTestId('destacados-formulario')).toBeVisible();
      await expect(page.getByRole('heading', { level: 1, name: 'Destacados de inicio' })).toBeVisible();
      const guias = page.getByTestId('destacados-guias-elemento');
      await expect(guias).toHaveCount(original.guias_ids.length);
      await expect(page.getByTestId('destacados-guias-contador')).toContainText(`${original.guias_ids.length} de 3 mínimo`);
      await axe(page);

      // Por debajo del mínimo: no se guarda y el resumen explica el motivo.
      const quitar = original.guias_ids.length - 2;
      for (let i = 0; i < quitar; i++) await page.getByTestId('destacados-guias-quitar-0').click();
      await expect(guias).toHaveCount(2);
      await page.getByTestId('destacados-guardar').click();
      await expect(page.getByTestId('destacados-errores')).toContainText('Elige al menos 3 guías');
      await expect(page.getByTestId('destacados-errores')).toBeFocused();

      // Salir con cambios sin guardar pide confirmación; «Cancelar» mantiene la pantalla.
      await page.getByTestId('panel-nav-medios').click();
      await expect(page.getByTestId('destacados-dialogo-salir')).toBeVisible();
      await page.getByTestId('destacados-dialogo-salir-cancelar').click();
      await expect(page).toHaveURL(/\/panel\/inicio$/);
      await page.getByTestId('panel-nav-medios').click();
      await page.getByTestId('destacados-dialogo-salir-confirmar').click();
      await expect(page).toHaveURL(/\/panel\/medios$/);

      // Reordenar los itinerarios (Bajar el primero) y guardar: se aplica al instante.
      await irA(page, '/panel/inicio');
      await expectPanel(page.getByTestId('destacados-formulario')).toBeVisible();
      await page.locator('#destacados-itinerarios-bajar-0').click();
      await expect(page.locator('#destacados-itinerarios-bajar-1')).toBeFocused();
      await page.getByTestId('destacados-guardar').click();
      await expectPanel(page.getByTestId('destacados-exito')).toContainText('Los cambios ya se ven en el inicio.');
      await expect(page.getByTestId('destacados-ver-inicio')).toHaveAttribute('href', '/');
      await axe(page);
      const guardado = await apiGet<ConfigInicioApi>(page, '/inicio');
      expect(guardado.itinerarios_ids).toEqual([original.itinerarios_ids[1], original.itinerarios_ids[0], ...original.itinerarios_ids.slice(2)]);
    } finally {
      await apiEscribir(page, 'put', '/inicio', entradaInicio(original));
    }
  });

  test('AC_TKT024_04 / AC_TKT024_05 taxonomías: alta en diálogo, retiro y reactivación, retiro bloqueado y licencias en solo lectura', async ({ page }) => {
    await entrarComoEditorCompartido(page);
    await irA(page, '/panel/taxonomias');
    await expectPanel(page.getByTestId('taxonomias-tabla')).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Regiones' })).toHaveAttribute('aria-selected', 'true');
    await axe(page);

    const nombre = `Región E2E ${sufijo()}`;
    await page.getByTestId('taxonomias-nuevo').click();
    const dialogo = page.getByTestId('taxonomias-dialogo');
    await expect(dialogo).toBeVisible();
    await expect(page.getByTestId('taxonomias-campo-nombre')).toBeFocused();
    await page.getByTestId('taxonomias-campo-nombre').fill(nombre);
    await expect(page.getByTestId('taxonomias-campo-slug')).toHaveValue(/^region-e2e-[0-9a-f]{8}$/);
    await page.getByTestId('taxonomias-campo-continente').selectOption('OCEANIA');
    await axe(page);
    await page.getByTestId('taxonomias-dialogo-guardar').click();
    await expect(dialogo).toBeHidden();
    await expectPanel(page.getByTestId('taxonomias-exito')).toContainText(nombre);
    const fila = page.getByTestId('taxonomias-fila').filter({ hasText: nombre });
    await expectPanel(fila).toContainText('Activo');

    // Retirar (sin uso) y reactivar.
    await fila.getByRole('button', { name: `Retirar ${nombre}` }).click();
    await page.getByTestId('taxonomias-dialogo-estado-confirmar').click();
    await expectPanel(fila).toContainText('Retirado');
    await fila.getByRole('button', { name: `Reactivar ${nombre}` }).click();
    await page.getByTestId('taxonomias-dialogo-estado-confirmar').click();
    await expectPanel(fila).toContainText('Activo');

    // Retirar un país que usa un destino publicado: bloqueado con la lista de usos (RULE-007).
    const publicados = await apiGet<{ resultados: { id: number }[] }>(page, '/contenidos/destinos?estado=PUBLICADO');
    const destino = await apiGet<{ pais_id: number }>(page, `/contenidos/destinos/${publicados.resultados[0].id}`);
    await page.getByRole('tab', { name: 'Países' }).click();
    await expect(page).toHaveURL(/catalogo=paises/);
    await expectPanel(page.getByTestId(`taxonomias-retirar-${destino.pais_id}`)).toBeVisible();
    await page.getByTestId(`taxonomias-retirar-${destino.pais_id}`).click();
    await page.getByTestId('taxonomias-dialogo-estado-confirmar').click();
    await expectPanel(page.getByTestId('taxonomias-bloqueo')).toContainText('No se puede retirar');
    await expect(page.getByTestId('taxonomias-bloqueo-usos').getByRole('listitem').first()).toBeVisible();
    await axe(page);

    // Licencias: solo lectura para el Editor (RULE-014).
    await page.getByRole('tab', { name: 'Licencias' }).click();
    await expectPanel(page.getByTestId('taxonomias-solo-admin')).toContainText('Solo un administrador puede modificar las licencias y las escalas.');
    await expect(page.getByTestId('taxonomias-nuevo')).toHaveCount(0);
    await expect(page.getByTestId('taxonomias-fila').first().getByRole('button')).toHaveCount(0);
    await page.getByRole('tab', { name: 'Escalas' }).click();
    await expectPanel(page.getByTestId('taxonomias-tabla-dificultad')).toBeVisible();
    await expect(page.getByTestId('taxonomias-tabla-dificultad').getByRole('button')).toHaveCount(0);
    await axe(page);
  });

  test('AC_TKT024_10 configuración del sitio: guarda la marca y la ve el sitio público', async ({ page }) => {
    await entrarComoAdminCompartido(page);
    const original = await apiGet<ConfiguracionApi>(page, '/configuracion');
    try {
      await irA(page, '/panel/configuracion');
      await expectPanel(page.getByTestId('config-formulario')).toBeVisible();
      await expect(page.getByTestId('config-campo-marca')).toHaveValue(original.nombre_marca);
      if (original.responsable_nombre === null) {
        await expect(page.getByTestId('config-responsable-vacio')).toContainText('[RESPONSABLE POR DEFINIR]');
      }
      await axe(page);
      const lema = `Lema E2E ${sufijo()}`;
      await page.getByTestId('config-campo-lema').fill(lema);
      await page.getByTestId('config-campo-descargo').fill(`${original.texto_descargo} (revisado)`);
      await expect(page.getByTestId('config-vista-descargo')).toContainText('(revisado)');
      await page.getByTestId('config-guardar').click();
      await expectPanel(page.getByTestId('config-exito')).toContainText('Configuración guardada.');
      const publica = await page.request.get('/api/v1/publico/configuracion');
      expect(((await publica.json()) as { lema: string }).lema).toBe(lema);
    } finally {
      await apiEscribir(page, 'put', '/configuracion', entradaConfiguracion(original));
    }
  });

  test('AC_TKT024_06 / AC_TKT024_07 / AC_TKT024_08 FLOW-015: alta con contraseña temporal única, desactivar y anonimizar; la propia cuenta no se desactiva', async ({ page, browser }) => {
    const admin = await entrarComoAdminCompartido(page);
    await irA(page, '/panel/usuarios');
    await expectPanel(page.getByTestId('cuentas-tabla')).toBeVisible();
    await axe(page);
    await page.getByTestId('cuentas-nueva').click();
    await expect(page).toHaveURL(/\/panel\/usuarios\/nuevo$/);
    const usuario = `e2e.alta.${sufijo()}`;
    await page.getByTestId('cuenta-campo-usuario').fill(usuario);
    await page.getByTestId('cuenta-campo-nombre').fill('Alta E2E');
    await page.getByTestId('cuenta-rol-EDITOR').check();
    await axe(page);
    await page.getByTestId('cuenta-guardar').click();
    await expectPanel(page.getByTestId('secreto-temporal')).toContainText(`Contraseña temporal de ${usuario}`);
    await expect(page.getByTestId('secreto-temporal')).toContainText('Se muestra solo esta vez.');
    await expect(page.getByRole('heading', { name: `Contraseña temporal de ${usuario}` })).toBeFocused();
    const temporal = (await page.getByTestId('secreto-valor').textContent())?.trim() ?? '';
    expect(temporal.length).toBeGreaterThanOrEqual(16);
    await axe(page);
    await page.getByTestId('secreto-guardado').click();
    await expect(page).toHaveURL(/\/panel\/usuarios\/\d+$/);
    await expect(page.getByTestId('secreto-temporal')).toHaveCount(0);
    await expect(page.getByTestId('cuenta-estado')).toContainText('Pendiente de activación');
    await expect(page.locator('body')).not.toContainText(temporal);

    // AC-106: la contraseña temporal entra y exige cambiarla (otra sesión, sin tocar la del Administrador).
    const otro = await browser.newContext({ baseURL: test.info().project.use.baseURL });
    const otraPagina = await otro.newPage();
    const login = await loginApi(otraPagina, usuario, temporal);
    expect(login.status(), await login.text()).toBe(200);
    expect(((await login.json()) as { paso_pendiente: string }).paso_pendiente).toBe('CAMBIO_CREDENCIAL');
    await otro.close();

    // Desactivar (efecto descrito antes de confirmar) y anonimizar.
    await page.getByTestId('cuenta-accion-desactivar').click();
    await expect(page.getByTestId('cuenta-dialogo-accion')).toContainText('Se cerrarán todas sus sesiones de inmediato.');
    await expect(page.getByTestId('cuenta-dialogo-accion-cancelar')).toBeFocused();
    await axe(page);
    await page.getByTestId('cuenta-dialogo-accion-confirmar').click();
    await expectPanel(page.getByTestId('cuenta-estado')).toContainText('Desactivada');
    await page.getByTestId('cuenta-accion-anonimizar').click();
    await page.getByTestId('cuenta-dialogo-accion-confirmar').click();
    await expectPanel(page.getByTestId('cuenta-anonimizada')).toBeVisible();
    await expect(page.getByTestId('cuenta-estado')).toContainText('Anonimizada');

    // RULE-015: la propia cuenta no se puede desactivar ni cambiar de rol.
    const propias = await apiGet<{ resultados: { id: number; usuario: string | null }[]; total_paginas: number }>(page, '/cuentas?estado=ACTIVA&rol=ADMINISTRADOR');
    const propia = propias.resultados.find((c) => c.usuario === admin.usuario);
    expect(propia, 'la cuenta del Administrador de la prueba está en la primera página').toBeDefined();
    await irA(page, `/panel/usuarios/${propia!.id}`);
    await expectPanel(page.getByTestId('cuenta-accion-desactivar-motivo')).toContainText('No puedes desactivar tu propia cuenta.');
    await expect(page.getByTestId('cuenta-accion-desactivar')).toHaveAttribute('aria-disabled', 'true');
    await expect(page.getByTestId('cuenta-rol-motivo')).toContainText('No puedes cambiar tu propio rol.');
    await axe(page);
  });

  test('AC_TKT024_06 QA c1 FALLO-01: la contraseña temporal no se descarta sin «Ya la guardé» (menú, Atrás y recarga)', async ({ page }) => {
    await entrarComoAdminCompartido(page);
    await irA(page, '/panel/usuarios');
    await page.getByTestId('cuentas-nueva').click();
    await expectPanel(page.getByTestId('cuenta-formulario')).toBeVisible();
    const usuario = `e2e.secreto.${sufijo()}`;
    await page.getByTestId('cuenta-campo-usuario').fill(usuario);
    await page.getByTestId('cuenta-campo-nombre').fill('Secreto E2E');
    await page.getByTestId('cuenta-rol-EDITOR').check();
    await page.getByTestId('cuenta-guardar').click();
    await expectPanel(page.getByTestId('secreto-temporal')).toBeVisible();
    // La URL ya es la de la cuenta creada y no hay «Volver» mientras el secreto está visible.
    await expect(page).toHaveURL(/\/panel\/usuarios\/\d+$/);
    const urlCuenta = page.url();
    await expect(page.getByTestId('cuenta-volver')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: `Contraseña temporal de ${usuario}` })).toBeFocused();

    // Menú lateral: pide confirmación; «Cancelar» se queda con el secreto.
    await page.getByTestId('panel-nav-usuarios').click();
    const dialogo = page.getByTestId('cuenta-dialogo-salir');
    await expect(dialogo).toBeVisible();
    await expect(dialogo).toContainText('no podrás volver a verla');
    await expect(page.getByTestId('cuenta-dialogo-salir-cancelar')).toBeFocused();
    await axe(page);
    await page.getByTestId('cuenta-dialogo-salir-cancelar').click();
    await expect(page).toHaveURL(urlCuenta);
    await expect(page.getByTestId('secreto-temporal')).toBeVisible();

    // Atrás del navegador: también pregunta.
    await page.goBack();
    await expect(dialogo).toBeVisible();
    await page.getByTestId('cuenta-dialogo-salir-cancelar').click();
    await expect(page.getByTestId('secreto-temporal')).toBeVisible();
    await expect(page).toHaveURL(urlCuenta);

    // Recarga: aviso nativo (beforeunload); al aceptarlo, la ficha explica cómo emitir otra contraseña.
    const avisos: string[] = [];
    page.on('dialog', (d) => {
      avisos.push(d.type());
      void d.accept();
    });
    await page.reload();
    await page.locator('html[data-app-lista="true"]').waitFor({ state: 'attached' });
    expect(avisos).toContain('beforeunload');
    await expect(page).toHaveURL(urlCuenta);
    await expectPanel(page.getByTestId('cuenta-aviso-pendiente')).toContainText('Restablecer contraseña');
    await expect(page.getByTestId('secreto-temporal')).toHaveCount(0);
    await expect(page.getByTestId('cuenta-campo-usuario')).toHaveValue(usuario);
    await expect(page.getByTestId('cuenta-guardar')).toHaveText('Guardar');
  });

  test('AC_TKT024_04 QA c1 FALLO-02: activar una pestaña o el select «Catálogo» mantiene el foco en el control', async ({ page }) => {
    await entrarComoEditorCompartido(page);
    await irA(page, '/panel/taxonomias');
    await expectPanel(page.getByTestId('taxonomias-tabla')).toBeVisible();
    await page.getByTestId('taxonomias-tab-paises').click();
    await expect(page).toHaveURL(/catalogo=paises/);
    await expectPanel(page.getByTestId('taxonomias-tabla')).toBeVisible();
    await expect(page.getByTestId('taxonomias-tab-paises')).toBeFocused();
    // Teclado: la flecha mueve el foco y Enter activa; el foco sigue en la pestaña activada.
    await page.keyboard.press('ArrowRight');
    await expect(page.getByTestId('taxonomias-tab-categorias')).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/catalogo=categorias/);
    await expect(page.getByTestId('taxonomias-tab-categorias')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('taxonomias-tab-categorias')).toBeFocused();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press(' ');
    await expect(page).toHaveURL(/catalogo=licencias/);
    await expect(page.getByTestId('taxonomias-tab-licencias')).toBeFocused();
    // Móvil: el select «Catálogo» conserva el foco al cambiar.
    await page.setViewportSize({ width: 375, height: 800 });
    await page.getByTestId('taxonomias-select').selectOption('escalas');
    await expect(page).toHaveURL(/catalogo=escalas/);
    await expectPanel(page.getByTestId('taxonomias-tabla-dificultad')).toBeVisible();
    await expect(page.getByTestId('taxonomias-select')).toBeFocused();
    await axe(page);
  });

  test('AC_TKT024_09 FLOW-016: auditoría de solo lectura con filtros en la URL y «Ver cambios»', async ({ page }) => {
    await entrarComoAdminCompartido(page);
    // Una acción auditada reciente y propia: reguardar la configuración tal cual (CONFIG_SITIO).
    const config = await apiGet<ConfiguracionApi>(page, '/configuracion');
    await apiEscribir(page, 'put', '/configuracion', entradaConfiguracion(config));
    await irA(page, '/panel/auditoria');
    await expectPanel(page.getByTestId('auditoria-tabla')).toBeVisible();
    await expect(page.getByTestId('auditoria-nota')).toContainText('Registro de solo lectura. Se conserva 365 días.');
    await axe(page);
    await page.getByTestId('auditoria-accion').selectOption('CONFIG_SITIO');
    await page.getByTestId('auditoria-aplicar').click();
    await expect(page).toHaveURL(/accion=CONFIG_SITIO/);
    const fila = page.getByTestId('auditoria-fila').first();
    await expectPanel(fila).toContainText('Configuración del sitio');
    await expect(fila).toContainText('hora de Bogotá');
    await expect(fila.getByTestId('auditoria-entidad')).toHaveAttribute('href', '/panel/configuracion');
    const ver = fila.getByRole('button', { name: 'Ver cambios' });
    if ((await ver.count()) > 0) {
      await expect(ver).toHaveAttribute('aria-expanded', 'false');
      await ver.click();
      await expect(ver).toHaveAttribute('aria-expanded', 'true');
    }
    // Rango invertido: no se consulta y se explica en el filtro.
    await page.getByTestId('auditoria-desde').fill('2026-10-10');
    await page.getByTestId('auditoria-hasta').fill('2026-10-01');
    await page.getByTestId('auditoria-aplicar').click();
    await expectPanel(page.getByTestId('auditoria-fechas-error')).toContainText('posterior');
    await page.getByTestId('auditoria-limpiar').click();
    await expect(page).toHaveURL(/\/panel\/auditoria$/);
    await expectPanel(page.getByTestId('auditoria-tabla')).toBeVisible();
    await axe(page);
  });
});
