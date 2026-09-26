/**
 * Validación de la consulta de búsqueda (FEAT-016, AC-020, ALT-006): 2..100 caracteres tras
 * recortar espacios. Función pura; el servidor sigue siendo la autoridad (DEC-AUTO-048).
 */
export const MIN_CONSULTA = 2;
export const MAX_CONSULTA = 100;

export type ResultadoConsulta =
  | { readonly valida: true; readonly consulta: string }
  | { readonly valida: false; readonly mensaje: string };

export function validarConsulta(valor: string | null | undefined): ResultadoConsulta {
  const consulta = (valor ?? '').replace(/\s+/g, ' ').trim();
  const longitud = [...consulta].length;
  if (longitud < MIN_CONSULTA) {
    return { valida: false, mensaje: `Escribe al menos ${MIN_CONSULTA} caracteres.` };
  }
  if (longitud > MAX_CONSULTA) {
    return { valida: false, mensaje: `Escribe como máximo ${MAX_CONSULTA} caracteres.` };
  }
  return { valida: true, consulta };
}
