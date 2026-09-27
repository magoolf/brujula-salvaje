/**
 * Modelo común de error del frontend (Skill_Frontend §10 y §27.3).
 * Es un tipo puro: no depende de Angular ni de la forma del backend. Las capas superiores
 * (STATE/UI) solo conocen `ErrorApi`, nunca `HttpErrorResponse` ni el Problem Details original.
 *
 * Mapeo RFC 9457 → ErrorApi (Skill_Frontend §27.3):
 *   type → tipo · title/detail → mensaje · errors → campos · trace_id → traceId
 */
export type CategoriaErrorApi =
  | 'validacion'
  | 'no_autenticado'
  | 'permiso_denegado'
  | 'no_encontrado'
  | 'conflicto'
  | 'retirado'
  | 'regla_negocio'
  | 'limite_tasa'
  | 'sin_conexion'
  | 'servidor'
  | 'desconocido';

export interface ErrorApi {
  /**
   * Tipo del problema: último segmento de la URI `type` (`{base}/errors/{code}`, DEC-AUTO-103).
   * Si el backend no envía `type`, se usa `code` y, en su defecto, la categoría.
   */
  readonly tipo: string;
  /** Categoría estable para decidir la reacción de la UI sin depender de códigos HTTP (Regla 13). */
  readonly categoria: CategoriaErrorApi;
  /** `code` del Problem Details (catálogo de contracts/openapi.yaml) o `null`. */
  readonly codigo: string | null;
  /** Mensaje en español apto para mostrar (detail → title → mensaje genérico). */
  readonly mensaje: string;
  /** Mensajes por campo (`errors` del Problem Details). Vacío si no hay. */
  readonly campos: Readonly<Record<string, readonly string[]>>;
  /** `trace_id` del backend (32 hex) o `null`. Correlaciona con logs sin exponer PII. */
  readonly traceId: string | null;
  /** Miembros de extensión del problema (p. ej. `alternativas` y `listado_padre` en un 410). */
  readonly extra: Readonly<Record<string, unknown>>;
}

export const MENSAJE_ERROR_GENERICO =
  'Tuvimos un problema de nuestro lado. Vuelve a intentarlo en unos segundos.';
export const MENSAJE_SIN_CONEXION = 'Sin conexión. Lo que ya cargaste sigue disponible.';
