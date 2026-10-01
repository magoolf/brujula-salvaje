import { Component, computed, input, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';

/**
 * FormField de contraseña con «Mostrar» (HANDOFF_UI_UX FormField password): etiqueta visible,
 * ayuda y error vinculados con aria-describedby, aria-invalid al fallar, autocomplete correcto y
 * pegado permitido (WCAG 3.3.8, gestores de contraseñas).
 */
@Component({
  selector: 'app-campo-contrasena',
  imports: [ReactiveFormsModule],
  template: `
    <div class="campo">
      <label [for]="idCampo()"
        >{{ etiqueta() }} <span class="obligatorio">(obligatorio)</span></label
      >
      @if (ayuda(); as textoAyuda) {
        <p class="ayuda" [id]="idCampo() + '-ayuda'">{{ textoAyuda }}</p>
      }
      <div class="entrada">
        <input
          class="entrada-texto"
          [id]="idCampo()"
          [type]="visible() ? 'text' : 'password'"
          [formControl]="control()"
          [attr.autocomplete]="autocomplete()"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="descritoPor()"
          [readOnly]="soloLectura()"
          [attr.data-testid]="testId()"
          spellcheck="false"
          autocapitalize="off"
        />
        <button
          type="button"
          class="mostrar"
          [attr.aria-pressed]="visible()"
          [attr.aria-controls]="idCampo()"
          [attr.data-testid]="testId() + '-mostrar'"
          (click)="alternar()"
        >
          Mostrar <span class="bs-solo-lectores">{{ etiqueta() }}</span>
        </button>
      </div>
      @if (error(); as mensaje) {
        <p class="error-campo" [id]="idCampo() + '-error'" [attr.data-testid]="testId() + '-error'">
          {{ mensaje }}
        </p>
      }
    </div>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .entrada {
      display: flex;
      gap: var(--bs-space-2);
      align-items: stretch;
    }
    .entrada input {
      flex: 1;
      min-width: 0;
    }
    .mostrar {
      flex: none;
      min-width: var(--bs-size-target);
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-3);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      font: inherit;
      cursor: pointer;
    }
    .mostrar[aria-pressed='true'] {
      background: var(--bs-color-action-selected-bg);
    }
  `,
})
export class CampoContrasena {
  readonly control = input.required<FormControl<string>>();
  readonly etiqueta = input.required<string>();
  readonly idCampo = input.required<string>();
  readonly autocomplete = input<'current-password' | 'new-password'>('current-password');
  readonly error = input<string | null>(null);
  readonly ayuda = input<string | null>(null);
  readonly soloLectura = input(false);
  readonly testId = input('campo-contrasena');

  protected readonly visible = signal(false);
  protected readonly descritoPor = computed(() => {
    const ids = [
      this.ayuda() ? `${this.idCampo()}-ayuda` : null,
      this.error() ? `${this.idCampo()}-error` : null,
    ].filter((id): id is string => id !== null);
    return ids.length > 0 ? ids.join(' ') : null;
  });

  protected alternar(): void {
    this.visible.update((v) => !v);
  }
}
