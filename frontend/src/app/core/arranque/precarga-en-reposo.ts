/** Subconjunto de `Window` que usa `precargarEnReposo` (sustituible en pruebas). */
export interface EntornoReposo {
  requestIdleCallback?(callback: () => void, opciones?: { timeout: number }): unknown;
  setTimeout(callback: () => void, ms?: number): unknown;
}

/** Plazo máximo de `requestIdleCallback` (si el hilo nunca queda ocioso, se precarga igualmente). */
export const PLAZO_REPOSO_MS = 3000;

/** Espera de respaldo en navegadores sin `requestIdleCallback` (Safari). */
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
 * Ejecuta `precargar` cuando el hilo principal queda ocioso (o tras `PLAZO_REPOSO_MS`), fuera del
 * camino crítico de la carga: el chunk llega antes de que el usuario lo pida sin competir con el LCP
 * ni con la hidratación. Los errores de la precarga se ignoran (el clic volverá a intentarlo).
 */
export function precargarEnReposo(entorno: EntornoReposo, precargar: () => Promise<unknown>): void {
  const ejecutar = () => {
    precargar().catch(() => undefined);
  };
  if (typeof entorno.requestIdleCallback === 'function') {
    entorno.requestIdleCallback(ejecutar, { timeout: PLAZO_REPOSO_MS });
  } else {
    entorno.setTimeout(ejecutar, RESPALDO_SIN_REPOSO_MS);
  }
}
