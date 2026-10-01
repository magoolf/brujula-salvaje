/**
 * Comprobaciones previas del cambio de contraseña (RULE-017, SCR-032). El servidor es la
 * autoridad (lista de comprometidas, coincidencia con el usuario); aquí solo se evita enviar lo que
 * seguro se rechazará y se da el mensaje junto al campo.
 */
export const LONGITUD_MINIMA_CONTRASENA = 12;

export const MENSAJE_POLITICA_CONTRASENA =
  'Elige una contraseña menos común. Usa al menos 12 caracteres; una frase larga funciona bien.';
export const MENSAJE_NO_COINCIDEN = 'Las contraseñas no coinciden.';
export const MENSAJE_ACTUAL_OBLIGATORIA = 'Escribe tu contraseña actual.';

export interface CambioContrasena {
  readonly actual: string;
  readonly nueva: string;
  readonly confirmacion: string;
}

/** Claves alineadas con los campos del contrato (`errors` del Problem) + `confirmacion`. */
export type CampoCambioContrasena = 'contrasena_actual' | 'contrasena_nueva' | 'confirmacion';

export function validarCambioContrasena(
  datos: CambioContrasena,
): Partial<Record<CampoCambioContrasena, string>> {
  const errores: Partial<Record<CampoCambioContrasena, string>> = {};
  if (datos.actual.length === 0) errores.contrasena_actual = MENSAJE_ACTUAL_OBLIGATORIA;
  if (datos.nueva.length < LONGITUD_MINIMA_CONTRASENA) {
    errores.contrasena_nueva = MENSAJE_POLITICA_CONTRASENA;
  }
  if (datos.confirmacion !== datos.nueva) errores.confirmacion = MENSAJE_NO_COINCIDEN;
  return errores;
}
