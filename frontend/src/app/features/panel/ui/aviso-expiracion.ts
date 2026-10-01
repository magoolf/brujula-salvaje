import { Component, ElementRef, effect, inject, output, signal, viewChild } from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import { ExpiracionSesionStore } from '../state/expiracion-sesion.store';

/**
 * SessionExpiryDialog (HANDOFF_UI_UX; AC-109, AC_TKT010_11): alertdialog modal 2 min antes de la
 * expiración por inactividad con cuenta atrás visible (anunciada solo al abrir y a los 30 s) y
 * «Seguir conectado» (foco inicial) / «Cerrar sesión». Al llegar a 0 ofrece volver a entrar.
 */
@Component({
  selector: 'app-aviso-expiracion',
  imports: [Boton],
  template: `
    <dialog
      #dialogo
      class="dialogo"
      role="alertdialog"
      aria-labelledby="expiracion-titulo"
      aria-describedby="expiracion-texto"
      data-testid="aviso-expiracion"
      (cancel)="$event.preventDefault()"
    >
      <div class="cuerpo">
        @if (store.expirada()) {
          <h2 id="expiracion-titulo">Tu sesión expiró</h2>
          <p id="expiracion-texto">
            Por seguridad cerramos la sesión por inactividad. Lo que tengas en pantalla sigue aquí;
            vuelve a entrar para continuar.
          </p>
          <div class="acciones">
            <button type="button" appBoton data-testid="aviso-expiracion-entrar" (click)="volverAEntrar.emit()">
              Volver a entrar
            </button>
          </div>
        } @else {
          <h2 id="expiracion-titulo">Tu sesión está por expirar</h2>
          <p id="expiracion-texto">
            Por inactividad, se cerrará en
            <span class="cuenta" data-testid="aviso-expiracion-cuenta">{{ store.cuentaAtras() }}</span>.
          </p>
          <div class="acciones">
            <button
              #seguir
              type="button"
              appBoton
              [cargando]="store.renovando()"
              data-testid="aviso-expiracion-seguir"
              (click)="seguirConectado()"
            >
              Seguir conectado
            </button>
            <button
              type="button"
              appBoton
              variante="secondary"
              data-testid="aviso-expiracion-cerrar"
              (click)="cerrarSesion.emit()"
            >
              Cerrar sesión
            </button>
          </div>
          @if (errorRenovar(); as mensaje) {
            <p class="error" role="alert">{{ mensaje }}</p>
          }
        }
        <p class="bs-solo-lectores" aria-live="assertive">{{ store.anuncio() }}</p>
      </div>
    </dialog>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .cuerpo {
      display: grid;
      gap: var(--bs-space-4);
    }
    .cuenta {
      font-variant-numeric: tabular-nums;
      font-weight: var(--bs-font-weight-bold);
    }
    .error {
      color: var(--bs-color-status-error-fg);
    }
  `,
})
export class AvisoExpiracion {
  protected readonly store = inject(ExpiracionSesionStore);
  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private readonly seguir = viewChild<ElementRef<HTMLButtonElement>>('seguir');

  readonly cerrarSesion = output<void>();
  readonly volverAEntrar = output<void>();

  protected readonly errorRenovar = signal<string | null>(null);

  constructor() {
    effect(() => {
      const abierto = this.store.avisoVisible() || this.store.expirada();
      const dialogo = this.dialogo().nativeElement;
      if (abierto && !dialogo.open) {
        dialogo.showModal();
        this.seguir()?.nativeElement.focus();
      } else if (!abierto && dialogo.open) {
        dialogo.close();
      }
    });
  }

  protected async seguirConectado(): Promise<void> {
    const error = await this.store.seguirConectado();
    this.errorRenovar.set(error === null ? null : error.mensaje);
  }
}
