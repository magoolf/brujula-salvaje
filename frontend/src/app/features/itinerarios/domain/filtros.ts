import { FiltrosItinerarios, OrdenItinerarios } from './modelos';

/** El estado de orden/página vive en la URL (mismo patrón que Destinos, RULE-019/DEC-AUTO-047). */
export type QueryParamsItinerarios = Readonly<Record<string, string | readonly string[]>>;

const ORDENES_VALIDOS: ReadonlySet<string> = new Set<OrdenItinerarios>([
  'titulo',
  'duracion_asc',
  'duracion_desc',
]);

function aTexto(valor: string | readonly string[] | undefined): string | null {
  if (valor === undefined) return null;
  return Array.isArray(valor) ? (valor[0] ?? null) : (valor as string);
}

function ordenValido(valor: string | null): OrdenItinerarios {
  return valor !== null && ORDENES_VALIDOS.has(valor) ? (valor as OrdenItinerarios) : 'titulo';
}

function paginaValida(valor: string | null): number {
  const n = Number(valor);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

export function filtrosDesdeQueryParams(params: QueryParamsItinerarios): FiltrosItinerarios {
  return {
    orden: ordenValido(aTexto(params['orden'])),
    pagina: paginaValida(aTexto(params['pagina'])),
  };
}

/** queryParams para el enlace de un orden (reinicia a página 1). */
export function queryParamsOrden(orden: OrdenItinerarios): Record<string, string | null> {
  return { orden: orden === 'titulo' ? null : orden, pagina: null };
}
