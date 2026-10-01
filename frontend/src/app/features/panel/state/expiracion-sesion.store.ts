import { DestroyRef, Injectable, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

import { ErrorApi } from '../../../core/http/error-api.model';
import {
  AVISO_EXPIRACION_SEGUNDOS,
  debeAvisarExpiracion,
  formatearCuentaAtras,
  segundosRestantes,
  textoAnuncioExpiracion,
} from '../domain/expiracion';
import { SesionPanelStore } from './sesion-panel.store';

/** Intervalo del reloj de la cuenta atrás. */
export const TICK_EXPIRACION_MS = 1000;

/**
 * STATE del aviso de expiración por inactividad (AC-109, AC_TKT010_11). Se provee en el armazón del
 * panel. La inactividad la mide el servidor y otras peticiones la renuevan, así que la hora de
 * expiración conocida puede quedarse vieja: al entrar en la ventana de aviso (≤ 2 min) se relee la
 * sesión (sin renovarla) y solo si la expiración se confirma aparece el diálogo.
 */
@Injectable()
export class ExpiracionSesionStore {
  private readonly sesionStore = inject(SesionPanelStore);

  private readonly _ahora = signal(Date.now());
  /** Expiración (ms) ya contrastada con el servidor. */
  private readonly _confirmada = signal<number | null>(null);
  private readonly _anuncio = signal<string | null>(null);
  private readonly _renovando = signal(false);
  private verificando = false;
  private avisoAbierto = false;

  private readonly expiraEn = computed(
    () => this.sesionStore.sesion()?.expiraInactividadEn.getTime() ?? null,
  );
  readonly restantes = computed(() => {
    const expira = this.expiraEn();
    return expira === null ? null : segundosRestantes(new Date(expira), new Date(this._ahora()));
  });
  private readonly confirmada = computed(
    () => this.expiraEn() !== null && this._confirmada() === this.expiraEn(),
  );
  /** Diálogo «Tu sesión está por expirar». */
  readonly avisoVisible = computed(() => {
    const restantes = this.restantes();
    return restantes !== null && this.confirmada() && debeAvisarExpiracion(restantes);
  });
  /** La sesión llegó a 0: la siguiente acción lleva a SCR-030 (ALT-014). */
  readonly expirada = computed(() => this.confirmada() && this.restantes() === 0);
  readonly cuentaAtras = computed(() => formatearCuentaAtras(this.restantes() ?? 0));
  readonly anuncio = this._anuncio.asReadonly();
  readonly renovando = this._renovando.asReadonly();

  constructor() {
    if (!isPlatformBrowser(inject(PLATFORM_ID))) return;
    const reloj = setInterval(() => this.tick(), TICK_EXPIRACION_MS);
    inject(DestroyRef).onDestroy(() => clearInterval(reloj));
  }

  /** Avanza el reloj y decide si contrastar la expiración o anunciar la cuenta atrás. */
  tick(ahora: number = Date.now()): void {
    this._ahora.set(ahora);
    const restantes = this.restantes();
    const expira = this.expiraEn();
    if (restantes === null || expira === null) return;
    if (restantes <= AVISO_EXPIRACION_SEGUNDOS && this._confirmada() !== expira) {
      void this.contrastar(expira);
      return;
    }
    const visible = this.avisoVisible();
    if (visible && !this.avisoAbierto) {
      this._anuncio.set(textoAnuncioExpiracion(restantes, true));
    } else if (visible) {
      const texto = textoAnuncioExpiracion(restantes, false);
      if (texto !== null) this._anuncio.set(texto);
    }
    this.avisoAbierto = visible;
  }

  /** «Seguir conectado». */
  async seguirConectado(): Promise<ErrorApi | null> {
    this._renovando.set(true);
    const error = await this.sesionStore.renovar();
    this._renovando.set(false);
    if (error === null) {
      this.avisoAbierto = false;
      this._anuncio.set(null);
    }
    return error;
  }

  private async contrastar(expira: number): Promise<void> {
    if (this.verificando) return;
    this.verificando = true;
    await this.sesionStore.cargar();
    this.verificando = false;
    const actual = this.expiraEn();
    // Si el servidor confirma la misma expiración se avisa; si cambió (otra petición la renovó),
    // se vuelve a esperar a la nueva ventana de aviso.
    if (actual === expira) this._confirmada.set(expira);
    this.tick(this._ahora());
  }
}
