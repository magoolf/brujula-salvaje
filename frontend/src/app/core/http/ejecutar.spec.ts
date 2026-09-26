import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { esNoAutenticado } from './clasificar-error';
import { ejecutar } from './ejecutar';
import { nonceDesdePeticion } from './nonce-csp';

describe('ejecutar (Reglas 11 y 12)', () => {
  it('devuelve null y ejecuta el efecto tras el éxito', async () => {
    const recargar = vi.fn();
    await expect(ejecutar(of({ id: 1 }), recargar)).resolves.toBeNull();
    expect(recargar).toHaveBeenCalledWith({ id: 1 });
  });

  it('devuelve el ErrorApi normalizado si la escritura falla', async () => {
    const fallo = new HttpErrorResponse({
      status: 409,
      error: {
        type: 'https://x.example/errors/conflicto_version',
        title: 'Conflicto',
        status: 409,
        code: 'conflicto_version',
        trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
      },
    });
    const recargar = vi.fn();
    const error = await ejecutar(
      throwError(() => fallo),
      recargar,
    );
    expect(error).toMatchObject({ tipo: 'conflicto_version', categoria: 'conflicto' });
    expect(recargar).not.toHaveBeenCalled();
  });
});

describe('clasificar-error y nonce CSP', () => {
  it('esNoAutenticado solo es verdadero para 401 HTTP', () => {
    expect(esNoAutenticado(new HttpErrorResponse({ status: 401 }))).toBe(true);
    expect(esNoAutenticado(new HttpErrorResponse({ status: 403 }))).toBe(false);
    expect(esNoAutenticado(new Error('x'))).toBe(false);
  });

  it('AC_TKT002_03 acepta el nonce del proxy (32 hex / base64) e ignora valores con formato inesperado', () => {
    expect(nonceDesdePeticion('0123456789abcdef0123456789abcdef')).toBe(
      '0123456789abcdef0123456789abcdef',
    );
    expect(nonceDesdePeticion('rAnd0m+B64/Value==')).toBe('rAnd0m+B64/Value==');
    expect(nonceDesdePeticion('"><script>alert(1)</script>')).toBeNull();
    expect(nonceDesdePeticion('corto')).toBeNull();
    expect(nonceDesdePeticion(null)).toBeNull();
    expect(nonceDesdePeticion(undefined)).toBeNull();
  });
});
