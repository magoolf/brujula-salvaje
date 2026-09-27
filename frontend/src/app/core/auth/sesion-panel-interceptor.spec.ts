import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { destinoTrasAcceso, esDestinoSeguro } from './destino-seguro';
import { sesionPanelInterceptor } from './sesion-panel-interceptor';

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

  it('ante un 401 del panel redirige a /panel/acceso con un siguiente seguro y propaga el error', () => {
    vi.spyOn(router, 'url', 'get').mockReturnValue('/panel/contenido/destinos?pagina=2');
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const errores: unknown[] = [];

    http
      .get('/api/v1/panel/contenidos/destinos')
      .subscribe({ error: (e: unknown) => errores.push(e) });
    ctrl
      .expectOne('/api/v1/panel/contenidos/destinos')
      .flush({ code: 'sesion_expirada' }, { status: 401, statusText: 'Unauthorized' });

    expect(navegar).toHaveBeenCalledWith(['/panel/acceso'], {
      queryParams: { siguiente: '/panel/contenido/destinos?pagina=2' },
    });
    expect(errores).toHaveLength(1);
  });

  it('omite `siguiente` si la ruta actual no es un destino seguro', () => {
    vi.spyOn(router, 'url', 'get').mockReturnValue('/destinos');
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    http.get('/api/v1/panel/cuentas').subscribe({ error: () => undefined });
    ctrl
      .expectOne('/api/v1/panel/cuentas')
      .flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(navegar).toHaveBeenCalledWith(['/panel/acceso'], { queryParams: {} });
  });

  it('no actúa en los endpoints de autenticación ni en otros códigos', () => {
    const navegar = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    http.post('/api/v1/panel/auth/login', {}).subscribe({ error: () => undefined });
    ctrl
      .expectOne('/api/v1/panel/auth/login')
      .flush(null, { status: 401, statusText: 'Unauthorized' });
    http.get('/api/v1/panel/cuentas').subscribe({ error: () => undefined });
    ctrl.expectOne('/api/v1/panel/cuentas').flush(null, { status: 403, statusText: 'Forbidden' });
    http.get('/api/v1/publico/inicio').subscribe({ error: () => undefined });
    ctrl
      .expectOne('/api/v1/publico/inicio')
      .flush(null, { status: 401, statusText: 'Unauthorized' });
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
  ])('esDestinoSeguro(%j) = %s', (valor, esperado) => {
    expect(esDestinoSeguro(valor)).toBe(esperado);
  });

  it('rechaza valores no texto o demasiado largos y cae al Tablero', () => {
    expect(esDestinoSeguro(null)).toBe(false);
    expect(esDestinoSeguro('/panel/' + 'a'.repeat(3000))).toBe(false);
    expect(destinoTrasAcceso('https://evil.example')).toBe('/panel');
    expect(destinoTrasAcceso('/panel/cuenta')).toBe('/panel/cuenta');
  });
});
