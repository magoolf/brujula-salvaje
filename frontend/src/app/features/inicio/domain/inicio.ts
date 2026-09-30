import { Inicio } from './modelos';

/**
 * Estado vacío del entorno (VIEW_SPEC SCR-001.empty): ni bloque principal ni ninguna sección con
 * contenido. RULE-016 garantiza mínimos cuando SÍ hay contenido publicado, así que esto solo ocurre
 * en un entorno recién desplegado sin datos.
 */
export function esInicioVacio(inicio: Inicio): boolean {
  return (
    inicio.hero === null &&
    inicio.destinos.length === 0 &&
    inicio.itinerarios.length === 0 &&
    inicio.guias.length === 0 &&
    inicio.tipos.length === 0
  );
}

export interface AccesoMosaico {
  readonly id: string;
  readonly etiqueta: string;
  readonly descripcion: string;
  readonly ruta: string;
}

/**
 * «Otras formas de explorar» (RULE-030): solo los accesos ya implementados. Colecciones* queda
 * fuera hasta TKT-009 (MOD-005).
 */
export const ACCESOS_MOSAICO: readonly AccesoMosaico[] = [
  { id: 'mapa', etiqueta: 'Mapa', descripcion: 'Explora destinos sobre un mapa del mundo.', ruta: '/destinos/mapa' },
  {
    id: 'cuando-ir',
    etiqueta: 'Cuándo ir',
    descripcion: 'Encuentra destinos según el mes del viaje.',
    ruta: '/cuando-ir',
  },
];
