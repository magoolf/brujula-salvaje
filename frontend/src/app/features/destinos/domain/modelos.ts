/**
 * Dominio puro de Exploración de destinos (MOD-002) y Ficha de destino (MOD-003, solo Destino).
 * Sin dependencias de Angular ni RxJS (Skill_Frontend Regla 08). Los DTO del cliente OpenAPI
 * mueren en `data/` (Regla 04): estos tipos son los únicos que STATE y UI conocen.
 */

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

export interface RefTaxonomiaVista {
  readonly slug: string;
  readonly nombre: string;
}

export interface TarjetaDestino {
  readonly slug: string;
  readonly titulo: string;
  readonly pais: RefTaxonomiaVista;
  readonly region: RefTaxonomiaVista;
  readonly tipos: readonly RefTaxonomiaVista[];
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface PaginaDestinos {
  readonly resultados: readonly TarjetaDestino[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}

export type TramoDuracionCodigo = '1-3' | '4-7' | '8-14' | '15+';

export interface OpcionEscala {
  readonly nivel: number;
  readonly etiqueta: string;
  readonly descripcion: string;
}

export interface OpcionRegionFaceta {
  readonly slug: string;
  readonly nombre: string;
  readonly continente: string;
  readonly paises: readonly RefTaxonomiaVista[];
}

export interface OpcionTramoDuracion {
  readonly codigo: TramoDuracionCodigo;
  readonly etiqueta: string;
  readonly minDias: number;
  readonly maxDias: number | null;
}

export interface FacetasDestinos {
  readonly tipos: readonly RefTaxonomiaVista[];
  readonly regiones: readonly OpcionRegionFaceta[];
  readonly dificultad: readonly OpcionEscala[];
  readonly presupuesto: readonly OpcionEscala[];
  readonly tramosDuracion: readonly OpcionTramoDuracion[];
}

export type OrdenDestinos = 'nombre' | 'dificultad_asc' | 'dificultad_desc';

export interface FiltrosDestinos {
  readonly tipo: readonly string[];
  readonly region: string | null;
  readonly pais: string | null;
  readonly dificultadMin: number | null;
  readonly dificultadMax: number | null;
  readonly mes: number | null;
  readonly duracion: readonly TramoDuracionCodigo[];
  readonly presupuesto: readonly number[];
  readonly orden: OrdenDestinos;
  readonly pagina: number;
}

export interface PuntoMapa {
  readonly slug: string;
  readonly titulo: string;
  readonly pais: string;
  readonly region: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly latitud: number;
  readonly longitud: number;
}

export interface PaginaMapa {
  readonly resultados: readonly PuntoMapa[];
  readonly pagina: number;
  readonly totalPaginas: number;
}

export interface FuenteVista {
  readonly titulo: string;
  readonly url: string | null;
  readonly entidadEditora: string | null;
}

export interface TarjetaRelacionada {
  readonly tipo: 'DESTINO' | 'ITINERARIO' | 'GUIA' | 'TIPO' | 'COLECCION';
  readonly slug: string;
  readonly ruta: string;
  readonly titulo: string;
  readonly resumen: string | null;
  readonly imagen: ImagenVista | null;
}

export interface ItinerarioTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly duracionDias: number;
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface GuiaTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly categoria: RefTaxonomiaVista;
  readonly imagen: ImagenVista | null;
}

export interface DestinoDetalle {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly pais: RefTaxonomiaVista;
  readonly region: RefTaxonomiaVista;
  readonly portada: ImagenVista | null;
  readonly galeria: readonly ImagenVista[];
  readonly dificultad: number;
  readonly nivelPresupuesto: number;
  readonly mesesMejorEpoca: readonly number[];
  readonly duracionMinDias: number;
  readonly duracionMaxDias: number;
  readonly clima: string;
  readonly altitudMaxM: number | null;
  readonly descripcionExperta: string;
  readonly comoLlegar: string;
  readonly seguridadRiesgos: string;
  readonly sostenibilidad: string;
  readonly latitud: number;
  readonly longitud: number;
  readonly tipoPrincipal: RefTaxonomiaVista;
  readonly tipos: readonly RefTaxonomiaVista[];
  readonly itinerarios: readonly ItinerarioTarjetaVista[];
  readonly itinerariosAfines: readonly ItinerarioTarjetaVista[];
  readonly guiasRelacionadas: readonly GuiaTarjetaVista[];
  readonly relacionados: readonly TarjetaRelacionada[];
  readonly fuentes: readonly FuenteVista[];
  readonly autoria: string;
  readonly fechaUltimaRevision: string;
}

export interface DestinoRetirado {
  readonly rutaListadoPadre: string;
  readonly alternativas: readonly TarjetaRelacionada[];
}

export interface MesResumen {
  readonly mes: number;
  readonly nombre: string;
  readonly slug: string;
  readonly numeroDestinos: number;
  readonly destacado: TarjetaDestino | null;
}
