/**
 * DATA: traducción del contrato (DTO generados desde contracts/openapi.yaml) al dominio del panel.
 * Los DTO no salen de esta carpeta (Skill_Frontend Regla 04).
 */
import { AutorizacionVigente } from '../../../api/models/autorizacion-vigente';
import { ContenidoRefPanel } from '../../../api/models/contenido-ref-panel';
import { ContenidoResumenPanel } from '../../../api/models/contenido-resumen-panel';
import { MfaActivacionInicio } from '../../../api/models/mfa-activacion-inicio';
import { SesionEstado } from '../../../api/models/sesion-estado';
import { Tablero } from '../../../api/models/tablero';
import {
  ActivacionMfa,
  AutorizacionTratamiento,
  ContenidoRef,
  ContenidoReciente,
  SaludEditorial,
  SesionPanel,
  TableroPanel,
} from '../domain/modelos';

export function mapSesion(dto: SesionEstado): SesionPanel {
  return {
    usuario: dto.usuario,
    nombreVisible: dto.nombre_visible,
    rol: dto.rol,
    pasoPendiente: dto.paso_pendiente,
    mfaActivo: dto.mfa_activo,
    mfaObligatorio: dto.mfa_obligatorio,
    expiraInactividadEn: new Date(dto.expira_inactividad_en),
    expiraAbsolutaEn: new Date(dto.expira_absoluta_en),
    redireccion: dto.redireccion,
  };
}

export function mapAutorizacion(dto: AutorizacionVigente): AutorizacionTratamiento {
  return {
    versionPolitica: dto.version_politica,
    vigenteDesde: dto.vigente_desde,
    resumenFinalidad: dto.resumen_finalidad,
    urlPolitica: dto.url_politica,
    otorgadaEn: dto.otorgada_en ? new Date(dto.otorgada_en) : null,
    versionOtorgada: dto.version_otorgada ?? null,
  };
}

export function mapActivacionMfa(dto: MfaActivacionInicio): ActivacionMfa {
  return { otpauthUri: dto.otpauth_uri, claveSecreta: dto.clave_secreta };
}

function mapReciente(dto: ContenidoResumenPanel): ContenidoReciente {
  return {
    id: dto.id,
    tipo: dto.tipo,
    titulo: dto.titulo,
    estado: dto.estado_editorial,
    actualizadoEn: new Date(dto.actualizado_en),
    actualizadoPor: dto.actualizado_por.etiqueta,
    urlPublica: dto.publicado && dto.url_publica ? dto.url_publica : null,
  };
}

function mapRef(dto: ContenidoRefPanel): ContenidoRef {
  return { id: dto.id, tipo: dto.tipo, titulo: dto.titulo };
}

function mapSalud(dto: Tablero['salud_editorial']): SaludEditorial | null {
  if (dto === null || dto === undefined) return null;
  return {
    revisionesAntiguas: (dto.revisiones_antiguas ?? []).map(mapRef),
    mediosPendientesMetadatos: dto.medios_pendientes_metadatos ?? 0,
    mediosSinUso: dto.medios_sin_uso ?? 0,
    coleccionesBajoMinimo: (dto.colecciones_bajo_minimo ?? []).map(mapRef),
    contenidosConPocosRelacionados: (dto.contenidos_con_pocos_relacionados ?? []).map(mapRef),
  };
}

export function mapTablero(dto: Tablero): TableroPanel {
  return {
    conteos: dto.conteos.map((c) => ({
      tipo: c.tipo,
      borrador: c.borrador,
      publicado: c.publicado,
      retirado: c.retirado,
    })),
    recientes: dto.recientes.map(mapReciente),
    alertas: dto.alertas.map((a) => ({
      codigo: a.code,
      mensaje: a.mensaje,
      enlace: a.enlace ?? null,
    })),
    saludEditorial: mapSalud(dto.salud_editorial),
  };
}
