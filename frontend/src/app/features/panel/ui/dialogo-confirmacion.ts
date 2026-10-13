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

import { Boton, VarianteBoton } from '../../../shared/ui/boton/boton';

/**
 * Diálogo de confirmación del panel (HANDOFF Dialog/alertdialog): <dialog> modal nativo (resto de la
 * página inerte), foco inicial en «Cancelar» (acciones destructivas), Escape cancela y el foco vuelve
 * al control que lo abrió (o a `retornoFoco` si se indica: p. ej. el disparador de un menú que se cierra
 * al abrir el diálogo, WCAG 2.4.3), y si ninguno puede recibirlo tras el render, a `respaldoFoco`.
 * Controlado con `[abierto]` + `(abiertoChange)`.
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
  /**
   * Último recurso al cerrar (WCAG 2.4.3): destino estable y anunciado (p. ej. el encabezado del
   * editor) si el disparador desapareció o sigue deshabilitado tras confirmar.
   */
  readonly respaldoFoco = input<HTMLElement | null>(null);

  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
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
        devolverFoco(this.documento, this.injector, dialogo, [this.retorno, this.origen, untracked(this.respaldoFoco)]);
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

/**
 * Enfoca el primer candidato que de verdad recibe el foco (conectado, habilitado, visible): un botón
 * [disabled], un elemento retirado del DOM o uno dentro de un <details> cerrado no lo aceptan y se pasa
 * al siguiente. Devuelve el elemento enfocado o null.
 */
export function enfocarPrimero(
  documento: Document,
  candidatos: readonly (HTMLElement | null | undefined)[],
): HTMLElement | null {
  for (const candidato of candidatos) {
    // <body> no es un destino: es lo que queda cuando el foco se pierde.
    if (!candidato?.isConnected || candidato === documento.body) continue;
    candidato.focus();
    if (documento.activeElement === candidato) return candidato;
  }
  return null;
}

/**
 * Devuelve el foco al cerrar un diálogo (WCAG 2.4.3, QA TKT-023 F-02-R). Se llama justo después de
 * `dialog.close()` y espera al siguiente render: al confirmar, la operación ya terminó pero la vista aún
 * no refleja su resultado (el disparador sigue [disabled] mientras procesaba, o va a desaparecer, como
 * «Más acciones» al retirar). Tras el render se prueba la cadena `candidatos` en orden (retorno → origen
 * → respaldo). Si entretanto otro código llevó el foco a otro sitio (p. ej. el enlace del ErrorSummary
 * a un campo), se respeta; el foco que el propio navegador restaura al cerrar el <dialog> (WebKit lo
 * devuelve al elemento enfocado antes de abrirlo, que no es el botón pulsado) no cuenta como tal.
 */
export function devolverFoco(
  documento: Document,
  injector: Injector,
  dialogo: HTMLElement,
  candidatos: readonly (HTMLElement | null | undefined)[],
): void {
  const alCerrar = documento.activeElement;
  afterNextRender(
    () => {
      const activo = documento.activeElement;
      const perdido =
        activo === null ||
        activo === documento.body ||
        activo === alCerrar ||
        !activo.isConnected ||
        dialogo.contains(activo);
      if (perdido) enfocarPrimero(documento, candidatos);
    },
    { injector },
  );
}
