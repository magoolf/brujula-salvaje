/**
 * Formulario del Editor de contenido (SCR-036, FEAT-034..040, TKT-023): modelo único para los 7
 * tipos, valores vacíos, validación de formato al guardar (la de publicación es del servidor,
 * RULE-002..027), propuesta de slug (RULE-008), contadores y secciones por tipo (BLUEPRINT §11.2).
 * Puro: sin Angular ni RxJS (Regla 08). Los campos numéricos se guardan como texto (lo que el
 * usuario escribe) y se convierten al construir la petición en data/.
 */
import { EstadoMedio } from './medios';
import { EstadoEditorial, TipoContenido } from './modelos';

/** Medio referenciado por el contenido (portada o galería). */
export interface MedioRef {
  readonly id: number;
  /** null si se desconoce (p. ej. en una revisión restaurada con un medio que ya no se lista). */
  readonly estado: EstadoMedio | null;
  readonly miniatura: string | null;
  readonly textoAlternativo: string | null;
}

/** Contenido referenciado (relacionados, destino de un itinerario, elementos de colección…). */
export interface RefContenido {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
  readonly estado: EstadoEditorial | null;
  /** Slug, si se conoce (términos del glosario: enlace `/glosario#{slug}`). */
  readonly slug?: string | null;
}

/** Resultado de una búsqueda de contenido para un Combobox (error ya traducido a texto). */
export interface ResultadoBusqueda {
  readonly resultados: readonly RefContenido[];
  readonly error: string | null;
}

/** Mínimo de caracteres para buscar en un Combobox (HANDOFF Combobox). */
export const MINIMO_BUSQUEDA = 2;

/** Opción de un catálogo (país, categoría de guía, tipo de aventura, término del glosario). */
export interface OpcionCatalogo {
  readonly id: number;
  readonly nombre: string;
  /** Estado editorial cuando la opción es un contenido (tipos de aventura, términos). */
  readonly estado?: EstadoEditorial | null;
}

export interface FuenteForm {
  /** Identidad estable en la lista (track) independiente de la posición. */
  readonly clave: string;
  readonly titulo: string;
  readonly url: string;
  readonly entidadEditora: string;
  readonly fechaConsulta: string;
}

export interface DiaForm {
  readonly clave: string;
  readonly titulo: string;
  /** HTML de lista blanca (RULE-022). */
  readonly actividades: string;
  readonly distanciaKm: string;
  readonly desnivelPositivo: string;
  readonly desnivelNegativo: string;
  readonly alojamiento: string;
  /** HTML de lista blanca (RULE-022). */
  readonly consejos: string;
}

export interface ChecklistItemForm {
  readonly clave: string;
  readonly texto: string;
  readonly grupo: string;
  readonly esencial: boolean;
}

export interface ElementoColeccionForm {
  readonly clave: string;
  readonly contenido: RefContenido;
  readonly nota: string;
}

/**
 * Valores del formulario. Los campos que no usa un tipo se ignoran al construir su petición.
 * `descripcion` es el texto enriquecido principal de cada tipo (descripción experta del destino,
 * descripción del tipo y de la colección, cuerpo de la guía y de la página).
 */
export interface FormularioContenido {
  readonly tipo: TipoContenido;
  // Comunes (ATR-COMUN)
  readonly titulo: string;
  readonly slug: string;
  readonly fechaRevision: string;
  readonly seoTitulo: string;
  readonly seoDescripcion: string;
  readonly fuentes: readonly FuenteForm[];
  readonly relaciones: readonly RefContenido[];
  readonly terminos: readonly OpcionCatalogo[];
  readonly resumen: string;
  readonly descripcion: string;
  readonly portada: MedioRef | null;
  readonly galeria: readonly MedioRef[];
  readonly tipos: readonly number[];
  readonly dificultad: string;
  // Destino
  readonly pais: string;
  readonly tipoPrincipal: string;
  readonly meses: readonly number[];
  readonly duracionMin: string;
  readonly duracionMax: string;
  readonly presupuesto: string;
  readonly clima: string;
  readonly altitud: string;
  readonly comoLlegar: string;
  readonly seguridad: string;
  readonly sostenibilidad: string;
  readonly latitud: string;
  readonly longitud: string;
  // Itinerario
  readonly destino: RefContenido | null;
  readonly duracionDias: string;
  readonly distanciaTotal: string;
  readonly desnivelAcumulado: string;
  readonly dias: readonly DiaForm[];
  readonly riesgos: string;
  // Guía
  readonly categoria: string;
  readonly destinos: readonly RefContenido[];
  readonly remiteMetodologia: boolean;
  // Tipo de aventura
  readonly nivelExigencia: string;
  readonly orden: string;
  readonly checklist: readonly ChecklistItemForm[];
  // Colección
  readonly elementos: readonly ElementoColeccionForm[];
  // Término del glosario
  readonly definicion: string;
  // Página institucional
  readonly versionDocumento: string;
  readonly vigenteDesde: string;
}

let secuenciaClaves = 0;
/** Clave local estable de un elemento de lista (track), nunca enviada al servidor. */
export function nuevaClaveLista(prefijo: string): string {
  secuenciaClaves += 1;
  return `${prefijo}-${secuenciaClaves}`;
}

export function formularioVacio(tipo: TipoContenido): FormularioContenido {
  return {
    tipo,
    titulo: '',
    slug: '',
    fechaRevision: '',
    seoTitulo: '',
    seoDescripcion: '',
    fuentes: [],
    relaciones: [],
    terminos: [],
    resumen: '',
    descripcion: '',
    portada: null,
    galeria: [],
    tipos: [],
    dificultad: '',
    pais: '',
    tipoPrincipal: '',
    meses: [],
    duracionMin: '',
    duracionMax: '',
    presupuesto: '',
    clima: '',
    altitud: '',
    comoLlegar: '',
    seguridad: '',
    sostenibilidad: '',
    latitud: '',
    longitud: '',
    destino: null,
    duracionDias: '',
    distanciaTotal: '',
    desnivelAcumulado: '',
    dias: [],
    riesgos: '',
    categoria: '',
    destinos: [],
    remiteMetodologia: false,
    nivelExigencia: '',
    orden: '0',
    checklist: [],
    elementos: [],
    definicion: '',
    versionDocumento: '',
    vigenteDesde: '',
  };
}

/** Hay cambios sin guardar (ALT-026) si los valores difieren de los guardados. */
export function hayCambios(actual: FormularioContenido, guardado: FormularioContenido): boolean {
  return JSON.stringify(actual) !== JSON.stringify(guardado);
}

// ---------------------------------------------------------------------------------------------
// Límites del contrato (contracts/openapi.yaml, *Campos)
// ---------------------------------------------------------------------------------------------
export const LIMITES = {
  titulo: 150,
  slug: 120,
  resumen: 300,
  seoTitulo: 70,
  seoDescripcion: 160,
  clima: 5000,
  definicion: 600,
  versionDocumento: 20,
  fuenteTitulo: 200,
  fuenteUrl: 500,
  fuenteEntidad: 150,
  diaTitulo: 150,
  diaAlojamiento: 300,
  checklistTexto: 200,
  checklistGrupo: 60,
  notaElemento: 300,
  relaciones: 12,
  terminos: 50,
  fuentes: 30,
  galeria: 30,
  dias: 60,
  checklist: 100,
  elementos: 100,
  tipos: 12,
  destinosGuia: 20,
} as const;

/** Mínimos que muestran los contadores (se exigen al publicar, no al guardar). */
export const MINIMOS = {
  palabrasDescripcionDestino: 600,
  galeriaDestino: 3,
  checklist: 8,
  elementosColeccion: 4,
  relacionados: 3,
} as const;

export const PATRON_SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;

/** RULE-008: slug propuesto desde el título (minúsculas, sin tildes, guiones). */
export function proponerSlug(titulo: string): string {
  return titulo
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/ñ/g, 'n')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, LIMITES.slug)
    .replace(/-+$/g, '');
}

/** Texto visible de un HTML (sin etiquetas ni entidades básicas) para contar palabras. */
export function textoPlano(html: string): string {
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&(amp|lt|gt|quot|#39);/g, 'x')
    .replace(/\s+/g, ' ')
    .trim();
}

export function contarPalabras(html: string): number {
  const texto = textoPlano(html);
  return texto === '' ? 0 : texto.split(' ').length;
}

/** «412 de 600 palabras mínimas». */
export function textoContadorPalabras(palabras: number, minimo: number): string {
  return `${palabras} de ${minimo} palabras mínimas`;
}

/** Indicador de días del itinerario (AC-118): «Días: 5 de 7 según la duración». */
export function indicadorDias(
  formulario: Pick<FormularioContenido, 'dias' | 'duracionDias'>,
): { readonly texto: string; readonly coincide: boolean } {
  const duracion = aEntero(formulario.duracionDias);
  const dias = formulario.dias.length;
  if (duracion === null || Number.isNaN(duracion)) {
    return { texto: `Días: ${dias}. Indica la duración para comprobarlos.`, coincide: false };
  }
  return { texto: `Días: ${dias} de ${duracion} según la duración`, coincide: dias === duracion };
}

/** «{n} de {min} mínimo». */
export function textoMinimo(cantidad: number, minimo: number): string {
  return `${cantidad} de ${minimo} mínimo`;
}

// ---------------------------------------------------------------------------------------------
// Conversión de los valores de texto
// ---------------------------------------------------------------------------------------------
/** '' → null; texto no entero → NaN. */
export function aEntero(valor: string): number | null {
  const limpio = valor.trim();
  if (limpio === '') return null;
  return /^-?\d+$/.test(limpio) ? Number(limpio) : Number.NaN;
}

/** '' → null; admite coma decimal; texto no numérico → NaN. */
export function aDecimal(valor: string): number | null {
  const limpio = valor.trim().replace(',', '.');
  if (limpio === '') return null;
  return /^-?\d+(\.\d+)?$/.test(limpio) ? Number(limpio) : Number.NaN;
}

/** Coordenadas con 6 decimales (RULE-023). */
export function redondearCoordenada(valor: number): number {
  return Math.round(valor * 1e6) / 1e6;
}

export function aIdOpcional(valor: string): number | null {
  const id = aEntero(valor);
  return id !== null && !Number.isNaN(id) && id > 0 ? id : null;
}

/** RULE-021: URL de una fuente, solo http o https. */
export function esUrlHttp(valor: string): boolean {
  try {
    const url = new URL(valor);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * RULE-021: destino de un enlace del texto enriquecido. Solo http, https o una ruta interna
 * («/…», nunca «//…», que sería otro dominio). Cualquier otro esquema (javascript:, data:…) se
 * descarta (THREAT-021).
 */
export function esHrefPermitido(href: string): boolean {
  const valor = href.trim();
  if (valor === '') return false;
  if (valor.startsWith('/')) return !valor.startsWith('//') && !valor.includes('\\');
  return esUrlHttp(valor);
}

/** Enlace externo (avisado en el diálogo de enlace y en el sitio, DEC-AUTO-078). */
export function esEnlaceExterno(href: string): boolean {
  return !href.trim().startsWith('/');
}

/** Slug válido para el enlace de un término del glosario (`/glosario#{slug}`). */
export function esSlugValido(slug: string | null | undefined): slug is string {
  return typeof slug === 'string' && PATRON_SLUG.test(slug);
}

// ---------------------------------------------------------------------------------------------
// Validación de formato al guardar (la de publicación la hace el servidor)
// ---------------------------------------------------------------------------------------------
/** Clave de un campo del formulario: 'titulo', 'dias.2.titulo', 'fuentes.0.url', '_general'. */
export type ErroresFormulario = Readonly<Record<string, string>>;

export const MENSAJES = {
  obligatorio: 'Este campo es obligatorio.',
  slug: 'Usa solo minúsculas, números y guiones (sin guiones al principio ni al final).',
  entero: 'Escribe un número entero.',
  numero: 'Escribe un número.',
  fechaFutura: 'La fecha de última revisión no puede ser futura.',
  url: 'Escribe una dirección completa que empiece por http:// o https://.',
  duracion: 'La duración mínima no puede ser mayor que la máxima.',
  principal: 'El tipo principal debe estar entre los tipos marcados.',
  duplicado: 'Este elemento está repetido.',
} as const;

function maximo(limite: number): string {
  return `Escribe como máximo ${limite} caracteres.`;
}

function rango(min: number, max: number): string {
  return `Escribe un valor entre ${min} y ${max}.`;
}

function demasiados(limite: number): string {
  return `Como máximo ${limite} elementos.`;
}

function longitud(texto: string): number {
  return [...texto].length;
}

type Errores = Record<string, string>;

function validarLongitud(errores: Errores, campo: string, valor: string, limite: number): void {
  if (longitud(valor) > limite) errores[campo] = maximo(limite);
}

function validarEntero(
  errores: Errores,
  campo: string,
  valor: string,
  min: number,
  max: number,
): void {
  const n = aEntero(valor);
  if (n === null) return;
  if (Number.isNaN(n)) errores[campo] = MENSAJES.entero;
  else if (n < min || n > max) errores[campo] = rango(min, max);
}

function validarDecimal(
  errores: Errores,
  campo: string,
  valor: string,
  min: number,
  max: number,
): void {
  const n = aDecimal(valor);
  if (n === null) return;
  if (Number.isNaN(n)) errores[campo] = MENSAJES.numero;
  else if (n < min || n > max) errores[campo] = rango(min, max);
}

function validarCantidad(errores: Errores, campo: string, cantidad: number, limite: number): void {
  if (cantidad > limite) errores[campo] = demasiados(limite);
}

function fechaFutura(valor: string, hoy: string): boolean {
  return valor !== '' && valor > hoy;
}

function validarComunes(f: FormularioContenido, errores: Errores, hoy: string): void {
  if (f.titulo.trim() === '') errores['titulo'] = MENSAJES.obligatorio;
  else validarLongitud(errores, 'titulo', f.titulo, LIMITES.titulo);
  if (f.tipo !== 'PAGINA') {
    const slug = f.slug.trim();
    if (slug !== '' && !PATRON_SLUG.test(slug)) errores['slug'] = MENSAJES.slug;
    else validarLongitud(errores, 'slug', slug, LIMITES.slug);
  }
  if (fechaFutura(f.fechaRevision, hoy)) errores['fechaRevision'] = MENSAJES.fechaFutura;
  if (f.tipo === 'TERMINO') {
    validarLongitud(errores, 'definicion', f.definicion, LIMITES.definicion);
    return;
  }
  validarLongitud(errores, 'seoTitulo', f.seoTitulo, LIMITES.seoTitulo);
  validarLongitud(errores, 'seoDescripcion', f.seoDescripcion, LIMITES.seoDescripcion);
  if (f.tipo === 'PAGINA') return;
  validarLongitud(errores, 'resumen', f.resumen, LIMITES.resumen);
  validarCantidad(errores, 'relaciones', f.relaciones.length, LIMITES.relaciones);
  validarCantidad(errores, 'terminos', f.terminos.length, LIMITES.terminos);
  validarCantidad(errores, 'fuentes', f.fuentes.length, LIMITES.fuentes);
  f.fuentes.forEach((fuente, i) => {
    const base = `fuentes.${i}`;
    if (fuente.titulo.trim() === '') errores[`${base}.titulo`] = MENSAJES.obligatorio;
    else validarLongitud(errores, `${base}.titulo`, fuente.titulo, LIMITES.fuenteTitulo);
    const url = fuente.url.trim();
    if (url !== '' && (!esUrlHttp(url) || longitud(url) > LIMITES.fuenteUrl)) {
      errores[`${base}.url`] = MENSAJES.url;
    }
    validarLongitud(errores, `${base}.entidadEditora`, fuente.entidadEditora, LIMITES.fuenteEntidad);
  });
}

function validarDestino(f: FormularioContenido, errores: Errores): void {
  validarEntero(errores, 'dificultad', f.dificultad, 1, 5);
  validarEntero(errores, 'presupuesto', f.presupuesto, 1, 4);
  validarEntero(errores, 'duracionMin', f.duracionMin, 1, 90);
  validarEntero(errores, 'duracionMax', f.duracionMax, 1, 90);
  validarEntero(errores, 'altitud', f.altitud, -500, 9000);
  validarDecimal(errores, 'latitud', f.latitud, -90, 90);
  validarDecimal(errores, 'longitud', f.longitud, -180, 180);
  validarLongitud(errores, 'clima', f.clima, LIMITES.clima);
  validarCantidad(errores, 'tipos', f.tipos.length, LIMITES.tipos);
  validarCantidad(errores, 'galeria', f.galeria.length, LIMITES.galeria);
  const min = aEntero(f.duracionMin);
  const max = aEntero(f.duracionMax);
  if (
    errores['duracionMin'] === undefined &&
    errores['duracionMax'] === undefined &&
    min !== null &&
    max !== null &&
    min > max
  ) {
    errores['duracionMax'] = MENSAJES.duracion;
  }
  const principal = aIdOpcional(f.tipoPrincipal);
  if (principal !== null && !f.tipos.includes(principal)) errores['tipoPrincipal'] = MENSAJES.principal;
}

function validarItinerario(f: FormularioContenido, errores: Errores): void {
  validarEntero(errores, 'dificultad', f.dificultad, 1, 5);
  validarEntero(errores, 'duracionDias', f.duracionDias, 1, 60);
  validarDecimal(errores, 'distanciaTotal', f.distanciaTotal, 0, 99999.9);
  validarEntero(errores, 'desnivelAcumulado', f.desnivelAcumulado, 0, 1000000);
  validarCantidad(errores, 'tipos', f.tipos.length, LIMITES.tipos);
  validarCantidad(errores, 'galeria', f.galeria.length, LIMITES.galeria);
  validarCantidad(errores, 'dias', f.dias.length, LIMITES.dias);
  // El contrato no admite días sin título o actividades (DiaEntrada, DEC-AUTO-905).
  f.dias.forEach((dia, i) => {
    const base = `dias.${i}`;
    if (dia.titulo.trim() === '') errores[`${base}.titulo`] = MENSAJES.obligatorio;
    else validarLongitud(errores, `${base}.titulo`, dia.titulo, LIMITES.diaTitulo);
    if (textoPlano(dia.actividades) === '') errores[`${base}.actividades`] = MENSAJES.obligatorio;
    validarDecimal(errores, `${base}.distanciaKm`, dia.distanciaKm, 0, 99999.9);
    validarEntero(errores, `${base}.desnivelPositivo`, dia.desnivelPositivo, 0, 20000);
    validarEntero(errores, `${base}.desnivelNegativo`, dia.desnivelNegativo, 0, 20000);
    validarLongitud(errores, `${base}.alojamiento`, dia.alojamiento, LIMITES.diaAlojamiento);
  });
}

function validarTipo(f: FormularioContenido, errores: Errores): void {
  validarEntero(errores, 'nivelExigencia', f.nivelExigencia, 1, 5);
  validarEntero(errores, 'orden', f.orden, 0, 1000);
  validarCantidad(errores, 'checklist', f.checklist.length, LIMITES.checklist);
  const vistos = new Set<string>();
  f.checklist.forEach((item, i) => {
    const base = `checklist.${i}`;
    const texto = item.texto.trim();
    if (texto === '') errores[`${base}.texto`] = MENSAJES.obligatorio;
    else if (vistos.has(texto.toLowerCase())) errores[`${base}.texto`] = MENSAJES.duplicado;
    else validarLongitud(errores, `${base}.texto`, item.texto, LIMITES.checklistTexto);
    vistos.add(texto.toLowerCase());
    validarLongitud(errores, `${base}.grupo`, item.grupo, LIMITES.checklistGrupo);
  });
}

function validarColeccion(f: FormularioContenido, errores: Errores): void {
  validarCantidad(errores, 'elementos', f.elementos.length, LIMITES.elementos);
  f.elementos.forEach((el, i) =>
    validarLongitud(errores, `elementos.${i}.nota`, el.nota, LIMITES.notaElemento),
  );
}

function validarPagina(f: FormularioContenido, errores: Errores): void {
  if (f.versionDocumento.trim() === '') errores['versionDocumento'] = MENSAJES.obligatorio;
  else validarLongitud(errores, 'versionDocumento', f.versionDocumento, LIMITES.versionDocumento);
  if (f.vigenteDesde === '') errores['vigenteDesde'] = MENSAJES.obligatorio;
}

/**
 * Validación de formato al «Guardar borrador» (FLOW-011 paso 3). Nunca exige los requisitos de
 * publicación: esos los indica el CompletenessPanel y se validan en SCR-038.
 * @param hoy Fecha máxima admitida para la revisión (AAAA-MM-DD), de `fechaMaximaRevision` (RULE-009).
 */
export function validarFormato(f: FormularioContenido, hoy: string): ErroresFormulario {
  const errores: Errores = {};
  validarComunes(f, errores, hoy);
  switch (f.tipo) {
    case 'DESTINO':
      validarDestino(f, errores);
      break;
    case 'ITINERARIO':
      validarItinerario(f, errores);
      break;
    case 'GUIA':
      validarCantidad(errores, 'tipos', f.tipos.length, LIMITES.tipos);
      validarCantidad(errores, 'destinos', f.destinos.length, LIMITES.destinosGuia);
      break;
    case 'TIPO':
      validarTipo(f, errores);
      break;
    case 'COLECCION':
      validarColeccion(f, errores);
      break;
    case 'PAGINA':
      validarPagina(f, errores);
      break;
    case 'TERMINO':
      break;
  }
  return errores;
}

/** Desfase de la zona horaria más adelantada (UTC+14, Kiritimati). */
const DESFASE_MAXIMO_MS = 14 * 60 * 60 * 1000;

/**
 * Fecha máxima admitida (AAAA-MM-DD) para la revisión y las fechas de consulta (RULE-009,
 * DEC-AUTO-977): la fecha actual en UTC+14. Una fecha es «futura» solo si lo es en todas las zonas
 * horarias, así que el criterio no depende de la zona del navegador ni de la hora del día; con la
 * fecha local, un contenido revisado «hoy» en otra zona se bloqueaba al guardar o publicar.
 */
export function fechaMaximaRevision(ahora: Date): string {
  return new Date(ahora.getTime() + DESFASE_MAXIMO_MS).toISOString().slice(0, 10);
}

/** Id del DOM del control de un campo (destino de los enlaces del ErrorSummary). */
export function idCampo(clave: string): string {
  return `campo-${clave.replace(/[^a-zA-Z0-9]+/g, '-')}`;
}

// ---------------------------------------------------------------------------------------------
// Secciones por tipo (BLUEPRINT §11.2 SCR-036; HANDOFF: una página con secciones)
// ---------------------------------------------------------------------------------------------
export type IdSeccion =
  | 'identidad'
  | 'datos'
  | 'contenido'
  | 'viaje'
  | 'seguridad'
  | 'ubicacion'
  | 'dias'
  | 'checklist'
  | 'elementos'
  | 'medios'
  | 'relacionados'
  | 'fuentes'
  | 'seo'
  | 'revision'
  | 'historial';

export interface SeccionEditor {
  readonly id: IdSeccion;
  readonly titulo: string;
  /** Campos (primer segmento de la clave) cuyos requisitos o errores pertenecen a la sección. */
  readonly campos: readonly string[];
}

const S = (id: IdSeccion, titulo: string, campos: readonly string[]): SeccionEditor => ({
  id,
  titulo,
  campos,
});

const SECCION_MEDIOS = S('medios', 'Medios', ['portada', 'galeria']);
const SECCION_RELACIONADOS = S('relacionados', 'Relacionados y glosario', ['relaciones', 'terminos']);
const SECCION_FUENTES = S('fuentes', 'Fuentes', ['fuentes', 'remiteMetodologia']);
const SECCION_SEO = S('seo', 'SEO', ['seoTitulo', 'seoDescripcion']);
const SECCION_REVISION = S('revision', 'Revisión', ['fechaRevision']);
const SECCION_HISTORIAL = S('historial', 'Historial', []);

const SECCIONES: Readonly<Record<TipoContenido, readonly SeccionEditor[]>> = {
  DESTINO: [
    S('identidad', 'Identidad', ['titulo', 'slug', 'pais']),
    S('datos', 'Datos clave', ['tipos', 'tipoPrincipal', 'dificultad', 'meses', 'duracionMin', 'duracionMax', 'presupuesto', 'clima', 'altitud']),
    S('contenido', 'Contenido experto', ['resumen', 'descripcion']),
    S('viaje', 'Viaje', ['comoLlegar']),
    S('seguridad', 'Seguridad y sostenibilidad', ['seguridad', 'sostenibilidad']),
    S('ubicacion', 'Ubicación', ['latitud', 'longitud']),
    SECCION_MEDIOS,
    SECCION_RELACIONADOS,
    SECCION_FUENTES,
    SECCION_SEO,
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
  ITINERARIO: [
    S('identidad', 'Identidad', ['titulo', 'slug', 'destino']),
    S('datos', 'Datos', ['duracionDias', 'dificultad', 'tipos', 'distanciaTotal', 'desnivelAcumulado']),
    S('contenido', 'Resumen', ['resumen']),
    S('dias', 'Días', ['dias']),
    S('seguridad', 'Riesgos y seguridad', ['riesgos']),
    SECCION_MEDIOS,
    SECCION_RELACIONADOS,
    SECCION_FUENTES,
    SECCION_SEO,
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
  GUIA: [
    S('identidad', 'Identidad', ['titulo', 'slug', 'categoria']),
    S('contenido', 'Resumen y cuerpo', ['resumen', 'descripcion']),
    S('datos', 'Destinos y tipos relacionados', ['destinos', 'tipos']),
    S('medios', 'Medios', ['portada']),
    SECCION_RELACIONADOS,
    SECCION_FUENTES,
    SECCION_SEO,
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
  TIPO: [
    S('identidad', 'Identidad', ['titulo', 'slug', 'orden']),
    S('contenido', 'Descripción', ['resumen', 'descripcion']),
    S('datos', 'Nivel de exigencia', ['nivelExigencia']),
    S('checklist', 'Checklist', ['checklist']),
    S('medios', 'Medios', ['portada']),
    S('relacionados', 'Relacionados', ['relaciones', 'terminos']),
    SECCION_SEO,
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
  COLECCION: [
    S('identidad', 'Identidad', ['titulo', 'slug']),
    S('contenido', 'Descripción', ['resumen', 'descripcion']),
    S('elementos', 'Elementos', ['elementos']),
    S('medios', 'Portada', ['portada']),
    SECCION_SEO,
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
  TERMINO: [
    S('identidad', 'Término', ['titulo', 'slug', 'definicion']),
    S('relacionados', 'Contenidos vinculados', []),
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
  PAGINA: [
    S('identidad', 'Página', ['titulo', 'versionDocumento', 'vigenteDesde']),
    S('contenido', 'Cuerpo', ['descripcion']),
    SECCION_SEO,
    SECCION_REVISION,
    SECCION_HISTORIAL,
  ],
};

export function seccionesDe(tipo: TipoContenido): readonly SeccionEditor[] {
  return SECCIONES[tipo];
}

/** Sección a la que pertenece un campo ('dias.2.titulo' → «Días»); null si no tiene. */
export function seccionDeCampo(tipo: TipoContenido, campo: string): SeccionEditor | null {
  const raiz = campo.split('.')[0];
  return SECCIONES[tipo].find((s) => s.campos.includes(raiz)) ?? null;
}

/** Nombre legible de un campo para el ErrorSummary y el CompletenessPanel. */
const ETIQUETAS_CAMPO: Readonly<Record<string, string>> = {
  titulo: 'Título',
  slug: 'Slug',
  pais: 'País',
  tipos: 'Tipos de aventura',
  tipoPrincipal: 'Tipo principal',
  dificultad: 'Dificultad',
  meses: 'Mejores meses',
  duracionMin: 'Duración mínima',
  duracionMax: 'Duración máxima',
  presupuesto: 'Presupuesto',
  clima: 'Clima',
  altitud: 'Altitud máxima',
  resumen: 'Resumen',
  descripcion: 'Descripción',
  comoLlegar: 'Cómo llegar',
  seguridad: 'Seguridad y riesgos',
  sostenibilidad: 'Sostenibilidad',
  latitud: 'Latitud',
  longitud: 'Longitud',
  portada: 'Portada',
  galeria: 'Galería',
  relaciones: 'Relacionados',
  terminos: 'Términos del glosario',
  fuentes: 'Fuentes',
  remiteMetodologia: 'Remite a la Metodología',
  seoTitulo: 'Título SEO',
  seoDescripcion: 'Descripción SEO',
  fechaRevision: 'Fecha de revisión',
  destino: 'Destino',
  duracionDias: 'Duración',
  distanciaTotal: 'Distancia total',
  desnivelAcumulado: 'Desnivel acumulado',
  dias: 'Días',
  riesgos: 'Riesgos y seguridad',
  categoria: 'Categoría',
  destinos: 'Destinos relacionados',
  nivelExigencia: 'Nivel de exigencia',
  orden: 'Orden',
  checklist: 'Checklist',
  elementos: 'Elementos',
  definicion: 'Definición',
  versionDocumento: 'Versión del documento',
  vigenteDesde: 'Vigente desde',
  _general: 'General',
};

const ETIQUETAS_SUBCAMPO: Readonly<Record<string, string>> = {
  titulo: 'título',
  actividades: 'actividades',
  distanciaKm: 'distancia',
  desnivelPositivo: 'desnivel positivo',
  desnivelNegativo: 'desnivel negativo',
  alojamiento: 'alojamiento',
  consejos: 'consejos',
  url: 'URL',
  entidadEditora: 'entidad editora',
  fechaConsulta: 'fecha de consulta',
  texto: 'texto',
  grupo: 'grupo',
  nota: 'nota',
  contenido: 'contenido',
};

const SINGULAR_LISTA: Readonly<Record<string, string>> = {
  dias: 'Día',
  fuentes: 'Fuente',
  checklist: 'Elemento',
  elementos: 'Elemento',
  relaciones: 'Relacionado',
  galeria: 'Imagen',
};

export function etiquetaCampo(campo: string): string {
  const [raiz, indice, sub] = campo.split('.');
  if (indice !== undefined && /^\d+$/.test(indice)) {
    const elemento = `${SINGULAR_LISTA[raiz] ?? ETIQUETAS_CAMPO[raiz] ?? raiz} ${Number(indice) + 1}`;
    return sub === undefined ? elemento : `${elemento}: ${ETIQUETAS_SUBCAMPO[sub] ?? sub}`;
  }
  return ETIQUETAS_CAMPO[raiz] ?? raiz;
}

/** Destino del enlace de un error: el control del campo o, en una lista, su contenedor. */
export function idDestinoCampo(campo: string): string {
  return idCampo(campo === '_general' ? 'titulo' : campo);
}

// ---------------------------------------------------------------------------------------------
// Listas: altas, bajas y reordenación (SortableList con «Subir»/«Bajar», WCAG 2.5.7)
// ---------------------------------------------------------------------------------------------
export function moverEn<T>(lista: readonly T[], desde: number, hasta: number): readonly T[] {
  if (desde === hasta || desde < 0 || hasta < 0 || desde >= lista.length || hasta >= lista.length) {
    return lista;
  }
  const copia = [...lista];
  const [elemento] = copia.splice(desde, 1);
  copia.splice(hasta, 0, elemento);
  return copia;
}

export function quitarEn<T>(lista: readonly T[], indice: number): readonly T[] {
  return lista.filter((_, i) => i !== indice);
}

export function reemplazarEn<T>(lista: readonly T[], indice: number, valor: T): readonly T[] {
  return lista.map((actual, i) => (i === indice ? valor : actual));
}

/** Añade referencias sin duplicados (por tipo e id), respetando el máximo. */
export function anadirSinDuplicados<T extends { readonly id: number; readonly tipo?: string }>(
  lista: readonly T[],
  nuevos: readonly T[],
  limite: number,
): readonly T[] {
  const clave = (x: T): string => `${x.tipo ?? ''}:${x.id}`;
  const vistos = new Set(lista.map(clave));
  const resultado = [...lista];
  for (const nuevo of nuevos) {
    if (resultado.length >= limite) break;
    if (vistos.has(clave(nuevo))) continue;
    vistos.add(clave(nuevo));
    resultado.push(nuevo);
  }
  return resultado;
}

/** Anuncio role=status de un movimiento: «Día 2 movido a la posición 3 de 7». */
export function anuncioMovido(nombre: string, posicion: number, total: number): string {
  return `${nombre} movido a la posición ${posicion} de ${total}.`;
}

export const MESES: readonly { readonly numero: number; readonly nombre: string }[] = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
].map((nombre, i) => ({ numero: i + 1, nombre }));

/** Alterna un valor en una lista de números (casillas de tipos y meses), ordenada. */
export function alternarNumero(lista: readonly number[], valor: number): readonly number[] {
  return lista.includes(valor)
    ? lista.filter((v) => v !== valor)
    : [...lista, valor].sort((a, b) => a - b);
}

/**
 * Una revisión restaurada (FEAT-050) solo trae ids: se completan los datos de visualización
 * (miniaturas, títulos) con los del formulario actual cuando el id coincide.
 */
export function enriquecerReferencias(
  restaurado: FormularioContenido,
  actual: FormularioContenido,
): FormularioContenido {
  const medios = new Map<number, MedioRef>();
  for (const m of [...(actual.portada ? [actual.portada] : []), ...actual.galeria]) medios.set(m.id, m);
  const contenidos = new Map<string, RefContenido>();
  for (const r of [
    ...actual.relaciones,
    ...actual.destinos,
    ...(actual.destino ? [actual.destino] : []),
    ...actual.elementos.map((e) => e.contenido),
  ]) {
    contenidos.set(`${r.tipo}:${r.id}`, r);
  }
  const terminos = new Map(actual.terminos.map((t) => [t.id, t]));
  const medio = (m: MedioRef): MedioRef => (m.estado === null ? (medios.get(m.id) ?? m) : m);
  const ref = (r: RefContenido): RefContenido =>
    r.estado === null ? (contenidos.get(`${r.tipo}:${r.id}`) ?? r) : r;
  return {
    ...restaurado,
    portada: restaurado.portada ? medio(restaurado.portada) : null,
    galeria: restaurado.galeria.map(medio),
    relaciones: restaurado.relaciones.map(ref),
    destinos: restaurado.destinos.map(ref),
    destino: restaurado.destino ? ref(restaurado.destino) : null,
    elementos: restaurado.elementos.map((e) => ({ ...e, contenido: ref(e.contenido) })),
    terminos: restaurado.terminos.map((t) => terminos.get(t.id) ?? t),
  };
}
