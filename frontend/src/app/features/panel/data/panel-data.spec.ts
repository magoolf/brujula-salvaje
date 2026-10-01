import { HttpErrorResponse, HttpHeaders, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { SesionEstado } from '../../../api/models/sesion-estado';
import { Tablero } from '../../../api/models/tablero';
import { normalizarError } from '../../../core/http/normalizar-error';
import { anotarEspera, leerRetryAfter } from './espera';
import { ESPERA_COOKIE_MS, PanelAuthRepositorio } from './panel-auth.repositorio';
import { PanelTableroRepositorio } from './panel-tablero.repositorio';
import { mapAutorizacion, mapTablero } from './panel.mapper';

const BASE = '/api/v1/panel';

export const SESION_DTO: SesionEstado = {
  usuario: 'editora.uno',
  nombre_visible: 'Editora Uno',
  rol: 'EDITOR',
  paso_pendiente: 'NINGUNO',
  mfa_activo: false,
  mfa_obligatorio: false,
  expira_inactividad_en: '2026-09-30T10:30:00Z',
  expira_absoluta_en: '2026-09-30T22:00:00Z',
  redireccion: '/panel',
};

const TABLERO_DTO: Tablero = {
  conteos: [{ tipo: 'DESTINO', borrador: 1, publicado: 2, retirado: 0 }],
  recientes: [
    {
      id: 7,
      tipo: 'DESTINO',
      titulo: 'Patagonia',
      estado_editorial: 'PUBLICADO',
      publicado: true,
      url_publica: '/destinos/patagonia',
      actualizado_en: '2026-09-29T08:00:00Z',
      actualizado_por: { id: 1, etiqueta: 'editora.uno' },
      version: 3,
    },
    {
      id: 8,
      tipo: 'GUIA',
      titulo: 'Borrador',
      estado_editorial: 'BORRADOR',
      publicado: false,
      url_publica: null,
      actualizado_en: '2026-09-29T09:00:00Z',
      actualizado_por: { id: null, etiqueta: 'sistema' },
      version: 1,
    },
  ],
  alertas: [{ code: 'responsable_sin_definir', mensaje: 'Faltan datos.', enlace: '/panel/configuracion' }],
  salud_editorial: {
    revisiones_antiguas: [{ id: 1, tipo: 'DESTINO', titulo: 'Viejo', estado_editorial: 'PUBLICADO' }],
    medios_sin_uso: 2,
  },
};

describe('panel.mapper', () => {
  it('AC_TKT010_09 traduce el tablero (sin DTO fuera de data/)', () => {
    const tablero = mapTablero(TABLERO_DTO);
    expect(tablero.conteos[0]).toEqual({ tipo: 'DESTINO', borrador: 1, publicado: 2, retirado: 0 });
    expect(tablero.recientes[0].urlPublica).toBe('/destinos/patagonia');
    expect(tablero.recientes[0].actualizadoPor).toBe('editora.uno');
    expect(tablero.recientes[1].urlPublica).toBeNull();
    expect(tablero.alertas[0]).toEqual({
      codigo: 'responsable_sin_definir',
      mensaje: 'Faltan datos.',
      enlace: '/panel/configuracion',
    });
    expect(tablero.saludEditorial).toEqual({
      revisionesAntiguas: [{ id: 1, tipo: 'DESTINO', titulo: 'Viejo' }],
      mediosPendientesMetadatos: 0,
      mediosSinUso: 2,
      coleccionesBajoMinimo: [],
      contenidosConPocosRelacionados: [],
    });
    expect(mapTablero({ ...TABLERO_DTO, salud_editorial: null, alertas: [{ code: 'destacado_retirado', mensaje: 'x' }] })).toMatchObject({
      saludEditorial: null,
      alertas: [{ enlace: null }],
    });
  });

  it('traduce la autorización (sin otorgar todavía)', () => {
    expect(
      mapAutorizacion({
        version_politica: '1.0',
        vigente_desde: '2026-01-01',
        resumen_finalidad: 'Finalidad',
        url_politica: '/politica-de-tratamiento-de-datos',
      }),
    ).toEqual({
      versionPolitica: '1.0',
      vigenteDesde: '2026-01-01',
      resumenFinalidad: 'Finalidad',
      urlPolitica: '/politica-de-tratamiento-de-datos',
      otorgadaEn: null,
      versionOtorgada: null,
    });
  });
});

describe('espera (Retry-After → ErrorApi.extra)', () => {
  it('AC_TKT010_02 copia Retry-After al Problem para el mensaje de bloqueo', () => {
    const error = new HttpErrorResponse({
      status: 429,
      error: { code: 'acceso_bloqueado_temporalmente', title: 'Bloqueado', status: 429 },
      headers: new HttpHeaders({ 'Retry-After': '900' }),
    });
    const normalizado = normalizarError(anotarEspera(error));
    expect(normalizado.codigo).toBe('acceso_bloqueado_temporalmente');
    expect(normalizado.extra['reintentar_en_segundos']).toBe(900);
  });

  it('acepta cuerpos en texto JSON y deja intactos los errores sin cabecera', () => {
    const texto = new HttpErrorResponse({
      status: 429,
      error: '{"code":"limite_tasa","title":"x","status":429}',
      headers: new HttpHeaders({ 'Retry-After': '30' }),
    });
    expect(normalizarError(anotarEspera(texto)).extra['reintentar_en_segundos']).toBe(30);
    const sinCabecera = new HttpErrorResponse({ status: 401, error: { code: 'x' } });
    expect(anotarEspera(sinCabecera)).toBe(sinCabecera);
    expect(anotarEspera('otro')).toBe('otro');
    expect(anotarEspera({ headers: 1 })).toEqual({ headers: 1 });
    const malo = new HttpErrorResponse({ status: 429, error: 'no-json', headers: new HttpHeaders({ 'Retry-After': '5' }) });
    expect(normalizarError(anotarEspera(malo)).extra).toEqual({});
  });

  it('Retry-After solo en segundos enteros positivos', () => {
    expect(leerRetryAfter('120')).toBe(120);
    expect(leerRetryAfter(' 7 ')).toBe(7);
    expect(leerRetryAfter('0')).toBeNull();
    expect(leerRetryAfter('Wed, 21 Oct 2026 07:28:00 GMT')).toBeNull();
    expect(leerRetryAfter(null)).toBeNull();
  });
});

describe('PanelAuthRepositorio y PanelTableroRepositorio', () => {
  let http: HttpTestingController;
  let repo: PanelAuthRepositorio;

  beforeEach(() => {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(PanelAuthRepositorio);
  });

  afterEach(() => http.verify());

  it('AC_TKT010_01 pide la cookie CSRF solo si no existe', async () => {
    const promesa = repo.asegurarCsrf();
    http.expectOne(`${BASE}/auth/csrf`).flush(null, { status: 204, statusText: 'No Content' });
    document.cookie = 'csrftoken=abc; path=/';
    await promesa;
    await repo.asegurarCsrf();
    http.expectNone(`${BASE}/auth/csrf`);
  });

  it('AC_TKT010_01 FALLO-01: tras el 204 espera a que la cookie sea legible antes de seguir', async () => {
    let resuelta = false;
    const promesa = repo.asegurarCsrf().then(() => (resuelta = true));
    http.expectOne(`${BASE}/auth/csrf`).flush(null, { status: 204, statusText: 'No Content' });
    // Simula WebKit: el Set-Cookie se refleja en document.cookie unos milisegundos después.
    await new Promise((r) => setTimeout(r, 60));
    expect(resuelta).toBe(false);
    document.cookie = 'csrftoken=tardia; path=/';
    await promesa;
    expect(resuelta).toBe(true);
  });

  it('AC_TKT010_01 FALLO-01: la espera está acotada si la cookie nunca llega', async () => {
    vi.useFakeTimers();
    try {
      let resuelta = false;
      const promesa = repo.asegurarCsrf().then(() => (resuelta = true));
      http.expectOne(`${BASE}/auth/csrf`).flush(null, { status: 204, statusText: 'No Content' });
      await vi.advanceTimersByTimeAsync(ESPERA_COOKIE_MS - 100);
      expect(resuelta).toBe(false);
      await vi.advanceTimersByTimeAsync(200);
      await promesa;
      expect(resuelta).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('AC_TKT010_01 login envía usuario, contraseña y siguiente y devuelve la sesión del dominio', async () => {
    const promesa = repo.iniciarSesion('editora.uno', 'secreto', '/panel/cuenta');
    const peticion = http.expectOne(`${BASE}/auth/login`);
    expect(peticion.request.body).toEqual({ usuario: 'editora.uno', contrasena: 'secreto', siguiente: '/panel/cuenta' });
    peticion.flush(SESION_DTO);
    const sesion = await promesa;
    expect(sesion.nombreVisible).toBe('Editora Uno');
    expect(sesion.expiraInactividadEn.toISOString()).toBe('2026-09-30T10:30:00.000Z');
  });

  it('AC_TKT010_02 un 429 de login conserva el Retry-After', async () => {
    const promesa = repo.iniciarSesion('x', 'y', null);
    http
      .expectOne(`${BASE}/auth/login`)
      .flush({ code: 'acceso_bloqueado_temporalmente' }, { status: 429, statusText: 'Too Many', headers: { 'Retry-After': '60' } });
    const error = await promesa.catch((e: unknown) => normalizarError(e));
    expect(error).toMatchObject({ extra: { reintentar_en_segundos: 60 } });
  });

  it('AC_TKT010_03/04/05/11 operaciones de sesión, contraseña, autorización y MFA', async () => {
    const verificar = repo.verificarMfa('123456');
    http.expectOne(`${BASE}/auth/mfa/verificar`).flush(SESION_DTO);
    expect((await verificar).usuario).toBe('editora.uno');

    const sesion = repo.sesion();
    http.expectOne(`${BASE}/auth/sesion`).flush(SESION_DTO);
    expect((await sesion).rol).toBe('EDITOR');

    const renovar = repo.renovarSesion();
    http.expectOne(`${BASE}/auth/sesion/renovar`).flush(SESION_DTO);
    await renovar;

    const cambiar = repo.cambiarContrasena('a', 'b');
    const peticionCambio = http.expectOne(`${BASE}/auth/contrasena`);
    expect(peticionCambio.request.body).toEqual({ contrasena_actual: 'a', contrasena_nueva: 'b' });
    peticionCambio.flush(SESION_DTO);
    await cambiar;

    const autorizacion = repo.autorizacion();
    http.expectOne(`${BASE}/auth/autorizacion`).flush({
      version_politica: '1.0',
      vigente_desde: '2026-01-01',
      resumen_finalidad: 'x',
      url_politica: '/politica-de-tratamiento-de-datos',
      otorgada_en: '2026-02-01T00:00:00Z',
      version_otorgada: '1.0',
    });
    expect((await autorizacion).otorgadaEn).toBeInstanceOf(Date);

    const autorizo = repo.registrarAutorizacion('AUTORIZO', '1.0');
    http.expectOne(`${BASE}/auth/autorizacion`).flush(SESION_DTO);
    expect(await autorizo).not.toBeNull();

    const noAutorizo = repo.registrarAutorizacion('NO_AUTORIZO', '1.0');
    http.expectOne(`${BASE}/auth/autorizacion`).flush(null, { status: 204, statusText: 'No Content' });
    expect(await noAutorizo).toBeNull();

    const logout = repo.cerrarSesion();
    http.expectOne(`${BASE}/auth/logout`).flush(null, { status: 204, statusText: 'No Content' });
    await logout;
  });

  it('AC_TKT010_06 activación, confirmación, desactivación y regeneración de MFA', async () => {
    const iniciar = repo.iniciarActivacionMfa('secreto');
    const peticion = http.expectOne(`${BASE}/auth/mfa/activacion`);
    expect(peticion.request.body).toEqual({ contrasena: 'secreto' });
    peticion.flush({ otpauth_uri: 'otpauth://totp/x?secret=ABCD', clave_secreta: 'ABCDEFGHIJKLMNOP' });
    expect(await iniciar).toEqual({ otpauthUri: 'otpauth://totp/x?secret=ABCD', claveSecreta: 'ABCDEFGHIJKLMNOP' });

    const confirmar = repo.confirmarActivacionMfa('123456');
    http.expectOne(`${BASE}/auth/mfa/activacion/confirmar`).flush({ codigos: ['AAAA-BBBB'] });
    expect(await confirmar).toEqual(['AAAA-BBBB']);

    const regenerar = repo.regenerarCodigos('123456');
    http.expectOne(`${BASE}/auth/mfa/codigos-recuperacion`).flush({ codigos: ['CCCC-DDDD'] });
    expect(await regenerar).toEqual(['CCCC-DDDD']);

    const desactivar = repo.desactivarMfa('secreto', '123456');
    http.expectOne(`${BASE}/auth/mfa/desactivar`).flush(null, { status: 204, statusText: 'No Content' });
    await desactivar;
  });

  it('AC_TKT010_09 el tablero viene de GET /api/v1/panel/tablero', async () => {
    const tablero = TestBed.inject(PanelTableroRepositorio).tablero();
    http.expectOne(`${BASE}/tablero`).flush(TABLERO_DTO);
    expect((await tablero).recientes).toHaveLength(2);
  });
});
