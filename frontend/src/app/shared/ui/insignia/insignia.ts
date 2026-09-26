import { Component, computed, input } from '@angular/core';

import { Icono } from '../icono/icono';
import { NombreIcono } from '../icono/iconos-lucide';

export type VarianteInsignia = 'borrador' | 'publicado' | 'retirado' | 'pendiente' | 'rechazado' | 'neutral' | 'esencial';

const ICONO_POR_VARIANTE: Record<VarianteInsignia, NombreIcono | null> = {
  borrador: 'circle-alert',
  publicado: 'circle-check',
  retirado: 'x',
  pendiente: 'info',
  rechazado: 'triangle-alert',
  neutral: null,
  esencial: 'circle-check',
};

/**
 * Badge / etiqueta (HANDOFF_UI_UX COMPONENTES.Badge): texto legible en español + icono de forma
 * distinta por estado, nunca solo color (1.4.1). El texto lo pasa quien la usa (no el enum).
 */
@Component({
  selector: 'app-insignia',
  imports: [Icono],
  template: `
    <span class="insignia" [attr.data-variante]="variante()" data-testid="insignia">
      @if (icono(); as nombre) {
        <app-icono [nombre]="nombre" [tamano]="16" />
      }
      <ng-content />
    </span>
  `,
  styles: `
    .insignia {
      display: inline-flex;
      align-items: center;
      gap: var(--bs-space-1);
      padding: 0.125rem var(--bs-space-2);
      border-radius: var(--bs-radius-sm);
      font-family: var(--bs-typography-body-sm-font-family);
      font-size: var(--bs-typography-body-sm-font-size);
      font-weight: var(--bs-font-weight-semibold);
      line-height: var(--bs-typography-body-sm-line-height);
      border: 1px solid transparent;
    }
    [data-variante='borrador'] { color: var(--bs-color-badge-borrador-fg); background: var(--bs-color-badge-borrador-bg); }
    [data-variante='publicado'],
    [data-variante='esencial'] { color: var(--bs-color-badge-publicado-fg); background: var(--bs-color-badge-publicado-bg); }
    [data-variante='retirado'],
    [data-variante='neutral'] { color: var(--bs-color-badge-retirado-fg); background: var(--bs-color-badge-retirado-bg); }
    [data-variante='pendiente'] { color: var(--bs-color-badge-pendiente-fg); background: var(--bs-color-badge-pendiente-bg); }
    [data-variante='rechazado'] { color: var(--bs-color-badge-rechazado-fg); background: var(--bs-color-badge-rechazado-bg); }
    @media (forced-colors: active) {
      .insignia { border-color: CanvasText; }
    }
  `,
})
export class Insignia {
  readonly variante = input<VarianteInsignia>('neutral');

  protected readonly icono = computed<NombreIcono | null>(() => ICONO_POR_VARIANTE[this.variante()]);
}
