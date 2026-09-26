/**
 * Cálculo puro de los elementos de la paginación numerada con elipsis
 * (HANDOFF_UI_UX COMPONENTES.Pagination: «Anterior / 1 … 4 5 6 … 12 / Siguiente»).
 */
export type ElementoPagina =
  | { readonly tipo: 'pagina'; readonly numero: number }
  | { readonly tipo: 'elipsis'; readonly clave: string };

export function normalizarTotal(total: number): number {
  return Number.isFinite(total) && total >= 1 ? Math.floor(total) : 1;
}

export function normalizarPagina(pagina: number, total: number): number {
  const t = normalizarTotal(total);
  if (!Number.isFinite(pagina)) return 1;
  return Math.min(t, Math.max(1, Math.floor(pagina)));
}

/**
 * @param vecinas cuántas páginas se muestran a cada lado de la actual (por defecto 1).
 * Siempre incluye la primera y la última; una elipsis sustituye solo huecos de 2 o más páginas.
 */
export function calcularPaginas(
  actual: number,
  total: number,
  vecinas = 1,
): readonly ElementoPagina[] {
  const t = normalizarTotal(total);
  const a = normalizarPagina(actual, t);
  const visibles = new Set<number>([1, t]);
  for (let n = a - vecinas; n <= a + vecinas; n++) {
    if (n >= 1 && n <= t) visibles.add(n);
  }
  const ordenadas = [...visibles].sort((x, y) => x - y);
  const elementos: ElementoPagina[] = [];
  let anterior = 0;
  for (const n of ordenadas) {
    const hueco = n - anterior - 1;
    if (hueco === 1) {
      elementos.push({ tipo: 'pagina', numero: anterior + 1 });
    } else if (hueco > 1) {
      elementos.push({ tipo: 'elipsis', clave: `e${anterior}` });
    }
    elementos.push({ tipo: 'pagina', numero: n });
    anterior = n;
  }
  return elementos;
}
