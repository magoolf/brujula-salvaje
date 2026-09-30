import { DestinoDetalle as DestinoDetalleDto } from '../../../api/models/destino-detalle';
import { DestinoTarjeta as DestinoTarjetaDto } from '../../../api/models/destino-tarjeta';
import { FacetasDestinos as FacetasDestinosDto } from '../../../api/models/facetas-destinos';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { PaginaDestinoTarjeta } from '../../../api/models/pagina-destino-tarjeta';
import { Meses } from '../../../api/models/meses';
import {
  mapAlternativasRetirado,
  mapDestinoDetalle,
  mapFacetas,
  mapImagen,
  mapMeses,
  mapPaginaDestinos,
  mapTarjetaDestino,
} from './destinos.mapper';

const IMAGEN: ImagenPublica = {
  ancho: 800,
  alto: 600,
  autor_credito: 'Jane Doe',
  derivados: [
    { ancho: 400, formato: 'WEBP', url: '/media/x-400.webp' },
    { ancho: 800, formato: 'WEBP', url: '/media/x-800.webp' },
  ],
  fuente_url: null,
  licencia: { codigo: 'CC-BY', nombre: 'CC BY 4.0', requiere_atribucion: true, url_texto_legal: 'https://x' },
  pie_de_foto: 'Una vista',
  texto_alternativo: 'Vista del destino',
};

const DESTINO_TARJETA: DestinoTarjetaDto = {
  dificultad: 3,
  pais: { slug: 'colombia', nombre: 'Colombia' },
  portada: IMAGEN,
  region: { slug: 'suramerica', nombre: 'Suramérica' },
  slug: 'patagonia',
  tipos: [{ slug: 'senderismo', nombre: 'Senderismo' }],
  titulo: 'Patagonia',
};

describe('mapImagen', () => {
  it('devuelve null para imagen nula o ausente', () => {
    expect(mapImagen(null)).toBeNull();
    expect(mapImagen(undefined)).toBeNull();
  });

  it('usa el primer derivado como src y conserva autor/licencia/pie', () => {
    const resultado = mapImagen(IMAGEN);
    expect(resultado).toEqual({
      src: '/media/x-400.webp',
      alt: 'Vista del destino',
      ancho: 800,
      alto: 600,
      derivados: [
        { url: '/media/x-400.webp', ancho: 400 },
        { url: '/media/x-800.webp', ancho: 800 },
      ],
      autorCredito: 'Jane Doe',
      pieDeFoto: 'Una vista',
      licenciaNombre: 'CC BY 4.0',
      licenciaUrl: 'https://x',
    });
  });
});

describe('mapTarjetaDestino', () => {
  it('mapea todos los campos de la tarjeta', () => {
    const resultado = mapTarjetaDestino(DESTINO_TARJETA);
    expect(resultado.slug).toBe('patagonia');
    expect(resultado.pais).toEqual({ slug: 'colombia', nombre: 'Colombia' });
    expect(resultado.tipos).toEqual([{ slug: 'senderismo', nombre: 'Senderismo' }]);
    expect(resultado.imagen?.src).toBe('/media/x-400.webp');
  });

  it('tarjeta sin portada produce imagen null', () => {
    const resultado = mapTarjetaDestino({ ...DESTINO_TARJETA, portada: null });
    expect(resultado.imagen).toBeNull();
  });
});

describe('mapPaginaDestinos', () => {
  it('mapea metadatos de paginación y resultados', () => {
    const dto: PaginaDestinoTarjeta = {
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [DESTINO_TARJETA],
    };
    const resultado = mapPaginaDestinos(dto);
    expect(resultado).toEqual({
      resultados: [mapTarjetaDestino(DESTINO_TARJETA)],
      pagina: 1,
      totalPaginas: 1,
      total: 1,
      tamanoPagina: 24,
    });
  });
});

describe('mapFacetas', () => {
  it('mapea tipos, regiones (con países), escalas y tramos', () => {
    const dto: FacetasDestinosDto = {
      dificultad: [{ escala: 'DIFICULTAD', nivel: 1, etiqueta: 'Fácil', descripcion: 'x' }],
      presupuesto: [{ escala: 'PRESUPUESTO', nivel: 1, etiqueta: 'Económico', descripcion: 'x' }],
      regiones: [
        {
          slug: 'suramerica',
          nombre: 'Suramérica',
          continente: 'AMERICA',
          paises: [{ slug: 'colombia', nombre: 'Colombia' }],
        },
      ],
      tipos: [{ slug: 'senderismo', nombre: 'Senderismo' }],
      tramos_duracion: [{ codigo: '1-3', etiqueta: '1 a 3 días', min_dias: 1, max_dias: 3 }],
    };
    const resultado = mapFacetas(dto);
    expect(resultado.regiones[0].paises).toEqual([{ slug: 'colombia', nombre: 'Colombia' }]);
    expect(resultado.tramosDuracion[0]).toEqual({ codigo: '1-3', etiqueta: '1 a 3 días', minDias: 1, maxDias: 3 });
    expect(resultado.dificultad[0].nivel).toBe(1);
  });
});

describe('mapDestinoDetalle', () => {
  const DETALLE: DestinoDetalleDto = {
    clima: 'Templado',
    como_llegar: '<p>En avión</p>',
    descripcion_experta: '<p>Descripción</p>',
    dificultad: 3,
    duracion_max_dias: 10,
    duracion_min_dias: 5,
    fuentes: [{ titulo: 'Fuente', url: 'https://x', entidad_editora: 'X' }],
    galeria: [IMAGEN],
    guias_relacionadas: [],
    itinerarios: [],
    itinerarios_afines: [],
    itinerarios_total: 0,
    latitud: 4.5,
    longitud: -74.2,
    meses_mejor_epoca: [6, 7],
    metadatos: {
      autoria: 'Equipo editorial',
      fecha_ultima_revision: '2026-01-01',
      publicado_actualizado_en: '2026-01-01',
      seo_descripcion: 'x',
      seo_titulo: 'x',
    },
    nivel_presupuesto: 2,
    pais: {
      codigo_iso2: 'CO',
      nombre: 'Colombia',
      region: { continente: 'AMERICA', nombre: 'Suramérica', slug: 'suramerica' },
      slug: 'colombia',
    },
    portada: IMAGEN,
    relacionados: [],
    resumen: 'Un resumen',
    seguridad_riesgos: '<p>Riesgos</p>',
    slug: 'patagonia',
    sostenibilidad: '<p>Sostenibilidad</p>',
    terminos: [],
    tipo_principal: { slug: 'senderismo', nombre: 'Senderismo' },
    tipos: [{ slug: 'senderismo', nombre: 'Senderismo' }],
    titulo: 'Patagonia',
  };

  it('mapea el detalle completo, incluida la región derivada del país', () => {
    const resultado = mapDestinoDetalle(DETALLE);
    expect(resultado.titulo).toBe('Patagonia');
    expect(resultado.region).toEqual({ slug: 'suramerica', nombre: 'Suramérica' });
    expect(resultado.galeria).toHaveLength(1);
    expect(resultado.fuentes).toEqual([{ titulo: 'Fuente', url: 'https://x', entidadEditora: 'X' }]);
    expect(resultado.autoria).toBe('Equipo editorial');
    expect(resultado.fechaUltimaRevision).toBe('2026-01-01');
  });

  it('filtra imágenes nulas de la galería sin lanzar', () => {
    const resultado = mapDestinoDetalle({ ...DETALLE, galeria: [] });
    expect(resultado.galeria).toEqual([]);
  });
});

describe('mapAlternativasRetirado', () => {
  it('devuelve lista vacía si el valor no es un array', () => {
    expect(mapAlternativasRetirado(undefined)).toEqual([]);
    expect(mapAlternativasRetirado('no es un array')).toEqual([]);
  });

  it('mapea solo los elementos con la forma esperada, descartando el resto', () => {
    const resultado = mapAlternativasRetirado([
      { tipo: 'DESTINO', slug: 'otro', titulo: 'Otro', origen: 'CURADO' },
      { forma: 'invalida' },
      'texto',
    ]);
    expect(resultado).toHaveLength(1);
    expect(resultado[0].slug).toBe('otro');
    expect(resultado[0].ruta).toBe('/destinos/otro');
  });
});

describe('mapMeses', () => {
  it('mapea los 12 meses con su destacado (o null)', () => {
    const dto: Meses = {
      meses: [
        { mes: 1, nombre: 'Enero', slug: 'enero', numero_destinos: 2, destacado: DESTINO_TARJETA },
        { mes: 2, nombre: 'Febrero', slug: 'febrero', numero_destinos: 0, destacado: null },
      ],
    };
    const resultado = mapMeses(dto);
    expect(resultado).toHaveLength(2);
    expect(resultado[0].destacado?.slug).toBe('patagonia');
    expect(resultado[1].destacado).toBeNull();
  });
});
