/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Glosario (Skill_Frontend §5.3). Los DTO
 * del cliente generado mueren aquí (Regla 04).
 */
import { ContenidoRefPublico } from '../../../api/models/contenido-ref-publico';
import { PaginaTerminoGlosarioPublico } from '../../../api/models/pagina-termino-glosario-publico';
import { TerminoGlosarioPublico } from '../../../api/models/termino-glosario-publico';
import { ContenidoRefVista, PaginaGlosario, TerminoGlosarioVista } from '../domain/modelos';

const RUTA_POR_TIPO: Record<string, string> = {
  DESTINO: '/destinos',
  ITINERARIO: '/itinerarios',
  GUIA: '/guias',
  TIPO: '/tipos-de-aventura',
  COLECCION: '/colecciones',
};

export function mapContenidoRef(dto: ContenidoRefPublico): ContenidoRefVista {
  return {
    tipo: dto.tipo,
    slug: dto.slug,
    titulo: dto.titulo,
    ruta: `${RUTA_POR_TIPO[dto.tipo] ?? ''}/${dto.slug}`,
  };
}

export function mapTermino(dto: TerminoGlosarioPublico): TerminoGlosarioVista {
  return {
    slug: dto.slug,
    termino: dto.termino,
    definicion: dto.definicion,
    usadoEn: dto.usado_en.map(mapContenidoRef),
  };
}

export function mapPaginaGlosario(dto: PaginaTerminoGlosarioPublico): PaginaGlosario {
  return {
    resultados: dto.resultados.map(mapTermino),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}
