import { ACCESOS_MOSAICO, esInicioVacio } from './inicio';
import { Inicio } from './modelos';

const INICIO_VACIO: Inicio = { hero: null, destinos: [], itinerarios: [], guias: [], tipos: [] };

describe('esInicioVacio', () => {
  it('es verdadero cuando no hay hero ni ninguna sección con contenido', () => {
    expect(esInicioVacio(INICIO_VACIO)).toBe(true);
  });

  it('es falso si hay hero', () => {
    expect(
      esInicioVacio({ ...INICIO_VACIO, hero: { titular: 't', subtitulo: 's', imagen: null } }),
    ).toBe(false);
  });

  it('es falso si cualquier sección tiene contenido', () => {
    expect(
      esInicioVacio({
        ...INICIO_VACIO,
        destinos: [{ slug: 'a', titulo: 'A', pais: { slug: 'p', nombre: 'P' }, dificultad: 1, imagen: null }],
      }),
    ).toBe(false);
  });
});

describe('ACCESOS_MOSAICO', () => {
  it('solo incluye accesos ya implementados (RULE-030): mapa y cuándo ir, no colecciones', () => {
    const ids = ACCESOS_MOSAICO.map((a) => a.id);
    expect(ids).toContain('mapa');
    expect(ids).toContain('cuando-ir');
    expect(ids).not.toContain('colecciones');
    expect(ids).not.toContain('sorprendeme');
  });
});
