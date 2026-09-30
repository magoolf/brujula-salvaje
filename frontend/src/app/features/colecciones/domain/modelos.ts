/**
 * DOMAIN: modelos de la feature Colecciones (SCR-013/014, FEAT-017). Sin dependencias de Angular
 * ni RxJS (Skill_Frontend Regla 08). Cada feature mantiene su propia copia de las vistas que
 * necesita (Regla 05: sin imports cruzados entre features).
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

export interface ColeccionTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly numeroElementos: number;
  readonly imagen: ImagenVista | null;
}

export interface PaginaColecciones {
  readonly resultados: readonly ColeccionTarjetaVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}

export interface DestinoTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly pais: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface ItinerarioTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly destino: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly duracionDias: number;
  readonly imagen: ImagenVista | null;
}

/** RULE-024: solo elementos publicados; exactamente uno de `destino`/`itinerario` según `tipo`. */
export type ElementoColeccionVista =
  | { readonly tipo: 'DESTINO'; readonly orden: number; readonly notaEditorial: string | null; readonly destino: DestinoTarjetaVista }
  | { readonly tipo: 'ITINERARIO'; readonly orden: number; readonly notaEditorial: string | null; readonly itinerario: ItinerarioTarjetaVista };

export interface ColeccionDetalle {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly descripcion: string;
  readonly portada: ImagenVista | null;
  readonly elementos: readonly ElementoColeccionVista[];
  readonly autoria: string;
  readonly fechaUltimaRevision: string;
}

export interface TarjetaRelacionadaVista {
  readonly slug: string;
  readonly ruta: string;
  readonly titulo: string;
  readonly resumen: string | null;
  readonly imagen: ImagenVista | null;
}

export interface ContenidoRetirado {
  readonly rutaListadoPadre: string;
  readonly alternativas: readonly TarjetaRelacionadaVista[];
}
