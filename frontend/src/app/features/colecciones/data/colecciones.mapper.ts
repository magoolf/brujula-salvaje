/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Colecciones (Skill_Frontend §5.3). Los
 * DTO del cliente generado mueren aquí (Regla 04).
 */
import { ColeccionDetalle as ColeccionDetalleDto } from '../../../api/models/coleccion-detalle';
import { ColeccionTarjeta as ColeccionTarjetaDto } from '../../../api/models/coleccion-tarjeta';
import { ContenidoRelacionado } from '../../../api/models/contenido-relacionado';
import { DestinoTarjeta } from '../../../api/models/destino-tarjeta';
import { ElementoColeccion } from '../../../api/models/elemento-coleccion';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ImagenPublicaNula } from '../../../api/models/imagen-publica-nula';
import { ItinerarioTarjeta } from '../../../api/models/itinerario-tarjeta';
import { PaginaColeccionTarjeta } from '../../../api/models/pagina-coleccion-tarjeta';
import { RefTaxonomia } from '../../../api/models/ref-taxonomia';
import {
  ColeccionDetalle,
  ColeccionTarjetaVista,
  DestinoTarjetaVista,
  ElementoColeccionVista,
  ImagenVista,
  ItinerarioTarjetaVista,
  PaginaColecciones,
  RefTaxonomiaVista,
  TarjetaRelacionadaVista,
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

export function mapColeccionTarjeta(dto: ColeccionTarjetaDto): ColeccionTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    numeroElementos: dto.numero_elementos,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapPaginaColecciones(dto: PaginaColeccionTarjeta): PaginaColecciones {
  return {
    resultados: dto.resultados.map(mapColeccionTarjeta),
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
    dificultad: dto.dificultad,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapItinerarioTarjeta(dto: ItinerarioTarjeta): ItinerarioTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    destino: mapRef(dto.destino),
    dificultad: dto.dificultad,
    duracionDias: dto.duracion_dias,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

/**
 * RULE-024: solo elementos publicados. Un elemento con la forma inesperada (tipo sin su
 * destino/itinerario correspondiente) se descarta en vez de lanzar (dato externo no confiable).
 */
export function mapElemento(dto: ElementoColeccion): ElementoColeccionVista | null {
  if (dto.tipo === 'DESTINO' && dto.destino) {
    return { tipo: 'DESTINO', orden: dto.orden, notaEditorial: dto.nota_editorial ?? null, destino: mapDestinoTarjeta(dto.destino) };
  }
  if (dto.tipo === 'ITINERARIO' && dto.itinerario) {
    return {
      tipo: 'ITINERARIO',
      orden: dto.orden,
      notaEditorial: dto.nota_editorial ?? null,
      itinerario: mapItinerarioTarjeta(dto.itinerario),
    };
  }
  return null;
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

export function mapColeccionDetalle(dto: ColeccionDetalleDto): ColeccionDetalle {
  const elementos: ElementoColeccionVista[] = [];
  for (const el of dto.elementos) {
    const mapeado = mapElemento(el);
    if (mapeado !== null) elementos.push(mapeado);
  }
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    descripcion: dto.descripcion,
    portada: mapImagen(dto.portada),
    elementos,
    autoria: dto.metadatos.autoria,
    fechaUltimaRevision: dto.metadatos.fecha_ultima_revision,
  };
}
