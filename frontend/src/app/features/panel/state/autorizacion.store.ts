import { Injectable, computed, inject, resource, signal } from '@angular/core';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { DecisionAutorizacion } from '../domain/modelos';
import { SesionPanelStore } from './sesion-panel.store';

/**
 * STATE de la autorización de tratamiento (SCR-033 y sección de SCR-032; FEAT-032, REQ-070).
 */
@Injectable()
export class AutorizacionStore {
  private readonly repo = inject(PanelAuthRepositorio);
  private readonly sesion = inject(SesionPanelStore);

  private readonly recurso = resource({ loader: () => this.repo.autorizacion() });
  private readonly _enviando = signal<DecisionAutorizacion | null>(null);

  readonly autorizacion = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  readonly enviando = this._enviando.asReadonly();

  recargar(): void {
    this.recurso.reload();
  }

  /** «Autorizo» registra fecha y versión; «No autorizo» cierra la sesión (DEC-AUTO-038). */
  async decidir(decision: DecisionAutorizacion): Promise<ErrorApi | null> {
    const vigente = this.autorizacion();
    if (vigente === null) return null;
    this._enviando.set(decision);
    const error = await this.sesion.registrarAutorizacion(decision, vigente.versionPolitica);
    this._enviando.set(null);
    // 409 conflicto_version: la política cambió mientras se leía; se recarga la vigente.
    if (error?.categoria === 'conflicto') this.recurso.reload();
    return error;
  }
}
