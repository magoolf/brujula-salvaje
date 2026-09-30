import { BusquedaAgrupada } from '../../../api/models/busqueda-agrupada';
import { PaginaResultadoBusqueda } from '../../../api/models/pagina-resultado-busqueda';
import { ResultadoBusqueda } from '../../../api/models/resultado-busqueda';
import { mapBusquedaAgrupada, mapPaginaResultados, mapResultado } from './busqueda.mapper';

const RESULTADO: ResultadoBusqueda = {
  pais: 'Colombia',
  portada: null,
  resumen: 'Un resumen',
  slug: 'patagonia',
  tipo: 'DESTINO',
  titulo: 'Patagonia',
};

describe('mapResultado', () => {
  it('construye la ruta interna a partir del tipo', () => {
    expect(mapResultado(RESULTADO).ruta).toBe('/destinos/patagonia');
  });

  it('sin resumen ni país produce null', () => {
    const resultado = mapResultado({ ...RESULTADO, pais: undefined, resumen: undefined });
    expect(resultado.pais).toBeNull();
    expect(resultado.resumen).toBeNull();
  });
});

describe('mapBusquedaAgrupada', () => {
  it('mapea los 4 grupos y el total', () => {
    const grupoVacio = { resultados: [], total: 0 };
    const dto: BusquedaAgrupada = {
      total: 1,
      grupos: {
        destinos: { resultados: [RESULTADO], total: 1 },
        itinerarios: grupoVacio,
        guias: grupoVacio,
        tipos: grupoVacio,
      },
    };
    const resultado = mapBusquedaAgrupada(dto);
    expect(resultado.total).toBe(1);
    expect(resultado.grupos.destinos.resultados).toHaveLength(1);
    expect(resultado.grupos.tipos.total).toBe(0);
  });
});

describe('mapPaginaResultados', () => {
  it('mapea metadatos de paginación', () => {
    const dto: PaginaResultadoBusqueda = {
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [RESULTADO],
    };
    expect(mapPaginaResultados(dto).total).toBe(1);
  });
});
