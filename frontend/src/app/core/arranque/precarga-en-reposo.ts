/** Subconjunto de `Window` que usa `precargarEnReposo` (sustituible en pruebas). */
export interface EntornoReposo {
  readonly document: { readonly readyState: DocumentReadyState };
  addEventListener(tipo: 'load', callback: () => void, opciones?: { once: boolean }): void;
  requestIdleCallback?(callback: () => void): unknown;
  setTimeout(callback: () => void, ms?: number): unknown;
}

/** Espera de respaldo tras `load` en navegadores sin `requestIdleCallback` (Safari). */
export const RESPALDO_SIN_REPOSO_MS = 1500;

/**
 * Crea un precargador idempotente de un módulo diferido (TKT-056, QA F-02): la primera llamada
 * ejecuta `cargar` (un `import()`) y las siguientes devuelven la misma promesa, así que precargar en
 * reposo, al acercar el puntero/foco y al pulsar comparten una única descarga. Un fallo de red no
 * queda cacheado: el siguiente intento vuelve a pedir el módulo.
 */
export function precargadorDe<T>(cargar: () => Promise<T>): () => Promise<T> {
  let promesa: Promise<T> | null = null;
  return () => {
    promesa ??= cargar().catch((error: unknown) => {
      promesa = null;
      throw error;
    });
    return promesa;
  };
}

/**
 * Ejecuta `precargar` fuera del arranque (TKT-056, QA c2 F-03): espera al evento `load` y después
 * a que el hilo principal quede ocioso, SIN plazo máximo (`requestIdleCallback` sin `timeout`), para
 * que la descarga y evaluación del módulo no compitan con el LCP, la hidratación ni la ventana
 * FCP→TTI. Si el hilo nunca queda ocioso no se precarga: la interacción (pointerdown/focus/clic)
 * sigue cargándolo bajo demanda. Los errores de la precarga se ignoran (el clic volverá a intentarlo).
 */
export function precargarEnReposo(entorno: EntornoReposo, precargar: () => Promise<unknown>): void {
  const ejecutar = () => {
    precargar().catch(() => undefined);
  };
  const enReposo = () => {
    if (typeof entorno.requestIdleCallback === 'function') {
      entorno.requestIdleCallback(ejecutar);
    } else {
      entorno.setTimeout(ejecutar, RESPALDO_SIN_REPOSO_MS);
    }
  };
  if (entorno.document.readyState === 'complete') {
    enReposo();
  } else {
    entorno.addEventListener('load', enReposo, { once: true });
  }
}
