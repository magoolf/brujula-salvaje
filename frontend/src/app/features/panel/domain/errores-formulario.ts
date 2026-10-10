/**
 * Traducción de los errores por campo de la API (`ErrorApi.campos`, claves del contrato) a los
 * campos de un formulario del panel (TKT-024). Los mensajes de claves desconocidas (o el mensaje
 * del problema si no hay ninguno por campo) van al resumen de errores. Puro (Regla 08).
 */
export interface ErroresTraducidos<C extends string> {
  readonly porCampo: Partial<Record<C, string>>;
  readonly generales: readonly string[];
}

export function erroresPorCampo<C extends string>(
  mapa: Readonly<Record<C, string>>,
  campos: Readonly<Record<string, readonly string[]>>,
  mensaje: string,
): ErroresTraducidos<C> {
  const inverso = new Map<string, C>();
  for (const [campo, api] of Object.entries(mapa) as [C, string][]) inverso.set(api, campo);
  const porCampo: Partial<Record<C, string>> = {};
  const generales: string[] = [];
  for (const [clave, mensajes] of Object.entries(campos)) {
    const campo = inverso.get(clave);
    if (campo !== undefined && mensajes.length > 0) porCampo[campo] = mensajes[0];
    else generales.push(...mensajes);
  }
  if (Object.keys(porCampo).length === 0 && generales.length === 0) generales.push(mensaje);
  return { porCampo, generales };
}

/** Quita el error de un campo (al editarlo). Devuelve el mismo objeto si no había error. */
export function sinError<C extends string>(
  errores: Partial<Record<C, string>>,
  campo: C,
): Partial<Record<C, string>> {
  if (errores[campo] === undefined) return errores;
  const copia = { ...errores };
  delete copia[campo];
  return copia;
}

/** Longitud en caracteres visibles (puntos de código), como los contadores. */
export function longitudTexto(texto: string): number {
  return [...texto].length;
}
