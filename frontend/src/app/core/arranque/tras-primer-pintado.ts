/** Subconjunto del navegador que usa `trasPrimerPintado` (sustituible en pruebas). */
export interface EntornoPintado {
  readonly document: { readonly visibilityState: DocumentVisibilityState };
  readonly performance: { getEntriesByName(nombre: string): readonly unknown[] };
  readonly PerformanceObserver?: new (callback: () => void) => {
    observe(opciones: { type: string; buffered?: boolean }): void;
    disconnect(): void;
  };
  setTimeout(callback: () => void, ms?: number): unknown;
}

/** Nombre de la entrada de Paint Timing del primer pintado con contenido. */
export const ENTRADA_FCP = 'first-contentful-paint';

/**
 * Espera máxima: si el navegador no informa del pintado (pestaña oculta, sin Paint Timing o un
 * documento que no pinta), la hidratación no queda retenida más de este tiempo.
 */
export const ESPERA_MAXIMA_PINTADO_MS = 1000;

/**
 * TKT-056: resuelve cuando el documento ya tuvo su primer pintado con contenido (FCP), en la tarea
 * siguiente; o como mucho a los `esperaMaximaMs`.
 *
 * Por qué: si el JavaScript está disponible al terminar de analizar el HTML (visitante recurrente
 * con caché, red rápida), los módulos se ejecutan antes del primer fotograma y la hidratación ocupaba
 * el hilo principal antes de que se pintara el HTML del SSR, que ya es el contenido completo: FCP y
 * LCP esperaban a la hidratación y a los módulos de la ruta que esta pide. Esperar al FCP deja pintar
 * primero y hidratar justo después. En una red lenta el FCP ocurre antes de que llegue el JavaScript
 * y la espera es nula. El SSR funciona sin JavaScript (enlaces y búsqueda), así que no se pierde
 * funcionalidad durante esa espera.
 */
export function trasPrimerPintado(
  entorno: EntornoPintado,
  esperaMaximaMs = ESPERA_MAXIMA_PINTADO_MS,
): Promise<void> {
  return new Promise((resolver) => {
    let resuelta = false;
    let observador: { disconnect(): void } | null = null;
    const terminar = () => {
      if (resuelta) return;
      resuelta = true;
      observador?.disconnect();
      resolver();
    };
    const Observador = entorno.PerformanceObserver;
    if (
      entorno.document.visibilityState === 'hidden' ||
      Observador === undefined ||
      entorno.performance.getEntriesByName(ENTRADA_FCP).length > 0
    ) {
      entorno.setTimeout(terminar, 0);
      return;
    }
    try {
      const o = new Observador(() => {
        if (entorno.performance.getEntriesByName(ENTRADA_FCP).length > 0) {
          entorno.setTimeout(terminar, 0);
        }
      });
      o.observe({ type: 'paint', buffered: true });
      observador = o;
    } catch {
      entorno.setTimeout(terminar, 0);
      return;
    }
    entorno.setTimeout(terminar, esperaMaximaMs);
  });
}
