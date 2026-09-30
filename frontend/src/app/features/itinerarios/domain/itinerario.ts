import { ItinerarioDetalle } from './modelos';

/** «5 km» / «820 m»: solo se muestra si el dato existe (RULE-020, no todos los itinerarios lo tienen). */
export function tieneMetricasRuta(
  itinerario: Pick<ItinerarioDetalle, 'distanciaTotalKm' | 'desnivelAcumuladoM'>,
): boolean {
  return itinerario.distanciaTotalKm !== null || itinerario.desnivelAcumuladoM !== null;
}

/** Fecha es-CO (RULE-009) a partir de un ISO 8601. */
export function formatoFechaEsCo(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}

/** Texto accesible del desnivel de un día (HANDOFF SCR-007: «desnivel positivo 850 metros, negativo 420 metros»). */
export function textoDesnivelDia(positivoM: number | null, negativoM: number | null): string | null {
  if (positivoM === null && negativoM === null) return null;
  const partes: string[] = [];
  if (positivoM !== null) partes.push(`desnivel positivo ${positivoM} metros`);
  if (negativoM !== null) partes.push(`negativo ${negativoM} metros`);
  return partes.join(', ');
}
