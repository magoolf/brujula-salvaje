import { Component, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { esDestinoSeguro } from '../../../core/auth/destino-seguro';
import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { MENSAJE_MOTIVO, mensajeFalloAcceso, motivoAcceso } from '../domain/acceso';
import { SesionPanelStore } from '../state/sesion-panel.store';
import { CampoContrasena } from './campo-contrasena';

const MENSAJE_USUARIO_VACIO = 'Escribe tu usuario.';
const MENSAJE_CONTRASENA_VACIA = 'Escribe tu contraseña.';

/**
 * SCR-030 Acceso (FEAT-029, FLOW-010, THREAT-001/018, AC-115). Mensaje de fallo genérico (nunca
 * dice si la cuenta existe), bloqueo con tiempo de espera, `?siguiente=` solo interno.
 */
@Component({
  selector: 'app-pagina-acceso',
  imports: [ReactiveFormsModule, Banner, Boton, CampoContrasena],
  template: `
    <h1 tabindex="-1">Acceso al panel editorial</h1>

    @if (mensajeMotivo(); as motivo) {
      <app-banner [variante]="motivo.variante" testId="acceso-motivo">{{ motivo.texto }}</app-banner>
    }
    <div #resumenError tabindex="-1" class="resumen">
      @if (errorAcceso(); as mensaje) {
        <app-banner variante="error" testId="acceso-error">{{ mensaje }}</app-banner>
      }
    </div>

    <form class="formulario" [formGroup]="formulario" novalidate (ngSubmit)="entrar()">
      <div class="campo">
        <label for="acceso-usuario">Usuario <span class="obligatorio">(obligatorio)</span></label>
        <input
          id="acceso-usuario"
          class="entrada-texto"
          type="text"
          formControlName="usuario"
          autocomplete="username"
          autocapitalize="off"
          spellcheck="false"
          [readOnly]="enviando()"
          [attr.aria-invalid]="errorUsuario() ? 'true' : null"
          [attr.aria-describedby]="errorUsuario() ? 'acceso-usuario-error' : null"
          data-testid="acceso-usuario"
        />
        @if (errorUsuario(); as mensaje) {
          <p class="error-campo" id="acceso-usuario-error">{{ mensaje }}</p>
        }
      </div>
      <app-campo-contrasena
        [control]="formulario.controls.contrasena"
        etiqueta="Contraseña"
        idCampo="acceso-contrasena"
        autocomplete="current-password"
        [error]="errorContrasena()"
        [soloLectura]="enviando()"
        testId="acceso-contrasena"
      />
      <button
        type="submit"
        appBoton
        class="ancho-completo"
        [cargando]="enviando()"
        [deshabilitadoEnfocable]="!enLinea()"
        [attr.aria-describedby]="enLinea() ? null : 'acceso-sin-conexion'"
        data-testid="acceso-entrar"
      >
        {{ enviando() ? 'Entrando…' : 'Entrar' }}
      </button>
      @if (!enLinea()) {
        <p class="ayuda" id="acceso-sin-conexion">Sin conexión: podrás entrar cuando vuelva.</p>
      }
    </form>
    <p class="ayuda">¿No puedes entrar? Pide a un administrador que restablezca tu contraseña.</p>
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
    .resumen {
      outline: none;
    }
    .resumen:empty {
      display: none;
    }
  `,
})
export class PaginaAcceso {
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly conectividad = inject(Conectividad);

  private readonly parametros = toSignal(this.ruta.queryParamMap, { requireSync: true });
  private readonly resumenError = viewChild.required<ElementRef<HTMLElement>>('resumenError');

  protected readonly formulario = new FormGroup({
    usuario: new FormControl('', { nonNullable: true }),
    contrasena: new FormControl('', { nonNullable: true }),
  });

  protected readonly enviando = signal(false);
  protected readonly errorAcceso = signal<string | null>(null);
  protected readonly errorUsuario = signal<string | null>(null);
  protected readonly errorContrasena = signal<string | null>(null);
  protected readonly enLinea = this.conectividad.enLinea;
  protected readonly mensajeMotivo = computed(() => {
    const motivo = motivoAcceso(this.parametros().get('motivo'));
    if (motivo === null || this.errorAcceso() !== null) return null;
    return { texto: MENSAJE_MOTIVO[motivo], variante: motivo === 'cerrada' ? 'success' : 'info' } as const;
  });

  constructor() {
    inject(Seo).establecer({ titulo: 'Acceso al panel editorial', indexable: false });
  }

  protected async entrar(): Promise<void> {
    if (this.enviando() || !this.enLinea()) return;
    const { usuario, contrasena } = this.formulario.getRawValue();
    this.errorUsuario.set(usuario.trim() === '' ? MENSAJE_USUARIO_VACIO : null);
    this.errorContrasena.set(contrasena === '' ? MENSAJE_CONTRASENA_VACIA : null);
    if (this.errorUsuario() !== null || this.errorContrasena() !== null) return;

    const siguiente = this.parametros().get('siguiente');
    this.enviando.set(true);
    this.errorAcceso.set(null);
    const error = await this.sesion.iniciarSesion(
      usuario.trim(),
      contrasena,
      esDestinoSeguro(siguiente) ? siguiente : null,
    );
    this.enviando.set(false);
    if (error !== null) {
      // THREAT-018: mensaje genérico; se vacía la contraseña y se conserva el usuario.
      this.formulario.controls.contrasena.setValue('');
      this.errorAcceso.set(mensajeFalloAcceso(error));
      queueMicrotask(() => this.resumenError().nativeElement.focus());
      return;
    }
    await this.router.navigateByUrl(this.sesion.rutaSiguiente());
  }
}
