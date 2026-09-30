/**
 * Dominio puro de «Mis aventuras guardadas» (FEAT-020, MOD-006, RULE-013). Sin dependencias de
 * Angular ni de RxJS (Skill_Frontend Regla 08): solo tipos y funciones de decisión reutilizables
 * por el store (STATE) y por la página de guardados (UI).
 *
 * RULE-013: los guardados se almacenan solo en el navegador (tipo, slug, título, país; máx. 100).
 * THREAT-026: lo leído del almacenamiento local es dato NO confiable (puede haberlo manipulado un
 * script local); `validarElementoGuardado` es la única puerta de entrada y descarta cualquier valor
 * que no cumpla la forma esperada.
 */

export type TipoContenidoGuardable = 'DESTINO' | 'ITINERARIO';

export interface ElementoGuardado {
  readonly tipo: TipoContenidoGuardable;
  readonly slug: string;
  readonly titulo: string;
  readonly pais: string | null;
}

/** Límite de elementos guardados (RULE-013). */
export const LIMITE_GUARDADOS = 100;

const TIPOS_VALIDOS: ReadonlySet<string> = new Set<TipoContenidoGuardable>([
  'DESTINO',
  'ITINERARIO',
]);
const SLUG_VALIDO = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const LONGITUD_MAX_SLUG = 120;
const LONGITUD_MAX_TEXTO = 200;

function esTipoValido(valor: unknown): valor is TipoContenidoGuardable {
  return typeof valor === 'string' && TIPOS_VALIDOS.has(valor);
}

/**
 * Valida y sanea un valor recuperado del almacenamiento local. Devuelve `null` si el valor no tiene
 * la forma esperada (THREAT-026): nunca se confía en su estructura ni se interpreta como HTML.
 */
export function validarElementoGuardado(valor: unknown): ElementoGuardado | null {
  if (typeof valor !== 'object' || valor === null) return null;
  const registro = valor as Record<string, unknown>;
  const { tipo, slug, titulo, pais } = registro;

  if (!esTipoValido(tipo)) return null;
  if (typeof slug !== 'string' || slug.length === 0 || slug.length > LONGITUD_MAX_SLUG) return null;
  if (!SLUG_VALIDO.test(slug)) return null;
  if (typeof titulo !== 'string' || titulo.trim() === '') return null;

  const paisSaneado =
    typeof pais === 'string' && pais.trim() !== '' ? pais.slice(0, LONGITUD_MAX_TEXTO) : null;

  return {
    tipo,
    slug,
    titulo: titulo.slice(0, LONGITUD_MAX_TEXTO),
    pais: paisSaneado,
  };
}

export function claveElemento(tipo: TipoContenidoGuardable, slug: string): string {
  return `${tipo}:${slug}`;
}

/**
 * Ruta interna construida solo a partir de tipo y slug ya validados (THREAT-026): nunca una URL
 * recibida del almacenamiento ni HTML.
 */
export function rutaElemento(elemento: ElementoGuardado): string {
  return elemento.tipo === 'DESTINO'
    ? `/destinos/${elemento.slug}`
    : `/itinerarios/${elemento.slug}`;
}

export function estaGuardado(
  lista: readonly ElementoGuardado[],
  tipo: TipoContenidoGuardable,
  slug: string,
): boolean {
  const clave = claveElemento(tipo, slug);
  return lista.some((elemento) => claveElemento(elemento.tipo, elemento.slug) === clave);
}

/** Añade (o mueve al frente si ya existía) un elemento, respetando `LIMITE_GUARDADOS`. */
export function agregarElemento(
  lista: readonly ElementoGuardado[],
  nuevo: ElementoGuardado,
): readonly ElementoGuardado[] {
  const clave = claveElemento(nuevo.tipo, nuevo.slug);
  const sinDuplicado = lista.filter(
    (elemento) => claveElemento(elemento.tipo, elemento.slug) !== clave,
  );
  return [nuevo, ...sinDuplicado].slice(0, LIMITE_GUARDADOS);
}

export function quitarElemento(
  lista: readonly ElementoGuardado[],
  tipo: TipoContenidoGuardable,
  slug: string,
): readonly ElementoGuardado[] {
  const clave = claveElemento(tipo, slug);
  return lista.filter((elemento) => claveElemento(elemento.tipo, elemento.slug) !== clave);
}
