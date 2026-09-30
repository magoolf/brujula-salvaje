/**
 * DOMAIN: modelos de la feature Glosario (SCR-018, FEAT-019, COULD). Sin dependencias de Angular ni
 * RxJS (Skill_Frontend Regla 08).
 */

export type TipoContenidoPublicoVista = 'DESTINO' | 'ITINERARIO' | 'GUIA' | 'TIPO' | 'COLECCION';

export interface ContenidoRefVista {
  readonly tipo: TipoContenidoPublicoVista;
  readonly slug: string;
  readonly titulo: string;
  readonly ruta: string;
}

export interface TerminoGlosarioVista {
  readonly slug: string;
  readonly termino: string;
  readonly definicion: string;
  readonly usadoEn: readonly ContenidoRefVista[];
}

export interface PaginaGlosario {
  readonly resultados: readonly TerminoGlosarioVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}
