/**
 * Lógica pura de filtros de "Explorar destinos" (FEAT-004, RULE-019, DEC-AUTO-047). El estado de
 * filtros vive en la URL (query params), no en un store con comandos: cada opción de filtro es un
 * enlace real que sustituye su clave en los query params (funciona sin JS, es compartible/marcable).
 */
import { FiltrosDestinos, OrdenDestinos, TramoDuracionCodigo } from './modelos';

export const TAMANO_PAGINA_DESTINOS = 24;

export const FILTROS_VACIOS: FiltrosDestinos = {
  tipo: [],
  region: null,
  pais: null,
  dificultadMin: null,
  dificultadMax: null,
  mes: null,
  duracion: [],
  presupuesto: [],
  orden: 'nombre',
  pagina: 1,
};

const ORDENES_VALIDOS: ReadonlySet<string> = new Set<OrdenDestinos>([
  'nombre',
  'dificultad_asc',
  'dificultad_desc',
]);
const TRAMOS_VALIDOS: ReadonlySet<string> = new Set<TramoDuracionCodigo>([
  '1-3',
  '4-7',
  '8-14',
  '15+',
]);
const SLUG_VALIDO = /^[a-z0-9]+(-[a-z0-9]+)*$/;

/**
 * `null` significa «quitar este parámetro» al fusionarlo con `queryParamsHandling: 'merge'`
 * (Angular Router); `undefined` significa «parámetro ausente» al leer la URL actual.
 */
export type ValorQueryParam = string | readonly string[] | null | undefined;
export type QueryParamsDestinos = Readonly<Record<string, ValorQueryParam>>;

function comoLista(valor: ValorQueryParam): readonly string[] {
  if (valor === undefined || valor === null) return [];
  if (Array.isArray(valor)) return valor;
  return [valor as string];
}

function comoEscalar(valor: ValorQueryParam): string | null {
  if (valor === undefined || valor === null) return null;
  if (Array.isArray(valor)) return valor[0] ?? null;
  return valor as string;
}

function entero(valor: string | null, minimo: number, maximo: number): number | null {
  if (valor === null) return null;
  const n = Number(valor);
  return Number.isInteger(n) && n >= minimo && n <= maximo ? n : null;
}

function soloSlugsValidos(valores: readonly string[]): readonly string[] {
  return valores.filter((v) => SLUG_VALIDO.test(v));
}

/**
 * Ajusta un rango de dificultad: si "desde" > "hasta" se intercambian (DEC-AUTO-067) en vez de
 * rechazarse.
 */
export function normalizarRangoDificultad(
  min: number | null,
  max: number | null,
): { readonly min: number | null; readonly max: number | null } {
  if (min !== null && max !== null && min > max) return { min: max, max: min };
  return { min, max };
}

/**
 * Construye los filtros a partir de los query params de la ruta. Los valores fuera de los dominios
 * cerrados se ignoran en silencio (AC-113): la UI nunca envía a la API un parámetro que ella misma
 * ya sabe inválido.
 */
export function filtrosDesdeQueryParams(params: QueryParamsDestinos): FiltrosDestinos {
  const rango = normalizarRangoDificultad(
    entero(comoEscalar(params['dificultad_min']), 1, 5),
    entero(comoEscalar(params['dificultad_max']), 1, 5),
  );
  const orden = comoEscalar(params['orden']);
  const duracion = comoLista(params['duracion']).filter((v) => TRAMOS_VALIDOS.has(v));
  const presupuesto = comoLista(params['presupuesto'])
    .map((v) => entero(v, 1, 4))
    .filter((v): v is number => v !== null);
  const pagina = entero(comoEscalar(params['pagina']), 1, Number.MAX_SAFE_INTEGER) ?? 1;

  return {
    tipo: soloSlugsValidos(comoLista(params['tipo'])),
    region: (() => {
      const r = comoEscalar(params['region']);
      return r !== null && SLUG_VALIDO.test(r) ? r : null;
    })(),
    pais: (() => {
      const p = comoEscalar(params['pais']);
      return p !== null && SLUG_VALIDO.test(p) ? p : null;
    })(),
    dificultadMin: rango.min,
    dificultadMax: rango.max,
    mes: entero(comoEscalar(params['mes']), 1, 12),
    duracion: duracion as readonly TramoDuracionCodigo[],
    presupuesto,
    orden: orden !== null && ORDENES_VALIDOS.has(orden) ? (orden as OrdenDestinos) : 'nombre',
    pagina,
  };
}

export function hayFiltrosActivos(filtros: FiltrosDestinos): boolean {
  return (
    filtros.tipo.length > 0 ||
    filtros.region !== null ||
    filtros.pais !== null ||
    filtros.dificultadMin !== null ||
    filtros.dificultadMax !== null ||
    filtros.mes !== null ||
    filtros.duracion.length > 0 ||
    filtros.presupuesto.length > 0
  );
}

function alternarEnLista<T>(lista: readonly T[], valor: T): readonly T[] {
  return lista.includes(valor) ? lista.filter((v) => v !== valor) : [...lista, valor];
}

/** query params completos (no solo el cambio) listos para `[queryParams]` con `queryParamsHandling: 'merge'`. */
export function alternarTipo(filtros: FiltrosDestinos, slug: string): QueryParamsDestinos {
  const siguiente = alternarEnLista(filtros.tipo, slug);
  return { tipo: siguiente.length > 0 ? siguiente : null, pagina: null };
}

export function alternarRegion(filtros: FiltrosDestinos, slug: string): QueryParamsDestinos {
  const activo = filtros.region === slug;
  // Al quitar la región se quitan también los países que dependían de ella (FEAT-004).
  return { region: activo ? null : slug, pais: null, pagina: null };
}

export function alternarPais(filtros: FiltrosDestinos, slug: string): QueryParamsDestinos {
  return { pais: filtros.pais === slug ? null : slug, pagina: null };
}

export function alternarMes(filtros: FiltrosDestinos, mes: number): QueryParamsDestinos {
  return { mes: filtros.mes === mes ? null : String(mes), pagina: null };
}

export function alternarDuracion(
  filtros: FiltrosDestinos,
  codigo: TramoDuracionCodigo,
): QueryParamsDestinos {
  const siguiente = alternarEnLista(filtros.duracion, codigo);
  return { duracion: siguiente.length > 0 ? siguiente : null, pagina: null };
}

export function alternarPresupuesto(filtros: FiltrosDestinos, nivel: number): QueryParamsDestinos {
  const siguiente = alternarEnLista(filtros.presupuesto, nivel);
  return {
    presupuesto: siguiente.length > 0 ? siguiente.map(String) : null,
    pagina: null,
  };
}

export function establecerRangoDificultad(min: number | null, max: number | null): QueryParamsDestinos {
  const rango = normalizarRangoDificultad(min, max);
  return {
    dificultad_min: rango.min === null ? null : String(rango.min),
    dificultad_max: rango.max === null ? null : String(rango.max),
    pagina: null,
  };
}

export function establecerOrden(orden: OrdenDestinos): QueryParamsDestinos {
  return { orden: orden === 'nombre' ? null : orden, pagina: null };
}

export function limpiarFiltros(): QueryParamsDestinos {
  return {
    tipo: null,
    region: null,
    pais: null,
    dificultad_min: null,
    dificultad_max: null,
    mes: null,
    duracion: null,
    presupuesto: null,
    pagina: null,
  };
}

export interface FiltroActivo {
  readonly clave: string;
  readonly etiqueta: string;
  readonly queryParams: QueryParamsDestinos;
}

/**
 * Fichas de filtros activos (con su etiqueta legible) y los query params que resultan de quitar
 * cada una. `nombrePorSlug` resuelve el nombre visible de tipo/región/país desde las facetas.
 */
export function filtrosActivosComoLista(
  filtros: FiltrosDestinos,
  nombrePorSlug: (slug: string) => string,
  etiquetaTramoDuracion: (codigo: TramoDuracionCodigo) => string,
  etiquetaNivel: (escala: 'dificultad' | 'presupuesto', nivel: number) => string,
): readonly FiltroActivo[] {
  const activos: FiltroActivo[] = [];

  for (const slug of filtros.tipo) {
    activos.push({
      clave: `tipo:${slug}`,
      etiqueta: `Tipo: ${nombrePorSlug(slug)}`,
      queryParams: alternarTipo(filtros, slug),
    });
  }
  if (filtros.region !== null) {
    activos.push({
      clave: `region:${filtros.region}`,
      etiqueta: `Región: ${nombrePorSlug(filtros.region)}`,
      queryParams: alternarRegion(filtros, filtros.region),
    });
  }
  if (filtros.pais !== null) {
    activos.push({
      clave: `pais:${filtros.pais}`,
      etiqueta: `País: ${nombrePorSlug(filtros.pais)}`,
      queryParams: alternarPais(filtros, filtros.pais),
    });
  }
  if (filtros.dificultadMin !== null || filtros.dificultadMax !== null) {
    const min = filtros.dificultadMin ?? 1;
    const max = filtros.dificultadMax ?? 5;
    activos.push({
      clave: 'dificultad',
      etiqueta:
        min === max
          ? `Dificultad: ${etiquetaNivel('dificultad', min)}`
          : `Dificultad: ${etiquetaNivel('dificultad', min)} a ${etiquetaNivel('dificultad', max)}`,
      queryParams: establecerRangoDificultad(null, null),
    });
  }
  if (filtros.mes !== null) {
    activos.push({
      clave: `mes:${filtros.mes}`,
      etiqueta: `Mes: ${nombrePorSlug(String(filtros.mes))}`,
      queryParams: alternarMes(filtros, filtros.mes),
    });
  }
  for (const codigo of filtros.duracion) {
    activos.push({
      clave: `duracion:${codigo}`,
      etiqueta: `Duración: ${etiquetaTramoDuracion(codigo)}`,
      queryParams: alternarDuracion(filtros, codigo),
    });
  }
  for (const nivel of filtros.presupuesto) {
    activos.push({
      clave: `presupuesto:${nivel}`,
      etiqueta: `Presupuesto: ${etiquetaNivel('presupuesto', nivel)}`,
      queryParams: alternarPresupuesto(filtros, nivel),
    });
  }
  return activos;
}
