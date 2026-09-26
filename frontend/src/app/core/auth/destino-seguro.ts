/**
 * Validación del parámetro `siguiente` del acceso al panel (SCR-030, AC-115, THREAT de redirección
 * abierta): solo se aceptan rutas relativas internas bajo `/panel`. Función pura.
 */
export const RUTA_ACCESO_PANEL = '/panel/acceso';
export const RUTA_TABLERO_PANEL = '/panel';

// Barra invertida, espacios y caracteres de control (C0 y DEL), por su código.
function tieneCaracterProhibido(valor: string): boolean {
  for (const caracter of valor) {
    const codigo = caracter.codePointAt(0) ?? 0;
    if (caracter === '\\' || /\s/.test(caracter) || codigo <= 0x1f || codigo === 0x7f) return true;
  }
  return false;
}

export function esDestinoSeguro(valor: string | null | undefined): valor is string {
  if (typeof valor !== 'string' || valor.length === 0 || valor.length > 2048) return false;
  if (tieneCaracterProhibido(valor)) return false;
  if (!valor.startsWith('/') || valor.startsWith('//')) return false;
  const ruta = valor.split(/[?#]/)[0];
  if (ruta !== RUTA_TABLERO_PANEL && !ruta.startsWith(`${RUTA_TABLERO_PANEL}/`)) return false;
  if (ruta.split('/').some((s) => s === '..' || s === '.')) return false;
  // Evita volver al propio formulario de acceso en bucle.
  return ruta !== RUTA_ACCESO_PANEL && !ruta.startsWith(`${RUTA_ACCESO_PANEL}/`);
}

/** Devuelve el destino si es seguro o el Tablero como alternativa. */
export function destinoTrasAcceso(valor: string | null | undefined): string {
  return esDestinoSeguro(valor) ? valor : RUTA_TABLERO_PANEL;
}
