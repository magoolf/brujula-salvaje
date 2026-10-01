/**
 * Reglas de presentación del Tablero (SCR-034, FEAT-033/049): etiquetas legibles de tipos y estados
 * (nunca el código del enum, HANDOFF Badge) y detección del estado vacío.
 */
import { ConteoPorTipo, EstadoEditorial, TableroPanel, TipoContenido } from './modelos';

export const ETIQUETA_TIPO: Readonly<Record<TipoContenido, string>> = {
  DESTINO: 'Destinos',
  ITINERARIO: 'Itinerarios',
  GUIA: 'Guías',
  TIPO: 'Tipos de aventura',
  COLECCION: 'Colecciones',
  TERMINO: 'Glosario',
  PAGINA: 'Páginas institucionales',
};

export const ETIQUETA_TIPO_SINGULAR: Readonly<Record<TipoContenido, string>> = {
  DESTINO: 'Destino',
  ITINERARIO: 'Itinerario',
  GUIA: 'Guía',
  TIPO: 'Tipo de aventura',
  COLECCION: 'Colección',
  TERMINO: 'Término del glosario',
  PAGINA: 'Página institucional',
};

export const ETIQUETA_ESTADO: Readonly<Record<EstadoEditorial, string>> = {
  BORRADOR: 'Borrador',
  PUBLICADO: 'Publicado',
  RETIRADO: 'Retirado',
};

export type VarianteEstado = 'borrador' | 'publicado' | 'retirado';

export function varianteEstado(estado: EstadoEditorial): VarianteEstado {
  switch (estado) {
    case 'BORRADOR':
      return 'borrador';
    case 'PUBLICADO':
      return 'publicado';
    case 'RETIRADO':
      return 'retirado';
  }
}

export function totalConteo(conteo: ConteoPorTipo): number {
  return conteo.borrador + conteo.publicado + conteo.retirado;
}

/** ST-EMPTY del Tablero: ningún contenido de ningún tipo ni actividad reciente. */
export function esTableroVacio(tablero: TableroPanel): boolean {
  return tablero.recientes.length === 0 && tablero.conteos.every((c) => totalConteo(c) === 0);
}

/** El widget de salud solo se muestra si hay algo que atender (EXP-001). */
export function hayAvisosDeSalud(tablero: TableroPanel): boolean {
  const salud = tablero.saludEditorial;
  if (salud === null) return false;
  return (
    salud.revisionesAntiguas.length > 0 ||
    salud.mediosPendientesMetadatos > 0 ||
    salud.mediosSinUso > 0 ||
    salud.coleccionesBajoMinimo.length > 0 ||
    salud.contenidosConPocosRelacionados.length > 0
  );
}
