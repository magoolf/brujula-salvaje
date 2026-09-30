import { PaginaTerminoGlosarioPublico } from '../../../api/models/pagina-termino-glosario-publico';
import { TerminoGlosarioPublico } from '../../../api/models/termino-glosario-publico';
import { mapContenidoRef, mapPaginaGlosario, mapTermino } from './glosario.mapper';

const TERMINO: TerminoGlosarioPublico = {
  definicion: 'Una definición',
  slug: 'trekking',
  termino: 'Trekking',
  usado_en: [{ slug: 'w-trek', tipo: 'ITINERARIO', titulo: 'W Trek' }],
};

describe('mapContenidoRef', () => {
  it('construye la ruta interna a partir del tipo', () => {
    expect(mapContenidoRef({ slug: 'w-trek', tipo: 'ITINERARIO', titulo: 'W Trek' }).ruta).toBe(
      '/itinerarios/w-trek',
    );
  });
});

describe('mapTermino', () => {
  it('mapea el término y sus referencias de uso', () => {
    const resultado = mapTermino(TERMINO);
    expect(resultado.termino).toBe('Trekking');
    expect(resultado.usadoEn).toEqual([{ tipo: 'ITINERARIO', slug: 'w-trek', titulo: 'W Trek', ruta: '/itinerarios/w-trek' }]);
  });
});

describe('mapPaginaGlosario', () => {
  it('mapea metadatos de paginación', () => {
    const dto: PaginaTerminoGlosarioPublico = {
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [TERMINO],
    };
    expect(mapPaginaGlosario(dto).resultados).toHaveLength(1);
  });
});
