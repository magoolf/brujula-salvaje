import { HttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ApiConfiguration } from '../../api/api-configuration';
import { XSRF_CABECERA, XSRF_COOKIE, proveerHttp } from './proveer-http';

describe('proveerHttp (XSRF, cliente generado)', () => {
  let http: HttpClient;
  let controlador: HttpTestingController;
  let documento: Document;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), ...proveerHttp(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpClient);
    controlador = TestBed.inject(HttpTestingController);
    documento = TestBed.inject(DOCUMENT);
    documento.cookie = `${XSRF_COOKIE}=token-de-prueba-123; path=/`;
  });

  afterEach(() => {
    documento.cookie = `${XSRF_COOKIE}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
    controlador.verify();
  });

  it('AC_TKT002_05 usa la cookie csrftoken y la cabecera X-CSRFToken de Django', () => {
    expect(XSRF_COOKIE).toBe('csrftoken');
    expect(XSRF_CABECERA).toBe('X-CSRFToken');

    http.post('/api/v1/panel/auth/logout', {}).subscribe();
    const peticion = controlador.expectOne('/api/v1/panel/auth/logout');
    expect(peticion.request.headers.get('X-CSRFToken')).toBe('token-de-prueba-123');
    expect(peticion.request.headers.get('traceparent')).toMatch(
      /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/,
    );
    peticion.flush(null);
  });

  it('AC_TKT002_05 no envía el token CSRF en peticiones de lectura (GET)', () => {
    http.get('/api/v1/publico/inicio').subscribe();
    const peticion = controlador.expectOne('/api/v1/publico/inicio');
    expect(peticion.request.headers.has('X-CSRFToken')).toBe(false);
    peticion.flush({});
  });

  it('configura el cliente generado con rutas desde la raíz del mismo origen (rootUrl vacío)', () => {
    expect(TestBed.inject(ApiConfiguration).rootUrl).toBe('');
  });
});
