/**
 * DATA: traducción del contrato OpenAPI hacia el dominio de Institucional (Skill_Frontend §5.3).
 * Los DTO del cliente generado mueren aquí (Regla 04).
 */
import { ConfiguracionPublica } from '../../../api/models/configuracion-publica';
import { ContenidoRefPublico } from '../../../api/models/contenido-ref-publico';
import { CreditoMedio } from '../../../api/models/credito-medio';
import { Escalas } from '../../../api/models/escalas';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { NivelEscala } from '../../../api/models/nivel-escala';
import { PaginaCreditoMedio } from '../../../api/models/pagina-credito-medio';
import { PaginaInstitucionalPublica } from '../../../api/models/pagina-institucional-publica';
import {
  ConfiguracionVista,
  ContenidoRefVista,
  CreditoMedioVista,
  EscalasVista,
  ImagenVista,
  NivelEscalaVista,
  PaginaCreditos,
  PaginaInstitucionalVista,
} from '../domain/modelos';

const RUTA_POR_TIPO: Record<string, string> = {
  DESTINO: '/destinos',
  ITINERARIO: '/itinerarios',
  GUIA: '/guias',
  TIPO: '/tipos-de-aventura',
  COLECCION: '/colecciones',
};

export function mapContenidoRef(dto: ContenidoRefPublico): ContenidoRefVista {
  return { tipo: dto.tipo, slug: dto.slug, titulo: dto.titulo, ruta: `${RUTA_POR_TIPO[dto.tipo] ?? ''}/${dto.slug}` };
}

export function mapImagen(dto: ImagenPublica): ImagenVista {
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
    fuenteUrl: dto.fuente_url ?? null,
  };
}

export function mapPaginaInstitucional(dto: PaginaInstitucionalPublica): PaginaInstitucionalVista {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    cuerpo: dto.cuerpo,
    versionDocumento: dto.version_documento,
    vigenteDesde: dto.vigente_desde,
    autoria: dto.metadatos.autoria,
    fechaUltimaRevision: dto.metadatos.fecha_ultima_revision,
  };
}

function mapNivelEscala(dto: NivelEscala): NivelEscalaVista {
  return { escala: dto.escala, nivel: dto.nivel, etiqueta: dto.etiqueta, descripcion: dto.descripcion };
}

export function mapEscalas(dto: Escalas): EscalasVista {
  return { dificultad: dto.dificultad.map(mapNivelEscala), presupuesto: dto.presupuesto.map(mapNivelEscala) };
}

export function mapConfiguracion(dto: ConfiguracionPublica): ConfiguracionVista {
  return {
    nombreMarca: dto.nombre_marca,
    lema: dto.lema ?? null,
    textoDescargo: dto.texto_descargo,
    responsable: {
      definido: dto.responsable.definido,
      nombre: dto.responsable.nombre ?? null,
      identificacion: dto.responsable.identificacion ?? null,
      domicilio: dto.responsable.domicilio ?? null,
      canalAtencion: dto.responsable.canal_atencion ?? null,
    },
  };
}

export function mapCreditoMedio(dto: CreditoMedio): CreditoMedioVista {
  return { imagen: mapImagen(dto.imagen), usadoEn: dto.usado_en.map(mapContenidoRef) };
}

export function mapPaginaCreditos(dto: PaginaCreditoMedio): PaginaCreditos {
  return {
    resultados: dto.resultados.map(mapCreditoMedio),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
    tamanoPagina: dto.tamano_pagina,
  };
}
