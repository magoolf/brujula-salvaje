import { CanDeactivateFn } from '@angular/router';

/** Pantalla que decide si se puede salir (p. ej. con cambios sin guardar). */
export interface ConSalidaControlada {
  puedeSalir(destino: string): boolean | Promise<boolean>;
}

/**
 * ALT-026: confirmación al salir del editor con cambios sin guardar. Archivo aparte para que la
 * configuración de rutas no arrastre el editor (que se carga en diferido).
 */
export const cambiosSinGuardarGuard: CanDeactivateFn<ConSalidaControlada> = (
  componente,
  _ruta,
  _estado,
  siguiente,
) => componente.puedeSalir(siguiente.url);
