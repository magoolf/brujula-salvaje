import { ContenidoRefVista, CreditoMedioVista, ImagenVista } from './modelos';
import { agruparCreditosPorContenido, formatoFechaEsCo } from './institucional';

const IMAGEN = (src: string): ImagenVista => ({
  src,
  alt: 'x',
  ancho: 1,
  alto: 1,
  derivados: [],
  autorCredito: 'x',
  pieDeFoto: null,
  licenciaNombre: 'x',
  licenciaUrl: null,
  fuenteUrl: null,
});

const CONTENIDO = (slug: string): ContenidoRefVista => ({ tipo: 'DESTINO', slug, titulo: slug, ruta: `/destinos/${slug}` });

describe('formatoFechaEsCo', () => {
  it('formatea una fecha ISO en es-CO', () => {
    expect(formatoFechaEsCo('2026-01-15')).toContain('2026');
  });

  it('devuelve el valor original si no es válida', () => {
    expect(formatoFechaEsCo('x')).toBe('x');
  });
});

describe('agruparCreditosPorContenido', () => {
  it('invierte el pivote medio→contenidos en contenido→medios', () => {
    const creditos: CreditoMedioVista[] = [
      { imagen: IMAGEN('a'), usadoEn: [CONTENIDO('patagonia')] },
      { imagen: IMAGEN('b'), usadoEn: [CONTENIDO('patagonia'), CONTENIDO('torres-del-paine')] },
    ];
    const grupos = agruparCreditosPorContenido(creditos);
    expect(grupos.map((g) => g.contenido.slug)).toEqual(['patagonia', 'torres-del-paine']);
    expect(grupos[0].medios.map((m) => m.src)).toEqual(['a', 'b']);
    expect(grupos[1].medios.map((m) => m.src)).toEqual(['b']);
  });

  it('lista vacía produce lista de grupos vacía', () => {
    expect(agruparCreditosPorContenido([])).toEqual([]);
  });
});
