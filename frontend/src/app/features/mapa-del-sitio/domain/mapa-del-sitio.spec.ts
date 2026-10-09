import {
  agruparPor,
  compararTexto,
  construirSecciones,
  rutaDeEntrada,
  totalEnlaces,
} from './mapa-del-sitio';
import { DatosMapaDelSitio, EntradaIndiceVista, SeccionMapa } from './modelos';

function entrada(parcial: Partial<EntradaIndiceVista> & Pick<EntradaIndiceVista, 'tipo' | 'slug'>): EntradaIndiceVista {
  return { titulo: parcial.slug, agrupacion: null, ...parcial };
}

const ANDES = { slug: 'andes', nombre: 'Andes' };
const AMAZONIA = { slug: 'amazonia', nombre: 'Amazonía' };
const SEGURIDAD = { slug: 'seguridad', nombre: 'Seguridad' };
const EQUIPO = { slug: 'equipo', nombre: 'Equipo' };

const DATOS: DatosMapaDelSitio = {
  entradas: [
    entrada({ tipo: 'DESTINO', slug: 'salkantay', titulo: 'Salkantay', agrupacion: ANDES }),
    entrada({ tipo: 'DESTINO', slug: 'cocuy', titulo: 'El Cocuy', agrupacion: ANDES }),
    entrada({ tipo: 'DESTINO', slug: 'yasuni', titulo: 'Yasuní', agrupacion: AMAZONIA }),
    entrada({ tipo: 'DESTINO', slug: 'sin-pais', titulo: 'Sin país' }),
    entrada({ tipo: 'ITINERARIO', slug: 'trek-5-dias', titulo: 'Trek de 5 días' }),
    entrada({ tipo: 'TIPO', slug: 'trekking', titulo: 'Trekking' }),
    entrada({ tipo: 'GUIA', slug: 'mal-de-altura', titulo: 'Mal de altura', agrupacion: SEGURIDAD }),
    entrada({ tipo: 'GUIA', slug: 'mochila', titulo: 'Mochila', agrupacion: EQUIPO }),
    entrada({ tipo: 'CATEGORIA_GUIA', slug: 'seguridad', titulo: 'Seguridad' }),
    entrada({ tipo: 'CATEGORIA_GUIA', slug: 'equipo', titulo: 'Equipo' }),
    entrada({ tipo: 'COLECCION', slug: 'volcanes', titulo: 'Volcanes' }),
    entrada({ tipo: 'PAGINA', slug: 'aviso-legal', titulo: 'Aviso legal' }),
    entrada({ tipo: 'PAGINA', slug: 'acerca-de', titulo: 'Acerca de' }),
  ],
  meses: [
    { numero: 1, slug: 'enero', nombre: 'Enero', numeroDestinos: 3 },
    { numero: 2, slug: 'febrero', nombre: 'Febrero', numeroDestinos: 1 },
    { numero: 13, slug: 'invalido', nombre: 'Inválido', numeroDestinos: 0 },
  ],
  terminos: [
    { slug: 'vivac', termino: 'Vivac', pagina: 1 },
    { slug: 'aclimatacion', termino: 'Aclimatación', pagina: 2 },
  ],
};

function seccion(secciones: readonly SeccionMapa[], id: string): SeccionMapa {
  const encontrada = secciones.find((s) => s.id === id);
  if (!encontrada) throw new Error(`Sin sección ${id}`);
  return encontrada;
}

function rutas(s: SeccionMapa): string[] {
  return s.grupos.flatMap((g) => g.enlaces.map((e) => e.ruta));
}

describe('rutaDeEntrada', () => {
  it('AC_TKT019_03 traduce cada tipo del índice a su ruta pública', () => {
    expect(rutaDeEntrada({ tipo: 'DESTINO', slug: 'a' })).toBe('/destinos/a');
    expect(rutaDeEntrada({ tipo: 'ITINERARIO', slug: 'a' })).toBe('/itinerarios/a');
    expect(rutaDeEntrada({ tipo: 'TIPO', slug: 'a' })).toBe('/tipos-de-aventura/a');
    expect(rutaDeEntrada({ tipo: 'GUIA', slug: 'a' })).toBe('/guias/a');
    expect(rutaDeEntrada({ tipo: 'CATEGORIA_GUIA', slug: 'a' })).toBe('/guias/categoria/a');
    expect(rutaDeEntrada({ tipo: 'COLECCION', slug: 'a' })).toBe('/colecciones/a');
    expect(rutaDeEntrada({ tipo: 'PAGINA', slug: 'politica-de-cookies' })).toBe('/politica-de-cookies');
  });

  it('AC_TKT019_04 descarta lo que no tiene página en el sitio (sin enlaces rotos)', () => {
    expect(rutaDeEntrada({ tipo: 'PAGINA', slug: 'desconocida' })).toBeNull();
    expect(rutaDeEntrada({ tipo: 'DESTINO', slug: '  ' })).toBeNull();
    expect(rutaDeEntrada({ tipo: 'OTRO' as never, slug: 'x' })).toBeNull();
  });
});

describe('compararTexto', () => {
  it('ordena en español ignorando tildes y mayúsculas', () => {
    expect(['yasuní', 'Ámbar', 'cocuy'].sort(compararTexto)).toEqual(['Ámbar', 'cocuy', 'yasuní']);
  });
});

describe('agruparPor', () => {
  it('agrupa por agrupación, respeta el orden dado y deja «Otros» al final', () => {
    const grupos = agruparPor(
      [
        entrada({ tipo: 'GUIA', slug: 'b', titulo: 'B', agrupacion: SEGURIDAD }),
        entrada({ tipo: 'GUIA', slug: 'a', titulo: 'A', agrupacion: EQUIPO }),
        entrada({ tipo: 'GUIA', slug: 'c', titulo: 'C' }),
      ],
      'guias',
      'Otras guías',
      [SEGURIDAD, EQUIPO],
      (g) => `/guias/categoria/${g.slug}`,
    );
    expect(grupos.map((g) => g.titulo)).toEqual(['Seguridad', 'Equipo', 'Otras guías']);
    expect(grupos.map((g) => g.ruta)).toEqual(['/guias/categoria/seguridad', '/guias/categoria/equipo', null]);
    expect(grupos[2].id).toBe('guias-otros');
  });

  it('sin orden dado, ordena los grupos alfabéticamente y omite grupos sin enlaces válidos', () => {
    const grupos = agruparPor(
      [
        entrada({ tipo: 'DESTINO', slug: 'x', agrupacion: ANDES }),
        entrada({ tipo: 'DESTINO', slug: 'y', agrupacion: AMAZONIA }),
        entrada({ tipo: 'PAGINA', slug: 'no-existe', agrupacion: { slug: 'z', nombre: 'Zeta' } }),
      ],
      'destinos',
      'Otros destinos',
    );
    expect(grupos.map((g) => g.titulo)).toEqual(['Amazonía', 'Andes']);
    expect(grupos.every((g) => g.ruta === null)).toBe(true);
  });

  it('elimina rutas duplicadas dentro de un grupo', () => {
    const grupos = agruparPor(
      [entrada({ tipo: 'DESTINO', slug: 'x' }), entrada({ tipo: 'DESTINO', slug: 'x' })],
      'destinos',
      'Otros destinos',
    );
    expect(grupos[0].enlaces).toHaveLength(1);
  });
});

describe('construirSecciones', () => {
  const secciones = construirSecciones(DATOS);

  it('AC_TKT019_02 incluye todas las secciones en el orden de HANDOFF_UI_UX', () => {
    expect(secciones.map((s) => s.id)).toEqual([
      'general',
      'destinos',
      'itinerarios',
      'tipos-de-aventura',
      'guias',
      'colecciones',
      'cuando-ir',
      'glosario',
      'institucional',
    ]);
  });

  it('AC_TKT019_02 cada sección enlaza su listado aunque no haya contenido', () => {
    const vacias = construirSecciones({ entradas: [], meses: [], terminos: [] });
    expect(seccion(vacias, 'destinos').enlacesSeccion.map((e) => e.ruta)).toEqual(['/destinos', '/destinos/mapa']);
    expect(seccion(vacias, 'colecciones').enlacesSeccion.map((e) => e.ruta)).toEqual(['/colecciones']);
    expect(seccion(vacias, 'colecciones').grupos).toEqual([]);
    expect(rutas(seccion(vacias, 'institucional'))).toEqual(['/creditos']);
  });

  it('AC_TKT019_03 destinos agrupados por región (h3) y alfabéticos dentro de cada una', () => {
    const destinos = seccion(secciones, 'destinos');
    expect(destinos.grupos.map((g) => g.titulo)).toEqual(['Amazonía', 'Andes', 'Otros destinos']);
    expect(destinos.grupos[1].enlaces.map((e) => e.etiqueta)).toEqual(['El Cocuy', 'Salkantay']);
  });

  it('AC_TKT019_03 guías agrupadas por categoría con enlace a la categoría y en su orden editorial', () => {
    const guias = seccion(secciones, 'guias');
    expect(guias.grupos.map((g) => [g.titulo, g.ruta])).toEqual([
      ['Seguridad', '/guias/categoria/seguridad'],
      ['Equipo', '/guias/categoria/equipo'],
    ]);
  });

  it('AC_TKT019_03 enlaza cada contenido publicado del índice', () => {
    const todas = secciones.flatMap(rutas);
    for (const e of DATOS.entradas.filter((x) => x.tipo !== 'CATEGORIA_GUIA')) {
      expect(todas).toContain(rutaDeEntrada(e));
    }
    expect(rutas(seccion(secciones, 'itinerarios'))).toEqual(['/itinerarios/trek-5-dias']);
    expect(rutas(seccion(secciones, 'tipos-de-aventura'))).toEqual(['/tipos-de-aventura/trekking']);
    expect(rutas(seccion(secciones, 'colecciones'))).toEqual(['/colecciones/volcanes']);
  });

  it('AC_TKT019_04 meses con su número de destinos, por número de mes (ruta real /cuando-ir/:mes) y sin meses inválidos', () => {
    const meses = seccion(secciones, 'cuando-ir').grupos[0].enlaces;
    expect(meses.map((m) => [m.etiqueta, m.ruta])).toEqual([
      ['Enero (3 destinos)', '/cuando-ir/1'],
      ['Febrero (1 destino)', '/cuando-ir/2'],
    ]);
  });

  it('AC_TKT019_03 términos del glosario con ancla y página del listado', () => {
    const terminos = seccion(secciones, 'glosario').grupos[0].enlaces;
    expect(terminos).toEqual([
      { etiqueta: 'Aclimatación', ruta: '/glosario', queryParams: { pagina: '2' }, fragmento: 'aclimatacion' },
      { etiqueta: 'Vivac', ruta: '/glosario', fragmento: 'vivac' },
    ]);
  });

  it('AC_TKT019_03 institucional: páginas legales alfabéticas y créditos', () => {
    expect(rutas(seccion(secciones, 'institucional'))).toEqual(['/acerca-de', '/aviso-legal', '/creditos']);
  });

  it('AC_TKT019_05 solo enlaza lo recibido del índice público (nada inventado)', () => {
    const fijas = new Set(['/creditos']);
    const delIndice = new Set(DATOS.entradas.map((e) => rutaDeEntrada(e)));
    for (const s of secciones.filter((x) => !['cuando-ir', 'glosario'].includes(x.id))) {
      for (const ruta of rutas(s)) {
        expect(delIndice.has(ruta) || fijas.has(ruta)).toBe(true);
      }
    }
  });

  it('totalEnlaces suma los enlaces de los grupos', () => {
    // 4 destinos + 1 itinerario + 1 tipo + 2 guías + 1 colección + 2 meses + 2 términos + 3 institucionales
    expect(totalEnlaces(secciones)).toBe(16);
  });
});
