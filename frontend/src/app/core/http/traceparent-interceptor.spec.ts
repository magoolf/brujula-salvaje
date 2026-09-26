import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { esTraceparentValido, generarTraceparent } from './traceparent';
import { traceparentInterceptor } from './traceparent-interceptor';

const W3C = /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/;

describe('traceparentInterceptor', () => {
  let http: HttpClient;
  let controlador: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(withInterceptors([traceparentInterceptor])), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpClient);
    controlador = TestBed.inject(HttpTestingController);
  });

  afterEach(() => controlador.verify());

  it('AC_TKT002_05 añade un traceparent W3C válido a cada petición', () => {
    http.get('/api/v1/publico/inicio').subscribe();
    http.get('/api/v1/publico/inicio').subscribe();
    const [a, b] = controlador.match('/api/v1/publico/inicio');

    const valorA = a.request.headers.get('traceparent');
    const valorB = b.request.headers.get('traceparent');
    expect(valorA).toMatch(W3C);
    expect(esTraceparentValido(valorA)).toBe(true);
    expect(valorB).not.toBe(valorA);
    a.flush({});
    b.flush({});
  });

  it('AC_TKT002_05 respeta un traceparent válido ya presente (reenviado por el SSR)', () => {
    const existente = '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01';
    http.get('/api/v1/publico/inicio', { headers: { traceparent: existente } }).subscribe();
    const peticion = controlador.expectOne('/api/v1/publico/inicio');
    expect(peticion.request.headers.get('traceparent')).toBe(existente);
    peticion.flush({});
  });

  it('AC_TKT002_05 sustituye un traceparent inválido', () => {
    http.get('/api/v1/publico/inicio', { headers: { traceparent: '00-000-abc-01' } }).subscribe();
    const peticion = controlador.expectOne('/api/v1/publico/inicio');
    expect(peticion.request.headers.get('traceparent')).toMatch(W3C);
    peticion.flush({});
  });
});

describe('traceparent (funciones puras)', () => {
  it('AC_TKT002_05 genera ids no nulos incluso si la fuente devuelve ceros', () => {
    const ceros = (bytes: Uint8Array<ArrayBuffer>) => bytes.fill(0);
    const valor = generarTraceparent(ceros);
    expect(valor).toBe('00-00000000000000000000000000000001-0000000000000001-01');
    expect(esTraceparentValido(valor)).toBe(true);
  });

  it('valida el formato y rechaza ids todo ceros, versiones u otros tipos', () => {
    expect(esTraceparentValido('00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01')).toBe(true);
    expect(esTraceparentValido('00-00000000000000000000000000000000-00f067aa0ba902b7-01')).toBe(false);
    expect(esTraceparentValido('00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01')).toBe(false);
    expect(esTraceparentValido('01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01')).toBe(false);
    expect(esTraceparentValido('00-4BF92F3577B34DA6A3CE929D0E0E4736-00f067aa0ba902b7-01')).toBe(false);
    expect(esTraceparentValido(null)).toBe(false);
    expect(esTraceparentValido(undefined)).toBe(false);
  });
});
