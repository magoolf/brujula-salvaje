import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelConfiguracionRepositorio } from '../data/panel-configuracion.repositorio';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import {
  CampoDestacados,
  ConfigInicio,
  DEFINICION_LISTA,
  FormularioDestacados,
  ListaDestacada,
  entradaDesdeFormulario,
  formularioDesdeConfig,
  validarDestacados,
} from '../domain/destacados';
import { ResultadoBusqueda } from '../domain/formulario-contenido';

/**
 * STATE de los Destacados de inicio (SCR-042, FEAT-043, FLOW-014, RULE-016, AC-011): lee la
 * configuración, busca contenido PUBLICADO para cada lista y guarda (se aplica al instante en el
 * inicio). Tras guardar fija la respuesta del servidor (§7). Sin bloqueo optimista: el contrato no
 * lleva versión (DEC-AUTO-1042).
 */
@Injectable()
export class DestacadosStore {
  private readonly repo = inject(PanelConfiguracionRepositorio);
  private readonly contenidos = inject(PanelContenidosRepositorio);

  private readonly _guardadoOk = signal(false);
  private readonly recurso = resource({ loader: () => this.repo.inicio() });

  readonly config = computed<ConfigInicio | null>(() =>
    this.recurso.hasValue() ? (this.recurso.value() ?? null) : null,
  );
  readonly guardado = computed<FormularioDestacados | null>(() => {
    const config = this.config();
    return config === null ? null : formularioDesdeConfig(config);
  });
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  /** «Los cambios ya se ven en el inicio.» + «Ver inicio» tras guardar. */
  readonly guardadoOk = this._guardadoOk.asReadonly();

  validar(formulario: FormularioDestacados): Partial<Record<CampoDestacados, string>> {
    return validarDestacados(formulario);
  }

  /** Combobox de cada lista: solo contenido PUBLICADO del tipo de la lista. */
  async buscar(lista: ListaDestacada, q: string): Promise<ResultadoBusqueda> {
    try {
      const resultados = await this.contenidos.buscar([DEFINICION_LISTA[lista].tipo], q.trim().slice(0, 100), 'PUBLICADO');
      return { resultados, error: null };
    } catch (error: unknown) {
      return { resultados: [], error: normalizarError(error).mensaje };
    }
  }

  async guardar(formulario: FormularioDestacados): Promise<ErrorApi | null> {
    this._guardadoOk.set(false);
    return ejecutar(defer(() => this.repo.guardarInicio(entradaDesdeFormulario(formulario))), (config) => {
      this.recurso.value.set(config);
      this._guardadoOk.set(true);
    });
  }

  descartarAviso(): void {
    this._guardadoOk.set(false);
  }

  recargar(): void {
    this.recurso.reload();
  }
}
