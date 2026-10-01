import { Component, WritableSignal, computed, input, output } from '@angular/core';

import { EnlaceValor } from './enlace-valor';

export type TipoCampoTexto = 'text' | 'url' | 'textarea';

/**
 * FormField de texto del panel (HANDOFF_UI_UX FormField): etiqueta visible con «(obligatorio)»,
 * ayuda, contador de caracteres opcional y error vinculados con aria-describedby, aria-invalid al
 * fallar y `name` en el control. Emite `editado` en cada cambio para que el formulario borre el
 * error de ese campo (límite 3 de EnlaceValor, QA TKT-010 c2).
 */
@Component({
  selector: 'app-campo-texto',
  imports: [EnlaceValor],
  template: `
    <div class="campo">
      <label [for]="idCampo()">
        {{ etiqueta() }}
        @if (obligatorio()) {
          <span class="obligatorio">(obligatorio)</span>
        }
      </label>
      @if (ayuda(); as texto) {
        <p class="ayuda" [id]="idCampo() + '-ayuda'">{{ texto }}</p>
      }
      @if (tipo() === 'textarea') {
        <textarea
          class="entrada-texto"
          rows="3"
          [id]="idCampo()"
          [name]="nombre()"
          [appEnlaceValor]="campo()"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="descritoPor()"
          [attr.aria-required]="obligatorio() ? 'true' : null"
          [attr.data-testid]="testId()"
          (input)="editado.emit()"
        ></textarea>
      } @else {
        <input
          class="entrada-texto"
          [type]="tipo()"
          [id]="idCampo()"
          [name]="nombre()"
          [appEnlaceValor]="campo()"
          [attr.autocomplete]="autocomplete()"
          [attr.inputmode]="tipo() === 'url' ? 'url' : null"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="descritoPor()"
          [attr.aria-required]="obligatorio() ? 'true' : null"
          [attr.data-testid]="testId()"
          (input)="editado.emit()"
        />
      }
      @if (maximo(); as max) {
        <p class="ayuda contador" [id]="idCampo() + '-contador'" [class.excedido]="longitud() > max">
          {{ longitud() }} de {{ max }} caracteres
        </p>
      }
      @if (error(); as mensaje) {
        <p class="error-campo" [id]="idCampo() + '-error'" [attr.data-testid]="testId() + '-error'">{{ mensaje }}</p>
      }
    </div>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    textarea {
      resize: vertical;
    }
    .contador {
      font-variant-numeric: tabular-nums;
    }
    .excedido {
      color: var(--bs-color-status-error-fg);
      font-weight: var(--bs-font-weight-semibold);
    }
  `,
})
export class CampoTexto {
  readonly campo = input.required<WritableSignal<string>>();
  readonly etiqueta = input.required<string>();
  readonly idCampo = input.required<string>();
  /** `name` del control (por defecto, el id). */
  readonly nombreCampo = input<string | null>(null);
  readonly tipo = input<TipoCampoTexto>('text');
  readonly obligatorio = input(false);
  readonly maximo = input<number | null>(null);
  readonly ayuda = input<string | null>(null);
  readonly error = input<string | null>(null);
  readonly autocomplete = input<string>('off');
  readonly testId = input('campo-texto');
  readonly editado = output<void>();

  protected readonly nombre = computed(() => this.nombreCampo() ?? this.idCampo());
  protected readonly longitud = computed(() => [...this.campo()()].length);
  protected readonly descritoPor = computed(() => {
    const id = this.idCampo();
    const ids = [
      this.ayuda() ? `${id}-ayuda` : null,
      this.maximo() !== null ? `${id}-contador` : null,
      this.error() ? `${id}-error` : null,
    ].filter((v): v is string => v !== null);
    return ids.length > 0 ? ids.join(' ') : null;
  });
}
