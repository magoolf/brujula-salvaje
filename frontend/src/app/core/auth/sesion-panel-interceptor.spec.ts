import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { destinoTrasAcceso, esDestinoSeguro } from './destino-seguro';
import { sesionPanelInterceptor } from './sesion-panel-interceptor';

const NO_AUTORIZADO = { status: 401, statusText: 'Unauthorized' };

describe('sesionPanelInterceptor (401 global)', () => {
  let http: HttpClient;
  let ctrl: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([sesionPanelInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    ctrl = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => ctrl.verify());

  it('AC_TKT010_07 ante un 401 del panel redirige a /panel/acceso con un siguiente seguro y propaga el error', () => {
    vi.spyOn(router, 'url', 'get').mockReturnValue('/panel/contenido/destinos?pagina=2');
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const errores: unknown[] = [];

    http
      .get('/api/v1/panel/contenidos/destinos')
      .subscribe({ error: (e: unknown) => errores.push(e) });
    ctrl
      .expectOne('/api/v1/panel/contenidos/destinos')
      .flush({ code: 'sesion_expirada' }, NO_AUTORIZADO);

    expect(navegar).toHaveBeenCalledWith(['/panel/acceso'], {
      queryParams: { motivo: 'expirada', siguiente: '/panel/contenido/destinos?pagina=2' },
    });
    expect(errores).toHaveLength(1);
  });

  it('AC_TKT010_07 omite `siguiente` si la ruta actual no es un destino seguro', () => {
    vi.spyOn(router, 'url', 'get').mockReturnValue('/destinos');
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    http.get('/api/v1/panel/cuentas').subscribe({ error: () => undefined });
    ctrl.expectOne('/api/v1/panel/cuentas').flush(null, NO_AUTORIZADO);
    expect(navegar).toHaveBeenCalledWith(['/panel/acceso'], {
      queryParams: { motivo: 'expirada' },
    });
  });

  it('AC_TKT010_11 un 401 de una operación de sesión (renovar, contraseña) también lleva a SCR-030', () => {
    vi.spyOn(router, 'url', 'get').mockReturnValue('/panel');
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    http.post('/api/v1/panel/auth/sesion/renovar', {}).subscribe({ error: () => undefined });
    ctrl
      .expectOne('/api/v1/panel/auth/sesion/renovar')
      .flush({ code: 'sesion_expirada' }, NO_AUTORIZADO);
    expect(navegar).toHaveBeenCalledWith(['/panel/acceso'], {
      queryParams: { motivo: 'expirada', siguiente: '/panel' },
    });
  });

  it('AC_TKT010_06 DEC-AUTO-215: el 401 credenciales_invalidas de la reautenticación NO expulsa', () => {
    vi.spyOn(router, 'url', 'get').mockReturnValue('/panel/cuenta');
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const errores: unknown[] = [];
    http
      .post('/api/v1/panel/auth/mfa/activacion', { contrasena: 'x' })
      .subscribe({ error: (e: unknown) => errores.push(e) });
    ctrl
      .expectOne('/api/v1/panel/auth/mfa/activacion')
      .flush(
        { code: 'credenciales_invalidas', title: 'Credenciales inválidas', status: 401 },
        NO_AUTORIZADO,
      );
    expect(navegar).not.toHaveBeenCalled();
    expect(errores).toHaveLength(1);
  });

  it('AC_TKT010_03 el 401 mfa_invalido de la verificación es un error de campo, no una expulsión', () => {
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    http.post('/api/v1/panel/auth/mfa/verificar', {}).subscribe({ error: () => undefined });
    ctrl
      .expectOne('/api/v1/panel/auth/mfa/verificar')
      .flush({ code: 'mfa_invalido' }, NO_AUTORIZADO);
    expect(navegar).not.toHaveBeenCalled();
  });

  it('no actúa en login, csrf ni en la consulta de sesión, ni en otros códigos o en la API pública', () => {
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    for (const url of [
      '/api/v1/panel/auth/login',
      '/api/v1/panel/auth/csrf',
      '/api/v1/panel/auth/sesion',
    ]) {
      http.post(url, {}).subscribe({ error: () => undefined });
      ctrl.expectOne(url).flush({ code: 'no_autenticado' }, NO_AUTORIZADO);
    }
    http.get('/api/v1/panel/cuentas').subscribe({ error: () => undefined });
    ctrl.expectOne('/api/v1/panel/cuentas').flush(null, { status: 403, statusText: 'Forbidden' });
    http.get('/api/v1/publico/inicio').subscribe({ error: () => undefined });
    ctrl.expectOne('/api/v1/publico/inicio').flush(null, NO_AUTORIZADO);
    expect(navegar).not.toHaveBeenCalled();
  });
});

describe('destino-seguro (AC-115)', () => {
  it.each([
    ['/panel', true],
    ['/panel/contenido/destinos', true],
    ['/panel/medios?pagina=2', true],
    ['/panel/acceso', false],
    ['/panel/acceso/verificacion', false],
    ['//evil.example/panel', false],
    ['https://evil.example/panel', false],
    ['/panelx', false],
    ['/destinos', false],
    ['/panel/../destinos', false],
    ['/panel/\\evil', false],
    ['/panel/a b', false],
    ['/panel/\u0000', false],
    ['', false],
  ])('AC_TKT010_07 esDestinoSeguro(%j) = %s', (valor, esperado) => {
    expect(esDestinoSeguro(valor)).toBe(esperado);
  });

  it('AC_TKT010_07 rechaza valores no texto o demasiado largos y cae al Tablero', () => {
    expect(esDestinoSeguro(null)).toBe(false);
    expect(esDestinoSeguro('/panel/' + 'a'.repeat(3000))).toBe(false);
    expect(destinoTrasAcceso('https://evil.example')).toBe('/panel');
    expect(destinoTrasAcceso('/panel/cuenta')).toBe('/panel/cuenta');
  });
});
