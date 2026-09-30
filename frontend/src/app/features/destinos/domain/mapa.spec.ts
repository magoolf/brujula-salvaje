import { agruparMarcadores, centroide, formatoCoordenadas, proyectar } from './mapa';
import { PuntoMapa } from './modelos';

function punto(slug: string, latitud: number, longitud: number): PuntoMapa {
  return {
    slug,
    titulo: slug,
    pais: 'País',
    region: { slug: 'region', nombre: 'Región' },
    dificultad: 3,
    latitud,
    longitud,
  };
}

describe('proyectar', () => {
  it('proyecta el centro del mundo (0,0) al centro del contenedor', () => {
    expect(proyectar(0, 0)).toEqual({ xPct: 50, yPct: 50 });
  });

  it('proyecta las esquinas del mundo', () => {
    expect(proyectar(90, -180)).toEqual({ xPct: 0, yPct: 0 });
    expect(proyectar(-90, 180)).toEqual({ xPct: 100, yPct: 100 });
  });

  it('acota valores fuera de rango en vez de desbordar', () => {
    const resultado = proyectar(200, 400);
    expect(resultado.xPct).toBeLessThanOrEqual(100);
    expect(resultado.yPct).toBeGreaterThanOrEqual(0);
  });
});

describe('agruparMarcadores', () => {
  it('un solo punto produce un marcador individual', () => {
    const elementos = agruparMarcadores([punto('a', 4.5, -74)]);
    expect(elementos).toHaveLength(1);
    expect(elementos[0].tipo).toBe('marcador');
  });

  it('agrupa puntos muy cercanos en un cluster', () => {
    const elementos = agruparMarcadores([punto('a', 4.5, -74), punto('b', 4.51, -74.01)]);
    expect(elementos).toHaveLength(1);
    expect(elementos[0].tipo).toBe('cluster');
    if (elementos[0].tipo === 'cluster') {
      expect(elementos[0].puntos).toHaveLength(2);
    }
  });

  it('no agrupa puntos lejanos', () => {
    const elementos = agruparMarcadores([punto('a', 4.5, -74), punto('b', 48.85, 2.35)]);
    expect(elementos).toHaveLength(2);
    expect(elementos.every((e) => e.tipo === 'marcador')).toBe(true);
  });

  it('lista vacía produce lista vacía', () => {
    expect(agruparMarcadores([])).toEqual([]);
  });
});

describe('centroide', () => {
  it('es null para una lista vacía', () => {
    expect(centroide([])).toBeNull();
  });

  it('promedia latitud y longitud', () => {
    const resultado = centroide([punto('a', 0, 0), punto('b', 10, 10)]);
    expect(resultado).toEqual({ latitud: 5, longitud: 5 });
  });
});

describe('formatoCoordenadas', () => {
  it('formatea con N/S y E/O según el signo', () => {
    expect(formatoCoordenadas(4.5709, -74.2973)).toBe('4,5709° N, 74,2973° O');
    expect(formatoCoordenadas(-33.45, 151.2)).toBe('33,4500° S, 151,2000° E');
  });
});
