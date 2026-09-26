import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { DestroyRef, Injectable, PLATFORM_ID, inject, signal } from '@angular/core';

/**
 * Estado de conexión del navegador (FEAT-028, GI-04). En el servidor siempre «en línea».
 * Expone solo señales de lectura (Regla 03).
 */
@Injectable({
  providedIn: 'root',
})
export class Conectividad {
  private readonly _enLinea = signal(true);
  private readonly _restablecida = signal(false);

  readonly enLinea = this._enLinea.asReadonly();
  /** true durante unos segundos tras recuperar la conexión («Conexión restablecida»). */
  readonly restablecida = this._restablecida.asReadonly();

  private temporizador: ReturnType<typeof setTimeout> | undefined;
  private navegador: Navigator | null = null;

  constructor() {
    if (!isPlatformBrowser(inject(PLATFORM_ID))) return;
    const ventana = inject(DOCUMENT).defaultView;
    if (ventana === null) return;

    this.navegador = ventana.navigator;
    this._enLinea.set(ventana.navigator.onLine);
    const alDesconectar = (): void => this.actualizar(false);
    const alConectar = (): void => this.actualizar(true);
    ventana.addEventListener('offline', alDesconectar);
    ventana.addEventListener('online', alConectar);
    inject(DestroyRef).onDestroy(() => {
      ventana.removeEventListener('offline', alDesconectar);
      ventana.removeEventListener('online', alConectar);
      clearTimeout(this.temporizador);
    });
  }

  /** Relee el estado del navegador (acción «Reintentar» del aviso GI-04). */
  comprobar(): void {
    if (this.navegador !== null) this.actualizar(this.navegador.onLine);
  }

  private actualizar(enLinea: boolean): void {
    const antes = this._enLinea();
    this._enLinea.set(enLinea);
    clearTimeout(this.temporizador);
    if (enLinea && !antes) {
      this._restablecida.set(true);
      this.temporizador = setTimeout(() => this._restablecida.set(false), 3000);
    } else {
      this._restablecida.set(false);
    }
  }
}
