/**
 * Vista previa (SCR-037, FEAT-035, TPL-PANEL-FULL): modelo de presentación de la plantilla pública
 * construido con los datos que devuelve el servidor sin persistir nada (forma `*Detalle` del tipo).
 * El panel no importa las páginas públicas (Regla 05: sin imports entre features): las reproduce con
 * este modelo común. Puro (Regla 08).
 */
import { RequisitosPublicacion } from './ciclo-editorial';
import { TipoContenido } from './modelos';

export const MARCA_VISTA_PREVIA = 'VISTA PREVIA – NO PUBLICADO';

export interface DerivadoVistaPrevia {
  readonly url: string;
  readonly ancho: number;
  readonly formato: 'AVIF' | 'WEBP' | 'JPEG';
}

export interface ImagenVistaPrevia {
  readonly src: string;
  readonly alt: string;
  readonly ancho: number;
  readonly alto: number;
  readonly derivados: readonly DerivadoVistaPrevia[];
  readonly credito: string | null;
  readonly pie: string | null;
}

export interface DatoClave {
  readonly etiqueta: string;
  readonly valor: string;
}

/** Bloque de texto enriquecido (HTML de lista blanca saneado por el servidor, RULE-022). */
export interface BloqueTexto {
  readonly titulo: string;
  readonly html: string;
}

export interface ElementoLista {
  readonly titulo: string;
  readonly detalle: string | null;
  /** HTML de lista blanca (actividades de un día). */
  readonly html: string | null;
  readonly destacado: boolean;
}

export interface ListaVistaPrevia {
  readonly titulo: string;
  readonly elementos: readonly ElementoLista[];
  /** Lista numerada (días de un itinerario, elementos de una colección). */
  readonly ordenada: boolean;
}

export interface FuenteVistaPrevia {
  readonly titulo: string;
  readonly url: string | null;
  readonly entidad: string | null;
}

/** Enlace a la versión pública de otro contenido (SCR-037: «llevan a sus versiones públicas»). */
export interface EnlacePublico {
  readonly titulo: string;
  readonly ruta: string;
}

export interface VistaPreviaContenido {
  readonly tipo: TipoContenido;
  readonly marca: string;
  readonly titulo: string;
  /** Línea sobre el título (país, categoría, destino del itinerario…). */
  readonly antetitulo: string | null;
  readonly resumen: string | null;
  readonly portada: ImagenVistaPrevia | null;
  readonly datos: readonly DatoClave[];
  readonly bloques: readonly BloqueTexto[];
  readonly listas: readonly ListaVistaPrevia[];
  readonly galeria: readonly ImagenVistaPrevia[];
  readonly fuentes: readonly FuenteVistaPrevia[];
  readonly enlaces: readonly EnlacePublico[];
  /** Fecha de revisión ya formateada o null. */
  readonly revision: string | null;
  readonly requisitos: RequisitosPublicacion;
}

/** Prefijo público por tipo de contenido referenciado (rutas del BLUEPRINT §10). */
const PREFIJO_PUBLICO: Readonly<Record<string, string>> = {
  DESTINO: '/destinos/',
  ITINERARIO: '/itinerarios/',
  GUIA: '/guias/',
  TIPO: '/tipos-de-aventura/',
  COLECCION: '/colecciones/',
};

/** Ruta pública de un contenido referenciado; null si el tipo o el slug no son válidos. */
export function rutaPublica(tipo: string, slug: string | null | undefined): string | null {
  const prefijo = PREFIJO_PUBLICO[tipo];
  if (prefijo === undefined || !slug || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(slug)) return null;
  return `${prefijo}${slug}`;
}

/** Escala 1..max como texto legible: «3 de 5». */
export function textoEscala(valor: number | null, max: number): string | null {
  if (valor === null || !Number.isInteger(valor) || valor < 1 || valor > max) return null;
  return `${valor} de ${max}`;
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
];

export function textoMeses(meses: readonly number[]): string | null {
  const nombres = meses.filter((m) => m >= 1 && m <= 12).map((m) => NOMBRES_MES[m - 1]);
  return nombres.length === 0 ? null : nombres.join(', ');
}

/** «3 a 5 días» / «4 días». */
export function textoDuracion(min: number | null, max: number | null): string | null {
  if (min === null && max === null) return null;
  if (min !== null && max !== null && min !== max) return `${min} a ${max} días`;
  const dias = (min ?? max) as number;
  return dias === 1 ? '1 día' : `${dias} días`;
}

/** Título del documento: «Vista previa (no publicado) — {título}». */
export function tituloDocumentoVistaPrevia(titulo: string): string {
  return `Vista previa (no publicado) — ${titulo.trim() || 'sin título'}`;
}
