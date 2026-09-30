import { DestinoDetalle } from './modelos';

/** RULE-006/FEAT-013: la sección de itinerarios muestra los propios o, si no hay, los afines. */
export function tieneItinerariosPropios(destino: Pick<DestinoDetalle, 'itinerarios'>): boolean {
  return destino.itinerarios.length > 0;
}

/** «5 a 10 días» (KeyFacts, HANDOFF SCR-004); un solo número si min === max. */
export function formatoDuracion(minDias: number, maxDias: number): string {
  return minDias === maxDias ? `${minDias} días` : `${minDias} a ${maxDias} días`;
}

/** Fecha es-CO (RULE-009) a partir de un ISO 8601. */
export function formatoFechaEsCo(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}

const NOMBRES_MES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
] as const;

/** Nombre del mes (1-12) según DATA-020/RULE-011; `null` si el número no es válido. */
export function nombreMes(mes: number): string | null {
  return Number.isInteger(mes) && mes >= 1 && mes <= 12 ? NOMBRES_MES[mes - 1] : null;
}

/** Mes anterior/siguiente en ciclo (1..12), para la navegación de SCR-016. */
export function mesAdyacente(mes: number, delta: 1 | -1): number {
  return ((((mes - 1 + delta) % 12) + 12) % 12) + 1;
}
