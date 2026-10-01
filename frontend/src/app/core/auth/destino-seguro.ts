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

/**
 * Punto, barra y barra invertida codificados (%2e, %2f, %5c, en cualquier capitalización): en una
 * ruta interna legítima del panel nunca hacen falta y permitirían saltar fuera de /panel tras la
 * decodificación del router o del servidor (QA TKT-010 FALLO-03: /panel/%2e%2e/destinos).
 */
const SEPARADOR_CODIFICADO = /%(2e|2f|5c)/i;

function decodificar(ruta: string): string | null {
  try {
    return decodeURIComponent(ruta);
  } catch {
    return null; // secuencia % mal formada
  }
}

function esRutaPanelValida(ruta: string): boolean {
  if (tieneCaracterProhibido(ruta) || ruta.startsWith('//')) return false;
  if (ruta !== RUTA_TABLERO_PANEL && !ruta.startsWith(`${RUTA_TABLERO_PANEL}/`)) return false;
  return !ruta.split('/').some((s) => s === '..' || s === '.');
}

export function esDestinoSeguro(valor: string | null | undefined): valor is string {
  if (typeof valor !== 'string' || valor.length === 0 || valor.length > 2048) return false;
  if (tieneCaracterProhibido(valor)) return false;
  if (!valor.startsWith('/') || valor.startsWith('//')) return false;
  const ruta = valor.split(/[?#]/)[0];
  if (SEPARADOR_CODIFICADO.test(ruta)) return false;
  // Se valida la ruta tal cual y también decodificada (lo que verá el router).
  const decodificada = decodificar(ruta);
  if (
    decodificada === null ||
    SEPARADOR_CODIFICADO.test(decodificada) || // doble codificación (%252e)
    !esRutaPanelValida(ruta) ||
    !esRutaPanelValida(decodificada)
  ) {
    return false;
  }
  // Evita volver al propio formulario de acceso en bucle.
  return !(
    decodificada === RUTA_ACCESO_PANEL || decodificada.startsWith(`${RUTA_ACCESO_PANEL}/`)
  );
}

/** Devuelve el destino si es seguro o el Tablero como alternativa. */
export function destinoTrasAcceso(valor: string | null | undefined): string {
  return esDestinoSeguro(valor) ? valor : RUTA_TABLERO_PANEL;
}
