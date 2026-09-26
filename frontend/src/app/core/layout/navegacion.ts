/**
 * Navegación global del sitio público (GI-01 y GI-02, BLUEPRINT §10 y §17).
 * RULE-030: solo se enlazan funcionalidades MUST (sus rutas definitivas del sitemap, DEC-AUTO-046);
 * Colecciones*, Cuándo ir*, Guardados* y Glosario* (SHOULD/COULD) se añadirán cuando sus features
 * estén implementadas.
 */
export interface EnlaceNavegacion {
  readonly etiqueta: string;
  readonly ruta: string;
  /** Identificador estable para pruebas (data-testid). */
  readonly id: string;
}

export const NAVEGACION_PRINCIPAL: readonly EnlaceNavegacion[] = [
  { etiqueta: 'Destinos', ruta: '/destinos', id: 'destinos' },
  { etiqueta: 'Tipos de aventura', ruta: '/tipos-de-aventura', id: 'tipos-de-aventura' },
  { etiqueta: 'Itinerarios', ruta: '/itinerarios', id: 'itinerarios' },
  { etiqueta: 'Guías', ruta: '/guias', id: 'guias' },
];

export const NAVEGACION_INSTITUCIONAL: readonly EnlaceNavegacion[] = [
  { etiqueta: 'Acerca de y metodología', ruta: '/acerca-de', id: 'acerca-de' },
  { etiqueta: 'Política de tratamiento de datos', ruta: '/politica-de-tratamiento-de-datos', id: 'tratamiento-de-datos' },
  { etiqueta: 'Política de cookies', ruta: '/politica-de-cookies', id: 'cookies' },
  { etiqueta: 'Aviso legal', ruta: '/aviso-legal', id: 'aviso-legal' },
  { etiqueta: 'Créditos de imágenes', ruta: '/creditos', id: 'creditos' },
  { etiqueta: 'Mapa del sitio', ruta: '/mapa-del-sitio', id: 'mapa-del-sitio' },
];

/** Identificador del contenido principal (destino del SkipLink). */
export const ID_CONTENIDO_PRINCIPAL = 'contenido-principal';
