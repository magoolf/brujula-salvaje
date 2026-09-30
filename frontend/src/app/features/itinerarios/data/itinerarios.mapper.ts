/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Itinerarios (Skill_Frontend §5.3). Los
 * DTO del cliente generado mueren aquí (Regla 04): `state/` y `ui/` solo ven `domain/modelos.ts`.
 */
import { ContenidoRelacionado } from '../../../api/models/contenido-relacionado';
import { DestinoTarjeta } from '../../../api/models/destino-tarjeta';
import { DiaItinerario } from '../../../api/models/dia-itinerario';
import { FuentePublica } from '../../../api/models/fuente-publica';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ImagenPublicaNula } from '../../../api/models/imagen-publica-nula';
import { ItinerarioDetalle as ItinerarioDetalleDto } from '../../../api/models/itinerario-detalle';
import { ItinerarioTarjeta as ItinerarioTarjetaDto } from '../../../api/models/itinerario-tarjeta';
import { PaginaItinerarioTarjeta } from '../../../api/models/pagina-itinerario-tarjeta';
import { RefTaxonomia } from '../../../api/models/ref-taxonomia';
import { TerminoRef } from '../../../api/models/termino-ref';
import {
  DestinoRefVista,
  ImagenVista,
  ItinerarioDetalle,
  ItinerarioTarjetaVista,
  PaginaItinerarios,
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

export function mapItinerarioTarjeta(dto: ItinerarioTarjetaDto): ItinerarioTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    destino: mapRef(dto.destino),
    dificultad: dto.dificultad,
    duracionDias: dto.duracion_dias,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapPaginaItinerarios(dto: PaginaItinerarioTarjeta): PaginaItinerarios {
  return {
    resultados: dto.resultados.map(mapItinerarioTarjeta),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}

function mapDestinoRef(dto: DestinoTarjeta): DestinoRefVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    pais: mapRef(dto.pais),
    region: mapRef(dto.region),
    dificultad: dto.dificultad,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapFuente(dto: FuentePublica): { titulo: string; url: string | null; entidadEditora: string | null } {
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

/** Alternativas de un 410 (`ProblemaRetirado.alternativas`), tratadas como dato NO confiable. */
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

function mapDia(dto: DiaItinerario) {
  return {
    numeroDia: dto.numero_dia,
    titulo: dto.titulo,
    actividades: dto.actividades,
    distanciaKm: dto.distancia_km ?? null,
    desnivelPositivoM: dto.desnivel_positivo_m ?? null,
    desnivelNegativoM: dto.desnivel_negativo_m ?? null,
    alojamientoOrientativo: dto.alojamiento_orientativo ?? null,
    consejos: dto.consejos ?? null,
  };
}

export function mapItinerarioDetalle(dto: ItinerarioDetalleDto): ItinerarioDetalle {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    destino: mapDestinoRef(dto.destino),
    dificultad: dto.dificultad,
    duracionDias: dto.duracion_dias,
    distanciaTotalKm: dto.distancia_total_km ?? null,
    desnivelAcumuladoM: dto.desnivel_acumulado_m ?? null,
    dias: dto.dias.map(mapDia),
    riesgosSeguridad: dto.riesgos_seguridad,
    portada: mapImagen(dto.portada),
    galeria: dto.galeria.map((g) => mapImagen(g)).filter((i): i is ImagenVista => i !== null),
    tipos: dto.tipos.map(mapRef),
    terminos: dto.terminos.map(mapTermino),
    fuentes: dto.fuentes.map(mapFuente),
    relacionados: dto.relacionados.map(mapRelacionado),
    autoria: dto.metadatos.autoria,
    fechaUltimaRevision: dto.metadatos.fecha_ultima_revision,
  };
}
