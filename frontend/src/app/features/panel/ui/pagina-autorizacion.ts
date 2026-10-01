import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { Router } from '@angular/router';

import { RUTA_ACCESO_PANEL } from '../../../core/auth/destino-seguro';
import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { DecisionAutorizacion } from '../domain/modelos';
import { AutorizacionStore } from '../state/autorizacion.store';
import { SesionPanelStore } from '../state/sesion-panel.store';

/**
 * SCR-033 Autorización de tratamiento de datos (FEAT-032, REQ-070, DEC-AUTO-038/079). Bloqueante:
 * «Autorizo» registra fecha y versión y continúa; «No autorizo» pide confirmación y cierra la sesión.
 */
@Component({
  selector: 'app-pagina-autorizacion',
  imports: [Banner, Boton, EstadoCargando, EstadoError],
  providers: [AutorizacionStore],
  template: `
    <h1 tabindex="-1">Autorización de tratamiento de datos</h1>
    @if (store.error(); as error) {
      <app-estado-error
        [mensaje]="error.mensaje"
        rutaSalida="/"
        etiquetaSalida="Ir al sitio público"
        (reintentar)="store.recargar()"
      />
    } @else if (store.autorizacion(); as autorizacion) {
      <p>Para usar el panel necesitamos tu autorización para tratar tus datos como miembro del equipo:</p>
      <p class="resumen" data-testid="autorizacion-resumen">{{ autorizacion.resumenFinalidad }}</p>
      <p>
        <a
          [href]="autorizacion.urlPolitica"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="autorizacion-politica"
          >Leer la política completa (versión {{ autorizacion.versionPolitica }})
          <span class="bs-solo-lectores">(se abre en una pestaña nueva)</span></a
        >
      </p>
      @if (errorDecision(); as mensaje) {
        <app-banner variante="error" testId="autorizacion-error">{{ mensaje }}</app-banner>
      }
      <div class="decision">
        <button
          type="button"
          appBoton
          [cargando]="store.enviando() === 'AUTORIZO'"
          [deshabilitadoEnfocable]="!enLinea()"
          data-testid="autorizacion-autorizo"
          (click)="decidir('AUTORIZO')"
        >
          {{ store.enviando() === 'AUTORIZO' ? 'Registrando…' : 'Autorizo' }}
        </button>
        <button
          type="button"
          appBoton
          variante="secondary"
          [deshabilitadoEnfocable]="!enLinea()"
          data-testid="autorizacion-no-autorizo"
          (click)="abrirConfirmacion()"
        >
          No autorizo
        </button>
      </div>
      @if (!enLinea()) {
        <p class="ayuda">Sin conexión: podrás decidir cuando vuelva.</p>
      }
    } @else {
      <app-estado-cargando etiqueta="Cargando la política de tratamiento…" />
    }

    <dialog
      #confirmacion
      class="dialogo"
      role="alertdialog"
      aria-labelledby="no-autorizo-titulo"
      aria-describedby="no-autorizo-texto"
      data-testid="autorizacion-confirmacion"
      (cancel)="cerrarConfirmacion()"
    >
      <div class="dialogo-cuerpo">
        <h2 id="no-autorizo-titulo">¿No autorizas el tratamiento?</h2>
        <p id="no-autorizo-texto">Si no autorizas, se cerrará tu sesión y no podrás usar el panel.</p>
        <div class="acciones">
          <button
            type="button"
            appBoton
            variante="danger"
            [cargando]="store.enviando() === 'NO_AUTORIZO'"
            data-testid="autorizacion-confirmar-no-autorizo"
            (click)="decidir('NO_AUTORIZO')"
          >
            No autorizo y salir
          </button>
          <button
            type="button"
            appBoton
            variante="secondary"
            autofocus
            data-testid="autorizacion-volver"
            (click)="cerrarConfirmacion()"
          >
            Volver
          </button>
        </div>
      </div>
    </dialog>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    :host {
      display: grid;
      gap: var(--bs-space-4);
    }
    h1 {
      font-size: var(--bs-typography-h2-font-size);
      line-height: var(--bs-typography-h2-line-height);
      outline: none;
    }
    .resumen {
      white-space: pre-line;
      padding: var(--bs-space-4);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-sunken);
    }
    .decision {
      display: grid;
      gap: var(--bs-space-3);
    }
    @media (min-width: 30rem) {
      .decision {
        display: flex;
        flex-wrap: wrap;
      }
    }
  `,
})
export class PaginaAutorizacion {
  protected readonly store = inject(AutorizacionStore);
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);
  private readonly confirmacion = viewChild.required<ElementRef<HTMLDialogElement>>('confirmacion');

  protected readonly enLinea = inject(Conectividad).enLinea;
  protected readonly errorDecision = signal<string | null>(null);

  constructor() {
    inject(Seo).establecer({ titulo: 'Autorización de tratamiento de datos', indexable: false });
  }

  protected abrirConfirmacion(): void {
    if (!this.enLinea()) return;
    this.confirmacion().nativeElement.showModal();
  }

  protected cerrarConfirmacion(): void {
    this.confirmacion().nativeElement.close();
  }

  protected async decidir(decision: DecisionAutorizacion): Promise<void> {
    if (this.store.enviando() !== null || !this.enLinea()) return;
    this.errorDecision.set(null);
    const error = await this.store.decidir(decision);
    if (decision === 'NO_AUTORIZO') this.cerrarConfirmacion();
    if (error !== null) {
      this.errorDecision.set(error.mensaje);
      return;
    }
    if (decision === 'NO_AUTORIZO') {
      await this.router.navigate([RUTA_ACCESO_PANEL], { queryParams: { motivo: 'cerrada' } });
      return;
    }
    await this.router.navigateByUrl(this.sesion.rutaSiguiente());
  }
}
