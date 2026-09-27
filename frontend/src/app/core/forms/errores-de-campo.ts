import { ErrorApi } from '../http/error-api.model';

/**
 * Traduce un ErrorApi a mensajes por control de formulario (Skill_Frontend §11):
 * ErrorApi → aErroresDeCampo(...) → formulario → mensaje debajo del campo.
 * Los errores de campos que el formulario no tiene y los de `_general` se devuelven como
 * generales (para el ErrorSummary), junto con el mensaje del problema si no hay ninguno por campo.
 */
export interface ErroresDeFormulario {
  readonly porCampo: Readonly<Record<string, readonly string[]>>;
  readonly generales: readonly string[];
}

export const CLAVE_ERROR_GENERAL = '_general';

export function aErroresDeCampo(
  error: ErrorApi,
  camposFormulario: readonly string[],
): ErroresDeFormulario {
  const conocidos = new Set(camposFormulario);
  const porCampo: Record<string, readonly string[]> = {};
  const generales: string[] = [];

  for (const [campo, mensajes] of Object.entries(error.campos)) {
    if (campo !== CLAVE_ERROR_GENERAL && conocidos.has(campo)) {
      porCampo[campo] = mensajes;
    } else {
      generales.push(...mensajes);
    }
  }
  if (Object.keys(porCampo).length === 0 && generales.length === 0) {
    generales.push(error.mensaje);
  }
  return { porCampo, generales };
}
