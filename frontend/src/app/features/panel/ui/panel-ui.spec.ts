import { HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Location } from '@angular/common';
import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Route, Router, Routes, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { DATOS_ZONA_PANEL } from '../../../core/layout/shell-publico/zona';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { PanelTableroRepositorio } from '../data/panel-tablero.repositorio';
import { AutorizacionTratamiento, SesionPanel, TableroPanel } from '../domain/modelos';
import { ExpiracionSesionStore } from '../state/expiracion-sesion.store';
import { AvisoExpiracion } from './aviso-expiracion';
import { CodigoQr } from './codigo-qr';
import { RUTAS_PANEL } from './panel.routes';

// jsdom no implementa <dialog> modal ni scrollIntoView: equivalentes mínimos para las pruebas.
beforeAll(() => {
  const proto = HTMLDialogElement.prototype as unknown as {
    showModal?: () => void;
    close?: () => void;
  };
  if (typeof proto.showModal !== 'function') {
    proto.showModal = function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
    proto.close = function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    };
  }
});

const AHORA = Date.now();

function sesion(parcial: Partial<SesionPanel> = {}): SesionPanel {
  return {
    usuario: 'editora.uno',
    nombreVisible: 'Editora Uno',
    rol: 'EDITOR',
    pasoPendiente: 'NINGUNO',
    mfaActivo: false,
    mfaObligatorio: false,
    expiraInactividadEn: new Date(AHORA + 30 * 60_000),
    expiraAbsolutaEn: new Date(AHORA + 12 * 3_600_000),
    redireccion: '/panel',
    ...parcial,
  };
}

function http(status: number, cuerpo: unknown = { code: 'x' }, cabeceras?: Record<string, string>) {
  return new HttpErrorResponse({ status, error: cuerpo, headers: new HttpHeaders(cabeceras ?? {}) });
}

const AUTORIZACION: AutorizacionTratamiento = {
  versionPolitica: '2.1',
  vigenteDesde: '2026-01-01',
  resumenFinalidad: 'Gestionar tu acceso al panel.',
  urlPolitica: '/politica-de-tratamiento-de-datos',
  otorgadaEn: new Date('2026-02-01T00:00:00Z'),
  versionOtorgada: '2.1',
};

const TABLERO: TableroPanel = {
  conteos: [
    { tipo: 'DESTINO', borrador: 2, publicado: 5, retirado: 1 },
    { tipo: 'GUIA', borrador: 0, publicado: 3, retirado: 0 },
  ],
  recientes: [
    {
      id: 1,
      tipo: 'DESTINO',
      titulo: 'Patagonia',
      estado: 'PUBLICADO',
      actualizadoEn: new Date('2026-09-29T08:00:00Z'),
      actualizadoPor: 'editora.uno',
      urlPublica: '/destinos/patagonia',
    },
  ],
  alertas: [{ codigo: 'responsable_sin_definir', mensaje: 'Faltan los datos del Responsable.', enlace: '/panel/configuracion' }],
  saludEditorial: {
    revisionesAntiguas: [],
    mediosPendientesMetadatos: 3,
    mediosSinUso: 0,
    coleccionesBajoMinimo: [],
    contenidosConPocosRelacionados: [],
  },
};

type RepoFalso = Record<keyof PanelAuthRepositorio, ReturnType<typeof vi.fn>>;

function repoFalso(sesionInicial: SesionPanel | null): RepoFalso {
  return {
    asegurarCsrf: vi.fn().mockResolvedValue(undefined),
    iniciarSesion: vi.fn().mockResolvedValue(sesion()),
    verificarMfa: vi.fn().mockResolvedValue(sesion()),
    cerrarSesion: vi.fn().mockResolvedValue(undefined),
    sesion: sesionInicial
      ? vi.fn().mockResolvedValue(sesionInicial)
      : vi.fn().mockImplementation(() => Promise.reject(http(401, { code: 'no_autenticado' }))),
    renovarSesion: vi.fn().mockResolvedValue(sesion()),
    cambiarContrasena: vi.fn().mockResolvedValue(sesion()),
    autorizacion: vi.fn().mockResolvedValue(AUTORIZACION),
    registrarAutorizacion: vi.fn().mockResolvedValue(sesion()),
    iniciarActivacionMfa: vi
      .fn()
      .mockResolvedValue({ otpauthUri: 'otpauth://totp/Br%C3%BAjula:editora?secret=ABCDEFGHIJKLMNOP', claveSecreta: 'ABCDEFGHIJKLMNOP' }),
    confirmarActivacionMfa: vi.fn().mockResolvedValue(['AAAA-BBBB', 'CCCC-DDDD']),
    desactivarMfa: vi.fn().mockResolvedValue(undefined),
    regenerarCodigos: vi.fn().mockResolvedValue(['EEEE-FFFF']),
  };
}

@Component({ selector: 'app-prueba-admin', template: '<h1>Zona de administración</h1>' })
class PaginaSoloAdmin {}

/** Rutas reales del panel con una ruta hija de Administrador de prueba (AC_TKT010_08). */
function rutasConAdmin(): Routes {
  return RUTAS_PANEL.map((ruta): Route =>
    ruta.canActivate
      ? {
          ...ruta,
          children: [
            { path: 'solo-admin', component: PaginaSoloAdmin, data: { rolMinimo: 'ADMINISTRADOR' } },
            ...(ruta.children ?? []),
          ],
        }
      : ruta,
  );
}

interface Montaje {
  harness: RouterTestingHarness;
  repo: RepoFalso;
  tablero: ReturnType<typeof vi.fn>;
  raiz: () => HTMLElement;
  router: Router;
}

async function montar(
  url: string,
  sesionInicial: SesionPanel | null,
  ajustar?: (repo: RepoFalso) => void,
  tablero: () => Promise<TableroPanel> = () => Promise.resolve(TABLERO),
): Promise<Montaje> {
  const repo = repoFalso(sesionInicial);
  ajustar?.(repo);
  const repoTablero = vi.fn().mockImplementation(tablero);
  TestBed.configureTestingModule({
    providers: [
      // Igual que app.routes.ts: la ruta panel declara su zona (ZonaOutlet de los armazones).
      provideRouter([{ path: 'panel', data: DATOS_ZONA_PANEL, children: rutasConAdmin() }]),
      { provide: PanelAuthRepositorio, useValue: repo },
      { provide: PanelTableroRepositorio, useValue: { tablero: repoTablero } },
    ],
  });
  const harness = await RouterTestingHarness.create();
  await harness.navigateByUrl(url);
  await estable(harness);
  return {
    harness,
    repo,
    tablero: repoTablero,
    raiz: () => harness.routeNativeElement?.ownerDocument.body ?? document.body,
    router: TestBed.inject(Router),
  };
}

async function estable(harness: RouterTestingHarness): Promise<void> {
  for (let i = 0; i < 3; i++) {
    await harness.fixture.whenStable();
    await new Promise((r) => setTimeout(r, 0));
  }
}

function el<T extends HTMLElement = HTMLElement>(m: Montaje, testId: string): T {
  const elemento = m.raiz().querySelector<T>(`[data-testid="${testId}"]`);
  if (elemento === null) throw new Error(`No existe [data-testid="${testId}"]`);
  return elemento;
}

function existe(m: Montaje, testId: string): boolean {
  return m.raiz().querySelector(`[data-testid="${testId}"]`) !== null;
}

function escribir(m: Montaje, selector: string, valor: string): void {
  const input = m.raiz().querySelector<HTMLInputElement>(selector);
  if (input === null) throw new Error(`No existe ${selector}`);
  input.value = valor;
  input.dispatchEvent(new Event('input'));
}

async function pulsar(m: Montaje, testId: string): Promise<void> {
  el(m, testId).click();
  await estable(m.harness);
}

describe('Panel — acceso y armazón (FLOW-010)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT010_07 sin sesión, una ruta del panel lleva a SCR-030 con siguiente y, tras entrar, vuelve a ella', async () => {
    const m = await montar('/panel/cuenta', null, (repo) =>
      repo.iniciarSesion.mockResolvedValue(sesion({ redireccion: '/panel/cuenta' })),
    );
    expect(m.router.url).toBe('/panel/acceso?siguiente=%2Fpanel%2Fcuenta');
    expect(m.raiz().querySelector('h1')?.textContent).toContain('Acceso al panel editorial');
    escribir(m, '[data-testid="acceso-usuario"]', 'editora.uno');
    escribir(m, '[data-testid="acceso-contrasena"]', 'frase-secreta');
    m.repo.sesion.mockResolvedValue(sesion({ redireccion: '/panel/cuenta' }));
    await pulsar(m, 'acceso-entrar');
    expect(m.repo.iniciarSesion).toHaveBeenCalledWith('editora.uno', 'frase-secreta', '/panel/cuenta');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/cuenta'));
  });

  it('AC_TKT010_07 un siguiente externo/malicioso no se envía y se entra al Tablero', async () => {
    const m = await montar('/panel/acceso?siguiente=https%3A%2F%2Fevil.example%2Fpanel', null);
    escribir(m, '[data-testid="acceso-usuario"]', 'editora.uno');
    escribir(m, '[data-testid="acceso-contrasena"]', 'frase-secreta');
    await pulsar(m, 'acceso-entrar');
    expect(m.repo.iniciarSesion).toHaveBeenCalledWith('editora.uno', 'frase-secreta', null);
    await vi.waitFor(() => expect(m.router.url).toBe('/panel'));
  });

  it('AC_TKT010_01 login correcto → Tablero; «Cerrar sesión» → SCR-030 con «Cerraste sesión.»', async () => {
    const m = await montar('/panel/acceso', null);
    escribir(m, '[data-testid="acceso-usuario"]', 'editora.uno');
    escribir(m, '[data-testid="acceso-contrasena"]', 'frase-secreta');
    await pulsar(m, 'acceso-entrar');
    await vi.waitFor(() => expect(existe(m, 'pagina-tablero')).toBe(true));
    expect(el(m, 'panel-usuario-nombre').textContent).toContain('Editora Uno');
    expect(el(m, 'panel-usuario-rol').textContent).toContain('Editor');
    await pulsar(m, 'panel-cerrar-sesion');
    expect(m.repo.cerrarSesion).toHaveBeenCalled();
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/acceso?motivo=cerrada'));
    await estable(m.harness);
    expect(el(m, 'acceso-motivo').textContent).toContain('Cerraste sesión.');
  });

  it('AC_TKT010_01 con sesión completa, /panel/acceso lleva al destino', async () => {
    const m = await montar('/panel/acceso?siguiente=%2Fpanel%2Fcuenta', sesion());
    expect(m.router.url).toBe('/panel/cuenta');
  });

  it('AC_TKT010_02 login fallido → mensaje genérico, contraseña vaciada y usuario conservado; bloqueo con minutos', async () => {
    const m = await montar('/panel/acceso', null, (repo) =>
      repo.iniciarSesion.mockImplementation(() =>
        Promise.reject(http(401, { code: 'credenciales_invalidas', title: 'x', status: 401 })),
      ),
    );
    await pulsar(m, 'acceso-entrar');
    expect(m.raiz().textContent).toContain('Escribe tu usuario.');
    expect(m.repo.iniciarSesion).not.toHaveBeenCalled();
    escribir(m, '[data-testid="acceso-usuario"]', 'no.existe');
    escribir(m, '[data-testid="acceso-contrasena"]', 'cualquiera');
    await pulsar(m, 'acceso-entrar');
    await vi.waitFor(() => expect(existe(m, 'acceso-error')).toBe(true));
    expect(el(m, 'acceso-error').textContent).toContain('Usuario o contraseña incorrectos.');
    expect(el<HTMLInputElement>(m, 'acceso-contrasena').value).toBe('');
    expect(el<HTMLInputElement>(m, 'acceso-usuario').value).toBe('no.existe');

    m.repo.iniciarSesion.mockImplementation(() =>
      Promise.reject(
        http(429, { code: 'acceso_bloqueado_temporalmente', title: 'x', status: 429, reintentar_en_segundos: 900 }),
      ),
    );
    escribir(m, '[data-testid="acceso-contrasena"]', 'otra');
    await pulsar(m, 'acceso-entrar');
    await vi.waitFor(() => expect(el(m, 'acceso-error').textContent).toContain('15 minutos'));
  });

  it('AC_TKT010_03 MFA: código inválido → error bajo el campo; código válido → Tablero; «Volver» cierra el intento', async () => {
    const m = await montar('/panel/acceso', null, (repo) => {
      repo.iniciarSesion.mockResolvedValue(sesion({ pasoPendiente: 'MFA' }));
      repo.verificarMfa.mockImplementationOnce(() => Promise.reject(http(401, { code: 'mfa_invalido' })));
    });
    escribir(m, '[data-testid="acceso-usuario"]', 'editora.uno');
    escribir(m, '[data-testid="acceso-contrasena"]', 'frase-secreta');
    await pulsar(m, 'acceso-entrar');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/acceso/verificacion'));
    await estable(m.harness);
    escribir(m, '#mfa-codigo', '12');
    await pulsar(m, 'mfa-verificar');
    expect(el(m, 'mfa-codigo-error').textContent).toContain('6 dígitos');
    escribir(m, '#mfa-codigo', '123 456');
    await pulsar(m, 'mfa-verificar');
    await vi.waitFor(() => expect(el(m, 'mfa-codigo-error').textContent).toContain('El código no es válido.'));
    expect(m.repo.verificarMfa).toHaveBeenCalledWith('123456');
    await pulsar(m, 'mfa-alternar-recuperacion');
    expect(m.raiz().querySelector('label[for="mfa-codigo"]')?.textContent).toContain('Código de recuperación');
    escribir(m, '#mfa-codigo', 'abcd-efgh');
    await pulsar(m, 'mfa-verificar');
    expect(m.repo.verificarMfa).toHaveBeenLastCalledWith('ABCD-EFGH');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel'));
  });

  it('AC_TKT010_03 «Volver» en la verificación cierra la sesión parcial', async () => {
    const m = await montar('/panel/acceso/verificacion', sesion({ pasoPendiente: 'MFA' }));
    await pulsar(m, 'mfa-volver');
    expect(m.repo.cerrarSesion).toHaveBeenCalled();
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/acceso'));
  });

  it('AC_TKT010_04 cambio obligatorio: SCR-032 sin navegación; contraseña débil → error de campo; correcto → continúa', async () => {
    const m = await montar('/panel', sesion({ pasoPendiente: 'CAMBIO_CREDENCIAL' }), (repo) => {
      repo.cambiarContrasena.mockImplementationOnce(() =>
        Promise.reject(
          http(400, { code: 'validacion', title: 'x', status: 400, errors: { contrasena_nueva: ['Elige una contraseña menos común.'] } }),
        ),
      );
      repo.cambiarContrasena.mockResolvedValue(sesion({ pasoPendiente: 'AUTORIZACION' }));
    });
    expect(m.router.url).toBe('/panel/cuenta');
    expect(existe(m, 'panel-layout-acceso')).toBe(true);
    expect(existe(m, 'panel-navegacion')).toBe(false);
    expect(el(m, 'cuenta-obligatorio').textContent).toContain('Debes cambiar tu contraseña temporal');
    expect(existe(m, 'cuenta-mfa')).toBe(false);

    escribir(m, '[data-testid="cuenta-actual"]', 'temporal');
    escribir(m, '[data-testid="cuenta-nueva"]', 'corta');
    escribir(m, '[data-testid="cuenta-confirmacion"]', 'distinta');
    await pulsar(m, 'cuenta-guardar-contrasena');
    expect(el(m, 'cuenta-nueva-error').textContent).toContain('Usa al menos 12 caracteres');
    expect(el(m, 'cuenta-confirmacion-error').textContent).toContain('no coinciden');
    expect(m.repo.cambiarContrasena).not.toHaveBeenCalled();

    escribir(m, '[data-testid="cuenta-nueva"]', 'contraseña123');
    escribir(m, '[data-testid="cuenta-confirmacion"]', 'contraseña123');
    await pulsar(m, 'cuenta-guardar-contrasena');
    await vi.waitFor(() => expect(el(m, 'cuenta-nueva-error').textContent).toContain('menos común'));

    escribir(m, '[data-testid="cuenta-actual"]', 'temporal');
    escribir(m, '[data-testid="cuenta-nueva"]', 'una frase larga y segura');
    escribir(m, '[data-testid="cuenta-confirmacion"]', 'una frase larga y segura');
    await pulsar(m, 'cuenta-guardar-contrasena');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/autorizacion'));
  });

  it('AC_TKT010_04 Administrador sin MFA: tras la contraseña pasa a activar MFA en la misma pantalla', async () => {
    const m = await montar('/panel/cuenta', sesion({ pasoPendiente: 'CAMBIO_CREDENCIAL', rol: 'ADMINISTRADOR' }), (repo) =>
      repo.cambiarContrasena.mockResolvedValue(sesion({ pasoPendiente: 'CONFIGURAR_MFA', rol: 'ADMINISTRADOR' })),
    );
    escribir(m, '[data-testid="cuenta-actual"]', 'temporal');
    escribir(m, '[data-testid="cuenta-nueva"]', 'una frase larga y segura');
    escribir(m, '[data-testid="cuenta-confirmacion"]', 'una frase larga y segura');
    await pulsar(m, 'cuenta-guardar-contrasena');
    await vi.waitFor(() => expect(existe(m, 'cuenta-mfa')).toBe(true));
    expect(existe(m, 'cuenta-contrasena')).toBe(false);
    expect(el(m, 'cuenta-obligatorio').textContent).toContain('debes activar la verificación en dos pasos');
  });

  it('AC_TKT010_05 autorización: «No autorizo» confirma y vuelve a SCR-030; «Autorizo» continúa', async () => {
    const m = await montar('/panel', sesion({ pasoPendiente: 'AUTORIZACION' }), (repo) =>
      repo.registrarAutorizacion.mockResolvedValueOnce(null),
    );
    expect(m.router.url).toBe('/panel/autorizacion');
    await vi.waitFor(() => expect(existe(m, 'autorizacion-resumen')).toBe(true));
    expect(el(m, 'autorizacion-politica').textContent).toContain('versión 2.1');
    await pulsar(m, 'autorizacion-no-autorizo');
    expect(el<HTMLDialogElement>(m, 'autorizacion-confirmacion').hasAttribute('open')).toBe(true);
    await pulsar(m, 'autorizacion-volver');
    expect(el<HTMLDialogElement>(m, 'autorizacion-confirmacion').hasAttribute('open')).toBe(false);
    await pulsar(m, 'autorizacion-no-autorizo');
    await pulsar(m, 'autorizacion-confirmar-no-autorizo');
    expect(m.repo.registrarAutorizacion).toHaveBeenCalledWith('NO_AUTORIZO', '2.1');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/acceso?motivo=cerrada'));
  });

  it('AC_TKT010_05 «Autorizo» registra la versión vigente y entra', async () => {
    const m = await montar('/panel/autorizacion', sesion({ pasoPendiente: 'AUTORIZACION' }));
    await vi.waitFor(() => expect(existe(m, 'autorizacion-autorizo')).toBe(true));
    await pulsar(m, 'autorizacion-autorizo');
    expect(m.repo.registrarAutorizacion).toHaveBeenCalledWith('AUTORIZO', '2.1');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel'));
  });

  it('AC_TKT010_06 activar MFA: contraseña errónea (401) es error de campo sin expulsar; QR, clave, confirmación y códigos', async () => {
    const m = await montar('/panel/cuenta', sesion(), (repo) => {
      repo.iniciarActivacionMfa.mockImplementationOnce(() =>
        Promise.reject(http(401, { code: 'credenciales_invalidas', title: 'x', status: 401 })),
      );
      repo.confirmarActivacionMfa.mockImplementationOnce(() =>
        Promise.reject(http(400, { code: 'validacion', title: 'x', status: 400, errors: { codigo: ['El código no es válido.'] } })),
      );
    });
    expect(existe(m, 'panel-navegacion')).toBe(true);
    expect(existe(m, 'cuenta-autorizacion')).toBe(true);
    await pulsar(m, 'mfa-empezar');
    await pulsar(m, 'mfa-reautenticar');
    expect(el(m, 'mfa-reautenticacion-error').textContent).toContain('Escribe tu contraseña actual.');
    escribir(m, '[data-testid="mfa-reautenticacion"]', 'equivocada');
    await pulsar(m, 'mfa-reautenticar');
    await vi.waitFor(() => expect(el(m, 'mfa-reautenticacion-error').textContent).toContain('La contraseña no es correcta.'));
    expect(m.router.url).toBe('/panel/cuenta');

    escribir(m, '[data-testid="mfa-reautenticacion"]', 'correcta');
    await pulsar(m, 'mfa-reautenticar');
    await vi.waitFor(() => expect(existe(m, 'mfa-paso-escanear')).toBe(true));
    const qr = el(m, 'codigo-qr');
    expect(qr.getAttribute('aria-label')).toBe('Código QR para configurar tu aplicación autenticadora');
    expect(qr.querySelector('path')?.getAttribute('d')).toMatch(/^M\d+ \d+h1v1h-1z/);
    expect(el(m, 'mfa-clave').textContent?.trim()).toBe('ABCD EFGH IJKL MNOP');

    await pulsar(m, 'mfa-continuar');
    escribir(m, '[data-testid="mfa-confirmar-codigo"]', 'abc');
    await pulsar(m, 'mfa-activar');
    expect(el(m, 'mfa-confirmar-error').textContent).toContain('6 dígitos');
    escribir(m, '[data-testid="mfa-confirmar-codigo"]', '000000');
    await pulsar(m, 'mfa-activar');
    await vi.waitFor(() => expect(el(m, 'mfa-confirmar-error').textContent).toContain('El código no es válido.'));
    m.repo.sesion.mockResolvedValue(sesion({ mfaActivo: true }));
    escribir(m, '[data-testid="mfa-confirmar-codigo"]', '123456');
    await pulsar(m, 'mfa-activar');
    await vi.waitFor(() => expect(existe(m, 'mfa-codigos')).toBe(true));
    expect(el(m, 'mfa-lista-codigos').textContent).toContain('AAAA-BBBB');
    expect(m.raiz().textContent).toContain('Paso 3 de 3');
    await pulsar(m, 'mfa-codigos-guardados');
    expect(existe(m, 'mfa-codigos')).toBe(false);
    expect(el(m, 'mfa-estado').textContent).toContain('activada');
  });

  it('AC_TKT010_06 desactivar MFA (con confirmación) y regenerar códigos; Admin: desactivar no disponible', async () => {
    const m = await montar('/panel/cuenta', sesion({ mfaActivo: true }));
    escribir(m, '[data-testid="mfa-regenerar-codigo"]', 'x');
    await pulsar(m, 'mfa-regenerar');
    expect(m.repo.regenerarCodigos).not.toHaveBeenCalled();
    escribir(m, '[data-testid="mfa-regenerar-codigo"]', '654321');
    await pulsar(m, 'mfa-regenerar');
    await vi.waitFor(() => expect(el(m, 'mfa-lista-codigos').textContent).toContain('EEEE-FFFF'));
    await pulsar(m, 'mfa-codigos-guardados');

    await pulsar(m, 'mfa-desactivar');
    expect(el<HTMLDialogElement>(m, 'mfa-dialogo-desactivar').hasAttribute('open')).toBe(true);
    await pulsar(m, 'mfa-confirmar-desactivar');
    expect(m.repo.desactivarMfa).not.toHaveBeenCalled();
    escribir(m, '[data-testid="mfa-desactivar-contrasena"]', 'correcta');
    escribir(m, '[data-testid="mfa-desactivar-codigo"]', '123456');
    m.repo.sesion.mockResolvedValue(sesion({ mfaActivo: false }));
    await pulsar(m, 'mfa-confirmar-desactivar');
    expect(m.repo.desactivarMfa).toHaveBeenCalledWith('correcta', '123456');
    await vi.waitFor(() => expect(existe(m, 'mfa-desactivado')).toBe(true));
    TestBed.resetTestingModule();

    const admin = await montar('/panel/cuenta', sesion({ rol: 'ADMINISTRADOR', mfaActivo: true, mfaObligatorio: true }));
    expect(existe(admin, 'mfa-desactivar')).toBe(false);
    expect(el(admin, 'mfa-obligatorio').textContent).toContain('obligatoria');
  });

  it('AC_TKT010_08 un Editor en una ruta de Administrador ve SCR-048 en la misma URL; el Administrador la ve', async () => {
    const editor = await montar('/panel/solo-admin', sesion());
    expect(TestBed.inject(Location).path()).toBe('/panel/solo-admin');
    expect(existe(editor, 'acceso-denegado')).toBe(true);
    expect(editor.raiz().textContent).toContain('No tienes permiso para ver esta sección');
    expect(editor.raiz().textContent).not.toContain('Zona de administración');
    TestBed.resetTestingModule();

    const admin = await montar('/panel/solo-admin', sesion({ rol: 'ADMINISTRADOR' }));
    expect(admin.raiz().textContent).toContain('Zona de administración');
    expect(existe(admin, 'acceso-denegado')).toBe(false);
  });

  it('AC_TKT010_09 Tablero con datos: alertas, conteos, últimos cambios y salud; sin accesos a secciones inexistentes', async () => {
    const m = await montar('/panel', sesion({ rol: 'ADMINISTRADOR' }));
    await vi.waitFor(() => expect(existe(m, 'tablero-conteos')).toBe(true));
    expect(el(m, 'tablero-conteo-DESTINO').textContent).toMatch(/Destinos\s*2\s*5\s*1\s*8/);
    expect(el(m, 'tablero-recientes').textContent).toContain('Patagonia');
    expect(el(m, 'tablero-alerta-responsable_sin_definir').textContent).toContain('Faltan los datos');
    expect(el(m, 'tablero-alerta-responsable_sin_definir').querySelector('a')).toBeNull();
    expect(existe(m, 'tablero-salud')).toBe(true);
    expect(existe(m, 'tablero-accesos')).toBe(false);
    expect(el(m, 'panel-nav-tablero').getAttribute('aria-current')).toBe('page');
    expect(el(m, 'panel-seccion-actual').textContent).toContain('Tablero');
  });

  it('AC_TKT010_09 Tablero vacío y con error (Reintentar)', async () => {
    const vacio = await montar('/panel', sesion(), undefined, () =>
      Promise.resolve({ conteos: [], recientes: [], alertas: [], saludEditorial: null }),
    );
    await vi.waitFor(() => expect(existe(vacio, 'tablero-vacio')).toBe(true));
    TestBed.resetTestingModule();

    let intentos = 0;
    const fallo = await montar('/panel', sesion(), undefined, () =>
      intentos++ === 0 ? Promise.reject(http(500)) : Promise.resolve(TABLERO),
    );
    await vi.waitFor(() => expect(existe(fallo, 'tablero-error')).toBe(true));
    await pulsar(fallo, 'estado-error-reintentar');
    await vi.waitFor(() => expect(existe(fallo, 'tablero-conteos')).toBe(true));
  });

  it('AC_TKT010_09 un 403 del tablero muestra SCR-048', async () => {
    const m = await montar('/panel', sesion(), undefined, () => Promise.reject(http(403, { code: 'permiso_denegado' })));
    await vi.waitFor(() => expect(existe(m, 'acceso-denegado')).toBe(true));
  });

  it('AC_TKT010_10 saltos al contenido y a la navegación, menú del cajón, noindex y 404 del panel', async () => {
    const m = await montar('/panel/no-existe', sesion());
    expect(existe(m, 'panel-no-encontrada')).toBe(true);
    expect(el(m, 'panel-saltar-contenido').textContent).toContain('Saltar al contenido');
    expect(el(m, 'panel-navegacion').getAttribute('aria-label')).toBe('Navegación del panel');
    expect(document.head.querySelector('meta[name="robots"]')?.getAttribute('content')).toBe('noindex, nofollow');

    // OBS-06 (QA ciclo 1): por debajo de lg, cajón modal (<dialog> + showModal).
    const menu = el(m, 'panel-menu');
    const cajon = el<HTMLDialogElement>(m, 'panel-cajon');
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(menu.getAttribute('aria-haspopup')).toBe('dialog');
    expect(cajon.getAttribute('aria-modal')).toBe('true');
    await pulsar(m, 'panel-menu');
    expect(menu.getAttribute('aria-expanded')).toBe('true');
    expect(cajon.hasAttribute('open')).toBe(true);
    expect(document.activeElement?.getAttribute('data-testid')).toBe('panel-cajon-nav-tablero');
    cajon.dispatchEvent(new Event('cancel', { cancelable: true }));
    await estable(m.harness);
    expect(cajon.hasAttribute('open')).toBe(false);
    expect(menu.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(menu);
    await pulsar(m, 'panel-menu');
    await pulsar(m, 'panel-cajon-cerrar');
    expect(cajon.hasAttribute('open')).toBe(false);

    // jsdom no tiene matchMedia: se comporta como escritorio (barra lateral fija).
    await pulsar(m, 'panel-saltar-navegacion');
    await vi.waitFor(() => expect(document.activeElement?.id).toBe('panel-navegacion'));
    await pulsar(m, 'panel-saltar-contenido');
    expect(document.activeElement?.id).toBe('contenido-principal');
    await pulsar(m, 'panel-menu');
    await pulsar(m, 'panel-cajon-nav-cuenta');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/cuenta'));
    expect(cajon.hasAttribute('open')).toBe(false);
  });

  it('cerrar sesión con error se informa sin salir; en SCR-030 con sesión parcial se ofrece cerrar sesión', async () => {
    const m = await montar('/panel', sesion(), (repo) =>
      repo.cerrarSesion.mockImplementationOnce(() => Promise.reject(http(500))),
    );
    await pulsar(m, 'panel-cerrar-sesion');
    await vi.waitFor(() => expect(m.raiz().querySelector('.error-cierre')).not.toBeNull());
    expect(m.router.url).toBe('/panel');
    TestBed.resetTestingModule();

    const parcial = await montar('/panel/autorizacion', sesion({ pasoPendiente: 'AUTORIZACION' }), (repo) =>
      repo.cerrarSesion.mockImplementationOnce(() => Promise.reject(http(500))),
    );
    await pulsar(parcial, 'panel-acceso-cerrar-sesion');
    await vi.waitFor(() => expect(parcial.raiz().querySelector('[role="alert"]')).not.toBeNull());
    await pulsar(parcial, 'panel-acceso-cerrar-sesion');
    await vi.waitFor(() => expect(parcial.router.url).toBe('/panel/acceso?motivo=cerrada'));
  });

  it('guards: sin sesión, la verificación y la autorización van a SCR-030; con otro paso, a su pantalla', async () => {
    const sin = await montar('/panel/autorizacion', null);
    expect(sin.router.url).toBe('/panel/acceso');
    TestBed.resetTestingModule();
    const mfa = await montar('/panel/autorizacion', sesion({ pasoPendiente: 'MFA' }));
    expect(mfa.router.url).toBe('/panel/acceso/verificacion');
    TestBed.resetTestingModule();
    const externo = await montar('/panel', null);
    expect(externo.router.url).toBe('/panel/acceso?siguiente=%2Fpanel');
  });
});

describe('AvisoExpiracion (AC_TKT010_11)', () => {
  function crear(estado: { aviso: boolean; expirada: boolean }) {
    const falso = {
      avisoVisible: signal(estado.aviso),
      expirada: signal(estado.expirada),
      cuentaAtras: signal('1:45'),
      anuncio: signal('Por inactividad, tu sesión se cerrará en 1:45.'),
      renovando: signal(false),
      seguirConectado: vi.fn().mockResolvedValue(null),
    };
    TestBed.configureTestingModule({ providers: [{ provide: ExpiracionSesionStore, useValue: falso }] });
    const fixture = TestBed.createComponent(AvisoExpiracion);
    fixture.detectChanges();
    return { fixture, falso, raiz: fixture.nativeElement as HTMLElement };
  }

  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT010_11 alertdialog modal con cuenta atrás; «Seguir conectado» renueva y «Cerrar sesión» emite', async () => {
    const { fixture, falso, raiz } = crear({ aviso: true, expirada: false });
    await fixture.whenStable();
    const dialogo = raiz.querySelector('dialog') as HTMLDialogElement;
    expect(dialogo.getAttribute('role')).toBe('alertdialog');
    expect(dialogo.hasAttribute('open')).toBe(true);
    expect(raiz.querySelector('[data-testid="aviso-expiracion-cuenta"]')?.textContent).toBe('1:45');
    expect(raiz.textContent).toContain('Tu sesión está por expirar');
    (raiz.querySelector('[data-testid="aviso-expiracion-seguir"]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(falso.seguirConectado).toHaveBeenCalled();
    const cerrar = vi.fn();
    fixture.componentInstance.cerrarSesion.subscribe(cerrar);
    (raiz.querySelector('[data-testid="aviso-expiracion-cerrar"]') as HTMLButtonElement).click();
    expect(cerrar).toHaveBeenCalled();
    falso.avisoVisible.set(false);
    await fixture.whenStable();
    expect(dialogo.hasAttribute('open')).toBe(false);
  });

  it('AC_TKT010_11 al expirar ofrece volver a entrar; un fallo al renovar se muestra', async () => {
    const { fixture, falso, raiz } = crear({ aviso: true, expirada: false });
    falso.seguirConectado.mockResolvedValue({ mensaje: 'Sin conexión.' });
    (raiz.querySelector('[data-testid="aviso-expiracion-seguir"]') as HTMLButtonElement).click();
    await vi.waitFor(async () => {
      await fixture.whenStable();
      expect(raiz.textContent).toContain('Sin conexión.');
    });
    falso.avisoVisible.set(false);
    falso.expirada.set(true);
    await fixture.whenStable();
    expect(raiz.textContent).toContain('Tu sesión expiró');
    const volver = vi.fn();
    fixture.componentInstance.volverAEntrar.subscribe(volver);
    (raiz.querySelector('[data-testid="aviso-expiracion-entrar"]') as HTMLButtonElement).click();
    expect(volver).toHaveBeenCalled();
  });
});

describe('CodigoQr', () => {
  it('AC_TKT010_06 genera el QR en el navegador como SVG accesible (sin red)', async () => {
    const fixture = TestBed.createComponent(CodigoQr);
    fixture.componentRef.setInput('contenido', 'otpauth://totp/Br%C3%BAjula%20Salvaje:editora?secret=ABCDEFGHIJKLMNOP&issuer=Br%C3%BAjula%20Salvaje');
    await fixture.whenStable();
    const svg = (fixture.nativeElement as HTMLElement).querySelector('svg') as SVGElement;
    expect(svg.getAttribute('role')).toBe('img');
    const [, , ancho, alto] = (svg.getAttribute('viewBox') ?? '').split(' ').map(Number);
    expect(ancho).toBe(alto);
    // Versión ≥ 1 (21 módulos) + zona silenciosa de 4 módulos por lado.
    expect(ancho).toBeGreaterThanOrEqual(29);
    expect((ancho - 8 - 17) % 4).toBe(0);
  });
});
