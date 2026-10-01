import { Component, computed, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Insignia } from '../../../shared/ui/insignia/insignia';
import { MiniaturaMedio } from './miniatura-medio';
import {
  ETIQUETA_ESTADO_MEDIO,
  MENSAJE_NO_SELECCIONABLE,
  Medio,
  descripcionMosaico,
  nombreMedio,
  textoUsos,
  varianteEstadoMedio,
} from '../domain/medios';

/** Variante del mosaico (HANDOFF MediaTile). */
export type VarianteMosaico = 'enlace' | 'casilla' | 'radio';

/**
 * MediaTile (HANDOFF_UI_UX COMPONENTES): miniatura 1:1, nombre, insignia de estado, licencia y
 * «Usado en {n}». Variantes: enlace a SCR-040 (biblioteca) o seleccionable con casilla (selección
 * múltiple) o radio (una sola) para SCR-041; los no seleccionables muestran el motivo y su control
 * queda deshabilitado. La miniatura (MiniaturaMedio) se carga al acercarse a la pantalla.
 */
@Component({
  selector: 'app-mosaico-medio',
  imports: [RouterLink, Insignia, MiniaturaMedio],
  template: `
    @if (variante() === 'enlace') {
      <a
        class="mosaico"
        [routerLink]="['/panel/medios', medio().id]"
        [attr.aria-label]="descripcion()"
        [attr.data-testid]="'medio-mosaico-' + medio().id"
      >
        <app-miniatura-medio class="miniatura" [derivados]="medio().derivados" />
        <span class="datos">
          <span class="titulo">{{ nombre() }}</span>
          <app-insignia [variante]="variante_()">{{ etiquetaEstado() }}</app-insignia>
          <span class="meta">{{ licencia() }} · {{ usos() }}</span>
        </span>
      </a>
    } @else {
      <label
        class="mosaico mosaico--seleccionable"
        [class.seleccionado]="seleccionado()"
        [class.bloqueado]="!seleccionable()"
        [attr.data-testid]="'selector-mosaico-' + medio().id"
      >
        <input
          class="control"
          [type]="variante() === 'radio' ? 'radio' : 'checkbox'"
          [name]="nombreGrupo()"
          [checked]="seleccionado()"
          [disabled]="!seleccionable()"
          [attr.aria-describedby]="seleccionable() ? null : idMotivo()"
          [attr.data-testid]="'selector-control-' + medio().id"
          (change)="alternar.emit()"
        />
        <app-miniatura-medio class="miniatura" [derivados]="medio().derivados" />
        <span class="datos">
          <span class="titulo">{{ nombre() }}</span>
          <app-insignia [variante]="variante_()">{{ etiquetaEstado() }}</app-insignia>
          <span class="meta">{{ licencia() }} · {{ usos() }}</span>
          @if (!seleccionable()) {
            <span class="motivo" [id]="idMotivo()">{{ motivo }}</span>
          }
        </span>
      </label>
    }
  `,
  styles: `
    :host {
      display: block;
    }
    .mosaico {
      position: relative;
      display: grid;
      gap: var(--bs-space-2);
      height: 100%;
      box-sizing: border-box;
      padding: var(--bs-space-2);
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      text-decoration: none;
    }
    a.mosaico:hover,
    .mosaico--seleccionable:not(.bloqueado):hover {
      border-color: var(--bs-color-border-control);
      background: var(--bs-color-bg-sunken);
    }
    a.mosaico:focus-visible {
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring);
      outline-offset: var(--bs-border-width-focus-offset);
    }
    .mosaico--seleccionable {
      cursor: pointer;
    }
    .mosaico--seleccionable:has(.control:focus-visible) {
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring);
      outline-offset: var(--bs-border-width-focus-offset);
    }
    .seleccionado {
      border: 3px solid var(--bs-color-border-brand);
      padding: calc(var(--bs-space-2) - 2px);
    }
    .bloqueado {
      cursor: not-allowed;
    }
    .control {
      position: absolute;
      top: var(--bs-space-3);
      left: var(--bs-space-3);
      z-index: 1;
      width: 1.5rem;
      height: 1.5rem;
      margin: 0;
      accent-color: var(--bs-color-action-primary-bg);
    }
    .bloqueado .miniatura {
      opacity: 0.6;
    }
    .meta,
    .motivo {
      font-size: var(--bs-typography-body-sm-font-size);
      line-height: var(--bs-typography-body-sm-line-height);
      color: var(--bs-color-text-muted);
    }
    .datos {
      display: grid;
      gap: var(--bs-space-1);
      justify-items: start;
      min-width: 0;
    }
    .titulo {
      max-width: 100%;
      overflow-wrap: anywhere;
      font-weight: var(--bs-font-weight-semibold);
    }
    .motivo {
      color: var(--bs-color-status-warning-fg);
    }
    @media (forced-colors: active) {
      .seleccionado {
        border-color: Highlight;
      }
    }
  `,
})
export class MosaicoMedio {
  readonly medio = input.required<Medio>();
  readonly variante = input<VarianteMosaico>('enlace');
  readonly seleccionado = input(false);
  readonly seleccionable = input(true);
  /** `name` del grupo de radios o casillas (uno por selector). */
  readonly nombreGrupo = input('medios');
  readonly alternar = output<void>();

  protected readonly motivo = MENSAJE_NO_SELECCIONABLE;
  protected readonly nombre = computed(() => nombreMedio(this.medio()));
  protected readonly descripcion = computed(() => descripcionMosaico(this.medio()));
  protected readonly etiquetaEstado = computed(() => ETIQUETA_ESTADO_MEDIO[this.medio().estado]);
  protected readonly variante_ = computed(() => varianteEstadoMedio(this.medio().estado));
  protected readonly licencia = computed(() => this.medio().licencia?.nombre ?? 'Sin licencia');
  protected readonly usos = computed(() => textoUsos(this.medio().numeroUsos));
  protected readonly idMotivo = computed(() => `medio-${this.medio().id}-motivo`);
}
