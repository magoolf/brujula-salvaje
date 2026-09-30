/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Destinos (Skill_Frontend §5.3). Los
 * DTO del cliente generado (`api/models`) mueren aquí (Regla 04): `state/` y `ui/` solo ven los
 * tipos de `domain/modelos.ts`.
 */
import { ContenidoRelacionado } from '../../../api/models/contenido-relacionado';
import { DestinoDetalle as DestinoDetalleDto } from '../../../api/models/destino-detalle';
import { DestinoMapaItem } from '../../../api/models/destino-mapa-item';
import { DestinoTarjeta as DestinoTarjetaDto } from '../../../api/models/destino-tarjeta';
import { FacetasDestinos as FacetasDestinosDto } from '../../../api/models/facetas-destinos';
import { GuiaTarjeta as GuiaTarjetaDto } from '../../../api/models/guia-tarjeta';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ImagenPublicaNula } from '../../../api/models/imagen-publica-nula';
import { ItinerarioTarjeta as ItinerarioTarjetaDto } from '../../../api/models/itinerario-tarjeta';
import { Meses } from '../../../api/models/meses';
import { PaginaDestinoMapa } from '../../../api/models/pagina-destino-mapa';
import { PaginaDestinoTarjeta } from '../../../api/models/pagina-destino-tarjeta';
import { RefTaxonomia } from '../../../api/models/ref-taxonomia';
import {
  DestinoDetalle,
  FacetasDestinos,
  FuenteVista,
  GuiaTarjetaVista,
  ImagenVista,
  ItinerarioTarjetaVista,
  MesResumen,
  PaginaDestinos,
  PaginaMapa,
  PuntoMapa,
  RefTaxonomiaVista,
  TarjetaDestino,
  TarjetaRelacionada,
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

export function mapTarjetaDestino(dto: DestinoTarjetaDto): TarjetaDestino {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    pais: mapRef(dto.pais),
    region: mapRef(dto.region),
    tipos: dto.tipos.map(mapRef),
    dificultad: dto.dificultad,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapPaginaDestinos(dto: PaginaDestinoTarjeta): PaginaDestinos {
  return {
    resultados: dto.resultados.map(mapTarjetaDestino),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}

export function mapFacetas(dto: FacetasDestinosDto): FacetasDestinos {
  return {
    tipos: dto.tipos.map(mapRef),
    regiones: dto.regiones.map((r) => ({
      slug: r.slug,
      nombre: r.nombre,
      continente: r.continente,
      paises: r.paises.map(mapRef),
    })),
    dificultad: dto.dificultad.map((n) => ({ nivel: n.nivel, etiqueta: n.etiqueta, descripcion: n.descripcion })),
    presupuesto: dto.presupuesto.map((n) => ({ nivel: n.nivel, etiqueta: n.etiqueta, descripcion: n.descripcion })),
    tramosDuracion: dto.tramos_duracion.map((t) => ({
      codigo: t.codigo,
      etiqueta: t.etiqueta,
      minDias: t.min_dias,
      maxDias: t.max_dias ?? null,
    })),
  };
}

export function mapPuntoMapa(dto: DestinoMapaItem): PuntoMapa {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    pais: dto.pais.nombre,
    region: mapRef(dto.region),
    dificultad: dto.dificultad,
    latitud: dto.latitud,
    longitud: dto.longitud,
  };
}

export function mapPaginaMapa(dto: PaginaDestinoMapa): PaginaMapa {
  return {
    resultados: dto.resultados.map(mapPuntoMapa),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
  };
}

function mapItinerarioTarjeta(dto: ItinerarioTarjetaDto): ItinerarioTarjetaVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    duracionDias: dto.duracion_dias,
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

const RUTA_POR_TIPO: Record<string, string> = {
  DESTINO: '/destinos',
  ITINERARIO: '/itinerarios',
  GUIA: '/guias',
  TIPO: '/tipos-de-aventura',
  COLECCION: '/colecciones',
};

export function mapRelacionado(dto: ContenidoRelacionado): TarjetaRelacionada {
  return {
    tipo: dto.tipo,
    slug: dto.slug,
    ruta: `${RUTA_POR_TIPO[dto.tipo] ?? ''}/${dto.slug}`,
    titulo: dto.titulo,
    resumen: dto.resumen ?? null,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapFuente(dto: { titulo: string; url?: string | null; entidad_editora?: string | null }): FuenteVista {
  return { titulo: dto.titulo, url: dto.url ?? null, entidadEditora: dto.entidad_editora ?? null };
}

export function mapDestinoDetalle(dto: DestinoDetalleDto): DestinoDetalle {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    pais: mapRef(dto.pais),
    region: mapRef(dto.pais.region),
    portada: mapImagen(dto.portada),
    galeria: dto.galeria.map((g) => mapImagen(g)).filter((i): i is ImagenVista => i !== null),
    dificultad: dto.dificultad,
    nivelPresupuesto: dto.nivel_presupuesto,
    mesesMejorEpoca: dto.meses_mejor_epoca,
    duracionMinDias: dto.duracion_min_dias,
    duracionMaxDias: dto.duracion_max_dias,
    clima: dto.clima,
    altitudMaxM: dto.altitud_max_m ?? null,
    descripcionExperta: dto.descripcion_experta,
    comoLlegar: dto.como_llegar,
    seguridadRiesgos: dto.seguridad_riesgos,
    sostenibilidad: dto.sostenibilidad,
    latitud: dto.latitud,
    longitud: dto.longitud,
    tipoPrincipal: mapRef(dto.tipo_principal),
    tipos: dto.tipos.map(mapRef),
    itinerarios: dto.itinerarios.map(mapItinerarioTarjeta),
    itinerariosAfines: dto.itinerarios_afines.map(mapItinerarioTarjeta),
    guiasRelacionadas: dto.guias_relacionadas.map(mapGuiaTarjeta),
    relacionados: dto.relacionados.map(mapRelacionado),
    fuentes: dto.fuentes.map(mapFuente),
    autoria: dto.metadatos.autoria,
    fechaUltimaRevision: dto.metadatos.fecha_ultima_revision,
  };
}

/**
 * Alternativas de un 410 (`ProblemaRetirado.alternativas`), leídas desde `ErrorApi.extra` (ya
 * validado por `normalizarError`, pero se trata igual como dato externo: cualquier forma
 * inesperada produce una lista vacía en vez de lanzar).
 */
export function mapAlternativasRetirado(valor: unknown): readonly TarjetaRelacionada[] {
  if (!Array.isArray(valor)) return [];
  const resultado: TarjetaRelacionada[] = [];
  for (const item of valor) {
    if (
      typeof item === 'object' &&
      item !== null &&
      'slug' in item &&
      'titulo' in item &&
      'tipo' in item
    ) {
      resultado.push(mapRelacionado(item as ContenidoRelacionado));
    }
  }
  return resultado;
}

export function mapMeses(dto: Meses): readonly MesResumen[] {
  return dto.meses.map((m) => ({
    mes: m.mes,
    nombre: m.nombre,
    slug: m.slug,
    numeroDestinos: m.numero_destinos,
    destacado: m.destacado ? mapTarjetaDestino(m.destacado) : null,
  }));
}
