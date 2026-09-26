import { Component, input, output } from '@angular/core';

import { Icono } from '../icono/icono';

/**
 * Chip / ficha de filtro quitable (HANDOFF_UI_UX COMPONENTES.Chip): el chip completo es un botón
 * con nombre accesible «Quitar filtro {etiqueta}». La gestión del foco tras quitar (siguiente chip o
 * encabezado de resultados) es responsabilidad de la feature que renderiza la lista.
 */
@Component({
  selector: 'app-chip',
  imports: [Icono],
  template: `
    <button
      type="button"
      class="chip"
      [attr.aria-label]="'Quitar filtro ' + etiqueta()"
      [attr.data-testid]="testId()"
      (click)="quitar.emit()"
    >
      <span>{{ etiqueta() }}</span>
      <app-icono nombre="x" [tamano]="16" />
    </button>
  `,
  styles: `
    .chip {
      display: inline-flex;
      align-items: center;
      gap: var(--bs-space-2);
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-4) var(--bs-space-3);
      border: var(--bs-border-width-control) solid var(--bs-color-border-brand);
      border-radius: var(--bs-radius-pill);
      background: var(--bs-color-action-selected-bg);
      color: var(--bs-color-text-brand);
      font: inherit;
      font-weight: var(--bs-font-weight-semibold);
      cursor: pointer;
      transition: background-color var(--bs-motion-duration-fast) var(--bs-motion-easing-standard);
    }
    .chip:hover {
      background: var(--bs-color-bg-brand-faint);
    }
    .chip:active {
      transform: translateY(1px);
    }
  `,
})
export class Chip {
  /** Texto visible, p. ej. «Tipo: Senderismo». */
  readonly etiqueta = input.required<string>();
  readonly testId = input('chip');
  readonly quitar = output<void>();
}
