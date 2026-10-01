import { Component, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { RUTA_ACCESO_PANEL } from '../../../core/auth/destino-seguro';
import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';
import {
  MENSAJE_CODIGO_FORMATO,
  esCodigoVerificacionValido,
  mensajeFalloAcceso,
  normalizarCodigoMfa,
} from '../domain/acceso';
import { SesionPanelStore } from '../state/sesion-panel.store';

/**
 * SCR-031 Verificación en dos pasos (FEAT-030, FLOW-010). Acepta el código TOTP o un código de
 * recuperación; un código inválido cuenta como intento fallido (sin revelar más). «Volver» cierra
 * el intento (cierra la sesión parcial).
 */
@Component({
  selector: 'app-pagina-verificacion-mfa',
  imports: [ReactiveFormsModule, Boton],
  template: `
    <h1 tabindex="-1">Verificación en dos pasos</h1>
    <form class="formulario" novalidate (submit)="verificar($event)">
      <div class="campo">
        <label for="mfa-codigo">{{ etiqueta() }} <span class="obligatorio">(obligatorio)</span></label>
        <p class="ayuda" id="mfa-codigo-ayuda">{{ ayuda() }}</p>
        <input
          id="mfa-codigo"
          class="entrada-texto entrada-codigo"
          type="text"
          [formControl]="codigo"
          [attr.inputmode]="recuperacion() ? 'text' : 'numeric'"
          [attr.autocomplete]="recuperacion() ? 'off' : 'one-time-code'"
          [attr.maxlength]="recuperacion() ? 9 : 6"
          autocapitalize="characters"
          spellcheck="false"
          [readOnly]="enviando()"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="error() ? 'mfa-codigo-ayuda mfa-codigo-error' : 'mfa-codigo-ayuda'"
          data-testid="mfa-codigo"
        />
        @if (error(); as mensaje) {
          <p class="error-campo" id="mfa-codigo-error" role="alert" data-testid="mfa-codigo-error">
            {{ mensaje }}
          </p>
        }
      </div>
      <button
        type="submit"
        appBoton
        class="ancho-completo"
        [cargando]="enviando()"
        [deshabilitadoEnfocable]="!enLinea()"
        data-testid="mfa-verificar"
      >
        {{ enviando() ? 'Verificando…' : 'Verificar' }}
      </button>
      @if (!enLinea()) {
        <p class="ayuda">Sin conexión: podrás verificar cuando vuelva.</p>
      }
    </form>
    <div class="acciones">
      <button
        type="button"
        class="boton-enlace"
        data-testid="mfa-alternar-recuperacion"
        (click)="alternarRecuperacion()"
      >
        {{ recuperacion() ? 'Usar el código de la aplicación' : 'Usar un código de recuperación' }}
      </button>
      <button
        type="button"
        appBoton
        variante="ghost"
        [cargando]="volviendo()"
        data-testid="mfa-volver"
        (click)="volver()"
      >
        Volver
      </button>
    </div>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    :host {
      display: grid;
      gap: var(--bs-space-5);
    }
    h1 {
      font-size: var(--bs-typography-h2-font-size);
      line-height: var(--bs-typography-h2-line-height);
      outline: none;
    }
    .acciones {
      justify-content: space-between;
    }
  `,
})
export class PaginaVerificacionMfa {
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);

  protected readonly codigo = new FormControl('', { nonNullable: true });
  protected readonly recuperacion = signal(false);
  protected readonly enviando = signal(false);
  protected readonly volviendo = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly enLinea = inject(Conectividad).enLinea;
  protected readonly etiqueta = computed(() =>
    this.recuperacion() ? 'Código de recuperación' : 'Código de verificación',
  );
  protected readonly ayuda = computed(() =>
    this.recuperacion()
      ? 'Escribe uno de tus códigos de recuperación (formato XXXX-XXXX). Cada código sirve una sola vez.'
      : 'Escribe el código de 6 dígitos de tu aplicación autenticadora.',
  );

  constructor() {
    inject(Seo).establecer({ titulo: 'Verificación en dos pasos', indexable: false });
  }

  protected alternarRecuperacion(): void {
    this.recuperacion.update((v) => !v);
    this.codigo.setValue('');
    this.error.set(null);
  }

  protected async verificar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando() || !this.enLinea()) return;
    const codigo = normalizarCodigoMfa(this.codigo.value);
    if (!esCodigoVerificacionValido(codigo)) {
      this.error.set(MENSAJE_CODIGO_FORMATO);
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    const error = await this.sesion.verificarMfa(codigo);
    this.enviando.set(false);
    if (error !== null) {
      this.codigo.setValue('');
      this.error.set(mensajeFalloAcceso(error));
      return;
    }
    await this.router.navigateByUrl(this.sesion.rutaSiguiente());
  }

  protected async volver(): Promise<void> {
    this.volviendo.set(true);
    await this.sesion.cerrarSesion();
    this.volviendo.set(false);
    await this.router.navigate([RUTA_ACCESO_PANEL]);
  }
}
