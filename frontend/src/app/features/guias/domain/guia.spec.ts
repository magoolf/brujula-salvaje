import { formatoFechaEsCo, textoMinutosLectura, textoRevisado } from './guia';

describe('textoMinutosLectura', () => {
  it('null si no hay minutos', () => {
    expect(textoMinutosLectura(null)).toBeNull();
    expect(textoMinutosLectura(0)).toBeNull();
  });

  it('singular para 1 minuto', () => {
    expect(textoMinutosLectura(1)).toBe('1 min de lectura');
  });

  it('plural para varios minutos', () => {
    expect(textoMinutosLectura(6)).toBe('6 min de lectura');
  });
});

describe('formatoFechaEsCo', () => {
  it('formatea una fecha ISO en es-CO', () => {
    expect(formatoFechaEsCo('2026-01-15')).toContain('2026');
  });

  it('devuelve el valor original si no es válida', () => {
    expect(formatoFechaEsCo('x')).toBe('x');
  });
});

describe('textoRevisado', () => {
  it('antepone "Revisado el "', () => {
    expect(textoRevisado('2026-01-15')).toMatch(/^Revisado el /);
  });
});
