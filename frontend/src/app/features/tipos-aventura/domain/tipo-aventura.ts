import { ChecklistItemVista } from './modelos';

export interface GrupoChecklist {
  readonly nombre: string | null;
  readonly items: readonly ChecklistItemVista[];
}

/**
 * FEAT-011: agrupa el checklist por `grupo` (preservando el orden de aparición de cada grupo) y
 * ordena sus elementos por `orden`. Los elementos sin grupo quedan en un grupo `null` (se muestran
 * sin encabezado de grupo).
 */
export function agruparChecklist(items: readonly ChecklistItemVista[]): readonly GrupoChecklist[] {
  const ordenados = [...items].sort((a, b) => a.orden - b.orden);
  const grupos: GrupoChecklist[] = [];
  const indicePorNombre = new Map<string | null, number>();
  for (const item of ordenados) {
    const clave = item.grupo;
    let indice = indicePorNombre.get(clave);
    if (indice === undefined) {
      indice = grupos.length;
      indicePorNombre.set(clave, indice);
      grupos.push({ nombre: clave, items: [] });
    }
    (grupos[indice].items as ChecklistItemVista[]).push(item);
  }
  return grupos;
}

/** FEAT-011: la sección de checklist se oculta si el tipo no tiene elementos. */
export function tieneChecklist(items: readonly ChecklistItemVista[]): boolean {
  return items.length > 0;
}

/** Fecha es-CO (RULE-009) a partir de un ISO 8601. */
export function formatoFechaEsCo(iso: string): string {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' });
}
