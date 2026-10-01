/**
 * DATA: traducción del contrato de medios (DTO generados desde contracts/openapi.yaml, tag
 * panel-medios) al dominio del panel y a la inversa. Los DTO no salen de esta carpeta (Regla 04).
 */
import { Licencia } from '../../../api/models/licencia';
import { MedioCatalogacionEntrada } from '../../../api/models/medio-catalogacion-entrada';
import { MedioPanel } from '../../../api/models/medio-panel';
import { PaginaMedioPanel } from '../../../api/models/pagina-medio-panel';
import { PaginaUsoMedio } from '../../../api/models/pagina-uso-medio';
import { ResultadoSubida } from '../../../api/models/resultado-subida';
import { PanelListarMedios$Params } from '../../../api/fn/panel-medios/panel-listar-medios';
import {
  EntradaCatalogacion,
  FiltrosMedios,
  LicenciaCatalogo,
  Medio,
  PaginaMedios,
  PaginaUsos,
  ResultadoArchivo,
} from '../domain/medios';

export function mapMedio(dto: MedioPanel): Medio {
  return {
    id: dto.id,
    estado: dto.estado,
    tituloInterno: dto.titulo_interno ?? null,
    textoAlternativo: dto.texto_alternativo ?? null,
    pieDeFoto: dto.pie_de_foto ?? null,
    autorCredito: dto.autor_credito ?? null,
    fuenteUrl: dto.fuente_url ?? null,
    licencia: dto.licencia
      ? {
          id: dto.licencia.id,
          codigo: dto.licencia.codigo,
          nombre: dto.licencia.nombre,
          compatiblePublicacion: dto.licencia.compatible_publicacion,
        }
      : null,
    formatoOrigen: dto.formato_origen,
    anchoPx: dto.ancho_px,
    altoPx: dto.alto_px,
    pesoBytes: dto.peso_bytes,
    derivados: dto.derivados.map((d) => ({
      formato: d.formato,
      ancho: d.ancho,
      alto: d.alto ?? null,
      url: d.url,
    })),
    numeroUsos: dto.numero_usos,
    enUsoPublicado: dto.en_uso_publicado,
    subidoPor: dto.subido_por.etiqueta,
    subidoEn: new Date(dto.subido_en),
    actualizadoEn: new Date(dto.actualizado_en),
    pendientes: [...dto.pendientes_catalogacion],
  };
}

export function mapPaginaMedios(dto: PaginaMedioPanel): PaginaMedios {
  return {
    medios: dto.resultados.map(mapMedio),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
  };
}

export function mapPaginaUsos(dto: PaginaUsoMedio): PaginaUsos {
  return {
    usos: dto.resultados.map((u) => ({
      tipoContenido: u.tipo_contenido,
      contenidoId: u.contenido_id,
      titulo: u.titulo,
      estadoEditorial: u.estado_editorial ?? null,
      rol: u.rol,
    })),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
  };
}

/** Licencia del catálogo: los campos opcionales del contrato toman el valor más restrictivo. */
export function mapLicencia(dto: Licencia): LicenciaCatalogo {
  return {
    id: dto.id,
    codigo: dto.codigo ?? '',
    nombre: dto.nombre ?? dto.codigo ?? `Licencia ${dto.id}`,
    compatiblePublicacion: dto.compatible_publicacion ?? false,
    activa: dto.activo ?? false,
  };
}

export function mapResultadoSubida(dto: ResultadoSubida): readonly ResultadoArchivo[] {
  return dto.resultados.map((r) => ({
    nombreArchivo: r.nombre_archivo,
    resultado: r.resultado,
    medio: r.medio ? mapMedio(r.medio) : null,
    medioExistenteId: r.medio_existente_id ?? null,
    motivo: r.motivo?.code ?? null,
    local: false,
  }));
}

export function paramsListado(filtros: FiltrosMedios): PanelListarMedios$Params {
  return {
    estado: filtros.estado ?? undefined,
    licencia: filtros.licencia ?? undefined,
    en_uso: filtros.enUso ?? undefined,
    q: filtros.q === '' ? undefined : filtros.q,
    pagina: filtros.pagina > 1 ? filtros.pagina : undefined,
  };
}

/** Solo se envían los campos presentes en la entrada (PUT con semántica de campos opcionales). */
export function aCatalogacionDto(entrada: EntradaCatalogacion): MedioCatalogacionEntrada {
  const dto: MedioCatalogacionEntrada = {};
  if (entrada.tituloInterno !== undefined) dto.titulo_interno = entrada.tituloInterno;
  if (entrada.textoAlternativo !== undefined) dto.texto_alternativo = entrada.textoAlternativo;
  if (entrada.pieDeFoto !== undefined) dto.pie_de_foto = entrada.pieDeFoto;
  if (entrada.autorCredito !== undefined) dto.autor_credito = entrada.autorCredito;
  if (entrada.fuenteUrl !== undefined) dto.fuente_url = entrada.fuenteUrl;
  if (entrada.licenciaId !== undefined) dto.licencia_id = entrada.licenciaId;
  return dto;
}
