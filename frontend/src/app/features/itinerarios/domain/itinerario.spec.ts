import { formatoFechaEsCo, textoDesnivelDia, tieneMetricasRuta } from './itinerario';

describe('tieneMetricasRuta', () => {
  it('true si hay distancia o desnivel', () => {
    expect(tieneMetricasRuta({ distanciaTotalKm: 5, desnivelAcumuladoM: null })).toBe(true);
    expect(tieneMetricasRuta({ distanciaTotalKm: null, desnivelAcumuladoM: 100 })).toBe(true);
  });

  it('false si ambos son null', () => {
    expect(tieneMetricasRuta({ distanciaTotalKm: null, desnivelAcumuladoM: null })).toBe(false);
  });
});

describe('formatoFechaEsCo', () => {
  it('formatea una fecha ISO en es-CO', () => {
    expect(formatoFechaEsCo('2026-01-15')).toContain('2026');
  });

  it('devuelve el valor original si no es una fecha válida', () => {
    expect(formatoFechaEsCo('no-es-fecha')).toBe('no-es-fecha');
  });
});

describe('textoDesnivelDia', () => {
  it('null si ambos valores son null', () => {
    expect(textoDesnivelDia(null, null)).toBeNull();
  });

  it('combina positivo y negativo', () => {
    expect(textoDesnivelDia(850, 420)).toBe('desnivel positivo 850 metros, negativo 420 metros');
  });

  it('solo positivo', () => {
    expect(textoDesnivelDia(300, null)).toBe('desnivel positivo 300 metros');
  });

  it('solo negativo', () => {
    expect(textoDesnivelDia(null, 150)).toBe('negativo 150 metros');
  });
});
