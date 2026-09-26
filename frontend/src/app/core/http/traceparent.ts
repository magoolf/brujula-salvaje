/**
 * Cabecera W3C Trace Context `traceparent` (Skill_Frontend §27.5).
 * Formato: `00-<trace-id 32 hex>-<parent-id 16 hex>-<flags 2 hex>`; trace-id y parent-id no pueden
 * ser todo ceros. Funciones puras: la fuente de aleatoriedad se inyecta para poder probarlas.
 */
export const CABECERA_TRACEPARENT = 'traceparent';

const PATRON_TRACEPARENT = /^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$/;

export type FuenteAleatoria = (bytes: Uint8Array<ArrayBuffer>) => Uint8Array<ArrayBuffer>;

export const aleatorioCriptografico: FuenteAleatoria = (bytes) => globalThis.crypto.getRandomValues(bytes);

export function generarTraceparent(aleatorio: FuenteAleatoria = aleatorioCriptografico): string {
  const traceId = hexNoNulo(16, aleatorio);
  const parentId = hexNoNulo(8, aleatorio);
  return `00-${traceId}-${parentId}-01`;
}

export function esTraceparentValido(valor: string | null | undefined): boolean {
  if (typeof valor !== 'string') return false;
  const m = PATRON_TRACEPARENT.exec(valor);
  if (m === null) return false;
  return !/^0+$/.test(m[1]) && !/^0+$/.test(m[2]);
}

function hexNoNulo(longitud: number, aleatorio: FuenteAleatoria): string {
  const bytes = aleatorio(new Uint8Array(longitud));
  if (bytes.every((b) => b === 0)) bytes[longitud - 1] = 1;
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
