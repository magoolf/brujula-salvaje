import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelConfiguracionRepositorio } from '../data/panel-configuracion.repositorio';
import {
  CampoConfiguracion,
  ConfiguracionSitio,
  FormularioConfiguracion,
  entradaDesdeFormulario,
  formularioDesdeConfiguracion,
  validarConfiguracion,
} from '../domain/configuracion-sitio';

/**
 * STATE de la Configuración del sitio (SCR-047, FEAT-047, RULE-014, AC-070): lee la configuración
 * y la guarda. Tras guardar fija la respuesta del servidor (§7: invalidación en el store). Sin
 * bloqueo optimista: el contrato no lleva versión (DEC-AUTO-1042).
 */
@Injectable()
export class ConfiguracionSitioStore {
  private readonly repo = inject(PanelConfiguracionRepositorio);

  private readonly _avisoExito = signal<string | null>(null);
  private readonly recurso = resource({ loader: () => this.repo.configuracion() });

  readonly configuracion = computed<ConfiguracionSitio | null>(() =>
    this.recurso.hasValue() ? (this.recurso.value() ?? null) : null,
  );
  /** Formulario de los últimos datos guardados (referencia de «cambios sin guardar»). */
  readonly guardado = computed<FormularioConfiguracion | null>(() => {
    const configuracion = this.configuracion();
    return configuracion === null ? null : formularioDesdeConfiguracion(configuracion);
  });
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly avisoExito = this._avisoExito.asReadonly();

  validar(formulario: FormularioConfiguracion): Partial<Record<CampoConfiguracion, string>> {
    return validarConfiguracion(formulario);
  }

  async guardar(formulario: FormularioConfiguracion): Promise<ErrorApi | null> {
    this._avisoExito.set(null);
    return ejecutar(
      defer(() => this.repo.guardarConfiguracion(entradaDesdeFormulario(formulario))),
      (configuracion) => {
        this.recurso.value.set(configuracion);
        this._avisoExito.set('Configuración guardada.');
      },
    );
  }

  descartarAviso(): void {
    this._avisoExito.set(null);
  }

  recargar(): void {
    this.recurso.reload();
  }
}
