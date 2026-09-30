/**
 * DOMAIN: modelos de la feature Institucional (SCR-020/021, FEAT-023/024). Sin dependencias de
 * Angular ni RxJS (Skill_Frontend Regla 08).
 */

export type SlugInstitucional =
  | 'acerca-de'
  | 'politica-de-tratamiento-de-datos'
  | 'politica-de-cookies'
  | 'aviso-legal';

export interface PaginaInstitucionalVista {
  readonly slug: SlugInstitucional;
  readonly titulo: string;
  readonly cuerpo: string;
  readonly versionDocumento: string;
  readonly vigenteDesde: string;
  readonly autoria: string;
  readonly fechaUltimaRevision: string;
}

export interface NivelEscalaVista {
  readonly escala: 'DIFICULTAD' | 'PRESUPUESTO';
  readonly nivel: number;
  readonly etiqueta: string;
  readonly descripcion: string;
}

export interface EscalasVista {
  readonly dificultad: readonly NivelEscalaVista[];
  readonly presupuesto: readonly NivelEscalaVista[];
}

export interface ResponsableVista {
  readonly definido: boolean;
  readonly nombre: string | null;
  readonly identificacion: string | null;
  readonly domicilio: string | null;
  readonly canalAtencion: string | null;
}

export interface ConfiguracionVista {
  readonly nombreMarca: string;
  readonly lema: string | null;
  readonly textoDescargo: string;
  readonly responsable: ResponsableVista;
}

export type TipoContenidoPublicoVista = 'DESTINO' | 'ITINERARIO' | 'GUIA' | 'TIPO' | 'COLECCION';

export interface ContenidoRefVista {
  readonly tipo: TipoContenidoPublicoVista;
  readonly slug: string;
  readonly titulo: string;
  readonly ruta: string;
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
  readonly fuenteUrl: string | null;
}

export interface CreditoMedioVista {
  readonly imagen: ImagenVista;
  readonly usadoEn: readonly ContenidoRefVista[];
}

export interface PaginaCreditos {
  readonly resultados: readonly CreditoMedioVista[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
  readonly tamanoPagina: number;
}
