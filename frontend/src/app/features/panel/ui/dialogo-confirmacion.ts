import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, effect, inject, input, output, untracked, viewChild } from '@angular/core';

import { Boton, VarianteBoton } from '../../../shared/ui/boton/boton';

/**
 * Diálogo de confirmación del panel (HANDOFF Dialog/alertdialog): <dialog> modal nativo (resto de la
 * página inerte), foco inicial en «Cancelar» (acciones destructivas), Escape cancela y el foco vuelve
 * al control que lo abrió (o a `retornoFoco` si se indica: p. ej. el disparador de un menú que se cierra
 * al abrir el diálogo, WCAG 2.4.3). Controlado con `[abierto]` + `(abiertoChange)`.
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
            {{ textoCancelar() }}
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
  readonly textoCancelar = input('Cancelar');
  readonly procesando = input(false);
  /** Prefijo de los id y del data-testid. */
  readonly idBase = input('dialogo-confirmacion');
  readonly confirmar = output<void>();
  /** Destino del foco al cerrar cuando el control que abrió el diálogo ya no está visible. */
  readonly retornoFoco = input<HTMLElement | null>(null);

  private readonly documento = inject(DOCUMENT);
  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private readonly botonCancelar = viewChild.required<ElementRef<HTMLButtonElement>>('cancelar');
  private origen: HTMLElement | null = null;
  /** `retornoFoco` al abrir: el disparador puede cambiar al cerrar (p. ej. la confirmación vuelve a null). */
  private retorno: HTMLElement | null = null;

  constructor() {
    effect(() => {
      const abierto = this.abierto();
      const dialogo = this.dialogo().nativeElement;
      if (abierto && !dialogo.open) {
        this.origen = this.documento.activeElement as HTMLElement | null;
        this.retorno = untracked(this.retornoFoco);
        dialogo.showModal();
        this.botonCancelar().nativeElement.focus();
      } else if (!abierto && dialogo.open) {
        dialogo.close();
        destinoFoco(this.retorno, this.origen)?.focus();
        this.origen = null;
        this.retorno = null;
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

/**
 * Elemento al que vuelve el foco al cerrar un diálogo: `retorno` si sigue en el documento; si no, el
 * control que lo abrió. Un elemento dentro de un <details> cerrado (menú «Más acciones») sigue conectado
 * pero no puede recibir el foco: por eso el editor indica el <summary> como `retorno`.
 */
export function destinoFoco(retorno: HTMLElement | null, origen: HTMLElement | null): HTMLElement | null {
  return retorno?.isConnected ? retorno : origen;
}
