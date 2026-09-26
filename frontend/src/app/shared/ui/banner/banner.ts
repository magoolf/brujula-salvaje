import { Component, computed, input, output, signal } from '@angular/core';

import { Icono } from '../icono/icono';
import { NombreIcono } from '../icono/iconos-lucide';

export type VarianteBanner = 'info' | 'success' | 'warning' | 'error';

const ICONOS: Record<VarianteBanner, NombreIcono> = {
  info: 'info',
  success: 'circle-check',
  warning: 'triangle-alert',
  error: 'circle-alert',
};

/**
 * InlineAlert / Banner persistente (HANDOFF_UI_UX, DEC-AUTO-068): icono + título + texto + acción
 * opcional (contenido proyectado). role=alert en error, role=status en el resto. Persiste hasta que
 * el usuario lo cierra (solo success/info son descartables) o cambia de vista.
 */
@Component({
  selector: 'app-banner',
  imports: [Icono],
  template: `
    @if (visible()) {
      <div
        class="banner"
        [attr.data-variante]="variante()"
        [attr.role]="rol()"
        [attr.data-testid]="testId()"
      >
        <app-icono class="icono" [nombre]="icono()" [tamano]="24" />
        <div class="cuerpo">
          @if (titulo()) {
            <p class="titulo">{{ titulo() }}</p>
          }
          <div class="texto"><ng-content /></div>
          <div class="acciones"><ng-content select="[banner-accion]" /></div>
        </div>
        @if (descartable()) {
          <button type="button" class="cerrar" aria-label="Cerrar aviso" (click)="cerrar()">
            <app-icono nombre="x" [tamano]="20" />
          </button>
        }
      </div>
    }
  `,
  styles: `
    .banner {
      display: flex;
      align-items: flex-start;
      gap: var(--bs-space-3);
      padding: var(--bs-space-4);
      border-radius: var(--bs-radius-md);
      border-inline-start: 4px solid currentColor;
    }
    .cuerpo {
      flex: 1;
      display: grid;
      gap: var(--bs-space-1);
      color: var(--bs-color-text-default);
    }
    .titulo {
      font-weight: var(--bs-font-weight-bold);
    }
    .acciones:empty {
      display: none;
    }
    [data-variante='info'] {
      color: var(--bs-color-status-info-fg);
      background: var(--bs-color-status-info-bg);
    }
    [data-variante='success'] {
      color: var(--bs-color-status-success-fg);
      background: var(--bs-color-status-success-bg);
    }
    [data-variante='warning'] {
      color: var(--bs-color-status-warning-fg);
      background: var(--bs-color-status-warning-bg);
    }
    [data-variante='error'] {
      color: var(--bs-color-status-error-fg);
      background: var(--bs-color-status-error-bg);
    }
    .cerrar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: var(--bs-size-target);
      height: var(--bs-size-target);
      margin: calc(-1 * var(--bs-space-2));
      border: 0;
      border-radius: var(--bs-radius-md);
      background: transparent;
      color: var(--bs-color-text-default);
      cursor: pointer;
    }
    @media (forced-colors: active) {
      .banner {
        border: 1px solid CanvasText;
      }
    }
  `,
})
export class Banner {
  readonly variante = input<VarianteBanner>('info');
  readonly titulo = input<string | null>(null);
  readonly testId = input('banner');
  /** Solo se permite descartar avisos success/info. */
  readonly permitirCerrar = input(false);
  readonly cerrado = output<void>();

  private readonly _cerrado = signal(false);

  protected readonly visible = computed(() => !this._cerrado());
  protected readonly icono = computed(() => ICONOS[this.variante()]);
  protected readonly rol = computed(() => (this.variante() === 'error' ? 'alert' : 'status'));
  protected readonly descartable = computed(
    () => this.permitirCerrar() && (this.variante() === 'success' || this.variante() === 'info'),
  );

  protected cerrar(): void {
    this._cerrado.set(true);
    this.cerrado.emit();
  }
}
