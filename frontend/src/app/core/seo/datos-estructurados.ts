/**
 * Constructores puros de datos estructurados schema.org (FEAT-027). Sin dependencias de Angular.
 */
export type JsonLd = Readonly<Record<string, unknown>>;

export interface MigaSeo {
  readonly etiqueta: string;
  /** Ruta interna absoluta desde la raíz (p. ej. `/destinos`). */
  readonly ruta: string;
}

export function urlAbsoluta(origen: string, ruta: string): string {
  const limpia = ruta.split(/[?#]/)[0];
  return origen.replace(/\/+$/, '') + (limpia.startsWith('/') ? limpia : `/${limpia}`);
}

export function migasDePanJsonLd(origen: string, migas: readonly MigaSeo[]): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: migas.map((miga, indice) => ({
      '@type': 'ListItem',
      position: indice + 1,
      name: miga.etiqueta,
      item: urlAbsoluta(origen, miga.ruta),
    })),
  };
}

export function sitioWebJsonLd(origen: string, nombre: string, idioma: string): JsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: nombre,
    url: urlAbsoluta(origen, '/'),
    inLanguage: idioma,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${urlAbsoluta(origen, '/buscar')}?q={consulta}`,
      'query-input': 'required name=consulta',
    },
  };
}

/**
 * Serializa JSON-LD para un `<script type="application/ld+json">` sin permitir cerrar la etiqueta
 * ni inyectar HTML (`<`, `>`, `&` y separadores de línea se escapan como secuencias Unicode).
 */
export function serializarJsonLd(datos: JsonLd | readonly JsonLd[]): string {
  return JSON.stringify(datos)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}
