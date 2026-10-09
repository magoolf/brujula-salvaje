import { mapEntradaIndice, mapMeses, mapTermino } from './mapa-del-sitio.mapper';

describe('mapa-del-sitio.mapper', () => {
  it('mapEntradaIndice conserva tipo, slug, título y agrupación', () => {
    expect(
      mapEntradaIndice({
        tipo: 'DESTINO',
        slug: 'cocuy',
        titulo: 'El Cocuy',
        agrupacion: { slug: 'andes', nombre: 'Andes' },
        publicado_actualizado_en: '2026-01-01T00:00:00Z',
      }),
    ).toEqual({ tipo: 'DESTINO', slug: 'cocuy', titulo: 'El Cocuy', agrupacion: { slug: 'andes', nombre: 'Andes' } });
  });

  it('mapEntradaIndice normaliza agrupación ausente o null a null', () => {
    const base = { tipo: 'TIPO' as const, slug: 't', titulo: 'T', publicado_actualizado_en: '2026-01-01T00:00:00Z' };
    expect(mapEntradaIndice(base).agrupacion).toBeNull();
    expect(mapEntradaIndice({ ...base, agrupacion: null }).agrupacion).toBeNull();
  });

  it('mapMeses traduce numero_destinos', () => {
    expect(
      mapMeses({ meses: [{ mes: 1, nombre: 'Enero', slug: 'enero', numero_destinos: 4, destacado: null }] }),
    ).toEqual([{ numero: 1, slug: 'enero', nombre: 'Enero', numeroDestinos: 4 }]);
  });

  it('mapTermino guarda la página del listado', () => {
    expect(mapTermino({ slug: 'vivac', termino: 'Vivac', definicion: 'd', usado_en: [] }, 3)).toEqual({
      slug: 'vivac',
      termino: 'Vivac',
      pagina: 3,
    });
  });
});
