/**
 * Destacados de inicio (SCR-042, FEAT-043, FLOW-014, RULE-016, AC-011, TKT-024): bloque principal
 * (titular ≤80, subtítulo ≤160, imagen) y listas ordenadas de destinos (6-12), itinerarios (3-6) y
 * guías (3-6), siempre de contenido PUBLICADO. Puro: sin Angular ni RxJS (Regla 08).
 */
import { ErroresTraducidos, longitudTexto } from './errores-formulario';
import { MedioRef, RefContenido } from './formulario-contenido';
import { TipoContenido } from './modelos';

export type ListaDestacada = 'destinos' | 'itinerarios' | 'guias';

export const LISTAS_DESTACADAS: readonly ListaDestacada[] = ['destinos', 'itinerarios', 'guias'];

export interface DefinicionLista {
  readonly tipo: TipoContenido;
  readonly minimo: number;
  readonly maximo: number;
  /** Título de la sección (h2). */
  readonly titulo: string;
  /** Sustantivo en plural para los mensajes («destinos»). */
  readonly plural: string;
  /** Etiqueta del combobox de alta. */
  readonly etiquetaAnadir: string;
  /** Campo del contrato (ConfigInicioCampos). */
  readonly campoApi: string;
}

export const DEFINICION_LISTA: Readonly<Record<ListaDestacada, DefinicionLista>> = {
  destinos: { tipo: 'DESTINO', minimo: 6, maximo: 12, titulo: 'Destinos', plural: 'destinos', etiquetaAnadir: 'Añadir destino publicado', campoApi: 'destinos_ids' },
  itinerarios: {
    tipo: 'ITINERARIO',
    minimo: 3,
    maximo: 6,
    titulo: 'Itinerarios',
    plural: 'itinerarios',
    etiquetaAnadir: 'Añadir itinerario publicado',
    campoApi: 'itinerarios_ids',
  },
  guias: { tipo: 'GUIA', minimo: 3, maximo: 6, titulo: 'Guías', plural: 'guías', etiquetaAnadir: 'Añadir guía publicada', campoApi: 'guias_ids' },
};

export const LIMITE_TITULAR = 80;
export const LIMITE_SUBTITULO = 160;

export interface ConfigInicio {
  readonly titular: string;
  readonly subtitulo: string;
  readonly medio: MedioRef | null;
  readonly destinos: readonly RefContenido[];
  readonly itinerarios: readonly RefContenido[];
  readonly guias: readonly RefContenido[];
  readonly actualizadoEn: Date;
  readonly actualizadoPor: string;
}

export interface FormularioDestacados {
  readonly titular: string;
  readonly subtitulo: string;
  readonly medio: MedioRef | null;
  readonly destinos: readonly RefContenido[];
  readonly itinerarios: readonly RefContenido[];
  readonly guias: readonly RefContenido[];
}

export type CampoDestacados = 'titular' | 'subtitulo' | 'medio' | ListaDestacada;

export const CAMPOS_DESTACADOS: readonly CampoDestacados[] = [
  'titular',
  'subtitulo',
  'medio',
  'destinos',
  'itinerarios',
  'guias',
];

/** Entrada de escritura (ConfigInicioEntrada) en términos de dominio. */
export interface EntradaDestacados {
  readonly titular: string;
  readonly subtitulo: string;
  readonly medioId: number;
  readonly destinosIds: readonly number[];
  readonly itinerariosIds: readonly number[];
  readonly guiasIds: readonly number[];
}

export const TEXTO_LISTA_VACIA =
  'Sin destacados. El inicio se completará automáticamente con el contenido revisado más recientemente.';

export function formularioDesdeConfig(config: ConfigInicio): FormularioDestacados {
  return {
    titular: config.titular,
    subtitulo: config.subtitulo,
    medio: config.medio,
    destinos: config.destinos,
    itinerarios: config.itinerarios,
    guias: config.guias,
  };
}

/** «{n} de {mínimo} mínimo · máximo {máximo}» (contador role=status de cada lista). */
export function textoContadorLista(lista: ListaDestacada, cantidad: number): string {
  const def = DEFINICION_LISTA[lista];
  return `${cantidad} de ${def.minimo} mínimo · máximo ${def.maximo}`;
}

export function listaLlena(lista: ListaDestacada, cantidad: number): boolean {
  return cantidad >= DEFINICION_LISTA[lista].maximo;
}

/** Motivo de «Añadir» deshabilitado al llegar al máximo (Estados_UI.disabled). */
export function motivoListaLlena(lista: ListaDestacada): string {
  const def = DEFINICION_LISTA[lista];
  return `Ya hay ${def.maximo} ${def.plural}, el máximo. Quita uno para añadir otro.`;
}

/** El contenido ya no está PUBLICADO (o su estado se desconoce): no puede quedar destacado. */
export function esNoPublicado(ref: RefContenido): boolean {
  return ref.estado !== 'PUBLICADO';
}

/** Elementos de la lista que ya no están PUBLICADOS (p. ej. retirados después de elegirlos). */
export function noPublicados(lista: readonly RefContenido[]): readonly RefContenido[] {
  return lista.filter(esNoPublicado);
}

function errorLista(lista: ListaDestacada, elementos: readonly RefContenido[]): string | null {
  const def = DEFINICION_LISTA[lista];
  const n = elementos.length;
  if (n < def.minimo) return `Elige al menos ${def.minimo} ${def.plural} (ahora hay ${n}).`;
  if (n > def.maximo) return `Elige como máximo ${def.maximo} ${def.plural} (ahora hay ${n}).`;
  const fuera = noPublicados(elementos);
  if (fuera.length > 0) {
    return `Quita lo que ya no está publicado: ${fuera.map((r) => r.titulo).join(', ')}.`;
  }
  return null;
}

/** Validación de mínimos, máximos y estado al guardar (FLOW-014; el servidor sigue decidiendo). */
export function validarDestacados(f: FormularioDestacados): Partial<Record<CampoDestacados, string>> {
  const errores: Partial<Record<CampoDestacados, string>> = {};
  const titular = f.titular.trim();
  const subtitulo = f.subtitulo.trim();
  if (titular === '') errores.titular = 'Escribe el titular.';
  else if (longitudTexto(titular) > LIMITE_TITULAR) errores.titular = `Usa como máximo ${LIMITE_TITULAR} caracteres.`;
  if (subtitulo === '') errores.subtitulo = 'Escribe el subtítulo.';
  else if (longitudTexto(subtitulo) > LIMITE_SUBTITULO) {
    errores.subtitulo = `Usa como máximo ${LIMITE_SUBTITULO} caracteres.`;
  }
  if (f.medio === null) errores.medio = 'Elige la imagen del bloque principal.';
  else if (f.medio.estado !== null && f.medio.estado !== 'DISPONIBLE') {
    errores.medio = 'La imagen debe estar disponible: complétala en Medios o elige otra.';
  }
  for (const lista of LISTAS_DESTACADAS) {
    const error = errorLista(lista, f[lista]);
    if (error !== null) errores[lista] = error;
  }
  return errores;
}

export function entradaDesdeFormulario(f: FormularioDestacados): EntradaDestacados {
  return {
    titular: f.titular.trim(),
    subtitulo: f.subtitulo.trim(),
    medioId: f.medio?.id ?? 0,
    destinosIds: f.destinos.map((r) => r.id),
    itinerariosIds: f.itinerarios.map((r) => r.id),
    guiasIds: f.guias.map((r) => r.id),
  };
}

const ids = (lista: readonly RefContenido[]): string => lista.map((r) => r.id).join(',');

export function hayCambiosDestacados(
  actual: FormularioDestacados,
  guardado: FormularioDestacados | null,
): boolean {
  if (guardado === null) return false;
  return (
    actual.titular !== guardado.titular ||
    actual.subtitulo !== guardado.subtitulo ||
    (actual.medio?.id ?? null) !== (guardado.medio?.id ?? null) ||
    LISTAS_DESTACADAS.some((lista) => ids(actual[lista]) !== ids(guardado[lista]))
  );
}

const CAMPO_API: Readonly<Record<string, CampoDestacados>> = {
  hero_titular: 'titular',
  hero_subtitulo: 'subtitulo',
  hero_medio_id: 'medio',
  destinos_ids: 'destinos',
  itinerarios_ids: 'itinerarios',
  guias_ids: 'guias',
};

/**
 * Errores 400/422 de la API: `destinos_ids` y sus elementos (`destinos_ids.2`) van a la lista; el
 * resto, al resumen.
 */
export function erroresDestacados(
  campos: Readonly<Record<string, readonly string[]>>,
  mensaje: string,
): ErroresTraducidos<CampoDestacados> {
  const porCampo: Partial<Record<CampoDestacados, string>> = {};
  const generales: string[] = [];
  for (const [clave, mensajes] of Object.entries(campos)) {
    const campo = CAMPO_API[clave.split(/[.[]/)[0]];
    if (campo !== undefined && mensajes.length > 0) porCampo[campo] ??= mensajes[0];
    else generales.push(...mensajes);
  }
  if (Object.keys(porCampo).length === 0 && generales.length === 0) generales.push(mensaje);
  return { porCampo, generales };
}
