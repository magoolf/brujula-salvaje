import { FiltrosBusqueda, GrupoResultado } from './modelos';

export type QueryParamsBusqueda = Readonly<Record<string, string | readonly string[]>>;

const GRUPOS_VALIDOS: ReadonlySet<string> = new Set<GrupoResultado>([
  'destinos',
  'itinerarios',
  'guias',
  'tipos',
]);

const ETIQUETAS_GRUPO: Record<GrupoResultado, string> = {
  destinos: 'Destinos',
  itinerarios: 'Itinerarios',
  guias: 'Guías',
  tipos: 'Tipos de aventura',
};

export function etiquetaGrupo(grupo: GrupoResultado): string {
  return ETIQUETAS_GRUPO[grupo];
}

function aTexto(valor: string | readonly string[] | undefined): string | null {
  if (valor === undefined) return null;
  return Array.isArray(valor) ? (valor[0] ?? null) : (valor as string);
}

function paginaValida(valor: string | null): number {
  const n = Number(valor);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

function grupoValido(valor: string | null): GrupoResultado | null {
  return valor !== null && GRUPOS_VALIDOS.has(valor) ? (valor as GrupoResultado) : null;
}

/** FEAT-016: `q` es texto libre (dato, nunca instrucción); solo se recorta, la validación de forma
 * (2..100 caracteres) vive en `shared/ui/campo-busqueda/validar-consulta.ts` (Regla reutilizada, no
 * duplicada: `validarConsulta` es lógica de presentación agnóstica de feature). */
export function filtrosDesdeQueryParams(params: QueryParamsBusqueda): FiltrosBusqueda {
  return {
    q: aTexto(params['q'])?.trim() ?? '',
    tipo: grupoValido(aTexto(params['tipo'])),
    pagina: paginaValida(aTexto(params['pagina'])),
  };
}
