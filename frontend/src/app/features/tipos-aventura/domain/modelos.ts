/**
 * DOMAIN: modelos de la feature Tipos de aventura (SCR-008/009, FEAT-010/011). Sin dependencias de
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

export interface TipoTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly nivelExigencia: number;
  readonly numeroDestinos: number;
  readonly imagen: ImagenVista | null;
}

export interface PaginaTipos {
  readonly resultados: readonly TipoTarjetaVista[];
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

export interface GuiaTarjetaVista {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly categoria: RefTaxonomiaVista;
  readonly imagen: ImagenVista | null;
}

export interface ChecklistItemVista {
  readonly texto: string;
  readonly esencial: boolean;
  readonly grupo: string | null;
  readonly orden: number;
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

export interface TipoDetalle {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly descripcion: string;
  readonly nivelExigencia: number;
  readonly portada: ImagenVista | null;
  readonly destinos: readonly DestinoTarjetaVista[];
  readonly destinosTotal: number;
  readonly checklist: readonly ChecklistItemVista[];
  readonly guiasRelacionadas: readonly GuiaTarjetaVista[];
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
