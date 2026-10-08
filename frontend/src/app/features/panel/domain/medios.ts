/**
 * Dominio de medios del panel (MOD-011: FEAT-041/042, FLOW-013, RULE-005, RULE-021,
 * DEC-AUTO-044). Funciones puras, sin Angular ni RxJS (Skill_Frontend Regla 08): modelos, reglas de
 * la subida (validación previa en el cliente), de la catalogación, de los filtros de la biblioteca
 * (sincronizados con la URL) y de la selección del Selector de medios (SCR-041).
 * El servidor es siempre la autoridad: estas reglas solo evitan peticiones que se rechazarían y
 * explican el motivo antes de subir.
 */
import { EstadoEditorial } from './modelos';

// ------------------------------------------------------------------------------------------------
// Modelos
// ------------------------------------------------------------------------------------------------

/** STATE-002: PENDIENTE_METADATOS → DISPONIBLE → RETIRADO → PENDIENTE_METADATOS. */
export type EstadoMedio = 'PENDIENTE_METADATOS' | 'DISPONIBLE' | 'RETIRADO';
export type FormatoDerivado = 'AVIF' | 'WEBP' | 'JPEG';
export type FormatoOrigen = 'JPEG' | 'PNG' | 'WEBP';
export type PendienteCatalogacion =
  | 'texto_alternativo'
  | 'autor_credito'
  | 'licencia'
  | 'licencia_incompatible';

export interface DerivadoMedio {
  readonly formato: FormatoDerivado;
  readonly ancho: number;
  readonly alto: number | null;
  /** Ruta del endpoint autenticado del panel (sirve también medios no públicos). */
  readonly url: string;
}

export interface LicenciaMedio {
  readonly id: number;
  readonly codigo: string;
  readonly nombre: string;
  readonly compatiblePublicacion: boolean;
}

/** Licencia del catálogo (DATA-015) para el desplegable de SCR-040 y el filtro de SCR-039. */
export interface LicenciaCatalogo extends LicenciaMedio {
  readonly activa: boolean;
}

export interface Medio {
  readonly id: number;
  readonly estado: EstadoMedio;
  readonly tituloInterno: string | null;
  readonly textoAlternativo: string | null;
  readonly pieDeFoto: string | null;
  readonly autorCredito: string | null;
  readonly fuenteUrl: string | null;
  readonly licencia: LicenciaMedio | null;
  readonly formatoOrigen: FormatoOrigen;
  readonly anchoPx: number;
  readonly altoPx: number;
  readonly pesoBytes: number;
  readonly derivados: readonly DerivadoMedio[];
  readonly numeroUsos: number;
  readonly enUsoPublicado: boolean;
  readonly subidoPor: string;
  readonly subidoEn: Date;
  readonly actualizadoEn: Date;
  readonly pendientes: readonly PendienteCatalogacion[];
}

export interface PaginaMedios {
  readonly medios: readonly Medio[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
}

export type TipoUsoMedio = 'DESTINO' | 'ITINERARIO' | 'GUIA' | 'TIPO' | 'COLECCION' | 'CONFIG_INICIO';
export type RolUsoMedio = 'PORTADA' | 'GALERIA' | 'HERO';

export interface UsoMedio {
  readonly tipoContenido: TipoUsoMedio;
  readonly contenidoId: number;
  readonly titulo: string;
  readonly estadoEditorial: EstadoEditorial | null;
  readonly rol: RolUsoMedio;
}

export interface PaginaUsos {
  readonly usos: readonly UsoMedio[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
}

// ------------------------------------------------------------------------------------------------
// Etiquetas (nunca el código del enum en pantalla, HANDOFF Badge)
// ------------------------------------------------------------------------------------------------

export const ETIQUETA_ESTADO_MEDIO: Readonly<Record<EstadoMedio, string>> = {
  PENDIENTE_METADATOS: 'Pendiente de datos',
  DISPONIBLE: 'Disponible',
  RETIRADO: 'Retirado',
};

export type VarianteEstadoMedio = 'pendiente' | 'publicado' | 'retirado';

export function varianteEstadoMedio(estado: EstadoMedio): VarianteEstadoMedio {
  switch (estado) {
    case 'DISPONIBLE':
      return 'publicado';
    case 'RETIRADO':
      return 'retirado';
    default:
      return 'pendiente';
  }
}

export const ETIQUETA_PENDIENTE: Readonly<Record<PendienteCatalogacion, string>> = {
  texto_alternativo: 'Falta el texto alternativo',
  autor_credito: 'Falta el autor o crédito',
  licencia: 'Falta la licencia',
  licencia_incompatible: 'La licencia no permite publicar la imagen',
};

export const ETIQUETA_TIPO_USO: Readonly<Record<TipoUsoMedio, string>> = {
  DESTINO: 'Destino',
  ITINERARIO: 'Itinerario',
  GUIA: 'Guía',
  TIPO: 'Tipo de aventura',
  COLECCION: 'Colección',
  CONFIG_INICIO: 'Destacados de inicio',
};

export const ETIQUETA_ROL_USO: Readonly<Record<RolUsoMedio, string>> = {
  PORTADA: 'Portada',
  GALERIA: 'Galería',
  HERO: 'Imagen principal',
};

/** Nombre visible de un medio: título interno, texto alternativo o «Imagen n.º {id}». */
export function nombreMedio(medio: Pick<Medio, 'id' | 'tituloInterno' | 'textoAlternativo'>): string {
  const titulo = medio.tituloInterno?.trim() || medio.textoAlternativo?.trim();
  return titulo ? titulo : `Imagen n.º ${medio.id}`;
}

/** Texto accesible del mosaico (HANDOFF SCR-039: «{título}, {estado}, {licencia}, usado en {n}»). */
export function descripcionMosaico(medio: Medio): string {
  const licencia = medio.licencia?.nombre ?? 'sin licencia';
  const usos = medio.numeroUsos === 1 ? 'usado en 1 contenido' : `usado en ${medio.numeroUsos} contenidos`;
  return `${nombreMedio(medio)}, ${ETIQUETA_ESTADO_MEDIO[medio.estado]}, ${licencia}, ${usos}`;
}

/** «Usado en {n}» del mosaico. */
export function textoUsos(numero: number): string {
  return numero === 0 ? 'Sin usar' : `Usado en ${numero}`;
}

const FORMATO_PESO = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 1 });

/** Peso legible en KB/MB (base 1024, como lo muestran los sistemas de archivos). */
export function formatearPeso(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${FORMATO_PESO.format(bytes / 1024)} KB`;
  return `${FORMATO_PESO.format(bytes / (1024 * 1024))} MB`;
}

// ------------------------------------------------------------------------------------------------
// Imágenes: miniatura y srcset a partir de los derivados
// ------------------------------------------------------------------------------------------------

const PREFERENCIA_FORMATO: readonly FormatoDerivado[] = ['WEBP', 'JPEG', 'AVIF'];

/** Derivados de un formato ordenados por ancho (el WebP primero: lo soportan los 3 motores). */
function derivadosDeFormato(derivados: readonly DerivadoMedio[]): readonly DerivadoMedio[] {
  for (const formato of PREFERENCIA_FORMATO) {
    const lista = derivados.filter((d) => d.formato === formato);
    if (lista.length > 0) return [...lista].sort((a, b) => a.ancho - b.ancho);
  }
  return [];
}

/** Derivado más pequeño con al menos `anchoMinimo` px (o el mayor disponible). */
export function derivadoPara(
  derivados: readonly DerivadoMedio[],
  anchoMinimo: number,
): DerivadoMedio | null {
  const lista = derivadosDeFormato(derivados);
  if (lista.length === 0) return null;
  return lista.find((d) => d.ancho >= anchoMinimo) ?? lista[lista.length - 1];
}

/** `srcset` con todos los anchos del formato preferido. */
export function srcsetDe(derivados: readonly DerivadoMedio[]): string {
  return derivadosDeFormato(derivados)
    .map((d) => `${d.url} ${d.ancho}w`)
    .join(', ');
}

// ------------------------------------------------------------------------------------------------
// Subida (FLOW-013, DEC-AUTO-044): validación previa y resultado por archivo
// ------------------------------------------------------------------------------------------------

export const MAXIMO_ARCHIVOS = 10;
export const TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024;
export const TIPOS_PERMITIDOS: readonly string[] = ['image/jpeg', 'image/png', 'image/webp'];
export const EXTENSIONES_PERMITIDAS: readonly string[] = ['jpg', 'jpeg', 'png', 'webp'];
/** Valor del atributo `accept` del input de archivos. */
export const ACEPTAR_ARCHIVOS = TIPOS_PERMITIDOS.join(',');
export const REGLAS_SUBIDA =
  'JPEG, PNG o WebP · hasta 10 MB · mínimo 1.200 px en el lado mayor · hasta 10 a la vez';

export type MotivoRechazo =
  | 'formato_no_permitido'
  | 'tamano_excedido'
  | 'dimensiones_insuficientes'
  | 'megapixeles_excedidos'
  | 'archivo_corrupto';

export const MENSAJE_MOTIVO: Readonly<Record<MotivoRechazo, string>> = {
  formato_no_permitido: 'Formato no permitido: usa JPEG, PNG o WebP.',
  tamano_excedido: 'Supera los 10 MB.',
  dimensiones_insuficientes: 'Es demasiado pequeña: necesita al menos 1.200 px en el lado mayor.',
  megapixeles_excedidos: 'Supera los 40 megapíxeles.',
  archivo_corrupto: 'El archivo está dañado o no es una imagen válida.',
};

export const MENSAJE_DEMASIADOS_ARCHIVOS =
  'Puedes subir hasta 10 imágenes a la vez. Elige 10 o menos y vuelve a intentarlo.';
export const MENSAJE_DUPLICADA = 'Esta imagen ya está en la biblioteca.';

/** Lo mínimo de un `File` que hace falta para validarlo (sin depender del DOM). */
export interface ArchivoCandidato {
  readonly nombre: string;
  readonly tipo: string;
  readonly tamano: number;
}

function extension(nombre: string): string {
  const punto = nombre.lastIndexOf('.');
  return punto < 0 ? '' : nombre.slice(punto + 1).toLowerCase();
}

/**
 * Validación previa de un archivo (tipo declarado y extensión, tamaño). El tipo real, las
 * dimensiones y los megapíxeles los verifica el servidor por el contenido (THREAT-006).
 */
export function validarArchivo(archivo: ArchivoCandidato): MotivoRechazo | null {
  const tipo = archivo.tipo.toLowerCase();
  const tipoValido = tipo === '' || TIPOS_PERMITIDOS.includes(tipo);
  if (!tipoValido || !EXTENSIONES_PERMITIDAS.includes(extension(archivo.nombre))) {
    return 'formato_no_permitido';
  }
  if (archivo.tamano > TAMANO_MAXIMO_BYTES) return 'tamano_excedido';
  if (archivo.tamano === 0) return 'archivo_corrupto';
  return null;
}

/** Más de 10 archivos: se rechaza la selección completa, sin subir ninguno (HANDOFF MediaUploader). */
export function excedeMaximo(cantidad: number): boolean {
  return cantidad > MAXIMO_ARCHIVOS;
}

export type TipoResultadoArchivo = 'ACEPTADO' | 'RECHAZADO' | 'DUPLICADO';

export interface ResultadoArchivo {
  readonly nombreArchivo: string;
  readonly resultado: TipoResultadoArchivo;
  readonly medio: Medio | null;
  readonly medioExistenteId: number | null;
  readonly motivo: MotivoRechazo | null;
  /** `true` si lo rechazó la validación previa (no llegó a enviarse). */
  readonly local: boolean;
}

export function rechazoLocal(nombreArchivo: string, motivo: MotivoRechazo): ResultadoArchivo {
  return {
    nombreArchivo,
    resultado: 'RECHAZADO',
    medio: null,
    medioExistenteId: null,
    motivo,
    local: true,
  };
}

export function mensajeResultado(resultado: ResultadoArchivo): string {
  switch (resultado.resultado) {
    case 'ACEPTADO':
      return 'Aceptada. Completa sus datos para poder usarla.';
    case 'DUPLICADO':
      return MENSAJE_DUPLICADA;
    default:
      return resultado.motivo ? MENSAJE_MOTIVO[resultado.motivo] : MENSAJE_MOTIVO.archivo_corrupto;
  }
}

function plural(n: number, singular: string, pluralTexto: string): string {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}

/** Resumen final en role=status: «8 aceptadas, 1 rechazada, 1 duplicada». */
export function resumenSubida(resultados: readonly ResultadoArchivo[]): string {
  const aceptadas = resultados.filter((r) => r.resultado === 'ACEPTADO').length;
  const rechazadas = resultados.filter((r) => r.resultado === 'RECHAZADO').length;
  const duplicadas = resultados.filter((r) => r.resultado === 'DUPLICADO').length;
  const partes = [plural(aceptadas, 'aceptada', 'aceptadas')];
  if (rechazadas > 0) partes.push(plural(rechazadas, 'rechazada', 'rechazadas'));
  if (duplicadas > 0) partes.push(plural(duplicadas, 'duplicada', 'duplicadas'));
  return partes.join(', ');
}

/** Porcentaje entero 0..100 del progreso de envío. */
export function porcentaje(cargados: number, total: number | null): number {
  if (total === null || total <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((cargados / total) * 100)));
}

// ------------------------------------------------------------------------------------------------
// Catalogación (SCR-040, RULE-005, RULE-021)
// ------------------------------------------------------------------------------------------------

export type CampoCatalogacion =
  | 'tituloInterno'
  | 'textoAlternativo'
  | 'pieDeFoto'
  | 'autorCredito'
  | 'fuenteUrl'
  | 'licenciaId';

export interface FormularioCatalogacion {
  readonly tituloInterno: string;
  readonly textoAlternativo: string;
  readonly pieDeFoto: string;
  readonly autorCredito: string;
  readonly fuenteUrl: string;
  /** Id de la licencia como texto (valor del <select>); '' = sin licencia. */
  readonly licenciaId: string;
}

/** Entrada de la operación de catalogar (dominio; DATA la traduce al contrato). */
export interface EntradaCatalogacion {
  readonly tituloInterno?: string | null;
  readonly textoAlternativo?: string | null;
  readonly pieDeFoto?: string | null;
  readonly autorCredito?: string | null;
  readonly fuenteUrl?: string | null;
  readonly licenciaId?: number | null;
}

export const LONGITUD_MAXIMA: Readonly<Record<Exclude<CampoCatalogacion, 'licenciaId'>, number>> = {
  tituloInterno: 150,
  textoAlternativo: 250,
  pieDeFoto: 300,
  autorCredito: 150,
  fuenteUrl: 500,
};

export const MENSAJE_OBLIGATORIO_DISPONIBLE =
  'Obligatorio: una imagen disponible necesita este dato (RULE-005).';
export const MENSAJE_URL_FUENTE = 'Escribe una dirección completa que empiece por http:// o https://.';

export function formularioDesdeMedio(medio: Medio): FormularioCatalogacion {
  return {
    tituloInterno: medio.tituloInterno ?? '',
    textoAlternativo: medio.textoAlternativo ?? '',
    pieDeFoto: medio.pieDeFoto ?? '',
    autorCredito: medio.autorCredito ?? '',
    fuenteUrl: medio.fuenteUrl ?? '',
    licenciaId: medio.licencia ? String(medio.licencia.id) : '',
  };
}

function longitud(texto: string): number {
  return [...texto].length;
}

function tieneControl(texto: string): boolean {
  return [...texto].some((c) => {
    const codigo = c.codePointAt(0) ?? 0;
    return codigo < 0x20 || codigo === 0x7f;
  });
}

/** RULE-021: solo http/https, sin espacios ni caracteres de control. */
export function esUrlFuenteValida(url: string): boolean {
  if (!/^https?:\/\/\S+$/i.test(url) || tieneControl(url)) return false;
  try {
    const analizada = new URL(url);
    return (analizada.protocol === 'http:' || analizada.protocol === 'https:') && analizada.hostname !== '';
  } catch {
    return false;
  }
}

/**
 * Validación previa de la catalogación. Un medio PENDIENTE_METADATOS se puede guardar con datos
 * parciales (sigue pendiente); uno DISPONIBLE conserva siempre alt, crédito y licencia (RULE-005:
 * no hay transición DISPONIBLE → PENDIENTE_METADATOS).
 */
export function validarCatalogacion(
  formulario: FormularioCatalogacion,
  estado: EstadoMedio,
): Partial<Record<CampoCatalogacion, string>> {
  const errores: Partial<Record<CampoCatalogacion, string>> = {};
  for (const [campo, maximo] of Object.entries(LONGITUD_MAXIMA) as [
    Exclude<CampoCatalogacion, 'licenciaId'>,
    number,
  ][]) {
    if (longitud(formulario[campo].trim()) > maximo) {
      errores[campo] = `Máximo ${maximo} caracteres.`;
    }
  }
  if (estado === 'DISPONIBLE') {
    if (formulario.textoAlternativo.trim() === '') errores.textoAlternativo = MENSAJE_OBLIGATORIO_DISPONIBLE;
    if (formulario.autorCredito.trim() === '') errores.autorCredito = MENSAJE_OBLIGATORIO_DISPONIBLE;
    if (formulario.licenciaId === '') errores.licenciaId = MENSAJE_OBLIGATORIO_DISPONIBLE;
  }
  const url = formulario.fuenteUrl.trim();
  if (url !== '' && errores.fuenteUrl === undefined && !esUrlFuenteValida(url)) {
    errores.fuenteUrl = MENSAJE_URL_FUENTE;
  }
  return errores;
}

function textoONulo(texto: string): string | null {
  const recortado = texto.trim();
  return recortado === '' ? null : recortado;
}

/**
 * Cuerpo de la catalogación: todos los campos, con `null` para los vacíos (la API rechaza
 * `fuente_url: ""`; `null` es el valor «sin dato» del contrato).
 */
export function entradaDesdeFormulario(formulario: FormularioCatalogacion): EntradaCatalogacion {
  const licencia = formulario.licenciaId === '' ? null : Number(formulario.licenciaId);
  return {
    tituloInterno: textoONulo(formulario.tituloInterno),
    textoAlternativo: textoONulo(formulario.textoAlternativo),
    pieDeFoto: textoONulo(formulario.pieDeFoto),
    autorCredito: textoONulo(formulario.autorCredito),
    fuenteUrl: textoONulo(formulario.fuenteUrl),
    licenciaId: licencia !== null && Number.isSafeInteger(licencia) && licencia > 0 ? licencia : null,
  };
}

/** Clave de error del contrato (snake_case, con notación de puntos) → campo del formulario. */
const CAMPO_DE_CLAVE: Readonly<Record<string, CampoCatalogacion>> = {
  titulo_interno: 'tituloInterno',
  texto_alternativo: 'textoAlternativo',
  pie_de_foto: 'pieDeFoto',
  autor_credito: 'autorCredito',
  fuente_url: 'fuenteUrl',
  licencia_id: 'licenciaId',
  licencia: 'licenciaId',
};

export interface ErroresCatalogacion {
  readonly porCampo: Partial<Record<CampoCatalogacion, string>>;
  readonly generales: readonly string[];
}

/**
 * Reparte los errores por campo de un 400/422 (`errors` con notación de puntos, p. ej.
 * `licencia_id` o `datos.fuente_url`) entre los campos del formulario; el resto son generales.
 */
export function erroresCatalogacion(
  campos: Readonly<Record<string, readonly string[]>>,
  mensaje: string,
): ErroresCatalogacion {
  const porCampo: Partial<Record<CampoCatalogacion, string>> = {};
  const generales: string[] = [];
  for (const [clave, mensajes] of Object.entries(campos)) {
    const segmentos = clave.split('.');
    const campo = segmentos
      .map((s) => CAMPO_DE_CLAVE[s])
      .find((c): c is CampoCatalogacion => c !== undefined);
    if (campo !== undefined && mensajes.length > 0) {
      porCampo[campo] ??= mensajes[0];
    } else {
      generales.push(...mensajes);
    }
  }
  if (Object.keys(porCampo).length === 0 && generales.length === 0) generales.push(mensaje);
  return { porCampo, generales };
}

/** Licencias que se pueden asignar: activas, más la actual aunque esté inactiva. */
export function licenciasAsignables(
  catalogo: readonly LicenciaCatalogo[],
  actual: LicenciaMedio | null,
): readonly LicenciaCatalogo[] {
  const activas = catalogo.filter((l) => l.activa || l.id === actual?.id);
  if (actual !== null && !activas.some((l) => l.id === actual.id)) {
    return [...activas, { ...actual, activa: false }];
  }
  return activas;
}

/** AC-117: no se puede retirar un medio en uso por contenido publicado. */
export function puedeRetirar(medio: Medio): boolean {
  return medio.estado !== 'RETIRADO' && !medio.enUsoPublicado;
}

export function puedeReactivar(medio: Medio): boolean {
  return medio.estado === 'RETIRADO';
}

// ------------------------------------------------------------------------------------------------
// Filtros de la biblioteca (SCR-039: ?estado=&licencia=&q=&en_uso=&pagina=)
// ------------------------------------------------------------------------------------------------

export interface FiltrosMedios {
  readonly estado: EstadoMedio | null;
  readonly licencia: string | null;
  readonly enUso: boolean | null;
  readonly q: string;
  readonly pagina: number;
}

export const FILTROS_VACIOS: FiltrosMedios = {
  estado: null,
  licencia: null,
  enUso: null,
  q: '',
  pagina: 1,
};

const ESTADOS: readonly EstadoMedio[] = ['PENDIENTE_METADATOS', 'DISPONIBLE', 'RETIRADO'];
const PATRON_LICENCIA = /^[A-Za-z0-9.-]{1,40}$/;
const PAGINA_MAXIMA = 10_000;
const LONGITUD_Q = 100;

/** Lee los filtros de la URL descartando valores fuera del contrato (nunca provoca un 400). */
export function filtrosDesdeQuery(
  parametros: Readonly<Record<string, string | null | undefined>>,
): FiltrosMedios {
  const estado = parametros['estado'] ?? '';
  const licencia = parametros['licencia'] ?? '';
  const enUso = parametros['en_uso'];
  const q = (parametros['q'] ?? '').split(String.fromCharCode(0)).join('').trim().slice(0, LONGITUD_Q);
  const pagina = Number(parametros['pagina'] ?? '1');
  return {
    estado: (ESTADOS as readonly string[]).includes(estado) ? (estado as EstadoMedio) : null,
    licencia: PATRON_LICENCIA.test(licencia) ? licencia : null,
    enUso: enUso === 'true' ? true : enUso === 'false' ? false : null,
    q,
    pagina: Number.isInteger(pagina) && pagina >= 1 && pagina <= PAGINA_MAXIMA ? pagina : 1,
  };
}

/** Parámetros de URL de unos filtros (los vacíos y la página 1 se omiten: `null` los quita). */
export function queryDesdeFiltros(filtros: FiltrosMedios): Record<string, string | null> {
  return {
    estado: filtros.estado,
    licencia: filtros.licencia,
    en_uso: filtros.enUso === null ? null : String(filtros.enUso),
    q: filtros.q === '' ? null : filtros.q,
    pagina: filtros.pagina > 1 ? String(filtros.pagina) : null,
  };
}

/** Cambiar un filtro vuelve a la página 1. */
export function conFiltro(filtros: FiltrosMedios, cambio: Partial<FiltrosMedios>): FiltrosMedios {
  return { ...filtros, ...cambio, pagina: cambio.pagina ?? 1 };
}

export function hayFiltros(filtros: FiltrosMedios): boolean {
  return filtros.estado !== null || filtros.licencia !== null || filtros.enUso !== null || filtros.q !== '';
}

// ------------------------------------------------------------------------------------------------
// Selector de medios (SCR-041)
// ------------------------------------------------------------------------------------------------

export type ModoSeleccion = 'uno' | 'varios';

export const MENSAJE_NO_SELECCIONABLE = 'Completa sus datos en Medios para usarla';

/** RULE-005: solo los DISPONIBLES pueden ir a contenido que se va a publicar. */
export function esSeleccionable(medio: Pick<Medio, 'estado'>, permitirNoDisponibles: boolean): boolean {
  if (medio.estado === 'DISPONIBLE') return true;
  return permitirNoDisponibles && medio.estado === 'PENDIENTE_METADATOS';
}

/**
 * Alterna un medio en la selección. En modo «uno» la selección es ese medio; en «varios» se añade
 * al final (o se quita) respetando el máximo.
 */
export function alternarSeleccion<T extends { readonly id: number }>(
  seleccion: readonly T[],
  medio: T,
  modo: ModoSeleccion,
  maximo: number | null = null,
): readonly T[] {
  const yaEsta = seleccion.some((m) => m.id === medio.id);
  if (modo === 'uno') return yaEsta ? [] : [medio];
  if (yaEsta) return seleccion.filter((m) => m.id !== medio.id);
  if (maximo !== null && seleccion.length >= maximo) return seleccion;
  return [...seleccion, medio];
}

/** Mueve un elemento de `desde` a `hasta` (índices base 0, acotados). */
export function mover<T>(lista: readonly T[], desde: number, hasta: number): readonly T[] {
  if (desde < 0 || desde >= lista.length) return lista;
  const destino = Math.min(Math.max(hasta, 0), lista.length - 1);
  if (destino === desde) return lista;
  const copia = [...lista];
  const [elemento] = copia.splice(desde, 1);
  copia.splice(destino, 0, elemento);
  return copia;
}

/** Anuncio role=status tras reordenar (HANDOFF SortableList). */
export function anuncioMovimiento(nombre: string, posicion: number, total: number): string {
  return `${nombre} movida a la posición ${posicion} de ${total}.`;
}

/** Texto del botón principal: «Añadir {n} imágenes» / «Elegir portada». */
export function textoAnadir(cantidad: number, modo: ModoSeleccion): string {
  if (modo === 'uno') return 'Elegir imagen';
  if (cantidad === 0) return 'Añadir imágenes';
  return cantidad === 1 ? 'Añadir 1 imagen' : `Añadir ${cantidad} imágenes`;
}

export function textoRecuentoSeleccion(cantidad: number): string {
  if (cantidad === 0) return 'Ninguna imagen seleccionada';
  return cantidad === 1 ? '1 seleccionada' : `${cantidad} seleccionadas`;
}
