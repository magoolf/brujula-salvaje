import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { aErroresDeCampo } from '../../../core/forms/errores-de-campo';
import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { RUTA_CUENTA } from '../domain/acceso';
import { CampoCambioContrasena } from '../domain/contrasena';
import { AutorizacionStore } from '../state/autorizacion.store';
import { CuentaStore } from '../state/cuenta.store';
import { AsistenteMfa } from './asistente-mfa';
import { CampoContrasena } from './campo-contrasena';

const CAMPOS_CONTRASENA: readonly CampoCambioContrasena[] = [
  'contrasena_actual',
  'contrasena_nueva',
  'confirmacion',
];

/**
 * SCR-032 Mi cuenta (FEAT-030/031, RULE-017). Modo normal en el armazón del panel; modo obligatorio
 * (cambio de contraseña tras alta/restablecimiento, o MFA obligatorio del Administrador) en el
 * armazón de acceso, sin navegación, hasta completarlo (BLUEPRINT SCR-032).
 */
@Component({
  selector: 'app-pagina-cuenta',
  imports: [ReactiveFormsModule, DatePipe, Banner, Boton, CampoContrasena, AsistenteMfa],
  providers: [CuentaStore, AutorizacionStore],
  template: `
    <div class="pagina" data-testid="pagina-cuenta">
      <h1 tabindex="-1">Mi cuenta</h1>
      @if (store.modoObligatorio()) {
        <app-banner variante="warning" testId="cuenta-obligatorio">
          {{
            store.mostrarContrasena()
              ? 'Debes cambiar tu contraseña temporal para continuar.'
              : 'Como administrador, debes activar la verificación en dos pasos para continuar.'
          }}
        </app-banner>
      }

      @if (store.mostrarContrasena()) {
        <section class="seccion" aria-labelledby="contrasena-titulo" data-testid="cuenta-contrasena">
          <h2 id="contrasena-titulo">Contraseña</h2>
          @if (store.contrasenaCambiada() && !store.modoObligatorio()) {
            <app-banner variante="success" testId="cuenta-contrasena-ok">Actualizaste tu contraseña.</app-banner>
          }
          @if (errorGeneral(); as mensaje) {
            <app-banner variante="error" testId="cuenta-contrasena-error">{{ mensaje }}</app-banner>
          }
          <form class="formulario" [formGroup]="formulario" novalidate (ngSubmit)="cambiarContrasena()">
            <app-campo-contrasena
              [control]="formulario.controls.actual"
              etiqueta="Contraseña actual"
              idCampo="cuenta-actual"
              autocomplete="current-password"
              [error]="errores()['contrasena_actual'] ?? null"
              testId="cuenta-actual"
            />
            <app-campo-contrasena
              [control]="formulario.controls.nueva"
              etiqueta="Nueva contraseña"
              idCampo="cuenta-nueva"
              autocomplete="new-password"
              ayuda="Al menos 12 caracteres. Evita contraseñas comunes o tu nombre de usuario. No hace falta combinar símbolos."
              [error]="errores()['contrasena_nueva'] ?? null"
              testId="cuenta-nueva"
            />
            <app-campo-contrasena
              [control]="formulario.controls.confirmacion"
              etiqueta="Repite la nueva contraseña"
              idCampo="cuenta-confirmacion"
              autocomplete="new-password"
              [error]="errores()['confirmacion'] ?? null"
              testId="cuenta-confirmacion"
            />
            <div class="acciones">
              <button
                type="submit"
                appBoton
                [cargando]="guardando()"
                [deshabilitadoEnfocable]="!enLinea()"
                data-testid="cuenta-guardar-contrasena"
              >
                {{ guardando() ? 'Guardando…' : 'Cambiar contraseña' }}
              </button>
              @if (!enLinea()) {
                <p class="ayuda">Sin conexión: podrás guardar cuando vuelva.</p>
              }
            </div>
          </form>
        </section>
      }

      @if (store.mostrarMfa()) {
        <app-asistente-mfa (codigosGuardados)="alGuardarCodigos()" />
      }

      @if (store.mostrarAutorizacion()) {
        <section class="seccion" aria-labelledby="autorizacion-titulo" data-testid="cuenta-autorizacion">
          <h2 id="autorizacion-titulo">Autorización de tratamiento de datos</h2>
          @if (autorizacion.autorizacion(); as datos) {
            @if (datos.otorgadaEn; as fecha) {
              <p>
                Autorizaste el tratamiento el {{ fecha | date: 'longDate' }} (versión
                {{ datos.versionOtorgada }} de la política).
              </p>
            }
            <p><a [href]="datos.urlPolitica">Leer la política de tratamiento de datos</a></p>
          } @else if (autorizacion.error()) {
            <p class="ayuda">No pudimos cargar los datos de tu autorización.</p>
          }
        </section>
      }
    </div>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .pagina {
      display: grid;
      gap: var(--bs-space-6);
      max-width: 40rem;
    }
    h1 {
      outline: none;
    }
  `,
})
export class PaginaCuenta {
  protected readonly store = inject(CuentaStore);
  protected readonly autorizacion = inject(AutorizacionStore);
  private readonly router = inject(Router);

  protected readonly enLinea = inject(Conectividad).enLinea;
  protected readonly formulario = new FormGroup({
    actual: new FormControl('', { nonNullable: true }),
    nueva: new FormControl('', { nonNullable: true }),
    confirmacion: new FormControl('', { nonNullable: true }),
  });
  protected readonly guardando = signal(false);
  protected readonly errores = signal<Partial<Record<CampoCambioContrasena, string>>>({});
  protected readonly errorGeneral = signal<string | null>(null);

  constructor() {
    inject(Seo).establecer({ titulo: 'Mi cuenta', indexable: false });
  }

  protected async cambiarContrasena(): Promise<void> {
    if (this.guardando() || !this.enLinea()) return;
    const { actual, nueva, confirmacion } = this.formulario.getRawValue();
    this.errorGeneral.set(null);
    const locales = this.store.validarContrasena({ actual, nueva, confirmacion });
    this.errores.set(locales);
    if (Object.keys(locales).length > 0) return;

    this.guardando.set(true);
    const error = await this.store.cambiarContrasena(actual, nueva);
    this.guardando.set(false);
    if (error !== null) {
      const { porCampo, generales } = aErroresDeCampo(error, CAMPOS_CONTRASENA);
      this.errores.set({
        contrasena_actual: porCampo['contrasena_actual']?.[0],
        contrasena_nueva: porCampo['contrasena_nueva']?.[0],
      });
      this.errorGeneral.set(generales[0] ?? null);
      return;
    }
    this.formulario.reset();
    await this.continuarSiObligatorio();
  }

  protected async alGuardarCodigos(): Promise<void> {
    await this.continuarSiObligatorio();
  }

  /** En modo obligatorio continúa el FLOW-010 (SCR-033 o destino); si el siguiente paso también es
   * de esta pantalla (Administrador sin MFA tras cambiar la contraseña), cambia de sección. */
  private async continuarSiObligatorio(): Promise<void> {
    if (!this.store.modoObligatorio()) return;
    const siguiente = this.store.rutaSiguiente();
    if (siguiente === RUTA_CUENTA) {
      this.store.refrescarModo();
      return;
    }
    await this.router.navigateByUrl(siguiente);
  }
}
