/**
 * Zona de la aplicación según la URL (TKT-010): el panel editorial (/panel/**) tiene su propio
 * armazón; todo lo demás va dentro de ShellPublico. Función pura.
 */
export const PREFIJO_PANEL = '/panel';

export function esZonaPanel(url: string): boolean {
  const ruta = url.split(/[?#]/)[0];
  return ruta === PREFIJO_PANEL || ruta.startsWith(`${PREFIJO_PANEL}/`);
}
