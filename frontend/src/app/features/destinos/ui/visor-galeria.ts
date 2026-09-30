import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { Component, computed, inject, signal } from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import { Icono } from '../../../shared/ui/icono/icono';
import { ImagenVista } from '../domain/modelos';

export interface DatosVisorGaleria {
  readonly imagenes: readonly ImagenVista[];
  readonly indiceInicial: number;
  readonly tituloDestino: string;
}

/**
 * SCR-005 Visor de galería (FEAT-007): Dialog fullscreen sobre CDK Dialog (mismo mecanismo que
 * `MenuMovil`). ←/→ cambian de foto, Esc cierra (gestionado por `DialogRef`/CDK), sin bucle en los
 * extremos (Estados_UI.disabled del HANDOFF).
 */
@Component({
  selector: 'app-visor-galeria',
  host: { '(keydown.arrowleft)': 'anterior()', '(keydown.arrowright)': 'siguiente()' },
  imports: [Icono, Boton],
  template: `
    <div class="visor" role="dialog" [attr.aria-label]="'Galería de ' + datos.tituloDestino" data-testid="visor-galeria">
      <div class="barra">
        <span class="posicion" aria-live="polite">{{ indice() + 1 }} de {{ datos.imagenes.length }}</span>
        <button type="button" appBoton variante="ghost-inverse" aria-label="Cerrar galería" (click)="cerrar()">
          <app-icono nombre="x" [tamano]="24" etiqueta="Cerrar galería" />
        </button>
      </div>
      <div class="cuerpo">
        <button
          type="button"
          class="control"
          appBoton
          variante="ghost-inverse"
          aria-label="Foto anterior"
          [disabled]="indice() === 0"
          (click)="anterior()"
        >
          <app-icono nombre="chevron-left" [tamano]="32" />
        </button>
        <figure class="figura">
          <img [src]="actual().src" [alt]="actual().alt" />
          <figcaption>
            @if (actual().pieDeFoto; as pie) {
              <span>{{ pie }}</span>
            }
            <span>Foto: {{ actual().autorCredito }} · {{ actual().licenciaNombre }}</span>
          </figcaption>
        </figure>
        <button
          type="button"
          class="control"
          appBoton
          variante="ghost-inverse"
          aria-label="Foto siguiente"
          [disabled]="indice() === datos.imagenes.length - 1"
          (click)="siguiente()"
        >
          <app-icono nombre="chevron-right" [tamano]="32" />
        </button>
      </div>
    </div>
  `,
  styles: `
    .visor {
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100dvh;
      background: var(--bs-color-bg-inverse);
      color: var(--bs-color-text-inverse);
    }
    .barra {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--bs-space-4);
    }
    .cuerpo {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: var(--bs-space-4);
      padding-inline: var(--bs-space-4);
      min-height: 0;
    }
    .figura {
      display: grid;
      gap: var(--bs-space-2);
      justify-items: center;
      min-height: 0;
      height: 100%;
    }
    img {
      max-width: 100%;
      max-height: calc(100dvh - 10rem);
      object-fit: contain;
    }
    figcaption {
      display: grid;
      gap: var(--bs-space-1);
      text-align: center;
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-inverse-muted);
    }
    .control:disabled {
      opacity: 0.3;
      cursor: default;
    }
  `,
})
export class VisorGaleria {
  protected readonly datos = inject<DatosVisorGaleria>(DIALOG_DATA);
  private readonly dialogo = inject(DialogRef<void, VisorGaleria>);

  private readonly _indice = signal(
    Math.min(Math.max(this.datos.indiceInicial, 0), this.datos.imagenes.length - 1),
  );
  protected readonly indice = this._indice.asReadonly();
  protected readonly actual = computed(() => this.datos.imagenes[this.indice()]);

  protected anterior(): void {
    if (this.indice() > 0) this._indice.update((i) => i - 1);
  }

  protected siguiente(): void {
    if (this.indice() < this.datos.imagenes.length - 1) this._indice.update((i) => i + 1);
  }

  protected cerrar(): void {
    this.dialogo.close();
  }
}
