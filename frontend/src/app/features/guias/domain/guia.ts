/** EXP-004 (COULD): «N min de lectura»; `null` si el backend no lo calculó. */
export function textoMinutosLectura(minutos: number | null): string | null {
  if (minutos === null || minutos <= 0) return null;
  return minutos === 1 ? '1 min de lectura' : `${minutos} min de lectura`;
}

/** Fecha es-CO (RULE-009) a partir de un ISO 8601. */
export function formatoFechaEsCo(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}

/** «Revisado el {fecha}» (HANDOFF SCR-011). */
export function textoRevisado(iso: string): string {
  return `Revisado el ${formatoFechaEsCo(iso)}`;
}
