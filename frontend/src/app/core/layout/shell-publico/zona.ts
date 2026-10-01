/**
 * Zona de la aplicación (TKT-010): el panel editorial (/panel/**) tiene su propio armazón; todo lo
 * demás va dentro de ShellPublico. Funciones puras.
 *
 * La fuente de verdad es la configuración de rutas: la ruta `panel` de app.routes.ts declara
 * `data: DATOS_ZONA_PANEL`, y una ruta activada pertenece al panel si ella o alguno de sus
 * ancestros lo declara (QA TKT-010 ciclo 2, HALLAZGO-ZONA). La URL solo decide la zona del primer
 * render, antes de que el router reconozca la ruta (también en SSR e hidratación).
 */
export type Zona = 'publico' | 'panel';

export const PREFIJO_PANEL = '/panel';
const CLAVE_ZONA = 'zona';

/** `data` de la ruta raíz del panel en app.routes.ts. */
export const DATOS_ZONA_PANEL: Readonly<Record<string, unknown>> = { [CLAVE_ZONA]: 'panel' };

/** Lo mínimo de ActivatedRouteSnapshot que hace falta para decidir la zona. */
export interface NodoRutaZona {
  readonly routeConfig: { readonly data?: Readonly<Record<string, unknown>> } | null;
  readonly parent: NodoRutaZona | null;
  readonly firstChild: NodoRutaZona | null;
}

export function esZonaPanel(url: string): boolean {
  const ruta = url.split(/[?#]/)[0];
  return ruta === PREFIJO_PANEL || ruta.startsWith(`${PREFIJO_PANEL}/`);
}

/** Zona del primer render, a partir de la URL de la petición. */
export function zonaDeUrl(url: string): Zona {
  return esZonaPanel(url) ? 'panel' : 'publico';
}

/** Zona de una ruta activada: la que declara su configuración o la de un ancestro. */
export function zonaDeRuta(nodo: NodoRutaZona): Zona {
  for (let actual: NodoRutaZona | null = nodo; actual !== null; actual = actual.parent) {
    if (actual.routeConfig?.data?.[CLAVE_ZONA] === 'panel') return 'panel';
  }
  return 'publico';
}

/** Zona del estado de destino de una navegación (la de su ruta primaria más profunda). */
export function zonaDeEstado(raiz: NodoRutaZona): Zona {
  let hoja = raiz;
  while (hoja.firstChild !== null) hoja = hoja.firstChild;
  return zonaDeRuta(hoja);
}
