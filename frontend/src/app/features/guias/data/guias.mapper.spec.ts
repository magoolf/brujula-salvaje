import { CategoriaGuiaIndice } from '../../../api/models/categoria-guia-indice';
import { GuiaDetalle as GuiaDetalleDto } from '../../../api/models/guia-detalle';
import { GuiaTarjeta as GuiaTarjetaDto } from '../../../api/models/guia-tarjeta';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import {
  mapAlternativasRetirado,
  mapCategoria,
  mapCategoriaIndice,
  mapGuiaDetalle,
  mapGuiaTarjeta,
  mapPaginaCategorias,
  mapPaginaGuias,
} from './guias.mapper';

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

const GUIA_TARJETA: GuiaTarjetaDto = {
  categoria: { slug: 'seguridad', nombre: 'Seguridad' },
  fecha_ultima_revision: '2026-01-01',
  minutos_lectura: 6,
  portada: IMAGEN,
  resumen: 'Un resumen',
  slug: 'primeros-auxilios',
  titulo: 'Primeros auxilios en montaña',
};

describe('mapGuiaTarjeta', () => {
  it('mapea todos los campos', () => {
    const resultado = mapGuiaTarjeta(GUIA_TARJETA);
    expect(resultado.minutosLectura).toBe(6);
    expect(resultado.categoria).toEqual({ slug: 'seguridad', nombre: 'Seguridad' });
  });

  it('sin minutos_lectura produce null', () => {
    expect(mapGuiaTarjeta({ ...GUIA_TARJETA, minutos_lectura: null }).minutosLectura).toBeNull();
  });
});

describe('mapCategoriaIndice', () => {
  it('mapea numero_guias y guias_recientes', () => {
    const dto: CategoriaGuiaIndice = {
      descripcion: 'x',
      nombre: 'Seguridad',
      slug: 'seguridad',
      numero_guias: 5,
      guias_recientes: [GUIA_TARJETA],
    };
    const resultado = mapCategoriaIndice(dto);
    expect(resultado.numeroGuias).toBe(5);
    expect(resultado.guiasRecientes).toHaveLength(1);
  });
});

describe('mapPaginaCategorias / mapPaginaGuias', () => {
  it('mapean metadatos de paginación', () => {
    const paginaCategorias = mapPaginaCategorias({
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 0,
      total_paginas: 1,
      resultados: [],
    });
    expect(paginaCategorias.total).toBe(0);

    const paginaGuias = mapPaginaGuias({
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [GUIA_TARJETA],
    });
    expect(paginaGuias.resultados).toHaveLength(1);
  });
});

describe('mapCategoria', () => {
  it('mapea slug, nombre y descripción', () => {
    expect(mapCategoria({ slug: 'seguridad', nombre: 'Seguridad', descripcion: 'x' })).toEqual({
      slug: 'seguridad',
      nombre: 'Seguridad',
      descripcion: 'x',
    });
  });
});

describe('mapAlternativasRetirado', () => {
  it('lista vacía si no es un array', () => {
    expect(mapAlternativasRetirado(42)).toEqual([]);
  });
});

describe('mapGuiaDetalle', () => {
  const DETALLE: GuiaDetalleDto = {
    categoria: { slug: 'seguridad', nombre: 'Seguridad', descripcion: 'x' },
    cuerpo: '<p>Cuerpo</p>',
    destinos_relacionados: [],
    fuentes: [],
    metadatos: {
      autoria: 'Equipo editorial',
      fecha_ultima_revision: '2026-01-01',
      publicado_actualizado_en: '2026-01-01',
      seo_descripcion: 'x',
      seo_titulo: 'x',
    },
    minutos_lectura: 8,
    portada: IMAGEN,
    relacionados: [],
    remite_a_metodologia: true,
    resumen: 'Un resumen',
    slug: 'primeros-auxilios',
    terminos: [],
    tipos_relacionados: [],
    titulo: 'Primeros auxilios en montaña',
  };

  it('mapea el detalle completo', () => {
    const resultado = mapGuiaDetalle(DETALLE);
    expect(resultado.titulo).toBe('Primeros auxilios en montaña');
    expect(resultado.remiteAMetodologia).toBe(true);
    expect(resultado.minutosLectura).toBe(8);
  });
});
