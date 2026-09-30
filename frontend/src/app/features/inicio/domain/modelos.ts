/**
 * Dominio puro de Inicio (MOD-001, SCR-001). Sin dependencias de Angular ni RxJS (Regla 08).
 */

export interface ImagenVista {
  readonly src: string;
  readonly alt: string;
  readonly ancho: number;
  readonly alto: number;
  readonly derivados: readonly { readonly url: string; readonly ancho: number }[];
}

export interface RefTaxonomiaVista {
  readonly slug: string;
  readonly nombre: string;
}

export interface HeroInicio {
  readonly titular: string;
  readonly subtitulo: string;
  readonly imagen: ImagenVista | null;
}

export interface DestinoTarjetaInicio {
  readonly slug: string;
  readonly titulo: string;
  readonly pais: RefTaxonomiaVista;
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface ItinerarioTarjetaInicio {
  readonly slug: string;
  readonly titulo: string;
  readonly duracionDias: number;
  readonly dificultad: number;
  readonly imagen: ImagenVista | null;
}

export interface GuiaTarjetaInicio {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly imagen: ImagenVista | null;
}

export interface TipoTarjetaInicio {
  readonly slug: string;
  readonly titulo: string;
  readonly resumen: string;
  readonly nivelExigencia: number;
  readonly numeroDestinos: number;
  readonly imagen: ImagenVista | null;
}

export interface Inicio {
  readonly hero: HeroInicio | null;
  readonly destinos: readonly DestinoTarjetaInicio[];
  readonly itinerarios: readonly ItinerarioTarjetaInicio[];
  readonly guias: readonly GuiaTarjetaInicio[];
  readonly tipos: readonly TipoTarjetaInicio[];
}
