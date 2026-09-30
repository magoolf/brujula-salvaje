/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Búsqueda (Skill_Frontend §5.3). Los
 * DTO del cliente generado mueren aquí (Regla 04).
 */
import { BusquedaAgrupada } from '../../../api/models/busqueda-agrupada';
import { GrupoBusqueda } from '../../../api/models/grupo-busqueda';
import { PaginaResultadoBusqueda } from '../../../api/models/pagina-resultado-busqueda';
import { ResultadoBusqueda } from '../../../api/models/resultado-busqueda';
import {
  BusquedaAgrupadaVista,
  GrupoBusquedaVista,
  ImagenVista,
  PaginaResultados,
  ResultadoBusquedaVista,
} from '../domain/modelos';

const RUTA_POR_TIPO: Record<string, string> = {
  DESTINO: '/destinos',
  ITINERARIO: '/itinerarios',
  GUIA: '/guias',
  TIPO: '/tipos-de-aventura',
};

function mapImagen(dto: ResultadoBusqueda['portada']): ImagenVista | null {
  if (dto === undefined || dto === null) return null;
  return {
    src: dto.derivados[0]?.url ?? '',
    alt: dto.texto_alternativo,
    ancho: dto.ancho ?? 0,
    alto: dto.alto ?? 0,
    derivados: dto.derivados.map((d) => ({ url: d.url, ancho: d.ancho })),
  };
}

export function mapResultado(dto: ResultadoBusqueda): ResultadoBusquedaVista {
  return {
    tipo: dto.tipo,
    slug: dto.slug,
    ruta: `${RUTA_POR_TIPO[dto.tipo] ?? ''}/${dto.slug}`,
    titulo: dto.titulo,
    resumen: dto.resumen ?? null,
    pais: dto.pais ?? null,
    imagen: mapImagen(dto.portada),
  };
}

function mapGrupo(dto: GrupoBusqueda): GrupoBusquedaVista {
  return { resultados: dto.resultados.map(mapResultado), total: dto.total };
}

export function mapBusquedaAgrupada(dto: BusquedaAgrupada): BusquedaAgrupadaVista {
  return {
    total: dto.total,
    grupos: {
      destinos: mapGrupo(dto.grupos.destinos),
      itinerarios: mapGrupo(dto.grupos.itinerarios),
      guias: mapGrupo(dto.grupos.guias),
      tipos: mapGrupo(dto.grupos.tipos),
    },
  };
}

export function mapPaginaResultados(dto: PaginaResultadoBusqueda): PaginaResultados {
  return {
    resultados: dto.resultados.map(mapResultado),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}
