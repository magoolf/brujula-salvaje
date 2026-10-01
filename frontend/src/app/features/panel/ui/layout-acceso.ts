import { Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { RUTA_ACCESO_PANEL } from '../../../core/auth/destino-seguro';
import { ID_CONTENIDO_PRINCIPAL } from '../../../core/layout/navegacion';
import { ZonaOutlet } from '../../../core/layout/shell-publico/zona-outlet';
import { Boton } from '../../../shared/ui/boton/boton';
import { SkipLink } from '../../../shared/ui/skip-link/skip-link';
import { SesionPanelStore } from '../state/sesion-panel.store';
import { PaginaAutorizacion } from './pagina-autorizacion';
import { PaginaCuenta } from './pagina-cuenta';

/**
 * TPL-PANEL-AUTH (SCR-030, 031, 033 y SCR-032 en modo obligatorio): fondo bg.canvas-panel, tarjeta
 * centrada con la marca y la etiqueta «Panel editorial», sin navegación lateral. Solo ofrece
 * «Cerrar sesión» cuando hay una sesión (parcial). SCR-033 y SCR-032 usan la tarjeta ancha (dialog-md).
 */
@Component({
  selector: 'app-layout-acceso',
  imports: [ZonaOutlet, SkipLink, Boton],
  template: `
    <app-skip-link [destino]="idContenido" texto="Saltar al contenido" />
    <main
      [id]="idContenido"
      tabindex="-1"
      class="lienzo"
      data-testid="panel-layout-acceso"
    >
      <div class="tarjeta" [class.tarjeta--ancha]="ancha()">
        <p class="marca">
          <span class="nombre">Brújula Salvaje</span>
          <span class="etiqueta">Panel editorial</span>
        </p>
        <router-outlet appZona="panel" (activate)="alActivar($event)" />
        @if (haySesion()) {
          <div class="salir">
            <button
              type="button"
              appBoton
              variante="ghost"
              [cargando]="cerrando()"
              data-testid="panel-acceso-cerrar-sesion"
              (click)="cerrarSesion()"
            >
              {{ cerrando() ? 'Cerrando sesión…' : 'Cerrar sesión' }}
            </button>
            @if (errorCierre(); as mensaje) {
              <p class="error" role="alert">{{ mensaje }}</p>
            }
          </div>
        }
      </div>
    </main>
  `,
  styles: `
    :host {
      display: block;
      min-height: 100dvh;
      background: var(--bs-color-bg-canvas-panel);
    }
    .lienzo {
      box-sizing: border-box;
      display: grid;
      place-items: start center;
      min-height: 100dvh;
      padding: var(--bs-space-8) var(--bs-grid-margin-xs);
      outline: none;
    }
    .tarjeta {
      box-sizing: border-box;
      display: grid;
      gap: var(--bs-space-5);
      width: 100%;
      max-width: var(--bs-size-auth-card);
      padding: var(--bs-space-6);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      box-shadow: var(--bs-shadow-1);
    }
    .tarjeta--ancha {
      max-width: var(--bs-size-dialog-md);
    }
    .marca {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: var(--bs-space-2);
    }
    .nombre {
      font-family: var(--bs-font-family-display);
      font-weight: var(--bs-font-weight-extrabold);
      color: var(--bs-color-text-brand);
    }
    .etiqueta {
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-muted);
    }
    .salir {
      display: grid;
      gap: var(--bs-space-2);
      justify-items: start;
      padding-top: var(--bs-space-4);
      border-top: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
    }
    .error {
      color: var(--bs-color-status-error-fg);
    }
    @media (min-width: 48rem) {
      .lienzo {
        place-items: center;
      }
    }
    @media (forced-colors: active) {
      .tarjeta {
        border: 1px solid CanvasText;
      }
    }
  `,
})
export class LayoutAcceso {
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);

  protected readonly idContenido = ID_CONTENIDO_PRINCIPAL;
  protected readonly haySesion = computed(() => this.sesion.sesion() !== null);
  protected readonly ancha = signal(false);
  protected readonly cerrando = signal(false);
  protected readonly errorCierre = signal<string | null>(null);

  protected alActivar(componente: unknown): void {
    this.ancha.set(componente instanceof PaginaAutorizacion || componente instanceof PaginaCuenta);
  }

  protected async cerrarSesion(): Promise<void> {
    this.cerrando.set(true);
    this.errorCierre.set(null);
    const error = await this.sesion.cerrarSesion();
    this.cerrando.set(false);
    if (error !== null) {
      this.errorCierre.set(error.mensaje);
      return;
    }
    await this.router.navigate([RUTA_ACCESO_PANEL], { queryParams: { motivo: 'cerrada' } });
  }
}
