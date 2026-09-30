/**
 * DOMAIN: modelos de la feature Itinerarios (SCR-006/007, FEAT-008/009). Sin dependencias de
 * Angular ni RxJS (Skill_Frontend Regla 08). Cada feature mantiene su propia copia de las vistas
 * que necesita (Regla 05: sin imports cruzados entre features).
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

export interface ItinerarioTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly destino: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly duracionDias: number;
  readonly imagen: ImagenVista | null;
}

export interface PaginaItinerarios {
  readonly resultados: readonly ItinerarioTarjetaVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}

export type OrdenItinerarios = 'titulo' | 'duracion_asc' | 'duracion_desc';

export interface FiltrosItinerarios {
  readonly orden: OrdenItinerarios;
  readonly pagina: number;
}

export interface DiaItinerarioVista {
  readonly numeroDia: number;
  readonly titulo: string;
  readonly actividades: string;
  readonly distanciaKm: number | null;
  readonly desnivelPositivoM: number | null;
  readonly desnivelNegativoM: number | null;
  readonly alojamientoOrientativo: string | null;
  readonly consejos: string | null;
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

export interface DestinoRefVista {
  readonly slug: string;
  readonly titulo: string;
  readonly pais: RefTaxonomiaVista;
  readonly region: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface ItinerarioDetalle {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly destino: DestinoRefVista;
  readonly dificultad: number;
  readonly duracionDias: number;
  readonly distanciaTotalKm: number | null;
  readonly desnivelAcumuladoM: number | null;
  readonly dias: readonly DiaItinerarioVista[];
  readonly riesgosSeguridad: string;
  readonly portada: ImagenVista | null;
  readonly galeria: readonly ImagenVista[];
  readonly tipos: readonly RefTaxonomiaVista[];
  readonly terminos: readonly TerminoRefVista[];
  readonly fuentes: readonly FuenteVista[];
  readonly relacionados: readonly TarjetaRelacionadaVista[];
  readonly autoria: string;
  readonly fechaUltimaRevision: string;
}

/** Alternativas de un 410 (mismo contrato que en el resto de fichas públicas). */
export interface ContenidoRetirado {
  readonly rutaListadoPadre: string;
  readonly alternativas: readonly TarjetaRelacionadaVista[];
}
