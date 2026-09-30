/**
 * DOMAIN: modelos de la feature Guías (SCR-010/011/012, FEAT-012). Sin dependencias de Angular ni
 * RxJS (Skill_Frontend Regla 08). Cada feature mantiene su propia copia de las vistas que necesita
 * (Regla 05: sin imports cruzados entre features).
 */

export interface RefTaxonomiaVista {
  readonly slug: string;
  readonly nombre: string;
}

export interface ImagenVista {
  readonly src: string;
  readonly alt: string;
  readonly ancho: number;
  readonly alto: number;
  readonly derivados: readonly { readonly url: string; readonly ancho: number }[];
  readonly autorCredito: string;
  readonly pieDeFoto: string | null;
  readonly licenciaNombre: string;
  readonly licenciaUrl: string | null;
}

export interface GuiaTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly categoria: RefTaxonomiaVista;
  readonly fechaUltimaRevision: string;
  readonly minutosLectura: number | null;
  readonly imagen: ImagenVista | null;
}

export interface CategoriaGuiaIndiceVista {
  readonly slug: string;
  readonly nombre: string;
  readonly descripcion: string;
  readonly numeroGuias: number;
  readonly guiasRecientes: readonly GuiaTarjetaVista[];
}

export interface PaginaCategorias {
  readonly resultados: readonly CategoriaGuiaIndiceVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}

export interface PaginaGuias {
  readonly resultados: readonly GuiaTarjetaVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}

export interface DestinoTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly pais: RefTaxonomiaVista;
  readonly region: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface FuenteVista {
  readonly titulo: string;
  readonly url: string | null;
  readonly entidadEditora: string | null;
}

export interface TerminoRefVista {
  readonly slug: string;
  readonly termino: string;
}

export type TipoContenidoPublicoVista = 'DESTINO' | 'ITINERARIO' | 'GUIA' | 'TIPO' | 'COLECCION';

export interface TarjetaRelacionadaVista {
  readonly tipo: TipoContenidoPublicoVista;
  readonly slug: string;
  readonly ruta: string;
  readonly titulo: string;
  readonly resumen: string | null;
  readonly imagen: ImagenVista | null;
}

export interface GuiaDetalle {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly categoria: RefTaxonomiaVista;
  readonly cuerpo: string;
  readonly minutosLectura: number | null;
  readonly portada: ImagenVista | null;
  readonly destinosRelacionados: readonly DestinoTarjetaVista[];
  readonly tiposRelacionados: readonly RefTaxonomiaVista[];
  readonly remiteAMetodologia: boolean;
  readonly terminos: readonly TerminoRefVista[];
  readonly fuentes: readonly FuenteVista[];
  readonly relacionados: readonly TarjetaRelacionadaVista[];
  readonly autoria: string;
  readonly fechaUltimaRevision: string;
}

export interface ContenidoRetirado {
  readonly rutaListadoPadre: string;
  readonly alternativas: readonly TarjetaRelacionadaVista[];
}
