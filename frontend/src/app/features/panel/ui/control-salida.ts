import { DOCUMENT } from '@angular/common';
import { DestroyRef, inject, signal } from '@angular/core';

/**
 * Confirmación al salir con cambios sin guardar (HANDOFF UnsavedChangesDialog, ALT-026) para los
 * formularios de configuración del panel (SCR-042, SCR-047; TKT-024). Se crea en el contexto de
 * inyección del componente: registra el aviso nativo del navegador al cerrar la pestaña y expone el
 * estado del diálogo de la navegación interna (canDeactivate → `pedir()`).
 */
export class ControlSalida {
  private readonly _abierta = signal(false);
  readonly abierta = this._abierta.asReadonly();
  private resolver: ((salir: boolean) => void) | null = null;

  constructor(private readonly sucio: () => boolean) {
    const ventana = inject(DOCUMENT).defaultView;
    const alDescargar = (evento: BeforeUnloadEvent): void => {
      if (this.sucio()) evento.preventDefault();
    };
    ventana?.addEventListener('beforeunload', alDescargar);
    inject(DestroyRef).onDestroy(() => {
      ventana?.removeEventListener('beforeunload', alDescargar);
      this.resolver?.(false);
    });
  }

  /** canDeactivate: sin cambios se sale; con cambios se abre el diálogo y se espera la respuesta. */
  puedeSalir(): boolean | Promise<boolean> {
    if (!this.sucio()) return true;
    this.resolver?.(false);
    this._abierta.set(true);
    return new Promise<boolean>((resolver) => (this.resolver = resolver));
  }

  responder(salir: boolean): void {
    this._abierta.set(false);
    this.resolver?.(salir);
    this.resolver = null;
  }
}
