/**
 * Lógica pura de los medidores segmentados (DifficultyMeter 1-5 y BudgetMeter 1-4, DEC-AUTO-063).
 * Sin Angular: normaliza el valor recibido y calcula los segmentos y el texto accesible.
 */
export interface SegmentoMedidor {
  readonly indice: number;
  readonly lleno: boolean;
}

/** Acota un valor a [1, maximo] como entero; `null` si no es un número finito. */
export function normalizarNivel(valor: number | null | undefined, maximo: number): number | null {
  if (typeof valor !== 'number' || !Number.isFinite(valor)) return null;
  return Math.min(maximo, Math.max(1, Math.round(valor)));
}

export function segmentos(nivel: number | null, maximo: number): readonly SegmentoMedidor[] {
  return Array.from({ length: maximo }, (_, i) => ({
    indice: i + 1,
    lleno: nivel !== null && i < nivel,
  }));
}

/** «Dificultad 3 de 5: Exigente» / «Presupuesto 2 de 4» / «Dificultad sin dato». */
export function textoAccesible(
  concepto: string,
  nivel: number | null,
  maximo: number,
  etiqueta: string | null,
): string {
  if (nivel === null) return `${concepto} sin dato`;
  const base = `${concepto} ${nivel} de ${maximo}`;
  return etiqueta !== null && etiqueta.trim() !== '' ? `${base}: ${etiqueta.trim()}` : base;
}
