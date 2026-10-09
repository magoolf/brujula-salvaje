/**
 * Ciclo editorial (STATE-001, SCR-038, FLOW-011/012, CHG-BP-001): requisitos de publicación,
 * análisis previo a «Publicar»/«Actualizar publicación» (co-publicación de tipos), impacto de retiro
 * (cascada de itinerarios y tipos, bloqueos), resultado de las transiciones y revisiones (FEAT-040,
 * FEAT-050). Puro: sin Angular ni RxJS (Regla 08).
 */
import { RefContenido, etiquetaCampo } from './formulario-contenido';
import { EstadoEditorial, TipoContenido } from './modelos';

/** Requisito incumplido de una entidad (ErrorRegla); `campo` es la clave del formulario. */
export interface Requisito {
  readonly campo: string;
  readonly codigo: string;
  readonly mensaje: string;
  /** Entidades enlazables desde el mensaje (p. ej. «Reactiva primero el tipo {nombre}»). */
  readonly referencias: readonly RefContenido[];
}

export interface RequisitosPublicacion {
  readonly cumple: boolean;
  readonly pendientes: readonly Requisito[];
}

export const SIN_REQUISITOS: RequisitosPublicacion = { cumple: true, pendientes: [] };

/**
 * Requisitos que la vista previa solo aproxima (DEC-AUTO-114, DEC-AUTO-986): RULE-006 cuenta en la
 * vista previa únicamente los relacionados curados ya publicados, sin el complemento automático por
 * afinidad que el servidor sí suma al analizar y al guardar. Son avisos, no bloqueos: decide el
 * análisis del servidor (y, en último término, el 422 del guardado).
 */
const CODIGOS_ORIENTATIVOS_VISTA_PREVIA: ReadonlySet<string> = new Set(['relacionados_insuficientes']);

/** ¿El requisito de la vista previa es orientativo (no bloquea «Actualizar publicación»)? */
export function esOrientativoVistaPrevia(requisito: Requisito): boolean {
  return CODIGOS_ORIENTATIVOS_VISTA_PREVIA.has(requisito.codigo);
}

export type RolEntidad = 'PRINCIPAL' | 'COPUBLICACION' | 'CASCADA';

/** Validación de una entidad en el estado resultante de la operación (ValidacionEntidad). */
export interface ValidacionEntidad {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
  readonly estado: EstadoEditorial;
  readonly version: number;
  readonly rol: RolEntidad;
  readonly cumple: boolean;
  readonly pendientes: readonly Requisito[];
}

export interface EntidadVersionada {
  readonly id: number;
  readonly version: number;
}

export interface BloqueoCascada {
  readonly tipoAventura: RefContenido;
  readonly itinerarios: readonly RefContenido[];
  readonly totalItinerarios: number;
}

export type OperacionPublicacion = 'PUBLICAR' | 'ACTUALIZAR_PUBLICACION';

/** Resultado del análisis sin efectos (panelAnalizarPublicacion). */
export interface AnalisisPublicacion {
  readonly operacion: OperacionPublicacion;
  readonly confirmable: boolean;
  readonly entidad: ValidacionEntidad;
  /** «Se publicarán también» (tipos en BORRADOR del destino). */
  readonly copublicacion: readonly ValidacionEntidad[];
  /** Lista EXACTA a enviar como `copublicar_tipos`. */
  readonly copublicarTipos: readonly EntidadVersionada[];
  readonly tiposEnCascada: readonly RefContenido[];
  readonly bloqueosCascada: readonly BloqueoCascada[];
}

/** Uso que bloquea un retiro (RULE-007). */
export interface UsoBloqueante {
  readonly id: number;
  readonly tipoEntidad: string;
  readonly titulo: string;
  readonly estado: EstadoEditorial | null;
}

export type SeccionDestacada = 'DESTINOS' | 'ITINERARIOS' | 'GUIAS';

export interface ImpactoRetiro {
  readonly retirable: boolean;
  readonly bloqueos: readonly UsoBloqueante[];
  readonly bloqueosCascada: readonly BloqueoCascada[];
  readonly itinerariosEnCascada: readonly RefContenido[];
  readonly tiposEnCascada: readonly RefContenido[];
  readonly colecciones: readonly RefContenido[];
  readonly destacados: readonly SeccionDestacada[];
  readonly enlacesEntrantes: number;
}

/** Cascada calculada por el servidor (409 cascada_sin_confirmar / impacto_modificado). */
export interface ImpactoCascada {
  readonly itinerariosEnCascada: readonly RefContenido[];
  readonly tiposEnCascada: readonly RefContenido[];
  readonly bloqueosCascada: readonly BloqueoCascada[];
}

/** Entidad que cambió de estado en la operación. */
export interface EntidadTransitada {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
  readonly estado: EstadoEditorial;
  readonly version: number;
  readonly origen: RolEntidad;
  readonly urlPublica: string | null;
}

export interface ResultadoTransicion {
  readonly id: number;
  readonly estado: EstadoEditorial;
  readonly version: number;
  readonly urlPublica: string | null;
  readonly entidades: readonly EntidadTransitada[];
}

/** Errores de una publicación agrupados por entidad (FLOW-011 6a'). */
export interface ErroresEntidad {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
  readonly rol: RolEntidad;
  readonly errores: readonly Requisito[];
}

export type MotivoRevision = 'PUBLICACION' | 'ACTUALIZACION' | 'RETIRO' | 'RESTAURACION';

export interface RevisionResumen {
  readonly numero: number;
  readonly creadaEn: Date;
  readonly creadaPor: string;
  readonly motivo: MotivoRevision;
}

export interface PaginaRevisiones {
  readonly revisiones: readonly RevisionResumen[];
  readonly pagina: number;
  readonly totalPaginas: number;
}

export const ETIQUETA_MOTIVO_REVISION: Readonly<Record<MotivoRevision, string>> = {
  PUBLICACION: 'Publicación',
  ACTUALIZACION: 'Actualización de la publicación',
  RETIRO: 'Retiro',
  RESTAURACION: 'Restauración',
};

export const ETIQUETA_DESTACADO: Readonly<Record<SeccionDestacada, string>> = {
  DESTINOS: 'Destinos destacados del inicio',
  ITINERARIOS: 'Itinerarios destacados del inicio',
  GUIAS: 'Guías destacadas del inicio',
};

/** Longitud máxima del motivo interno del retiro (texto libre, nunca se publica). */
export const LONGITUD_MAXIMA_MOTIVO = 500;

/** Retirar exige un motivo escrito (HANDOFF SCR-038: «Retirar» deshabilitado sin motivo). */
export function motivoValido(motivo: string): boolean {
  const limpio = motivo.trim();
  return limpio !== '' && [...limpio].length <= LONGITUD_MAXIMA_MOTIVO;
}

/** Entidades que el editor vio y confirma en la cascada (`cascada_confirmada`). */
export function cascadaConfirmada(
  impacto: Pick<ImpactoCascada, 'itinerariosEnCascada' | 'tiposEnCascada'>,
): readonly { readonly id: number; readonly tipo: TipoContenido }[] {
  return [...impacto.itinerariosEnCascada, ...impacto.tiposEnCascada].map((e) => ({
    id: e.id,
    tipo: e.tipo,
  }));
}

export function hayCascada(
  impacto: Pick<ImpactoCascada, 'itinerariosEnCascada' | 'tiposEnCascada'>,
): boolean {
  return impacto.itinerariosEnCascada.length > 0 || impacto.tiposEnCascada.length > 0;
}

/** Sustituye la cascada de un impacto por la recalculada por el servidor (impacto_modificado). */
export function conCascada(impacto: ImpactoRetiro, cascada: ImpactoCascada): ImpactoRetiro {
  return {
    ...impacto,
    itinerariosEnCascada: cascada.itinerariosEnCascada,
    tiposEnCascada: cascada.tiposEnCascada,
    bloqueosCascada: cascada.bloqueosCascada,
    retirable:
      impacto.bloqueos.length === 0 && cascada.bloqueosCascada.length === 0,
  };
}

/** Todos los requisitos pendientes de un análisis (principal + co-publicados). */
export function pendientesAnalisis(analisis: AnalisisPublicacion): number {
  return (
    analisis.entidad.pendientes.length +
    analisis.copublicacion.reduce((total, e) => total + e.pendientes.length, 0)
  );
}

/** «No se puede publicar todavía. Corrige 3 problemas:» (ErrorSummary). */
export function tituloResumenErrores(accion: string, cantidad: number): string {
  const problemas = cantidad === 1 ? '1 problema' : `${cantidad} problemas`;
  return `No se puede ${accion} todavía. Corrige ${problemas}:`;
}

/**
 * Une los requisitos del servidor sobre el estado guardado (o de la vista previa) en un único
 * resumen para el CompletenessPanel: «Listo para publicar» o «Faltan {n} requisitos».
 */
export function textoCompletitud(requisitos: RequisitosPublicacion): string {
  const n = requisitos.pendientes.length;
  if (requisitos.cumple || n === 0) return 'Listo para publicar';
  return n === 1 ? 'Falta 1 requisito para publicar' : `Faltan ${n} requisitos para publicar`;
}

/** Entidades distintas de la principal en un resultado (para el mensaje de éxito). */
export function entidadesAdicionales(resultado: ResultadoTransicion): readonly EntidadTransitada[] {
  return resultado.entidades.filter((e) => e.origen !== 'PRINCIPAL');
}

/** Texto del enlace de un requisito: «Galería: Faltan imágenes…». */
export function textoRequisito(requisito: Requisito): string {
  return requisito.campo === '_general'
    ? requisito.mensaje
    : `${etiquetaCampo(requisito.campo)}: ${requisito.mensaje}`;
}
