import { ImagenPublica } from '../../../api/models/imagen-publica';
import { PaginaTipoAventuraTarjeta } from '../../../api/models/pagina-tipo-aventura-tarjeta';
import { TipoAventuraDetalle as TipoAventuraDetalleDto } from '../../../api/models/tipo-aventura-detalle';
import { TipoAventuraTarjeta as TipoAventuraTarjetaDto } from '../../../api/models/tipo-aventura-tarjeta';
import {
  mapAlternativasRetirado,
  mapPaginaTipos,
  mapRelacionado,
  mapTipoDetalle,
  mapTipoTarjeta,
} from './tipos-aventura.mapper';

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

const TARJETA: TipoAventuraTarjetaDto = {
  nivel_exigencia: 4,
  numero_destinos: 6,
  portada: IMAGEN,
  resumen: 'Un resumen',
  slug: 'buceo',
  titulo: 'Buceo',
};

describe('mapTipoTarjeta', () => {
  it('mapea todos los campos', () => {
    const resultado = mapTipoTarjeta(TARJETA);
    expect(resultado).toEqual({
      slug: 'buceo',
      titulo: 'Buceo',
      resumen: 'Un resumen',
      nivelExigencia: 4,
      numeroDestinos: 6,
      imagen: expect.objectContaining({ src: '/media/x-400.webp' }),
    });
  });
});

describe('mapPaginaTipos', () => {
  it('mapea metadatos de paginación y resultados', () => {
    const dto: PaginaTipoAventuraTarjeta = {
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [TARJETA],
    };
    expect(mapPaginaTipos(dto).total).toBe(1);
  });
});

describe('mapRelacionado', () => {
  it('construye la ruta interna a partir del tipo', () => {
    expect(mapRelacionado({ origen: 'CURADO', slug: 'buceo', tipo: 'TIPO', titulo: 'Buceo' }).ruta).toBe(
      '/tipos-de-aventura/buceo',
    );
  });
});

describe('mapAlternativasRetirado', () => {
  it('lista vacía si no es un array', () => {
    expect(mapAlternativasRetirado(null)).toEqual([]);
  });
});

describe('mapTipoDetalle', () => {
  const DETALLE: TipoAventuraDetalleDto = {
    checklist: [{ esencial: true, grupo: 'Calzado', orden: 1, texto: 'Botas' }],
    descripcion: '<p>Descripción</p>',
    destinos: [],
    destinos_total: 0,
    fuentes: [],
    guias_relacionadas: [],
    metadatos: {
      autoria: 'Equipo editorial',
      fecha_ultima_revision: '2026-01-01',
      publicado_actualizado_en: '2026-01-01',
      seo_descripcion: 'x',
      seo_titulo: 'x',
    },
    nivel_exigencia: 4,
    portada: IMAGEN,
    relacionados: [],
    resumen: 'Un resumen',
    slug: 'buceo',
    terminos: [],
    titulo: 'Buceo',
  };

  it('mapea el detalle completo, incluido el checklist', () => {
    const resultado = mapTipoDetalle(DETALLE);
    expect(resultado.titulo).toBe('Buceo');
    expect(resultado.checklist).toEqual([{ texto: 'Botas', esencial: true, grupo: 'Calzado', orden: 1 }]);
  });

  it('checklist vacío se mapea a lista vacía (FEAT-011: sección oculta)', () => {
    expect(mapTipoDetalle({ ...DETALLE, checklist: [] }).checklist).toEqual([]);
  });
});
