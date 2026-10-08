import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';

import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { PanelTableroRepositorio } from '../data/panel-tablero.repositorio';
import { AutorizacionTratamiento, SesionPanel, TableroPanel } from '../domain/modelos';
import { AutorizacionStore } from './autorizacion.store';
import { CuentaStore } from './cuenta.store';
import { ExpiracionSesionStore } from './expiracion-sesion.store';
import { SesionPanelStore } from './sesion-panel.store';
import { TableroStore } from './tablero.store';

const AHORA = new Date('2026-09-30T10:00:00Z').getTime();

export function sesion(parcial: Partial<SesionPanel> = {}): SesionPanel {
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

function http(status: number, cuerpo: unknown = { code: 'x' }): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: cuerpo });
}

const AUTORIZACION: AutorizacionTratamiento = {
  versionPolitica: '1.0',
  vigenteDesde: '2026-01-01',
  resumenFinalidad: 'Finalidad',
  urlPolitica: '/politica-de-tratamiento-de-datos',
  otorgadaEn: null,
  versionOtorgada: null,
};

type RepoFalso = Record<keyof PanelAuthRepositorio, ReturnType<typeof vi.fn>>;

function repoFalso(): RepoFalso {
  return {
    asegurarCsrf: vi.fn().mockResolvedValue(undefined),
    iniciarSesion: vi.fn().mockResolvedValue(sesion()),
    verificarMfa: vi.fn().mockResolvedValue(sesion()),
    cerrarSesion: vi.fn().mockResolvedValue(undefined),
    sesion: vi.fn().mockResolvedValue(sesion()),
    renovarSesion: vi.fn().mockResolvedValue(sesion()),
    cambiarContrasena: vi.fn().mockResolvedValue(sesion()),
    autorizacion: vi.fn().mockResolvedValue(AUTORIZACION),
    registrarAutorizacion: vi.fn().mockResolvedValue(sesion()),
    iniciarActivacionMfa: vi.fn().mockResolvedValue({ otpauthUri: 'otpauth://totp/x', claveSecreta: 'ABCDEFGHIJKLMNOP' }),
    confirmarActivacionMfa: vi.fn().mockResolvedValue(['AAAA-BBBB']),
    desactivarMfa: vi.fn().mockResolvedValue(undefined),
    regenerarCodigos: vi.fn().mockResolvedValue(['CCCC-DDDD']),
  };
}

function configurar(repo: RepoFalso, extra: unknown[] = []): void {
  TestBed.configureTestingModule({
    providers: [{ provide: PanelAuthRepositorio, useValue: repo }, ...(extra as never[])],
  });
}

describe('SesionPanelStore (STATE-004)', () => {
  it('AC_TKT010_01 login correcto sin pasos → sesión y destino al Tablero; cierre la olvida', async () => {
    const repo = repoFalso();
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    expect(store.rutaSiguiente()).toBe('/panel/acceso');
    expect(await store.iniciarSesion('editora.uno', 'secreto', null)).toBeNull();
    expect(repo.asegurarCsrf).toHaveBeenCalled();
    expect(store.autenticada()).toBe(true);
    expect(store.rutaSiguiente()).toBe('/panel');
    expect(store.secciones().map((s) => s.id)).toEqual([
      'tablero',
      'contenido-destinos',
      'contenido-itinerarios',
      'contenido-guias',
      'contenido-tipos-aventura',
      'contenido-colecciones',
      'contenido-glosario',
      'contenido-paginas',
      'medios',
      'cuenta',
    ]);
    expect(await store.cerrarSesion()).toBeNull();
    expect(store.sesion()).toBeNull();
    expect(store.secciones()).toEqual([]);
  });

  it('AC_TKT010_01 FALLO-01: un 403 csrf_invalido en el login se reintenta una sola vez', async () => {
    const repo = repoFalso();
    repo.iniciarSesion
      .mockImplementationOnce(() => Promise.reject(http(403, { code: 'csrf_invalido' })))
      .mockResolvedValueOnce(sesion());
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    expect(await store.iniciarSesion('x', 'y', null)).toBeNull();
    expect(repo.iniciarSesion).toHaveBeenCalledTimes(2);
    expect(repo.asegurarCsrf).toHaveBeenCalledTimes(2);
    expect(store.autenticada()).toBe(true);
  });

  it('AC_TKT010_01 FALLO-01: no oculta otros 403 ni reintenta más de una vez', async () => {
    const repo = repoFalso();
    repo.iniciarSesion.mockImplementation(() => Promise.reject(http(403, { code: 'permiso_denegado' })));
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    expect((await store.iniciarSesion('x', 'y', null))?.codigo).toBe('permiso_denegado');
    expect(repo.iniciarSesion).toHaveBeenCalledTimes(1);
    repo.iniciarSesion.mockImplementation(() => Promise.reject(http(403, { code: 'csrf_invalido' })));
    expect((await store.iniciarSesion('x', 'y', null))?.codigo).toBe('csrf_invalido');
    expect(repo.iniciarSesion).toHaveBeenCalledTimes(3);
  });

  it('AC_TKT010_02 login fallido → ErrorApi y sin sesión; fallo del CSRF corta el login', async () => {
    const repo = repoFalso();
    repo.iniciarSesion.mockRejectedValue(http(401, { code: 'credenciales_invalidas' }));
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    expect((await store.iniciarSesion('x', 'y', null))?.codigo).toBe('credenciales_invalidas');
    expect(store.sesion()).toBeNull();
    repo.asegurarCsrf.mockRejectedValue(http(429, { code: 'limite_tasa' }));
    expect((await store.iniciarSesion('x', 'y', null))?.codigo).toBe('limite_tasa');
    expect(repo.iniciarSesion).toHaveBeenCalledTimes(1);
  });

  it('AC_TKT010_03 con MFA el siguiente paso es SCR-031 y tras verificar va al destino', async () => {
    const repo = repoFalso();
    repo.iniciarSesion.mockResolvedValue(sesion({ pasoPendiente: 'MFA', redireccion: '/panel/cuenta' }));
    repo.verificarMfa.mockResolvedValue(sesion({ redireccion: '/panel/cuenta' }));
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    await store.iniciarSesion('x', 'y', '/panel/cuenta');
    expect(store.rutaSiguiente()).toBe('/panel/acceso/verificacion');
    expect(await store.verificarMfa('123456')).toBeNull();
    expect(store.rutaSiguiente()).toBe('/panel/cuenta');
  });

  it('AC_TKT010_05 «No autorizo» olvida la sesión; «Autorizo» la actualiza', async () => {
    const repo = repoFalso();
    repo.registrarAutorizacion.mockResolvedValueOnce(null);
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    await store.iniciarSesion('x', 'y', null);
    expect(await store.registrarAutorizacion('NO_AUTORIZO', '1.0')).toBeNull();
    expect(store.sesion()).toBeNull();
    expect(await store.registrarAutorizacion('AUTORIZO', '1.0')).toBeNull();
    expect(store.sesion()).not.toBeNull();
  });

  it('cargar() sin sesión (401) → null; asegurar() reutiliza lo conocido', async () => {
    const repo = repoFalso();
    repo.sesion.mockRejectedValueOnce(http(401));
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    expect(store.cargada()).toBe(false);
    expect(await store.asegurar()).toBeNull();
    expect(store.cargada()).toBe(true);
    expect(await store.asegurar()).toBeNull();
    expect(repo.sesion).toHaveBeenCalledTimes(1);
    expect(await store.cargar()).not.toBeNull();
    expect(store.rol()).toBe('EDITOR');
    expect(store.pasoPendiente()).toBe('NINGUNO');
  });

  it('cerrarSesion(): un 401 se trata como cerrada; otro error se informa y se conserva', async () => {
    const repo = repoFalso();
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    await store.cargar();
    repo.cerrarSesion.mockRejectedValueOnce(http(500));
    expect((await store.cerrarSesion())?.categoria).toBe('servidor');
    expect(store.sesion()).not.toBeNull();
    repo.cerrarSesion.mockRejectedValueOnce(http(401));
    expect(await store.cerrarSesion()).toBeNull();
    expect(store.sesion()).toBeNull();
  });

  it('AC_TKT010_04 cambiarContrasena() y AC_TKT010_11 renovar() actualizan la sesión', async () => {
    const repo = repoFalso();
    repo.cambiarContrasena.mockResolvedValue(sesion({ pasoPendiente: 'AUTORIZACION' }));
    configurar(repo);
    const store = TestBed.inject(SesionPanelStore);
    expect(await store.cambiarContrasena('a', 'b')).toBeNull();
    expect(store.rutaSiguiente()).toBe('/panel/autorizacion');
    expect(await store.renovar()).toBeNull();
    expect(store.pasoPendiente()).toBe('NINGUNO');
  });
});

describe('ExpiracionSesionStore (AC-109)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(AHORA);
  });
  afterEach(() => vi.useRealTimers());

  async function crear(expiraEnSegundos: number, repo = repoFalso()) {
    const expira = new Date(AHORA + expiraEnSegundos * 1000);
    repo.sesion.mockResolvedValue(sesion({ expiraInactividadEn: expira }));
    configurar(repo, [ExpiracionSesionStore]);
    await TestBed.inject(SesionPanelStore).cargar();
    return { store: TestBed.inject(ExpiracionSesionStore), repo };
  }

  it('AC_TKT010_11 fuera de la ventana no avisa ni consulta al servidor', async () => {
    const { store, repo } = await crear(30 * 60);
    store.tick(AHORA);
    expect(store.avisoVisible()).toBe(false);
    expect(repo.sesion).toHaveBeenCalledTimes(1);
  });

  it('AC_TKT010_11 a 2 min contrasta con el servidor, avisa con cuenta atrás y anuncia al abrir y a los 30 s', async () => {
    const { store, repo } = await crear(100);
    store.tick(AHORA);
    await vi.waitFor(() => expect(store.avisoVisible()).toBe(true));
    expect(repo.sesion).toHaveBeenCalledTimes(2);
    expect(store.cuentaAtras()).toBe('1:40');
    expect(store.anuncio()).toBe('Por inactividad, tu sesión se cerrará en 1:40.');
    store.tick(AHORA + 10_000);
    expect(store.anuncio()).toBe('Por inactividad, tu sesión se cerrará en 1:40.');
    store.tick(AHORA + 70_000);
    expect(store.anuncio()).toBe('Por inactividad, tu sesión se cerrará en 0:30.');
  });

  it('AC_TKT010_11 «Seguir conectado» renueva y cierra el aviso', async () => {
    const { store, repo } = await crear(100);
    store.tick(AHORA);
    await vi.waitFor(() => expect(store.avisoVisible()).toBe(true));
    repo.renovarSesion.mockResolvedValue(sesion({ expiraInactividadEn: new Date(AHORA + 30 * 60_000) }));
    expect(await store.seguirConectado()).toBeNull();
    expect(store.avisoVisible()).toBe(false);
    expect(store.renovando()).toBe(false);
    expect(store.anuncio()).toBeNull();
  });

  it('AC_TKT010_11 si otra petición ya renovó la inactividad, no se avisa', async () => {
    const repo = repoFalso();
    const { store } = await crear(100, repo);
    repo.sesion.mockResolvedValue(sesion({ expiraInactividadEn: new Date(AHORA + 29 * 60_000) }));
    store.tick(AHORA);
    await vi.waitFor(() => expect(repo.sesion).toHaveBeenCalledTimes(2));
    await Promise.resolve();
    expect(store.avisoVisible()).toBe(false);
  });

  it('AC_TKT010_11 al llegar a 0 la sesión queda expirada; un fallo al renovar se informa', async () => {
    const { store, repo } = await crear(100);
    store.tick(AHORA);
    await vi.waitFor(() => expect(store.avisoVisible()).toBe(true));
    store.tick(AHORA + 101_000);
    expect(store.expirada()).toBe(true);
    expect(store.avisoVisible()).toBe(false);
    repo.renovarSesion.mockRejectedValue(http(401));
    expect((await store.seguirConectado())?.categoria).toBe('no_autenticado');
  });

  it('el reloj del navegador avanza solo y se detiene al destruirse', async () => {
    const { store } = await crear(30 * 60);
    vi.advanceTimersByTime(3_000);
    expect(store.restantes()).toBe(30 * 60 - 3);
    TestBed.resetTestingModule();
  });

  it('sin sesión no hay cuenta atrás', () => {
    configurar(repoFalso(), [ExpiracionSesionStore]);
    const store = TestBed.inject(ExpiracionSesionStore);
    store.tick(AHORA);
    expect(store.restantes()).toBeNull();
    expect(store.avisoVisible()).toBe(false);
  });
});

describe('TableroStore (SCR-034)', () => {
  const TABLERO: TableroPanel = {
    conteos: [{ tipo: 'DESTINO', borrador: 1, publicado: 0, retirado: 0 }],
    recientes: [],
    alertas: [
      { codigo: 'responsable_sin_definir', mensaje: 'Faltan datos.', enlace: '/panel/configuracion' },
      { codigo: 'destacado_retirado', mensaje: 'Revisa.', enlace: '/panel/cuenta' },
    ],
    saludEditorial: null,
  };

  function crear(tablero: () => Promise<TableroPanel>) {
    const repo = repoFalso();
    TestBed.configureTestingModule({
      providers: [
        TableroStore,
        { provide: PanelAuthRepositorio, useValue: repo },
        { provide: PanelTableroRepositorio, useValue: { tablero: vi.fn().mockImplementation(tablero) } },
      ],
    });
    return { store: TestBed.inject(TableroStore), sesion: TestBed.inject(SesionPanelStore) };
  }

  it('AC_TKT010_09 datos reales del tablero; alertas sin enlaces a secciones inexistentes', async () => {
    const { store, sesion: sesionStore } = crear(() => Promise.resolve(TABLERO));
    await sesionStore.cargar();
    expect(store.cargando()).toBe(true);
    await vi.waitFor(() => expect(store.tablero()).not.toBeNull());
    expect(store.vacio()).toBe(false);
    expect(store.mostrarSalud()).toBe(false);
    expect(store.alertas().map((a) => a.enlace)).toEqual([null, '/panel/cuenta']);
    expect(store.accesosRapidos().map((a) => a.id)).toEqual(['nuevo-destino', 'subir-medios']);
    expect(store.nombreVisible()).toBe('Editora Uno');
    store.recargar();
  });

  it('AC_TKT010_09 estado vacío y estado de error; 403 → SCR-048', async () => {
    const vacio = crear(() => Promise.resolve({ ...TABLERO, conteos: [], alertas: [] }));
    await vi.waitFor(() => expect(vacio.store.vacio()).toBe(true));
    expect(vacio.store.alertas()).toEqual([]);
    TestBed.resetTestingModule();

    const fallo = crear(() => Promise.reject(http(500)));
    await vi.waitFor(() => expect(fallo.store.error()).not.toBeNull());
    expect(fallo.store.accesoDenegado()).toBe(false);
    TestBed.resetTestingModule();

    const prohibido = crear(() => Promise.reject(http(403, { code: 'permiso_denegado' })));
    await vi.waitFor(() => expect(prohibido.store.accesoDenegado()).toBe(true));
  });
});

describe('AutorizacionStore (SCR-033)', () => {
  it('AC_TKT010_05 decide con la versión vigente; 409 recarga la política', async () => {
    const repo = repoFalso();
    configurar(repo, [AutorizacionStore]);
    const store = TestBed.inject(AutorizacionStore);
    expect(await store.decidir('AUTORIZO')).toBeNull();
    expect(repo.registrarAutorizacion).not.toHaveBeenCalled();
    await vi.waitFor(() => expect(store.autorizacion()).not.toBeNull());
    expect(await store.decidir('AUTORIZO')).toBeNull();
    expect(repo.registrarAutorizacion).toHaveBeenCalledWith('AUTORIZO', '1.0');
    repo.registrarAutorizacion.mockRejectedValueOnce(http(409, { code: 'conflicto_version' }));
    expect((await store.decidir('AUTORIZO'))?.categoria).toBe('conflicto');
    await vi.waitFor(() => expect(repo.autorizacion).toHaveBeenCalledTimes(2));
    expect(store.enviando()).toBeNull();
  });

  it('error de carga con Reintentar', async () => {
    const repo = repoFalso();
    repo.autorizacion.mockRejectedValueOnce(http(500));
    configurar(repo, [AutorizacionStore]);
    const store = TestBed.inject(AutorizacionStore);
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(store.autorizacion()).not.toBeNull());
  });
});

describe('CuentaStore (SCR-032)', () => {
  async function crear(parcial: Partial<SesionPanel> = {}, repo = repoFalso()) {
    repo.sesion.mockResolvedValue(sesion(parcial));
    configurar(repo, [CuentaStore]);
    await TestBed.inject(SesionPanelStore).cargar();
    return { store: TestBed.inject(CuentaStore), repo };
  }

  it('AC_TKT010_04 modo obligatorio de cambio de contraseña: solo la sección Contraseña', async () => {
    const { store } = await crear({ pasoPendiente: 'CAMBIO_CREDENCIAL' });
    expect(store.modoObligatorio()).toBe(true);
    expect(store.mostrarContrasena()).toBe(true);
    expect(store.mostrarMfa()).toBe(false);
    expect(store.mostrarAutorizacion()).toBe(false);
    expect(store.validarContrasena({ actual: 'a', nueva: 'corta', confirmacion: 'corta' })).toHaveProperty(
      'contrasena_nueva',
    );
    expect(await store.cambiarContrasena('a', 'una frase larga y segura')).toBeNull();
    expect(store.contrasenaCambiada()).toBe(true);
  });

  it('AC_TKT010_04 contraseña débil rechazada por el servidor → ErrorApi con el campo', async () => {
    const repo = repoFalso();
    repo.cambiarContrasena.mockRejectedValue(
      http(400, { code: 'validacion', errors: { contrasena_nueva: ['Elige una contraseña menos común.'] } }),
    );
    const { store } = await crear({}, repo);
    const error = await store.cambiarContrasena('a', 'contraseña123');
    expect(error?.campos['contrasena_nueva']).toEqual(['Elige una contraseña menos común.']);
    expect(store.contrasenaCambiada()).toBe(false);
  });

  it('AC_TKT010_06 asistente: reautenticar → escanear (1/3) → confirmar (2/3) → códigos (3/3)', async () => {
    const { store, repo } = await crear();
    expect(store.modoObligatorio()).toBe(false);
    expect(store.numeroPasoMfa()).toBeNull();
    store.empezarActivacionMfa();
    expect(store.pasoMfa()).toBe('reautenticar');
    store.continuarAConfirmacion();
    expect(store.pasoMfa()).toBe('reautenticar');
    expect(await store.iniciarActivacionMfa('secreto')).toBeNull();
    expect(store.numeroPasoMfa()).toBe(1);
    store.continuarAConfirmacion();
    expect(store.numeroPasoMfa()).toBe(2);
    store.volverAEscanear();
    expect(store.pasoMfa()).toBe('escanear');
    store.continuarAConfirmacion();
    repo.sesion.mockResolvedValue(sesion({ mfaActivo: true }));
    expect(await store.confirmarActivacionMfa('123456')).toBeNull();
    expect(store.numeroPasoMfa()).toBe(3);
    expect(store.codigos()).toEqual(['AAAA-BBBB']);
    expect(store.mfaActivo()).toBe(true);
    expect(store.puedeDesactivarMfa()).toBe(true);
    store.terminarCodigos();
    expect(store.codigos()).toBeNull();
  });

  it('AC_TKT010_06 DEC-AUTO-215: credenciales_invalidas vuelve como ErrorApi sin cambiar de paso', async () => {
    const repo = repoFalso();
    repo.iniciarActivacionMfa.mockRejectedValue(http(401, { code: 'credenciales_invalidas' }));
    const { store } = await crear({}, repo);
    store.empezarActivacionMfa();
    expect((await store.iniciarActivacionMfa('mal'))?.codigo).toBe('credenciales_invalidas');
    expect(store.pasoMfa()).toBe('reautenticar');
    store.cancelarActivacionMfa();
    expect(store.pasoMfa()).toBeNull();
    store.volverAEscanear();
    expect(store.pasoMfa()).toBeNull();
  });

  it('AC_TKT010_06 desactivar y regenerar; el Administrador no puede desactivar', async () => {
    const { store, repo } = await crear({ mfaActivo: true });
    expect(await store.regenerarCodigos('123456')).toBeNull();
    expect(store.codigos()).toEqual(['CCCC-DDDD']);
    repo.sesion.mockResolvedValue(sesion({ mfaActivo: false }));
    expect(await store.desactivarMfa('secreto', '123456')).toBeNull();
    expect(store.mfaDesactivado()).toBe(true);
    expect(store.mfaActivo()).toBe(false);
    repo.desactivarMfa.mockRejectedValue(http(400, { code: 'validacion', errors: { codigo: ['El código no es válido.'] } }));
    expect((await store.desactivarMfa('secreto', '000000'))?.campos['codigo']).toBeDefined();
    TestBed.resetTestingModule();
    const admin = await crear({ rol: 'ADMINISTRADOR', mfaActivo: true, mfaObligatorio: true });
    expect(admin.store.puedeDesactivarMfa()).toBe(false);
  });

  it('AC_TKT010_04 Admin sin MFA: tras la contraseña el modo pasa a configurar MFA', async () => {
    const repo = repoFalso();
    const { store } = await crear({ pasoPendiente: 'CAMBIO_CREDENCIAL', rol: 'ADMINISTRADOR' }, repo);
    repo.cambiarContrasena.mockResolvedValue(sesion({ pasoPendiente: 'CONFIGURAR_MFA', rol: 'ADMINISTRADOR' }));
    await store.cambiarContrasena('a', 'una frase larga y segura');
    expect(store.rutaSiguiente()).toBe('/panel/cuenta');
    store.refrescarModo();
    expect(store.mostrarContrasena()).toBe(false);
    expect(store.mostrarMfa()).toBe(true);
    expect(store.modoObligatorio()).toBe(true);
  });
});
