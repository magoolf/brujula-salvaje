import { ColeccionDetalle as ColeccionDetalleDto } from '../../../api/models/coleccion-detalle';
import { ColeccionTarjeta as ColeccionTarjetaDto } from '../../../api/models/coleccion-tarjeta';
import { ElementoColeccion } from '../../../api/models/elemento-coleccion';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import {
  mapAlternativasRetirado,
  mapColeccionDetalle,
  mapColeccionTarjeta,
  mapElemento,
  mapPaginaColecciones,
  mapRelacionado,
} from './colecciones.mapper';

const IMAGEN: ImagenPublica = {
  ancho: 800,
  alto: 600,
  autor_credito: 'Jane Doe',
  derivados: [{ ancho: 400, formato: 'WEBP', url: '/media/x-400.webp' }],
  fuente_url: null,
  licencia: { codigo: 'CC-BY', nombre: 'CC BY 4.0', requiere_atribucion: true, url_texto_legal: 'https://x' },
  pie_de_foto: null,
  texto_alternativo: 'Alt',
};

const TARJETA: ColeccionTarjetaDto = {
  numero_elementos: 5,
  portada: IMAGEN,
  resumen: 'Un resumen',
  slug: 'mejores-treks',
  titulo: 'Los mejores treks',
};

describe('mapColeccionTarjeta / mapPaginaColecciones', () => {
  it('mapea la tarjeta', () => {
    expect(mapColeccionTarjeta(TARJETA).numeroElementos).toBe(5);
  });

  it('mapea la página', () => {
    const pagina = mapPaginaColecciones({
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [TARJETA],
    });
    expect(pagina.resultados).toHaveLength(1);
  });
});

describe('mapElemento', () => {
  it('mapea un elemento DESTINO', () => {
    const dto: ElementoColeccion = {
      tipo: 'DESTINO',
      orden: 1,
      nota_editorial: 'Una joya',
      destino: { dificultad: 3, pais: { slug: 'cl', nombre: 'Chile' }, portada: null, region: { slug: 's', nombre: 'S' }, slug: 'patagonia', tipos: [], titulo: 'Patagonia' },
    };
    const resultado = mapElemento(dto);
    expect(resultado).toEqual({
      tipo: 'DESTINO',
      orden: 1,
      notaEditorial: 'Una joya',
      destino: expect.objectContaining({ slug: 'patagonia' }),
    });
  });

  it('mapea un elemento ITINERARIO', () => {
    const dto: ElementoColeccion = {
      tipo: 'ITINERARIO',
      orden: 2,
      nota_editorial: null,
      itinerario: { destino: { slug: 'patagonia', nombre: 'Patagonia' }, dificultad: 3, duracion_dias: 5, portada: null, slug: 'w-trek', titulo: 'W Trek' },
    };
    const resultado = mapElemento(dto);
    expect(resultado?.tipo).toBe('ITINERARIO');
  });

  it('descarta un elemento con tipo sin su contenido correspondiente (dato externo inconsistente)', () => {
    expect(mapElemento({ tipo: 'DESTINO', orden: 1, nota_editorial: null } as ElementoColeccion)).toBeNull();
  });
});

describe('mapRelacionado / mapAlternativasRetirado', () => {
  it('construye la ruta interna', () => {
    expect(mapRelacionado({ origen: 'CURADO', slug: 'a', tipo: 'COLECCION', titulo: 'A' }).ruta).toBe('/colecciones/a');
  });

  it('descarta valores no válidos', () => {
    expect(mapAlternativasRetirado('no-es-array')).toEqual([]);
  });
});

describe('mapColeccionDetalle', () => {
  const DETALLE: ColeccionDetalleDto = {
    descripcion: '<p>x</p>',
    elementos: [
      {
        tipo: 'DESTINO',
        orden: 1,
        nota_editorial: null,
        destino: { dificultad: 1, pais: { slug: 'p', nombre: 'P' }, portada: null, region: { slug: 'r', nombre: 'R' }, slug: 'd', tipos: [], titulo: 'D' },
      },
    ],
    metadatos: { autoria: 'Equipo editorial', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
    portada: IMAGEN,
    resumen: 'x',
    slug: 'mejores-treks',
    titulo: 'Los mejores treks',
  };

  it('mapea el detalle completo y filtra elementos inválidos', () => {
    const resultado = mapColeccionDetalle(DETALLE);
    expect(resultado.elementos).toHaveLength(1);
    expect(resultado.autoria).toBe('Equipo editorial');
  });
});
