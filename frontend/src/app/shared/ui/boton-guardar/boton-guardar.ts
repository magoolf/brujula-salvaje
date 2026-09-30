import { Component, computed, input, output } from '@angular/core';

import { Icono } from '../icono/icono';

/**
 * SaveButton (GI-07, HANDOFF_UI_UX): botón de icono con estado pulsado (aria-pressed) y nombre
 * accesible completo («Guardar {título}» / «Quitar {título} de guardados»). No sabe nada de
 * localStorage: la feature que lo usa decide qué hacer en `alternar` (Regla 11/12, comando en la
 * capa STATE). `deshabilitado` cubre ALT-011 (almacenamiento no disponible).
 */
@Component({
  selector: 'app-boton-guardar',
  imports: [Icono],
  template: `
    <button
      type="button"
      class="guardar"
      [class.guardar--icono]="soloIcono()"
      [attr.aria-pressed]="guardado()"
      [attr.aria-label]="etiquetaAccesible()"
      [attr.aria-disabled]="deshabilitado() ? 'true' : null"
      [attr.data-testid]="testId()"
      (click)="alPulsar()"
    >
      <app-icono [nombre]="guardado() ? 'bookmark-check' : 'bookmark'" [tamano]="20" />
      @if (!soloIcono()) {
        <span>{{ guardado() ? 'Guardado' : 'Guardar' }}</span>
      }
    </button>
  `,
  styles: `
    .guardar {
      display: inline-flex;
      align-items: center;
      gap: var(--bs-space-2);
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-3);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-radius: var(--bs-radius-pill);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      font: inherit;
      font-weight: var(--bs-font-weight-semibold);
      cursor: pointer;
    }
    .guardar--icono {
      padding: 0;
      width: var(--bs-size-target);
      justify-content: center;
      border-radius: var(--bs-radius-full, 999px);
    }
    .guardar[aria-pressed='true'] {
      border-color: var(--bs-color-border-brand);
      color: var(--bs-color-text-brand);
      background: var(--bs-color-action-selected-bg);
    }
    .guardar[aria-disabled='true'] {
      cursor: not-allowed;
      opacity: 0.6;
    }
    .guardar:hover {
      background: var(--bs-color-bg-brand-faint);
    }
  `,
})
export class BotonGuardar {
  readonly titulo = input.required<string>();
  readonly guardado = input(false);
  readonly deshabilitado = input(false);
  readonly soloIcono = input(true);
  readonly testId = input('boton-guardar');
  readonly alternar = output<void>();

  protected readonly etiquetaAccesible = computed(() =>
    this.guardado() ? `Quitar ${this.titulo()} de guardados` : `Guardar ${this.titulo()}`,
  );

  protected alPulsar(): void {
    if (this.deshabilitado()) return;
    this.alternar.emit();
  }
}
