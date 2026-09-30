import { Component, input, output } from '@angular/core';

import { Icono } from '../icono/icono';

/**
 * ShareButton (GI-06, HANDOFF_UI_UX): botón que delega en `core/layout/compartir.ts` (la feature
 * que lo usa decide el mensaje de confirmación según la vía, `role=status`). Presentacional puro:
 * no conoce la Web Share API ni el portapapeles.
 */
@Component({
  selector: 'app-boton-compartir',
  imports: [Icono],
  template: `
    <button
      type="button"
      class="compartir"
      [class.compartir--icono]="soloIcono()"
      [attr.aria-label]="'Compartir ' + titulo()"
      [attr.data-testid]="testId()"
      [disabled]="compartiendo()"
      (click)="compartir.emit()"
    >
      <app-icono nombre="share-2" [tamano]="20" />
      @if (!soloIcono()) {
        <span>Compartir</span>
      }
    </button>
  `,
  styles: `
    .compartir {
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
    .compartir--icono {
      padding: 0;
      width: var(--bs-size-target);
      justify-content: center;
      border-radius: var(--bs-radius-full, 999px);
    }
    .compartir:hover {
      background: var(--bs-color-bg-brand-faint);
    }
    .compartir:disabled {
      cursor: progress;
      opacity: 0.7;
    }
  `,
})
export class BotonCompartir {
  readonly titulo = input.required<string>();
  readonly soloIcono = input(true);
  readonly compartiendo = input(false);
  readonly testId = input('boton-compartir');
  readonly compartir = output<void>();
}
