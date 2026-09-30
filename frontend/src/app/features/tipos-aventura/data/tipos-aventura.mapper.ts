/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Tipos de aventura (Skill_Frontend
 * §5.3). Los DTO del cliente generado mueren aquí (Regla 04).
 */
import { ChecklistItem } from '../../../api/models/checklist-item';
import { ContenidoRelacionado } from '../../../api/models/contenido-relacionado';
import { DestinoTarjeta } from '../../../api/models/destino-tarjeta';
import { FuentePublica } from '../../../api/models/fuente-publica';
import { GuiaTarjeta as GuiaTarjetaDto } from '../../../api/models/guia-tarjeta';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ImagenPublicaNula } from '../../../api/models/imagen-publica-nula';
import { PaginaTipoAventuraTarjeta } from '../../../api/models/pagina-tipo-aventura-tarjeta';
import { RefTaxonomia } from '../../../api/models/ref-taxonomia';
import { TerminoRef } from '../../../api/models/termino-ref';
import { TipoAventuraDetalle as TipoAventuraDetalleDto } from '../../../api/models/tipo-aventura-detalle';
import { TipoAventuraTarjeta as TipoAventuraTarjetaDto } from '../../../api/models/tipo-aventura-tarjeta';
import {
  DestinoTarjetaVista,
  GuiaTarjetaVista,
  ImagenVista,
  PaginaTipos,
  RefTaxonomiaVista,
  TarjetaRelacionadaVista,
  TerminoRefVista,
  TipoDetalle,
  TipoTarjetaVista,
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

export function mapTipoTarjeta(dto: TipoAventuraTarjetaDto): TipoTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    nivelExigencia: dto.nivel_exigencia,
    numeroDestinos: dto.numero_destinos,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapPaginaTipos(dto: PaginaTipoAventuraTarjeta): PaginaTipos {
  return {
    resultados: dto.resultados.map(mapTipoTarjeta),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
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

function mapGuiaTarjeta(dto: GuiaTarjetaDto): GuiaTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    categoria: mapRef(dto.categoria),
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapFuente(dto: FuentePublica) {
  return { titulo: dto.titulo, url: dto.url ?? null, entidadEditora: dto.entidad_editora ?? null };
}

function mapTermino(dto: TerminoRef): TerminoRefVista {
  return { slug: dto.slug, termino: dto.termino };
}

function mapChecklistItem(dto: ChecklistItem) {
  return { texto: dto.texto, esencial: dto.esencial, grupo: dto.grupo ?? null, orden: dto.orden };
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

export function mapTipoDetalle(dto: TipoAventuraDetalleDto): TipoDetalle {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    descripcion: dto.descripcion,
    nivelExigencia: dto.nivel_exigencia,
    portada: mapImagen(dto.portada),
    destinos: dto.destinos.map(mapDestinoTarjeta),
    destinosTotal: dto.destinos_total,
    checklist: dto.checklist.map(mapChecklistItem),
    guiasRelacionadas: dto.guias_relacionadas.map(mapGuiaTarjeta),
    terminos: dto.terminos.map(mapTermino),
    fuentes: dto.fuentes.map(mapFuente),
    relacionados: dto.relacionados.map(mapRelacionado),
    autoria: dto.metadatos.autoria,
    fechaUltimaRevision: dto.metadatos.fecha_ultima_revision,
  };
}
