import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, effect, inject, input, output, viewChild } from '@angular/core';

import { Boton, VarianteBoton } from '../../../shared/ui/boton/boton';

/**
 * Diálogo de confirmación del panel (HANDOFF Dialog/alertdialog): <dialog> modal nativo (resto de la
 * página inerte), foco inicial en «Cancelar» (acciones destructivas), Escape cancela y el foco vuelve
 * al control que lo abrió. Controlado con `[abierto]` + `(abiertoChange)`.
 */
@Component({
  selector: 'app-dialogo-confirmacion',
  imports: [Boton],
  template: `
    <dialog
      #dialogo
      class="dialogo"
      role="alertdialog"
      aria-modal="true"
      [attr.aria-labelledby]="idBase() + '-titulo'"
      [attr.aria-describedby]="idBase() + '-texto'"
      [attr.data-testid]="idBase()"
      (cancel)="alCancelar($event)"
    >
      <div class="dialogo-cuerpo">
        <h2 [id]="idBase() + '-titulo'">{{ titulo() }}</h2>
        <div [id]="idBase() + '-texto'"><ng-content /></div>
        <div class="acciones">
          <button
            type="button"
            appBoton
            [variante]="variante()"
            [cargando]="procesando()"
            [attr.data-testid]="idBase() + '-confirmar'"
            (click)="confirmar.emit()"
          >
            {{ textoConfirmar() }}
          </button>
          <button
            #cancelar
            type="button"
            appBoton
            variante="secondary"
            [attr.data-testid]="idBase() + '-cancelar'"
            (click)="cerrar()"
          >
            Cancelar
          </button>
        </div>
      </div>
    </dialog>
  `,
  styleUrls: ['./panel-formularios.css'],
})
export class DialogoConfirmacion {
  /** Abierto/cerrado: `[abierto]` + `(abiertoChange)` (sin `model()` ni `[( )]`: ver selector). */
  readonly abierto = input(false);
  readonly abiertoChange = output<boolean>();
  readonly titulo = input.required<string>();
  readonly textoConfirmar = input.required<string>();
  readonly variante = input<VarianteBoton>('danger');
  readonly procesando = input(false);
  /** Prefijo de los id y del data-testid. */
  readonly idBase = input('dialogo-confirmacion');
  readonly confirmar = output<void>();

  private readonly documento = inject(DOCUMENT);
  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private readonly botonCancelar = viewChild.required<ElementRef<HTMLButtonElement>>('cancelar');
  private origen: HTMLElement | null = null;

  constructor() {
    effect(() => {
      const abierto = this.abierto();
      const dialogo = this.dialogo().nativeElement;
      if (abierto && !dialogo.open) {
        this.origen = this.documento.activeElement as HTMLElement | null;
        dialogo.showModal();
        this.botonCancelar().nativeElement.focus();
      } else if (!abierto && dialogo.open) {
        dialogo.close();
        this.origen?.focus();
        this.origen = null;
      }
    });
  }

  protected cerrar(): void {
    this.abiertoChange.emit(false);
  }

  protected alCancelar(evento: Event): void {
    evento.preventDefault();
    if (!this.procesando()) this.cerrar();
  }
}
