/**
 * Dominio puro del panel editorial (MOD-009 acceso, MOD-010 tablero). Sin Angular ni RxJS
 * (Skill_Frontend Regla 08). Los DTO del cliente OpenAPI mueren en `data/` (Regla 04): estos tipos
 * son los únicos que STATE y UI conocen. TKT-022/023/024 añaden aquí los modelos de sus áreas.
 */

/** Rol del staff (BLUEPRINT §6). El Administrador puede todo lo del Editor. */
export type RolPanel = 'EDITOR' | 'ADMINISTRADOR';

/** Paso pendiente de la sesión (STATE-004; orden SCR-030 → 031 → 032 → 033). */
export type PasoPendiente =
  | 'NINGUNO'
  | 'MFA'
  | 'CAMBIO_CREDENCIAL'
  | 'CONFIGURAR_MFA'
  | 'AUTORIZACION';

export interface SesionPanel {
  readonly usuario: string;
  readonly nombreVisible: string;
  readonly rol: RolPanel;
  readonly pasoPendiente: PasoPendiente;
  readonly mfaActivo: boolean;
  /** El Administrador no puede desactivar el MFA (DEC-AUTO-037). */
  readonly mfaObligatorio: boolean;
  readonly expiraInactividadEn: Date;
  readonly expiraAbsolutaEn: Date;
  /** Destino interno validado por el servidor tras completar el acceso (AC-115). */
  readonly redireccion: string;
}

/** Política de tratamiento vigente y autorización otorgada (FEAT-032, SCR-033/032). */
export interface AutorizacionTratamiento {
  readonly versionPolitica: string;
  readonly vigenteDesde: string;
  readonly resumenFinalidad: string;
  readonly urlPolitica: string;
  readonly otorgadaEn: Date | null;
  readonly versionOtorgada: string | null;
}

export type DecisionAutorizacion = 'AUTORIZO' | 'NO_AUTORIZO';

/** Secreto provisional para vincular la app autenticadora (FEAT-030). */
export interface ActivacionMfa {
  readonly otpauthUri: string;
  readonly claveSecreta: string;
}

export type TipoContenido =
  | 'DESTINO'
  | 'ITINERARIO'
  | 'GUIA'
  | 'TIPO'
  | 'COLECCION'
  | 'TERMINO'
  | 'PAGINA';

export type EstadoEditorial = 'BORRADOR' | 'PUBLICADO' | 'RETIRADO';

export interface ConteoPorTipo {
  readonly tipo: TipoContenido;
  readonly borrador: number;
  readonly publicado: number;
  readonly retirado: number;
}

export interface ContenidoReciente {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
  readonly estado: EstadoEditorial;
  readonly actualizadoEn: Date;
  readonly actualizadoPor: string;
  /** Ruta pública si está publicado (para «Ver en el sitio»). */
  readonly urlPublica: string | null;
}

export type CodigoAlertaTablero =
  | 'responsable_sin_definir'
  | 'destacado_retirado'
  | 'coleccion_bajo_minimo';

export interface AlertaTablero {
  readonly codigo: CodigoAlertaTablero;
  readonly mensaje: string;
  readonly enlace: string | null;
}

export interface ContenidoRef {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
}

/** Widget de salud editorial (EXP-001, COULD). */
export interface SaludEditorial {
  readonly revisionesAntiguas: readonly ContenidoRef[];
  readonly mediosPendientesMetadatos: number;
  readonly mediosSinUso: number;
  readonly coleccionesBajoMinimo: readonly ContenidoRef[];
  readonly contenidosConPocosRelacionados: readonly ContenidoRef[];
}

export interface TableroPanel {
  readonly conteos: readonly ConteoPorTipo[];
  readonly recientes: readonly ContenidoReciente[];
  readonly alertas: readonly AlertaTablero[];
  readonly saludEditorial: SaludEditorial | null;
}
