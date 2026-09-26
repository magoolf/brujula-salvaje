import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { REQUEST } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { API_INTERNAL_URL, esRutaApi, validarUrlInterna } from './api-interna';
import { reenvioSsrInterceptor } from './reenvio-ssr-interceptor';

function configurar(
  peticion: Request | null,
  base: string | null,
): { http: HttpClient; ctrl: HttpTestingController } {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withInterceptors([reenvioSsrInterceptor])),
      provideHttpClientTesting(),
      { provide: REQUEST, useValue: peticion },
      { provide: API_INTERNAL_URL, useValue: base },
    ],
  });
  return { http: TestBed.inject(HttpClient), ctrl: TestBed.inject(HttpTestingController) };
}

describe('reenvioSsrInterceptor', () => {
  const entrante = new Request('http://localhost:8080/destinos', {
    headers: {
      'x-forwarded-for': '203.0.113.7',
      traceparent: '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
      'x-request-id': 'abc123',
      cookie: 'sessionid=no-debe-reenviarse',
    },
  });

  it('en el SSR reescribe /api/ hacia API_INTERNAL_URL y reenvía X-Forwarded-For, traceparent y X-Request-Id sin modificar', () => {
    const { http, ctrl } = configurar(entrante, 'http://backend:8000');
    http.get('/api/v1/publico/inicio').subscribe();

    const peticion = ctrl.expectOne('http://backend:8000/api/v1/publico/inicio');
    expect(peticion.request.headers.get('x-forwarded-for')).toBe('203.0.113.7');
    expect(peticion.request.headers.get('traceparent')).toBe(
      '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',
    );
    expect(peticion.request.headers.get('x-request-id')).toBe('abc123');
    expect(peticion.request.headers.has('cookie')).toBe(false);
    peticion.flush({});
    ctrl.verify();
  });

  it('no toca peticiones ajenas a la API', () => {
    const { http, ctrl } = configurar(entrante, 'http://backend:8000');
    http.get('/fonts/x.woff2').subscribe();
    ctrl.expectOne('/fonts/x.woff2').flush('');
    ctrl.verify();
  });

  it('en el navegador (sin REQUEST) la petición sigue al mismo origen', () => {
    const { http, ctrl } = configurar(null, null);
    http.get('/api/v1/publico/inicio').subscribe();
    const peticion = ctrl.expectOne('/api/v1/publico/inicio');
    expect(peticion.request.headers.has('x-forwarded-for')).toBe(false);
    peticion.flush({});
    ctrl.verify();
  });

  it('sin API_INTERNAL_URL válida no reescribe la URL', () => {
    const { http, ctrl } = configurar(entrante, null);
    http.get('/api/v1/publico/inicio').subscribe();
    ctrl.expectOne('/api/v1/publico/inicio').flush({});
    ctrl.verify();
  });
});

describe('api-interna', () => {
  it('reconoce las rutas de la API y de salud', () => {
    expect(esRutaApi('/api/v1/publico/inicio')).toBe(true);
    expect(esRutaApi('/health/ready')).toBe(true);
    expect(esRutaApi('/destinos')).toBe(false);
  });

  it('valida API_INTERNAL_URL: solo http(s) sin credenciales, query ni fragmento', () => {
    expect(validarUrlInterna('http://backend:8000')).toBe('http://backend:8000');
    expect(validarUrlInterna(' https://api.interna/base/ ')).toBe('https://api.interna/base');
    expect(validarUrlInterna('ftp://backend')).toBeNull();
    expect(validarUrlInterna('http://u:p@backend')).toBeNull();
    expect(validarUrlInterna('http://backend?x=1')).toBeNull();
    expect(validarUrlInterna('no es url')).toBeNull();
    expect(validarUrlInterna('')).toBeNull();
    expect(validarUrlInterna(undefined)).toBeNull();
  });
});
