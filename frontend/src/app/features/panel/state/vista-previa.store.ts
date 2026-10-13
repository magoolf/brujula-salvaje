import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import { rutaEditor, tieneVistaPrevia, tipoDeRuta } from '../domain/contenidos';
import { TipoContenido } from '../domain/modelos';
import { VistaPreviaContenido } from '../domain/vista-previa';
import { idDeSegmento } from './editor-contenido.store';
import { MemoriaEditor } from './memoria-editor';

/**
 * STATE de la Vista previa (SCR-037, FEAT-035, DEC-AUTO-120): renderiza los datos ACTUALES del
 * formulario (el borrador en memoria que dejó el editor) sin persistir nada. Si se abre la URL
 * directamente (sin borrador en memoria), se previsualiza la versión guardada; en el alta sin
 * borrador no hay nada que mostrar. Se provee en la página.
 */
@Injectable()
export class VistaPreviaStore {
  private readonly repo = inject(PanelContenidosRepositorio);
  private readonly memoria = inject(MemoriaEditor);
  private readonly params = toSignal(inject(ActivatedRoute).paramMap, { requireSync: true });

  readonly tipo = computed<TipoContenido | null>(() => tipoDeRuta(this.params().get('tipo')));
  private readonly id = computed(() => idDeSegmento(this.params().get('id')));

  private readonly recurso = resource({
    params: () => {
      const tipo = this.tipo();
      const id = this.id();
      if (tipo === null || id === 'invalido' || !tieneVistaPrevia(tipo)) return undefined;
      const borrador = this.memoria.leer(tipo, id);
      if (borrador === null && id === null) return undefined;
      return { tipo, id, formulario: borrador?.formulario ?? null };
    },
    loader: async ({ params }): Promise<VistaPreviaContenido> => {
      const formulario =
        params.formulario ?? (await this.repo.obtener(params.tipo, params.id as number)).formulario;
      return this.repo.vistaPrevia(formulario, params.id);
    },
  });

  readonly vista = computed(() => (this.recurso.hasValue() ? (this.recurso.value() ?? null) : null));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  readonly noEncontrado = computed(() => {
    const tipo = this.tipo();
    return (
      tipo === null ||
      this.id() === 'invalido' ||
      !tieneVistaPrevia(tipo) ||
      this.error()?.categoria === 'no_encontrado'
    );
  });
  /** Alta sin borrador en memoria (p. ej. URL abierta en otra pestaña): nada que previsualizar. */
  readonly sinDatos = computed(() => {
    const tipo = this.tipo();
    return tipo !== null && this.id() === null && this.memoria.leer(tipo, null) === null;
  });
  readonly rutaEditor = computed(() => {
    const tipo = this.tipo();
    const id = this.id();
    return tipo === null || id === 'invalido' ? '/panel' : rutaEditor(tipo, id);
  });

  recargar(): void {
    this.recurso.reload();
  }
}
