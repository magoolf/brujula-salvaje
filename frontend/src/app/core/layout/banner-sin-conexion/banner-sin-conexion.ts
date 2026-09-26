import { Component, inject } from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import { Icono } from '../../../shared/ui/icono/icono';
import { Conectividad } from '../conectividad';

/**
 * OfflineBanner GI-04 (FEAT-028, AC-114): barra fija inferior que no empuja el contenido (CLS 0).
 * La región role=status existe siempre para que el cambio se anuncie; el contenido visible de la
 * página no se toca. «Reintentar» vuelve a comprobar la conexión; las features reintentan sus recursos al volver.
 */
@Component({
  selector: 'app-banner-sin-conexion',
  imports: [Boton, Icono],
  template: `
    <div class="region" role="status" data-testid="banner-sin-conexion">
      @if (!conectividad.enLinea()) {
        <div class="barra">
          <app-icono nombre="wifi-off" [tamano]="20" />
          <p>Sin conexión. Lo que ya cargaste sigue disponible.</p>
          <button type="button" appBoton variante="ghost-inverse" tamano="sm" (click)="reintentar()">
            Reintentar
          </button>
        </div>
      } @else if (conectividad.restablecida()) {
        <div class="barra"><app-icono nombre="circle-check" [tamano]="20" /><p>Conexión restablecida.</p></div>
      }
    </div>
  `,
  styles: `
    .region {
      position: fixed;
      inset: auto 0 0 0;
      z-index: var(--bs-z-banner-offline);
      pointer-events: none;
    }
    .barra {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: var(--bs-space-3);
      padding: var(--bs-space-3) var(--bs-space-4);
      padding-bottom: calc(var(--bs-space-3) + env(safe-area-inset-bottom));
      background: var(--bs-color-bg-inverse);
      color: var(--bs-color-text-inverse);
      pointer-events: auto;
    }
  `,
})
export class BannerSinConexion {
  protected readonly conectividad = inject(Conectividad);

  /** Vuelve a comprobar la conexión sin recargar (recargar sin red perdería el contenido visible). */
  protected reintentar(): void {
    this.conectividad.comprobar();
  }
}
