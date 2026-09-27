import { Component, ElementRef, computed, inject, input, signal, viewChild } from '@angular/core';
import { Router } from '@angular/router';

import { Icono } from '../icono/icono';
import { validarConsulta } from './validar-consulta';

export type VarianteBusqueda = 'cabecera' | 'grande' | 'resultados' | 'pagina-error';

/** Ruta pública de resultados (SCR-017, sitemap §10). */
export const RUTA_BUSCAR = '/buscar';

/**
 * SearchField (HANDOFF_UI_UX): form role=search con method GET a /buscar (funciona sin JS);
 * con JS valida al enviar (2..100 caracteres) y muestra el mensaje en línea sin navegar
 * (AC-020, ALT-006). Sin autocompletado (DEC-AUTO-048).
 */
@Component({
  selector: 'app-campo-busqueda',
  imports: [Icono],
  template: `
    <form
      role="search"
      method="get"
      [attr.action]="rutaBuscar"
      class="busqueda"
      [attr.data-variante]="variante()"
      [attr.data-testid]="testId()"
      (submit)="enviar($event)"
      novalidate
    >
      <label class="etiqueta" [class.bs-solo-lectores]="etiquetaOculta()" [for]="idCampo()">{{
        etiqueta()
      }}</label>
      <div class="fila">
        <input
          #campo
          [id]="idCampo()"
          name="q"
          type="search"
          enterkeyhint="search"
          autocomplete="off"
          [value]="valorInicial()"
          [attr.placeholder]="placeholder()"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="error() ? idError() : null"
          data-testid="campo-busqueda-entrada"
          (input)="limpiarError()"
        />
        <button type="submit" class="enviar" data-testid="campo-busqueda-enviar">
          <app-icono nombre="search" [tamano]="20" />
          <span [class.bs-solo-lectores]="soloIcono()">Buscar</span>
        </button>
      </div>
      @if (error(); as mensaje) {
        <p class="error" [id]="idError()" data-testid="campo-busqueda-error">{{ mensaje }}</p>
      }
    </form>
  `,
  styles: `
    .busqueda {
      display: grid;
      gap: var(--bs-space-2);
      width: 100%;
    }
    .etiqueta {
      font-family: var(--bs-typography-label-font-family);
      font-size: var(--bs-typography-label-font-size);
      font-weight: var(--bs-typography-label-font-weight);
    }
    .fila {
      display: flex;
      align-items: stretch;
      min-height: var(--bs-size-control-md);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-radius: var(--bs-radius-pill);
      background: var(--bs-color-bg-surface);
      overflow: hidden;
    }
    .fila:focus-within {
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring);
      outline-offset: var(--bs-border-width-focus-offset);
    }
    [data-variante='grande'] .fila {
      min-height: var(--bs-size-control-lg);
    }
    input {
      flex: 1;
      min-width: 0;
      padding-inline: var(--bs-space-4);
      border: 0;
      background: transparent;
      color: var(--bs-color-text-default);
      font: inherit;
    }
    input:focus-visible {
      outline: none;
    }
    input::placeholder {
      color: var(--bs-color-text-muted);
    }
    input[aria-invalid='true'] + .enviar {
      border-inline-start: 2px solid var(--bs-color-status-error-fg);
    }
    .enviar {
      display: inline-flex;
      align-items: center;
      gap: var(--bs-space-2);
      min-width: var(--bs-size-target);
      padding-inline: var(--bs-space-4);
      border: 0;
      background: var(--bs-color-action-primary-bg);
      color: var(--bs-color-action-primary-fg);
      font: inherit;
      font-weight: var(--bs-font-weight-semibold);
      cursor: pointer;
    }
    .enviar:hover {
      background: var(--bs-color-action-primary-bg-hover);
    }
    .enviar:focus-visible {
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring-inner);
      outline-offset: -6px;
    }
    .error {
      color: var(--bs-color-status-error-fg);
      font-size: var(--bs-typography-body-sm-font-size);
    }
  `,
})
export class CampoBusqueda {
  readonly variante = input<VarianteBusqueda>('cabecera');
  readonly etiqueta = input('Buscar destinos, itinerarios y guías');
  readonly etiquetaOculta = input(true);
  readonly placeholder = input('Ej.: Patagonia, buceo, altitud');
  readonly valorInicial = input('');
  readonly soloIcono = input(true);
  readonly idCampo = input('busqueda');
  readonly testId = input('campo-busqueda');

  protected readonly rutaBuscar = RUTA_BUSCAR;
  private readonly router = inject(Router);
  private readonly campo = viewChild.required<ElementRef<HTMLInputElement>>('campo');
  private readonly _error = signal<string | null>(null);
  protected readonly error = this._error.asReadonly();
  protected readonly idError = computed(() => `${this.idCampo()}-error`);

  protected enviar(evento: Event): void {
    evento.preventDefault();
    const resultado = validarConsulta(this.campo().nativeElement.value);
    if (!resultado.valida) {
      this._error.set(resultado.mensaje);
      this.campo().nativeElement.focus();
      return;
    }
    this._error.set(null);
    void this.router.navigate([RUTA_BUSCAR], { queryParams: { q: resultado.consulta } });
  }

  protected limpiarError(): void {
    if (this._error() !== null) this._error.set(null);
  }

  /** Enfoca el campo (p. ej. al abrir la búsqueda desplegable de la cabecera). */
  enfocar(): void {
    this.campo().nativeElement.focus();
  }
}
