import { Injectable, computed, inject, signal } from '@angular/core';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { esPasoDeCuentaObligatorio } from '../domain/acceso';
import {
  CambioContrasena,
  CampoCambioContrasena,
  validarCambioContrasena,
} from '../domain/contrasena';
import { ActivacionMfa } from '../domain/modelos';
import { SesionPanelStore } from './sesion-panel.store';

/** Pasos del asistente de activación de MFA (HANDOFF SCR-032: «Paso N de 3»). */
export type PasoActivacionMfa = 'reautenticar' | 'escanear' | 'confirmar' | 'codigos';

/**
 * STATE de Mi cuenta (SCR-032; FEAT-030/031, RULE-017, DEC-AUTO-215). Modo obligatorio cuando el
 * paso pendiente es CAMBIO_CREDENCIAL (solo contraseña) o CONFIGURAR_MFA (solo MFA del Administrador).
 */
@Injectable()
export class CuentaStore {
  private readonly repo = inject(PanelAuthRepositorio);
  private readonly sesionStore = inject(SesionPanelStore);

  private readonly _pasoMfa = signal<PasoActivacionMfa | null>(null);
  private readonly _activacion = signal<ActivacionMfa | null>(null);
  private readonly _codigos = signal<readonly string[] | null>(null);
  private readonly _contrasenaCambiada = signal(false);
  private readonly _mfaDesactivado = signal(false);

  /**
   * Modo con el que se entró en la pantalla. No sigue a la sesión en vivo: al completar el paso
   * obligatorio la sesión cambia, pero la pantalla debe seguir en su modo hasta que la persona
   * continúe (p. ej. para ver los códigos de recuperación una sola vez). `refrescarModo()` lo
   * actualiza cuando el siguiente paso obligatorio es otra sección de esta misma pantalla.
   */
  private readonly _pasoEntrada = signal(this.sesionStore.pasoPendiente());

  readonly sesion = this.sesionStore.sesion;
  readonly modoObligatorio = computed(() => {
    const paso = this._pasoEntrada();
    return paso !== null && esPasoDeCuentaObligatorio(paso);
  });
  readonly mostrarContrasena = computed(() => this._pasoEntrada() !== 'CONFIGURAR_MFA');
  readonly mostrarMfa = computed(() => this._pasoEntrada() !== 'CAMBIO_CREDENCIAL');
  readonly mostrarAutorizacion = computed(() => !this.modoObligatorio());
  readonly mfaActivo = computed(() => this.sesionStore.sesion()?.mfaActivo ?? false);
  /** DEC-AUTO-037: el Administrador no puede desactivar su MFA. */
  readonly puedeDesactivarMfa = computed(() => {
    const sesion = this.sesionStore.sesion();
    return sesion !== null && sesion.mfaActivo && !sesion.mfaObligatorio;
  });
  readonly pasoMfa = this._pasoMfa.asReadonly();
  readonly numeroPasoMfa = computed(() => {
    switch (this._pasoMfa()) {
      case 'escanear':
        return 1;
      case 'confirmar':
        return 2;
      case 'codigos':
        return 3;
      default:
        return null;
    }
  });
  readonly activacion = this._activacion.asReadonly();
  readonly codigos = this._codigos.asReadonly();
  readonly contrasenaCambiada = this._contrasenaCambiada.asReadonly();
  readonly mfaDesactivado = this._mfaDesactivado.asReadonly();
  /** Destino tras completar el modo obligatorio (SCR-033 o el destino final). */
  readonly rutaSiguiente = this.sesionStore.rutaSiguiente;

  /** El siguiente paso obligatorio sigue en esta pantalla (p. ej. contraseña → MFA del Admin). */
  refrescarModo(): void {
    this._pasoEntrada.set(this.sesionStore.pasoPendiente());
  }

  validarContrasena(datos: CambioContrasena): Partial<Record<CampoCambioContrasena, string>> {
    return validarCambioContrasena(datos);
  }

  async cambiarContrasena(actual: string, nueva: string): Promise<ErrorApi | null> {
    this._contrasenaCambiada.set(false);
    const error = await this.sesionStore.cambiarContrasena(actual, nueva);
    if (error === null) this._contrasenaCambiada.set(true);
    return error;
  }

  empezarActivacionMfa(): void {
    this._mfaDesactivado.set(false);
    this._codigos.set(null);
    this._pasoMfa.set('reautenticar');
  }

  cancelarActivacionMfa(): void {
    this._pasoMfa.set(null);
    this._activacion.set(null);
  }

  /**
   * Reautenticación con la contraseña (DEC-AUTO-215). Un 401 credenciales_invalidas vuelve como
   * error del campo; el interceptor global no lo trata como sesión expirada.
   */
  iniciarActivacionMfa(contrasena: string): Promise<ErrorApi | null> {
    return ejecutar(
      defer(() => this.repo.iniciarActivacionMfa(contrasena)),
      (activacion) => {
        this._activacion.set(activacion);
        this._pasoMfa.set('escanear');
      },
    );
  }

  continuarAConfirmacion(): void {
    if (this._activacion() !== null) this._pasoMfa.set('confirmar');
  }

  volverAEscanear(): void {
    if (this._activacion() !== null) this._pasoMfa.set('escanear');
  }

  async confirmarActivacionMfa(codigo: string): Promise<ErrorApi | null> {
    const error = await ejecutar(
      defer(() => this.repo.confirmarActivacionMfa(codigo)),
      (codigos) => {
        this._codigos.set(codigos);
        this._activacion.set(null);
        this._pasoMfa.set('codigos');
      },
    );
    // MFA activo y la sesión rotada: se relee para reflejar mfaActivo y el paso pendiente.
    if (error === null) await this.sesionStore.cargar();
    return error;
  }

  /** Cierra la vista de los códigos (se muestran una sola vez, OneTimeSecret). */
  terminarCodigos(): void {
    this._codigos.set(null);
    this._pasoMfa.set(null);
  }

  async desactivarMfa(contrasena: string, codigo: string): Promise<ErrorApi | null> {
    const error = await ejecutar(defer(() => this.repo.desactivarMfa(contrasena, codigo)));
    if (error === null) {
      this._mfaDesactivado.set(true);
      await this.sesionStore.cargar();
    }
    return error;
  }

  regenerarCodigos(codigo: string): Promise<ErrorApi | null> {
    return ejecutar(
      defer(() => this.repo.regenerarCodigos(codigo)),
      (codigos) => {
        this._codigos.set(codigos);
        this._pasoMfa.set(null);
      },
    );
  }
}
