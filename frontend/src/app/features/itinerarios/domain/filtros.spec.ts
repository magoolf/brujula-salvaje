import { filtrosDesdeQueryParams, queryParamsOrden } from './filtros';

describe('filtrosDesdeQueryParams', () => {
  it('valores por defecto sin parámetros', () => {
    expect(filtrosDesdeQueryParams({})).toEqual({ orden: 'titulo', pagina: 1 });
  });

  it('lee orden y página válidos', () => {
    expect(filtrosDesdeQueryParams({ orden: 'duracion_asc', pagina: '3' })).toEqual({
      orden: 'duracion_asc',
      pagina: 3,
    });
  });

  it('orden inválido cae a "titulo" (parámetro inválido se ignora, FEAT-004 mismo criterio)', () => {
    expect(filtrosDesdeQueryParams({ orden: 'no-existe' })).toEqual({ orden: 'titulo', pagina: 1 });
  });

  it('página inválida o menor a 1 cae a 1', () => {
    expect(filtrosDesdeQueryParams({ pagina: '0' }).pagina).toBe(1);
    expect(filtrosDesdeQueryParams({ pagina: 'abc' }).pagina).toBe(1);
  });

  it('toma el primer valor si el parámetro llega como lista', () => {
    expect(filtrosDesdeQueryParams({ orden: ['duracion_desc', 'titulo'] }).orden).toBe('duracion_desc');
  });
});

describe('queryParamsOrden', () => {
  it('titulo (por defecto) se omite de la URL', () => {
    expect(queryParamsOrden('titulo')).toEqual({ orden: null, pagina: null });
  });

  it('otros órdenes se incluyen y reinician la página', () => {
    expect(queryParamsOrden('duracion_asc')).toEqual({ orden: 'duracion_asc', pagina: null });
  });
});
