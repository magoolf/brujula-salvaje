import { formatoDuracion, formatoFechaEsCo, mesAdyacente, nombreMes, tieneItinerariosPropios } from './destino';

describe('tieneItinerariosPropios', () => {
  it('es verdadero solo cuando la lista de itinerarios no está vacía', () => {
    expect(tieneItinerariosPropios({ itinerarios: [] })).toBe(false);
    expect(tieneItinerariosPropios({ itinerarios: [{}] as never })).toBe(true);
  });
});

describe('formatoDuracion', () => {
  it('un solo número cuando min === max', () => {
    expect(formatoDuracion(5, 5)).toBe('5 días');
  });

  it('rango cuando difieren', () => {
    expect(formatoDuracion(5, 10)).toBe('5 a 10 días');
  });
});

describe('formatoFechaEsCo', () => {
  it('formatea una fecha ISO en es-CO', () => {
    expect(formatoFechaEsCo('2026-03-15')).toContain('2026');
    expect(formatoFechaEsCo('2026-03-15')).toContain('marzo');
  });

  it('devuelve el original si no es una fecha válida', () => {
    expect(formatoFechaEsCo('no-es-fecha')).toBe('no-es-fecha');
  });
});

describe('nombreMes', () => {
  it('devuelve el nombre para 1-12 y null fuera de rango', () => {
    expect(nombreMes(1)).toBe('enero');
    expect(nombreMes(12)).toBe('diciembre');
    expect(nombreMes(0)).toBeNull();
    expect(nombreMes(13)).toBeNull();
  });
});

describe('mesAdyacente', () => {
  it('avanza y retrocede en ciclo dentro de 1-12', () => {
    expect(mesAdyacente(1, -1)).toBe(12);
    expect(mesAdyacente(12, 1)).toBe(1);
    expect(mesAdyacente(6, 1)).toBe(7);
    expect(mesAdyacente(6, -1)).toBe(5);
  });
});
