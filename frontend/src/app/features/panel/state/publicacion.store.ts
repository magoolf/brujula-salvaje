import { Injectable, computed, inject, signal } from '@angular/core';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import {
  erroresDeFormulario,
  leerBloqueosCascada,
  leerEntidadesEnConflicto,
  leerErroresPorEntidad,
  leerImpactoCascada,
  leerUsos,
} from '../data/contenidos.mapper';
import { nuevaClaveIdempotencia } from '../data/panel-medios.repositorio';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import {
  AnalisisPublicacion,
  ErroresEntidad,
  ImpactoRetiro,
  Requisito,
  RequisitosPublicacion,
  ResultadoTransicion,
  cascadaConfirmada,
  conCascada,
  esOrientativoVistaPrevia,
  motivoValido,
} from '../domain/ciclo-editorial';
import { ContenidoEditable } from '../domain/contenidos';
import { FormularioContenido, RefContenido } from '../domain/formulario-contenido';

export type FasePublicacion = 'inactiva' | 'analizando' | 'lista' | 'confirmando' | 'hecha';

/** Resultado visible tras confirmar (banner de éxito con «Ver en el sitio»). */
export interface ExitoTransicion {
  readonly titulo: string;
  readonly urlPublica: string | null;
  /** Entidades co-publicadas o retiradas en cascada además de la principal. */
  readonly adicionales: readonly RefContenido[];
}

const CODIGO_CONFLICTO = 'conflicto_version';
const CODIGO_PUBLICACION_INVALIDA = 'publicacion_invalida';
const CODIGO_CASCADA_BLOQUEADA = 'cascada_bloqueada';
const CODIGOS_IMPACTO = new Set(['impacto_modificado', 'cascada_sin_confirmar']);
const CODIGO_DEPENDENCIA = 'dependencia_bloqueante';

/**
 * STATE del diálogo de publicación / retiro (SCR-038, FEAT-036/037, FLOW-011/012, CHG-BP-001):
 * análisis previo sin efectos, co-publicación atómica de tipos, «Actualizar publicación» con
 * cascada confirmada, impacto de retiro y retiro con `cascada_confirmada`. Interpreta los 409/422
 * del contrato (conflicto_version, publicacion_invalida, cascada_bloqueada, impacto_modificado,
 * dependencia_bloqueante). La clave Idempotency-Key se fija al preparar cada confirmación y se
 * reutiliza en el reintento de la misma operación (ALT-017).
 */
@Injectable()
export class PublicacionStore {
  private readonly repo = inject(PanelContenidosRepositorio);

  private readonly _fase = signal<FasePublicacion>('inactiva');
  private readonly _analisis = signal<AnalisisPublicacion | null>(null);
  /**
   * «Actualizar publicación»: requisitos del formulario (vista previa) además del análisis. La
   * confirmabilidad la decide el análisis del servidor; de la vista previa solo bloquean los
   * requisitos que el servidor comprueba igual (los orientativos son avisos).
   */
  private readonly _requisitosFormulario = signal<RequisitosPublicacion | null>(null);
  private readonly _erroresPorEntidad = signal<readonly ErroresEntidad[]>([]);
  private readonly _erroresCampo = signal<readonly Requisito[]>([]);
  private readonly _impacto = signal<ImpactoRetiro | null>(null);
  private readonly _impactoModificado = signal(false);
  private readonly _error = signal<ErrorApi | null>(null);
  private readonly _conflicto = signal<readonly RefContenido[] | null>(null);
  private readonly _exito = signal<ExitoTransicion | null>(null);
  private clave = nuevaClaveIdempotencia();

  readonly fase = this._fase.asReadonly();
  readonly analisis = this._analisis.asReadonly();
  readonly impacto = this._impacto.asReadonly();
  readonly impactoModificado = this._impactoModificado.asReadonly();
  readonly error = this._error.asReadonly();
  /** Conflicto de versión: entidades obsoletas (vacío si es solo la principal). */
  readonly conflicto = this._conflicto.asReadonly();
  readonly exito = this._exito.asReadonly();
  readonly erroresPorEntidad = this._erroresPorEntidad.asReadonly();

  /**
   * Requisitos pendientes de la entidad principal: los del análisis del servidor, los de la vista
   * previa del formulario en «Actualizar publicación» que el servidor exige igual al guardar, y los
   * de un 422. Los orientativos de la vista previa (RULE-006 sin afinidad) no bloquean: van a
   * `avisosPrincipal` (QA TKT-023 F-03, DEC-AUTO-986).
   */
  readonly pendientesPrincipal = computed<readonly Requisito[]>(() => {
    const porEntidad = this._erroresPorEntidad().find((e) => e.rol === 'PRINCIPAL');
    if (porEntidad) return porEntidad.errores;
    if (this._erroresCampo().length > 0) return this._erroresCampo();
    const analisis = this._analisis();
    const delFormulario = (this._requisitosFormulario()?.pendientes ?? []).filter((r) => !esOrientativoVistaPrevia(r));
    return [...delFormulario, ...(analisis?.entidad.pendientes ?? [])];
  });
  /**
   * Avisos no bloqueantes de la vista previa (p. ej. «menos de 3 relacionados curados publicados»):
   * el servidor completa los relacionados por afinidad, así que se informa sin impedir confirmar. Se
   * omiten si el análisis del servidor ya informa el mismo requisito (entonces sí bloquea).
   */
  readonly avisosPrincipal = computed<readonly Requisito[]>(() => {
    const delServidor = new Set((this._analisis()?.entidad.pendientes ?? []).map((r) => r.codigo));
    return (this._requisitosFormulario()?.pendientes ?? []).filter(
      (r) => esOrientativoVistaPrevia(r) && !delServidor.has(r.codigo),
    );
  });
  /** Tipos co-publicados con errores (de un 422 o del análisis). */
  readonly pendientesCopublicacion = computed(() => {
    const errores = this._erroresPorEntidad().filter((e) => e.rol !== 'PRINCIPAL');
    if (errores.length > 0) return errores;
    return (this._analisis()?.copublicacion ?? [])
      .filter((e) => !e.cumple)
      .map((e) => ({ id: e.id, tipo: e.tipo, titulo: e.titulo, rol: e.rol, errores: e.pendientes }));
  });
  readonly totalPendientes = computed(
    () =>
      this.pendientesPrincipal().length +
      this.pendientesCopublicacion().reduce((n, e) => n + e.errores.length, 0) +
      (this._analisis()?.bloqueosCascada.length ?? 0),
  );
  readonly confirmable = computed(() => {
    const analisis = this._analisis();
    return (
      this._fase() === 'lista' &&
      analisis !== null &&
      analisis.confirmable &&
      this.totalPendientes() === 0 &&
      this._conflicto() === null
    );
  });
  readonly retirable = computed(() => {
    const impacto = this._impacto();
    return this._fase() === 'lista' && impacto !== null && impacto.retirable && this._conflicto() === null;
  });

  cerrar(): void {
    this._fase.set('inactiva');
    this._analisis.set(null);
    this._requisitosFormulario.set(null);
    this._erroresPorEntidad.set([]);
    this._erroresCampo.set([]);
    this._impacto.set(null);
    this._impactoModificado.set(false);
    this._error.set(null);
    this._conflicto.set(null);
  }

  limpiarExito(): void {
    this._exito.set(null);
  }

  // ------------------------------------------------------------------- Publicar / Actualizar
  /**
   * Paso 1 del diálogo («Comprobando requisitos…»). BORRADOR: análisis del estado guardado.
   * PUBLICADO: requisitos del formulario (vista previa) + análisis multi-entidad con los tipos del
   * formulario (co-publicación de tipos añadidos y cascada de los quitados, AC-124/128).
   */
  async analizar(contenido: ContenidoEditable, formulario: FormularioContenido): Promise<ErrorApi | null> {
    this.cerrar();
    this._fase.set('analizando');
    this.clave = nuevaClaveIdempotencia();
    const actualizar = contenido.estado === 'PUBLICADO';
    const tipos = actualizar && contenido.tipo === 'DESTINO'
      ? { tipos: formulario.tipos, principal: formulario.tipoPrincipal }
      : null;
    let error = await ejecutar(
      defer(() => this.repo.analizar(contenido.tipo, contenido.id, contenido.version, tipos)),
      (analisis) => this._analisis.set(analisis),
    );
    if (error === null && actualizar && contenido.tipo !== 'TERMINO') {
      error = await ejecutar(defer(() => this.repo.vistaPrevia(formulario, contenido.id)), (vista) =>
        this._requisitosFormulario.set(vista.requisitos),
      );
    }
    if (error !== null) this.registrar(error);
    this._fase.set('lista');
    return error;
  }

  /**
   * «Confirmar publicación» / «Actualizar publicación». Devuelve el contenido actualizado (PUT) o
   * null si la operación fue una transición (el editor relee el contenido).
   */
  async confirmar(
    contenido: ContenidoEditable,
    formulario: FormularioContenido,
  ): Promise<{ readonly error: ErrorApi | null; readonly contenido: ContenidoEditable | null }> {
    const analisis = this._analisis();
    if (analisis === null || this._fase() === 'confirmando') return { error: null, contenido: null };
    this._fase.set('confirmando');
    this._error.set(null);
    let actualizado: ContenidoEditable | null = null;
    let error: ErrorApi | null;
    if (contenido.estado === 'PUBLICADO') {
      const opciones =
        contenido.tipo === 'DESTINO'
          ? {
              copublicarTipos: analisis.copublicarTipos,
              confirmarCascada: analisis.tiposEnCascada.length > 0,
              cascadaConfirmada: analisis.tiposEnCascada.map((t) => ({ id: t.id, tipo: t.tipo })),
            }
          : null;
      error = await ejecutar(
        defer(() => this.repo.actualizar(contenido.id, formulario, contenido.version, opciones)),
        (guardado) => {
          actualizado = guardado;
          this.marcarExito(guardado.formulario.titulo, guardado.urlPublica, guardado.entidadesAfectadas);
        },
      );
    } else {
      const clave = this.clave;
      error = await ejecutar(
        defer(() =>
          this.repo.publicar(contenido.tipo, contenido.id, contenido.version, analisis.copublicarTipos, clave),
        ),
        (resultado: ResultadoTransicion) =>
          this.marcarExito(formulario.titulo, resultado.urlPublica, resultado.entidades),
      );
    }
    if (error === null) {
      this._fase.set('hecha');
      return { error: null, contenido: actualizado };
    }
    this.registrar(error);
    this._fase.set('lista');
    // Cascada calculada de nuevo bajo bloqueo: se repite el análisis para mostrarla (AC-128).
    if (error.codigo !== null && CODIGOS_IMPACTO.has(error.codigo)) {
      await this.reanalizarTrasCambio(contenido, formulario);
    }
    return { error, contenido: null };
  }

  private async reanalizarTrasCambio(contenido: ContenidoEditable, formulario: FormularioContenido): Promise<void> {
    await this.analizar(contenido, formulario);
    this._impactoModificado.set(true);
  }

  // ------------------------------------------------------------------- Retirar
  async cargarImpacto(contenido: ContenidoEditable): Promise<ErrorApi | null> {
    this.cerrar();
    this._fase.set('analizando');
    this.clave = nuevaClaveIdempotencia();
    const error = await ejecutar(defer(() => this.repo.impactoRetiro(contenido.tipo, contenido.id)), (impacto) =>
      this._impacto.set(impacto),
    );
    if (error !== null) this.registrar(error);
    this._fase.set('lista');
    return error;
  }

  /** «Retirar» con motivo y la cascada que el editor vio (cascada_confirmada, AC-112/127). */
  async retirar(contenido: ContenidoEditable, motivo: string): Promise<ErrorApi | null> {
    const impacto = this._impacto();
    if (impacto === null || !motivoValido(motivo) || this._fase() === 'confirmando') return null;
    this._fase.set('confirmando');
    this._error.set(null);
    this._impactoModificado.set(false);
    const clave = this.clave;
    const error = await ejecutar(
      defer(() =>
        this.repo.retirar(contenido.tipo, contenido.id, contenido.version, motivo, cascadaConfirmada(impacto), clave),
      ),
      (resultado) => this.marcarExito(contenido.formulario.titulo, null, resultado.entidades),
    );
    if (error === null) {
      this._fase.set('hecha');
      return null;
    }
    this.registrarRetiro(error, impacto);
    this._fase.set('lista');
    return error;
  }

  private registrarRetiro(error: ErrorApi, impacto: ImpactoRetiro): void {
    if (error.codigo !== null && CODIGOS_IMPACTO.has(error.codigo)) {
      const cascada = leerImpactoCascada(error.extra);
      if (cascada !== null) this._impacto.set(conCascada(impacto, cascada));
      this._impactoModificado.set(true);
      // Nueva cascada → nueva operación: otra clave de idempotencia (la huella cambia).
      this.clave = nuevaClaveIdempotencia();
      return;
    }
    if (error.codigo === CODIGO_CASCADA_BLOQUEADA) {
      this._impacto.set({ ...impacto, bloqueosCascada: leerBloqueosCascada(error.extra), retirable: false });
      return;
    }
    if (error.codigo === CODIGO_DEPENDENCIA) {
      this._impacto.set({ ...impacto, bloqueos: leerUsos(error.extra), retirable: false });
      return;
    }
    this.registrar(error);
  }

  private registrar(error: ErrorApi): void {
    if (error.codigo === CODIGO_CONFLICTO) {
      this._conflicto.set(leerEntidadesEnConflicto(error.extra));
      return;
    }
    if (error.codigo === CODIGO_PUBLICACION_INVALIDA) {
      const porEntidad = leerErroresPorEntidad(error.extra);
      if (porEntidad.length > 0) {
        this._erroresPorEntidad.set(porEntidad);
        return;
      }
    }
    if (error.categoria === 'validacion' || error.categoria === 'regla_negocio') {
      const porCampo = Object.entries(erroresDeFormulario(error.campos)).map(
        ([campo, mensaje]): Requisito => ({ campo, codigo: 'validacion', mensaje, referencias: [] }),
      );
      if (porCampo.length > 0) {
        this._erroresCampo.set(porCampo);
        return;
      }
    }
    if (error.codigo === CODIGO_CASCADA_BLOQUEADA) {
      const analisis = this._analisis();
      if (analisis !== null) {
        this._analisis.set({ ...analisis, bloqueosCascada: leerBloqueosCascada(error.extra), confirmable: false });
        return;
      }
    }
    this._error.set(error);
  }

  private marcarExito(
    titulo: string,
    urlPublica: string | null,
    entidades: readonly { readonly id: number; readonly tipo: RefContenido['tipo']; readonly titulo: string; readonly estado: RefContenido['estado']; readonly origen?: string }[],
  ): void {
    this._exito.set({
      titulo,
      urlPublica,
      adicionales: entidades
        .filter((e) => e.origen !== 'PRINCIPAL')
        .map((e) => ({ id: e.id, tipo: e.tipo, titulo: e.titulo, estado: e.estado })),
    });
  }
}

