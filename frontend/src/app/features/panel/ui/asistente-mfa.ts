import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, computed, inject, output, signal, viewChild } from '@angular/core';

import { aErroresDeCampo } from '../../../core/forms/errores-de-campo';
import { ErrorApi } from '../../../core/http/error-api.model';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import {
  MENSAJE_CODIGO_FORMATO,
  MENSAJE_TOTP_FORMATO,
  agruparClave,
  esCodigoTotpValido,
  esCodigoVerificacionValido,
  esReautenticacionFallida,
  mensajeFalloAcceso,
  normalizarCodigoMfa,
} from '../domain/acceso';
import { CuentaStore } from '../state/cuenta.store';
import { CampoContrasena } from './campo-contrasena';
import { CodigoQr } from './codigo-qr';
import { EnlaceValor } from './enlace-valor';

const MENSAJE_CONTRASENA_INCORRECTA = 'La contraseña no es correcta.';
const MENSAJE_CONTRASENA_VACIA = 'Escribe tu contraseña actual.';

/**
 * Sección «Verificación en dos pasos» de SCR-032 (FEAT-030, DEC-AUTO-037/215): activar con
 * reautenticación + asistente de 3 pasos (QR/clave → confirmar → códigos de recuperación),
 * desactivar (no disponible para el Administrador) y regenerar códigos.
 */
@Component({
  selector: 'app-asistente-mfa',
  imports: [EnlaceValor, Banner, Boton, CampoContrasena, CodigoQr],
  template: `
    <section class="seccion" aria-labelledby="mfa-titulo" data-testid="cuenta-mfa">
      <h2 id="mfa-titulo">Verificación en dos pasos</h2>

      @if (store.codigos(); as codigos) {
        <div class="secreto" data-testid="mfa-codigos">
          @if (store.numeroPasoMfa(); as numero) {
            <p class="paso">Paso {{ numero }} de 3</p>
          }
          <h3>Tus códigos de recuperación</h3>
          <p>
            Se muestran solo esta vez. Guárdalos fuera del sistema: cada código te deja entrar una vez si
            no tienes tu aplicación a mano.
          </p>
          <ul class="lista-codigos mono" data-testid="mfa-lista-codigos">
            @for (codigo of codigos; track codigo) {
              <li>{{ codigo }}</li>
            }
          </ul>
          <div class="acciones">
            <button type="button" appBoton variante="secondary" (click)="copiar(codigos.join('\\n'))">
              Copiar
            </button>
            <button type="button" appBoton variante="secondary" (click)="descargar(codigos)">
              Descargar .txt
            </button>
            <button type="button" appBoton data-testid="mfa-codigos-guardados" (click)="terminar()">
              Ya los guardé
            </button>
          </div>
          <p class="ayuda" role="status">{{ copiado() ? 'Copiado al portapapeles.' : '' }}</p>
        </div>
      } @else {
        @switch (store.pasoMfa()) {
          @case ('reautenticar') {
            <form class="formulario" novalidate (submit)="reautenticar($event)">
              <p>Por seguridad, confirma tu contraseña antes de vincular una aplicación autenticadora.</p>
              <app-campo-contrasena
                [campo]="contrasenaReautenticacion"
                etiqueta="Tu contraseña actual"
                idCampo="mfa-reautenticacion"
                autocomplete="current-password"
                [error]="errorCampo()['contrasena'] ?? null"
                testId="mfa-reautenticacion"
              />
              <div class="acciones">
                <button type="submit" appBoton [cargando]="enviando()" data-testid="mfa-reautenticar">
                  {{ enviando() ? 'Comprobando…' : 'Continuar' }}
                </button>
                <button type="button" appBoton variante="ghost" (click)="cancelar()">Cancelar</button>
              </div>
            </form>
          }
          @case ('escanear') {
            @if (store.activacion(); as activacion) {
              <div class="asistente" data-testid="mfa-paso-escanear">
                <p class="paso">Paso 1 de 3</p>
                <p>Escanea este código con tu aplicación autenticadora o escribe la clave manualmente.</p>
                <app-codigo-qr [contenido]="activacion.otpauthUri" />
                <p class="etiqueta-campo" id="mfa-clave-etiqueta">Clave para escribir a mano</p>
                <p class="clave mono" aria-labelledby="mfa-clave-etiqueta" data-testid="mfa-clave">
                  {{ claveAgrupada() }}
                </p>
                <div class="acciones">
                  <button type="button" appBoton variante="secondary" (click)="copiar(activacion.claveSecreta)">
                    Copiar clave
                  </button>
                  <button type="button" appBoton data-testid="mfa-continuar" (click)="store.continuarAConfirmacion()">
                    Continuar
                  </button>
                  <button type="button" appBoton variante="ghost" (click)="cancelar()">Cancelar</button>
                </div>
                <p class="ayuda" role="status">{{ copiado() ? 'Copiado al portapapeles.' : '' }}</p>
              </div>
            }
          }
          @case ('confirmar') {
            <form class="formulario" novalidate (submit)="confirmar($event)" data-testid="mfa-paso-confirmar">
              <p class="paso">Paso 2 de 3</p>
              <div class="campo">
                <label for="mfa-confirmar-codigo"
                  >Código de la aplicación <span class="obligatorio">(obligatorio)</span></label
                >
                <p class="ayuda" id="mfa-confirmar-ayuda">Escribe los 6 dígitos que muestra tu aplicación.</p>
                <input
                  id="mfa-confirmar-codigo"
                  class="entrada-texto entrada-codigo"
                  type="text"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  [appEnlaceValor]="codigoConfirmacion"
                  [attr.aria-invalid]="errorCampo()['codigo'] ? 'true' : null"
                  [attr.aria-describedby]="errorCampo()['codigo'] ? 'mfa-confirmar-ayuda mfa-confirmar-error' : 'mfa-confirmar-ayuda'"
                  data-testid="mfa-confirmar-codigo"
                />
                @if (errorCampo()['codigo']; as mensaje) {
                  <p class="error-campo" id="mfa-confirmar-error" data-testid="mfa-confirmar-error">{{ mensaje }}</p>
                }
              </div>
              <div class="acciones">
                <button type="submit" appBoton [cargando]="enviando()" data-testid="mfa-activar">
                  {{ enviando() ? 'Activando…' : 'Activar' }}
                </button>
                <button type="button" appBoton variante="ghost" (click)="store.volverAEscanear()">Volver</button>
              </div>
            </form>
          }
          @default {
            @if (store.mfaDesactivado()) {
              <app-banner variante="success" testId="mfa-desactivado">Desactivaste la verificación en dos pasos.</app-banner>
            }
            @if (store.mfaActivo()) {
              <p data-testid="mfa-estado">Estado: <strong>activada</strong>.</p>
              <form class="formulario" novalidate (submit)="regenerar($event)">
                <div class="campo">
                  <label for="mfa-regenerar-codigo">Código de la aplicación para regenerar los códigos de recuperación</label>
                  <input
                    id="mfa-regenerar-codigo"
                    class="entrada-texto entrada-codigo"
                    type="text"
                    inputmode="numeric"
                    autocomplete="one-time-code"
                    maxlength="6"
                    [appEnlaceValor]="codigoRegeneracion"
                    [attr.aria-invalid]="errorCampo()['regenerar'] ? 'true' : null"
                    [attr.aria-describedby]="errorCampo()['regenerar'] ? 'mfa-regenerar-error' : null"
                    data-testid="mfa-regenerar-codigo"
                  />
                  @if (errorCampo()['regenerar']; as mensaje) {
                    <p class="error-campo" id="mfa-regenerar-error">{{ mensaje }}</p>
                  }
                </div>
                <div class="acciones">
                  <button type="submit" appBoton variante="secondary" [cargando]="enviando()" data-testid="mfa-regenerar">
                    Regenerar códigos de recuperación
                  </button>
                </div>
              </form>
              @if (store.puedeDesactivarMfa()) {
                <div class="acciones">
                  <button type="button" appBoton variante="danger" data-testid="mfa-desactivar" (click)="abrirDesactivar()">
                    Desactivar
                  </button>
                </div>
              } @else {
                <p class="ayuda" data-testid="mfa-obligatorio">
                  Como administrador, la verificación en dos pasos es obligatoria y no se puede desactivar.
                </p>
              }
            } @else {
              <p data-testid="mfa-estado">Estado: <strong>desactivada</strong>.</p>
              <p>Añade un segundo factor con una aplicación autenticadora (TOTP) para proteger tu cuenta.</p>
              <div class="acciones">
                <button type="button" appBoton data-testid="mfa-empezar" (click)="empezar()">
                  Activar verificación en dos pasos
                </button>
              </div>
            }
          }
        }
      }

      <dialog
        #dialogoDesactivar
        class="dialogo"
        role="alertdialog"
        aria-labelledby="mfa-desactivar-titulo"
        aria-describedby="mfa-desactivar-texto"
        data-testid="mfa-dialogo-desactivar"
        (cancel)="cerrarDesactivar()"
      >
        <form class="dialogo-cuerpo" novalidate (submit)="desactivar($event)">
          <h3 id="mfa-desactivar-titulo">Desactivar la verificación en dos pasos</h3>
          <p id="mfa-desactivar-texto">Tu cuenta quedará protegida solo con la contraseña.</p>
          <app-campo-contrasena
            [campo]="contrasenaDesactivar"
            etiqueta="Tu contraseña actual"
            idCampo="mfa-desactivar-contrasena"
            [error]="errorCampo()['contrasena_desactivar'] ?? null"
            testId="mfa-desactivar-contrasena"
          />
          <div class="campo">
            <label for="mfa-desactivar-codigo"
              >Código de la aplicación o de recuperación <span class="obligatorio">(obligatorio)</span></label
            >
            <input
              id="mfa-desactivar-codigo"
              class="entrada-texto entrada-codigo"
              type="text"
              autocomplete="one-time-code"
              maxlength="9"
              [appEnlaceValor]="codigoDesactivar"
              [attr.aria-invalid]="errorCampo()['codigo_desactivar'] ? 'true' : null"
              [attr.aria-describedby]="errorCampo()['codigo_desactivar'] ? 'mfa-desactivar-codigo-error' : null"
              data-testid="mfa-desactivar-codigo"
            />
            @if (errorCampo()['codigo_desactivar']; as mensaje) {
              <p class="error-campo" id="mfa-desactivar-codigo-error">{{ mensaje }}</p>
            }
          </div>
          @if (errorGeneral(); as mensaje) {
            <p class="error-campo" role="alert">{{ mensaje }}</p>
          }
          <div class="acciones">
            <button type="submit" appBoton variante="danger" [cargando]="enviando()" data-testid="mfa-confirmar-desactivar">
              Desactivar
            </button>
            <button type="button" appBoton variante="secondary" autofocus (click)="cerrarDesactivar()">Cancelar</button>
          </div>
        </form>
      </dialog>

      @if (errorGeneral() && !dialogoAbierto()) {
        <app-banner variante="error" testId="mfa-error">{{ errorGeneral() }}</app-banner>
      }
    </section>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .paso {
      font-weight: var(--bs-font-weight-semibold);
      color: var(--bs-color-text-muted);
    }
    .asistente,
    .secreto {
      display: grid;
      gap: var(--bs-space-3);
      justify-items: start;
    }
    .secreto {
      padding: var(--bs-space-4);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-status-warning-bg);
    }
    .clave {
      font-size: var(--bs-typography-body-lg-font-size);
    }
    .lista-codigos {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr));
      gap: var(--bs-space-2);
      width: 100%;
      margin: 0;
      padding: 0;
      list-style: none;
    }
  `,
})
export class AsistenteMfa {
  protected readonly store = inject(CuentaStore);
  private readonly documento = inject(DOCUMENT);
  private readonly dialogoDesactivar =
    viewChild.required<ElementRef<HTMLDialogElement>>('dialogoDesactivar');

  /** Los códigos se confirmaron como guardados (en modo obligatorio, la página continúa). */
  readonly codigosGuardados = output<void>();

  protected readonly contrasenaReautenticacion = signal('');
  protected readonly codigoConfirmacion = signal('');
  protected readonly codigoRegeneracion = signal('');
  protected readonly contrasenaDesactivar = signal('');
  protected readonly codigoDesactivar = signal('');

  protected readonly enviando = signal(false);
  protected readonly copiado = signal(false);
  protected readonly dialogoAbierto = signal(false);
  protected readonly errorCampo = signal<Readonly<Record<string, string>>>({});
  protected readonly errorGeneral = signal<string | null>(null);
  protected readonly claveAgrupada = computed(() =>
    agruparClave(this.store.activacion()?.claveSecreta ?? ''),
  );

  protected empezar(): void {
    this.limpiarErrores();
    this.contrasenaReautenticacion.set('');
    this.store.empezarActivacionMfa();
  }

  protected cancelar(): void {
    this.limpiarErrores();
    this.store.cancelarActivacionMfa();
  }

  /** DEC-AUTO-215: un 401 credenciales_invalidas es un error del campo, no una expulsión. */
  protected async reautenticar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) return;
    const contrasena = this.contrasenaReautenticacion();
    this.limpiarErrores();
    if (contrasena === '') {
      this.errorCampo.set({ contrasena: MENSAJE_CONTRASENA_VACIA });
      return;
    }
    const error = await this.conEnvio(() => this.store.iniciarActivacionMfa(contrasena));
    if (error === null) return;
    this.contrasenaReautenticacion.set('');
    if (esReautenticacionFallida(error)) {
      this.errorCampo.set({ contrasena: MENSAJE_CONTRASENA_INCORRECTA });
      return;
    }
    if (error.categoria === 'limite_tasa') {
      this.errorCampo.set({ contrasena: mensajeFalloAcceso(error) });
      return;
    }
    this.aplicarError(error, ['contrasena']);
  }

  protected async confirmar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) return;
    const codigo = normalizarCodigoMfa(this.codigoConfirmacion());
    this.limpiarErrores();
    if (!esCodigoTotpValido(codigo)) {
      this.errorCampo.set({ codigo: MENSAJE_TOTP_FORMATO });
      return;
    }
    const error = await this.conEnvio(() => this.store.confirmarActivacionMfa(codigo));
    this.codigoConfirmacion.set('');
    if (error !== null) this.aplicarError(error, ['codigo']);
  }

  protected async regenerar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) return;
    const codigo = normalizarCodigoMfa(this.codigoRegeneracion());
    this.limpiarErrores();
    if (!esCodigoTotpValido(codigo)) {
      this.errorCampo.set({ regenerar: MENSAJE_TOTP_FORMATO });
      return;
    }
    const error = await this.conEnvio(() => this.store.regenerarCodigos(codigo));
    this.codigoRegeneracion.set('');
    if (error !== null) {
      const { porCampo, generales } = aErroresDeCampo(error, ['codigo']);
      this.errorCampo.set({ regenerar: porCampo['codigo']?.[0] ?? generales[0] });
    }
  }

  protected abrirDesactivar(): void {
    this.limpiarErrores();
    this.contrasenaDesactivar.set('');
    this.codigoDesactivar.set('');
    this.dialogoDesactivar().nativeElement.showModal();
    this.dialogoAbierto.set(true);
  }

  protected cerrarDesactivar(): void {
    this.dialogoDesactivar().nativeElement.close();
    this.dialogoAbierto.set(false);
  }

  protected async desactivar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) return;
    const contrasena = this.contrasenaDesactivar();
    const codigo = normalizarCodigoMfa(this.codigoDesactivar());
    this.limpiarErrores();
    const errores: Record<string, string> = {};
    if (contrasena === '') errores['contrasena_desactivar'] = MENSAJE_CONTRASENA_VACIA;
    if (!esCodigoVerificacionValido(codigo)) errores['codigo_desactivar'] = MENSAJE_CODIGO_FORMATO;
    if (Object.keys(errores).length > 0) {
      this.errorCampo.set(errores);
      return;
    }
    const error = await this.conEnvio(() => this.store.desactivarMfa(contrasena, codigo));
    if (error === null) {
      this.cerrarDesactivar();
      return;
    }
    const { porCampo, generales } = aErroresDeCampo(error, ['contrasena', 'codigo']);
    this.errorCampo.set({
      ...(porCampo['contrasena'] ? { contrasena_desactivar: porCampo['contrasena'][0] } : {}),
      ...(porCampo['codigo'] ? { codigo_desactivar: porCampo['codigo'][0] } : {}),
    });
    this.errorGeneral.set(generales[0] ?? null);
  }

  protected terminar(): void {
    this.store.terminarCodigos();
    this.codigosGuardados.emit();
  }

  protected async copiar(texto: string): Promise<void> {
    try {
      await this.documento.defaultView?.navigator.clipboard.writeText(texto);
      this.copiado.set(true);
    } catch {
      this.copiado.set(false);
    }
  }

  /** «Descargar .txt» generado en el navegador (OneTimeSecret, sin pasar por el servidor). */
  protected descargar(codigos: readonly string[]): void {
    const ventana = this.documento.defaultView;
    if (!ventana) return;
    const contenido = `Códigos de recuperación de Brújula Salvaje (cada uno sirve una vez):\n${codigos.join('\n')}\n`;
    const url = ventana.URL.createObjectURL(new Blob([contenido], { type: 'text/plain' }));
    const enlace = this.documento.createElement('a');
    enlace.href = url;
    enlace.download = 'codigos-recuperacion-brujula-salvaje.txt';
    enlace.click();
    ventana.URL.revokeObjectURL(url);
  }

  private async conEnvio(comando: () => Promise<ErrorApi | null>): Promise<ErrorApi | null> {
    this.enviando.set(true);
    const error = await comando();
    this.enviando.set(false);
    return error;
  }

  private aplicarError(error: ErrorApi, campos: readonly string[]): void {
    const { porCampo, generales } = aErroresDeCampo(error, campos);
    const errores: Record<string, string> = {};
    for (const campo of campos) {
      const mensaje = porCampo[campo]?.[0];
      if (mensaje) errores[campo] = mensaje;
    }
    this.errorCampo.set(errores);
    this.errorGeneral.set(generales[0] ?? null);
  }

  private limpiarErrores(): void {
    this.errorCampo.set({});
    this.errorGeneral.set(null);
    this.copiado.set(false);
  }
}
