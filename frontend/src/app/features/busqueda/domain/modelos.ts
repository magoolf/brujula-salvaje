/**
 * DOMAIN: modelos de la feature Búsqueda (SCR-017, FEAT-016). Sin dependencias de Angular ni RxJS
 * (Skill_Frontend Regla 08).
 */

export type GrupoResultado = 'destinos' | 'itinerarios' | 'guias' | 'tipos';

export interface ImagenVista {
  readonly src: string;
  readonly alt: string;
  readonly ancho: number;
  readonly alto: number;
  readonly derivados: readonly { readonly url: string; readonly ancho: number }[];
}

export interface ResultadoBusquedaVista {
  readonly tipo: 'DESTINO' | 'ITINERARIO' | 'GUIA' | 'TIPO';
  readonly slug: string;
  readonly ruta: string;
  readonly titulo: string;
  readonly resumen: string | null;
  readonly pais: string | null;
  readonly imagen: ImagenVista | null;
}

export interface GrupoBusquedaVista {
  readonly resultados: readonly ResultadoBusquedaVista[];
  readonly total: number;
}

export interface BusquedaAgrupadaVista {
  readonly total: number;
  readonly grupos: Readonly<Record<GrupoResultado, GrupoBusquedaVista>>;
}

export interface PaginaResultados {
  readonly resultados: readonly ResultadoBusquedaVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}

export interface FiltrosBusqueda {
  readonly q: string;
  readonly tipo: GrupoResultado | null;
  readonly pagina: number;
}
