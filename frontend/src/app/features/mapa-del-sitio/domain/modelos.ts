/**
 * DOMAIN: modelos de la feature Mapa del sitio (SCR-022, FEAT-025, MUST, RULE-030). Sin
 * dependencias de Angular ni RxJS (Skill_Frontend Regla 08).
 */

export type TipoEntradaIndice =
  | 'DESTINO'
  | 'ITINERARIO'
  | 'TIPO'
  | 'GUIA'
  | 'CATEGORIA_GUIA'
  | 'COLECCION'
  | 'PAGINA';

export interface Agrupacion {
  readonly slug: string;
  readonly nombre: string;
}

/** Una página publicada según el índice público (AP-12). */
export interface EntradaIndiceVista {
  readonly tipo: TipoEntradaIndice;
  readonly slug: string;
  readonly titulo: string;
  /** Región (destinos) o categoría (guías); `null` en el resto. */
  readonly agrupacion: Agrupacion | null;
}

export interface MesVista {
  /** Número de mes (1-12): es el parámetro de la ruta /cuando-ir/:mes del sitio. */
  readonly numero: number;
  readonly slug: string;
  readonly nombre: string;
  readonly numeroDestinos: number;
}

/** Término publicado del glosario y la página del listado paginado en la que aparece. */
export interface TerminoVista {
  readonly slug: string;
  readonly termino: string;
  readonly pagina: number;
}

export interface DatosMapaDelSitio {
  readonly entradas: readonly EntradaIndiceVista[];
  readonly meses: readonly MesVista[];
  readonly terminos: readonly TerminoVista[];
}

/** Enlace interno del mapa (ruta del router, con query y fragmento opcionales). */
export interface EnlaceMapa {
  readonly etiqueta: string;
  readonly ruta: string;
  readonly queryParams?: Readonly<Record<string, string>>;
  readonly fragmento?: string;
}

/** Subgrupo de una sección (h3): región, categoría o, si `titulo` es null, la lista sin subtítulo. */
export interface GrupoMapa {
  readonly id: string;
  readonly titulo: string | null;
  /** Página propia del grupo (p. ej. la categoría de guías), si existe. */
  readonly ruta: string | null;
  readonly enlaces: readonly EnlaceMapa[];
}

/** Sección (h2) del mapa del sitio. */
export interface SeccionMapa {
  readonly id: string;
  readonly titulo: string;
  /** Páginas de la propia sección (listado, mapa…), siempre presentes aunque no haya contenido. */
  readonly enlacesSeccion: readonly EnlaceMapa[];
  readonly grupos: readonly GrupoMapa[];
}
