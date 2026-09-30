import { ContenidoRefVista, CreditoMedioVista, ImagenVista } from './modelos';

/** Fecha es-CO (RULE-009) a partir de un ISO 8601. */
export function formatoFechaEsCo(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}

/** GAP-004/ALT-024: marcador visible cuando el Responsable del tratamiento no está definido. */
export const MARCADOR_RESPONSABLE_PENDIENTE = '[RESPONSABLE POR DEFINIR]';

export interface GrupoCreditos {
  readonly contenido: ContenidoRefVista;
  readonly medios: readonly ImagenVista[];
}

/**
 * SCR-021: la API es medio-céntrica (`CreditoMedio.usado_en[]`, un medio puede aparecer en más de un
 * contenido); la vista requiere lo contrario, agrupado por contenido (HANDOFF: «h2 = título del
 * contenido»). Esta función pura invierte el pivote, preservando el orden de primera aparición del
 * contenido.
 */
export function agruparCreditosPorContenido(creditos: readonly CreditoMedioVista[]): readonly GrupoCreditos[] {
  const grupos: GrupoCreditos[] = [];
  const indicePorClave = new Map<string, number>();
  for (const credito of creditos) {
    for (const contenido of credito.usadoEn) {
      const clave = `${contenido.tipo}:${contenido.slug}`;
      let indice = indicePorClave.get(clave);
      if (indice === undefined) {
        indice = grupos.length;
        indicePorClave.set(clave, indice);
        grupos.push({ contenido, medios: [] });
      }
      (grupos[indice].medios as ImagenVista[]).push(credito.imagen);
    }
  }
  return grupos;
}
