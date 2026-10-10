import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  effect,
  inject,
  input,
  output,
  untracked,
  viewChild,
} from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import { devolverFoco } from './dialogo-confirmacion';

/**
 * Diálogo con formulario del panel (HANDOFF Dialog «dialog (formulario/información)», TKT-024):
 * <dialog> modal nativo, foco inicial en el primer control del formulario, Escape cancela (salvo
 * con una operación en curso) y el foco vuelve al disparador al cerrar. El contenido proyectado son
 * los campos; «Guardar» envía el formulario (`enviar`). Controlado con `[abierto]` + `(abiertoChange)`.
 */
@Component({
  selector: 'app-dialogo-formulario',
  imports: [Boton],
  template: `
    <dialog
      #dialogo
      class="dialogo dialogo-formulario"
      aria-modal="true"
      [attr.aria-labelledby]="idBase() + '-titulo'"
      [attr.data-testid]="idBase()"
      (cancel)="alCancelar($event)"
    >
      <form class="dialogo-cuerpo" novalidate (submit)="alEnviar($event)">
        <h2 [id]="idBase() + '-titulo'">{{ titulo() }}</h2>
        <ng-content />
        <div class="acciones">
          <button type="submit" appBoton [cargando]="procesando()" [attr.data-testid]="idBase() + '-guardar'">
            {{ textoGuardar() }}
          </button>
          <button type="button" appBoton variante="secondary" [attr.data-testid]="idBase() + '-cancelar'" (click)="cerrar()">
            Cancelar
          </button>
        </div>
      </form>
    </dialog>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .dialogo-formulario {
      width: min(100% - 2 * var(--bs-space-4), var(--bs-size-dialog-md));
      max-height: calc(100dvh - 2 * var(--bs-space-4));
      overflow-y: auto;
    }
    h2 {
      margin: 0;
    }
  `,
})
export class DialogoFormulario {
  readonly abierto = input(false);
  readonly abiertoChange = output<boolean>();
  readonly titulo = input.required<string>();
  readonly textoGuardar = input('Guardar');
  readonly procesando = input(false);
  readonly idBase = input('dialogo-formulario');
  readonly enviar = output<void>();
  /** Destino del foco al cerrar si el disparador ya no existe (p. ej. el encabezado de la pantalla). */
  readonly respaldoFoco = input<HTMLElement | null>(null);

  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private origen: HTMLElement | null = null;

  constructor() {
    effect(() => {
      const abierto = this.abierto();
      const dialogo = this.dialogo().nativeElement;
      if (abierto && !dialogo.open) {
        this.origen = this.documento.activeElement as HTMLElement | null;
        dialogo.showModal();
        afterNextRender(
          () => dialogo.querySelector<HTMLElement>('input:not([disabled]), select:not([disabled]), textarea:not([disabled])')?.focus(),
          { injector: this.injector },
        );
      } else if (!abierto && dialogo.open) {
        dialogo.close();
        devolverFoco(this.documento, this.injector, dialogo, [this.origen, untracked(this.respaldoFoco)]);
        this.origen = null;
      }
    });
  }

  protected alEnviar(evento: Event): void {
    evento.preventDefault();
    if (!this.procesando()) this.enviar.emit();
  }

  protected cerrar(): void {
    this.abiertoChange.emit(false);
  }

  protected alCancelar(evento: Event): void {
    evento.preventDefault();
    if (!this.procesando()) this.cerrar();
  }
}
