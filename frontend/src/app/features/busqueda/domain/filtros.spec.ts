import { etiquetaGrupo, filtrosDesdeQueryParams } from './filtros';

describe('filtrosDesdeQueryParams', () => {
  it('valores por defecto sin parámetros', () => {
    expect(filtrosDesdeQueryParams({})).toEqual({ q: '', tipo: null, pagina: 1 });
  });

  it('lee q, tipo y pagina', () => {
    expect(filtrosDesdeQueryParams({ q: 'patagonia', tipo: 'destinos', pagina: '2' })).toEqual({
      q: 'patagonia',
      tipo: 'destinos',
      pagina: 2,
    });
  });

  it('recorta espacios de q', () => {
    expect(filtrosDesdeQueryParams({ q: '  patagonia  ' }).q).toBe('patagonia');
  });

  it('tipo inválido se ignora (parámetro inválido → se ignora, FEAT-004 mismo criterio)', () => {
    expect(filtrosDesdeQueryParams({ tipo: 'no-existe' }).tipo).toBeNull();
  });

  it('página inválida cae a 1', () => {
    expect(filtrosDesdeQueryParams({ pagina: 'abc' }).pagina).toBe(1);
  });
});

describe('etiquetaGrupo', () => {
  it('devuelve la etiqueta en español de cada grupo', () => {
    expect(etiquetaGrupo('destinos')).toBe('Destinos');
    expect(etiquetaGrupo('tipos')).toBe('Tipos de aventura');
  });
});
