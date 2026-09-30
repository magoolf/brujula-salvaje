import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ItinerarioDetalle as ItinerarioDetalleDto } from '../../../api/models/itinerario-detalle';
import { ItinerarioTarjeta as ItinerarioTarjetaDto } from '../../../api/models/itinerario-tarjeta';
import { PaginaItinerarioTarjeta } from '../../../api/models/pagina-itinerario-tarjeta';
import {
  mapAlternativasRetirado,
  mapImagen,
  mapItinerarioDetalle,
  mapItinerarioTarjeta,
  mapPaginaItinerarios,
  mapRelacionado,
} from './itinerarios.mapper';

const IMAGEN: ImagenPublica = {
  ancho: 800,
  alto: 600,
  autor_credito: 'Jane Doe',
  derivados: [{ ancho: 400, formato: 'WEBP', url: '/media/x-400.webp' }],
  fuente_url: null,
  licencia: { codigo: 'CC-BY', nombre: 'CC BY 4.0', requiere_atribucion: true, url_texto_legal: 'https://x' },
  pie_de_foto: 'Pie',
  texto_alternativo: 'Alt',
};

const ITINERARIO_TARJETA: ItinerarioTarjetaDto = {
  destino: { slug: 'patagonia', nombre: 'Patagonia' },
  dificultad: 3,
  duracion_dias: 5,
  portada: IMAGEN,
  slug: 'w-trek',
  titulo: 'W Trek',
};

describe('mapImagen', () => {
  it('null para imagen nula o ausente', () => {
    expect(mapImagen(null)).toBeNull();
    expect(mapImagen(undefined)).toBeNull();
  });
});

describe('mapItinerarioTarjeta', () => {
  it('mapea todos los campos', () => {
    const resultado = mapItinerarioTarjeta(ITINERARIO_TARJETA);
    expect(resultado).toEqual({
      slug: 'w-trek',
      titulo: 'W Trek',
      destino: { slug: 'patagonia', nombre: 'Patagonia' },
      dificultad: 3,
      duracionDias: 5,
      imagen: expect.objectContaining({ src: '/media/x-400.webp' }),
    });
  });

  it('sin portada produce imagen null', () => {
    const resultado = mapItinerarioTarjeta({ ...ITINERARIO_TARJETA, portada: null });
    expect(resultado.imagen).toBeNull();
  });
});

describe('mapPaginaItinerarios', () => {
  it('mapea metadatos de paginación y resultados', () => {
    const dto: PaginaItinerarioTarjeta = {
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [ITINERARIO_TARJETA],
    };
    const resultado = mapPaginaItinerarios(dto);
    expect(resultado.total).toBe(1);
    expect(resultado.resultados).toEqual([mapItinerarioTarjeta(ITINERARIO_TARJETA)]);
  });
});

describe('mapRelacionado', () => {
  it('construye la ruta interna a partir del tipo', () => {
    const resultado = mapRelacionado({
      origen: 'CURADO',
      slug: 'torres-del-paine',
      tipo: 'DESTINO',
      titulo: 'Torres del Paine',
    });
    expect(resultado.ruta).toBe('/destinos/torres-del-paine');
  });
});

describe('mapAlternativasRetirado', () => {
  it('lista vacía si no es un array', () => {
    expect(mapAlternativasRetirado(undefined)).toEqual([]);
    expect(mapAlternativasRetirado('x')).toEqual([]);
  });

  it('descarta elementos con forma inválida', () => {
    const resultado = mapAlternativasRetirado([
      { tipo: 'ITINERARIO', slug: 'otro', titulo: 'Otro', origen: 'CURADO' },
      { forma: 'invalida' },
    ]);
    expect(resultado).toHaveLength(1);
    expect(resultado[0].slug).toBe('otro');
  });
});

describe('mapItinerarioDetalle', () => {
  const DETALLE: ItinerarioDetalleDto = {
    desnivel_acumulado_m: 850,
    destino: { dificultad: 3, pais: { slug: 'chile', nombre: 'Chile' }, portada: null, region: { slug: 's', nombre: 'S' }, slug: 'patagonia', tipos: [], titulo: 'Patagonia' },
    dias: [
      {
        actividades: '<p>Caminata</p>',
        alojamiento_orientativo: 'Refugio',
        consejos: 'Lleva agua',
        desnivel_negativo_m: 100,
        desnivel_positivo_m: 200,
        distancia_km: 12,
        numero_dia: 1,
        titulo: 'Inicio del sendero',
      },
    ],
    dificultad: 3,
    distancia_total_km: 80,
    duracion_dias: 5,
    fuentes: [{ titulo: 'Fuente', url: 'https://x', entidad_editora: 'X' }],
    galeria: [IMAGEN],
    metadatos: {
      autoria: 'Equipo editorial',
      fecha_ultima_revision: '2026-01-01',
      publicado_actualizado_en: '2026-01-01',
      seo_descripcion: 'x',
      seo_titulo: 'x',
    },
    portada: IMAGEN,
    relacionados: [],
    resumen: 'Un resumen',
    riesgos_seguridad: '<p>Riesgos</p>',
    slug: 'w-trek',
    terminos: [{ slug: 'trekking', termino: 'Trekking' }],
    tipos: [{ slug: 'senderismo', nombre: 'Senderismo' }],
    titulo: 'W Trek',
  };

  it('mapea el detalle completo, incluidos los días', () => {
    const resultado = mapItinerarioDetalle(DETALLE);
    expect(resultado.titulo).toBe('W Trek');
    expect(resultado.dias).toHaveLength(1);
    expect(resultado.dias[0]).toEqual({
      numeroDia: 1,
      titulo: 'Inicio del sendero',
      actividades: '<p>Caminata</p>',
      distanciaKm: 12,
      desnivelPositivoM: 200,
      desnivelNegativoM: 100,
      alojamientoOrientativo: 'Refugio',
      consejos: 'Lleva agua',
    });
    expect(resultado.terminos).toEqual([{ slug: 'trekking', termino: 'Trekking' }]);
    expect(resultado.autoria).toBe('Equipo editorial');
  });

  it('filtra imágenes nulas de la galería sin lanzar', () => {
    const resultado = mapItinerarioDetalle({ ...DETALLE, galeria: [] });
    expect(resultado.galeria).toEqual([]);
  });
});
