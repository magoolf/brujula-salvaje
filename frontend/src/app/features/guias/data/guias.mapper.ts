/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Guías (Skill_Frontend §5.3). Los DTO
 * del cliente generado mueren aquí (Regla 04).
 */
import { CategoriaGuiaIndice } from '../../../api/models/categoria-guia-indice';
import { CategoriaGuiaPublica } from '../../../api/models/categoria-guia-publica';
import { ContenidoRelacionado } from '../../../api/models/contenido-relacionado';
import { DestinoTarjeta } from '../../../api/models/destino-tarjeta';
import { FuentePublica } from '../../../api/models/fuente-publica';
import { GuiaDetalle as GuiaDetalleDto } from '../../../api/models/guia-detalle';
import { GuiaTarjeta as GuiaTarjetaDto } from '../../../api/models/guia-tarjeta';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ImagenPublicaNula } from '../../../api/models/imagen-publica-nula';
import { PaginaCategoriaGuiaIndice } from '../../../api/models/pagina-categoria-guia-indice';
import { PaginaGuiaTarjeta } from '../../../api/models/pagina-guia-tarjeta';
import { RefTaxonomia } from '../../../api/models/ref-taxonomia';
import { TerminoRef } from '../../../api/models/termino-ref';
import {
  CategoriaGuiaIndiceVista,
  DestinoTarjetaVista,
  GuiaDetalle,
  GuiaTarjetaVista,
  ImagenVista,
  PaginaCategorias,
  PaginaGuias,
  RefTaxonomiaVista,
  TarjetaRelacionadaVista,
  TerminoRefVista,
} from '../domain/modelos';

export function mapRef(dto: RefTaxonomia): RefTaxonomiaVista {
  return { slug: dto.slug, nombre: dto.nombre };
}

export function mapImagen(dto: ImagenPublicaNula | ImagenPublica | undefined): ImagenVista | null {
  if (dto === undefined || dto === null) return null;
  return {
    src: dto.derivados[0]?.url ?? '',
    alt: dto.texto_alternativo,
    ancho: dto.ancho ?? 0,
    alto: dto.alto ?? 0,
    derivados: dto.derivados.map((d) => ({ url: d.url, ancho: d.ancho })),
    autorCredito: dto.autor_credito,
    pieDeFoto: dto.pie_de_foto ?? null,
    licenciaNombre: dto.licencia.nombre,
    licenciaUrl: dto.licencia.url_texto_legal ?? null,
  };
}

export function mapGuiaTarjeta(dto: GuiaTarjetaDto): GuiaTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    categoria: mapRef(dto.categoria),
    fechaUltimaRevision: dto.fecha_ultima_revision,
    minutosLectura: dto.minutos_lectura ?? null,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapCategoriaIndice(dto: CategoriaGuiaIndice): CategoriaGuiaIndiceVista {
  return {
    slug: dto.slug,
    nombre: dto.nombre,
    descripcion: dto.descripcion,
    numeroGuias: dto.numero_guias,
    guiasRecientes: dto.guias_recientes.map(mapGuiaTarjeta),
  };
}

export function mapPaginaCategorias(dto: PaginaCategoriaGuiaIndice): PaginaCategorias {
  return {
    resultados: dto.resultados.map(mapCategoriaIndice),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}

export function mapPaginaGuias(dto: PaginaGuiaTarjeta): PaginaGuias {
  return {
    resultados: dto.resultados.map(mapGuiaTarjeta),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}

export function mapCategoria(dto: CategoriaGuiaPublica): RefTaxonomiaVista & { readonly descripcion: string } {
  return { slug: dto.slug, nombre: dto.nombre, descripcion: dto.descripcion };
}

function mapDestinoTarjeta(dto: DestinoTarjeta): DestinoTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    pais: mapRef(dto.pais),
    region: mapRef(dto.region),
    dificultad: dto.dificultad,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapFuente(dto: FuentePublica) {
  return { titulo: dto.titulo, url: dto.url ?? null, entidadEditora: dto.entidad_editora ?? null };
}

function mapTermino(dto: TerminoRef): TerminoRefVista {
  return { slug: dto.slug, termino: dto.termino };
}

const RUTA_POR_TIPO: Record<string, string> = {
  DESTINO: '/destinos',
  ITINERARIO: '/itinerarios',
  GUIA: '/guias',
  TIPO: '/tipos-de-aventura',
  COLECCION: '/colecciones',
};

export function mapRelacionado(dto: ContenidoRelacionado): TarjetaRelacionadaVista {
  return {
    tipo: dto.tipo,
    slug: dto.slug,
    ruta: `${RUTA_POR_TIPO[dto.tipo] ?? ''}/${dto.slug}`,
    titulo: dto.titulo,
    resumen: dto.resumen ?? null,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapAlternativasRetirado(valor: unknown): readonly TarjetaRelacionadaVista[] {
  if (!Array.isArray(valor)) return [];
  const resultado: TarjetaRelacionadaVista[] = [];
  for (const item of valor) {
    if (typeof item === 'object' && item !== null && 'slug' in item && 'titulo' in item && 'tipo' in item) {
      resultado.push(mapRelacionado(item as ContenidoRelacionado));
    }
  }
  return resultado;
}

export function mapGuiaDetalle(dto: GuiaDetalleDto): GuiaDetalle {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    categoria: mapRef(dto.categoria),
    cuerpo: dto.cuerpo,
    minutosLectura: dto.minutos_lectura ?? null,
    portada: mapImagen(dto.portada),
    destinosRelacionados: dto.destinos_relacionados.map(mapDestinoTarjeta),
    tiposRelacionados: dto.tipos_relacionados.map(mapRef),
    remiteAMetodologia: dto.remite_a_metodologia,
    terminos: dto.terminos.map(mapTermino),
    fuentes: dto.fuentes.map(mapFuente),
    relacionados: dto.relacionados.map(mapRelacionado),
    autoria: dto.metadatos.autoria,
    fechaUltimaRevision: dto.metadatos.fecha_ultima_revision,
  };
}
