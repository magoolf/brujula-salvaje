import { Injectable, computed, inject, signal } from '@angular/core';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { PanelMediosRepositorio, nuevaClaveIdempotencia } from '../data/panel-medios.repositorio';
import {
  MENSAJE_DEMASIADOS_ARCHIVOS,
  Medio,
  ResultadoArchivo,
  excedeMaximo,
  porcentaje,
  rechazoLocal,
  resumenSubida,
  validarArchivo,
} from '../domain/medios';

interface Progreso {
  readonly cargados: number;
  readonly total: number | null;
}

/**
 * STATE de la subida de imágenes (MediaUploader; FLOW-013, FEAT-041, ALT-017/020/021). Una instancia
 * por componente de subida (biblioteca SCR-039 o pestaña «Subir» del selector SCR-041).
 * - Validación previa en el cliente (tipo y tamaño) antes de enviar: los rechazos locales aparecen
 *   en la misma lista de resultados, sin llegar a subirse.
 * - Más de 10 archivos: se rechaza la selección completa, sin subir ninguno.
 * - El lote lleva una Idempotency-Key: «Reintentar» tras un fallo de red reenvía la misma.
 * Comandos con `ejecutar()` y `ErrorApi | null` (Reglas 11 y 12).
 */
@Injectable()
export class SubidaMediosStore {
  private readonly repo = inject(PanelMediosRepositorio);

  private readonly _resultados = signal<readonly ResultadoArchivo[]>([]);
  private readonly _subiendo = signal(false);
  private readonly _progreso = signal<Progreso | null>(null);
  private readonly _errorSeleccion = signal<string | null>(null);
  private readonly _errorEnvio = signal<ErrorApi | null>(null);
  /** Lote pendiente de reintento (solo los archivos válidos y su clave). */
  private pendiente: { archivos: readonly File[]; locales: readonly ResultadoArchivo[]; clave: string } | null =
    null;

  readonly resultados = this._resultados.asReadonly();
  readonly subiendo = this._subiendo.asReadonly();
  readonly errorSeleccion = this._errorSeleccion.asReadonly();
  readonly errorEnvio = this._errorEnvio.asReadonly();
  readonly porcentaje = computed(() => {
    const progreso = this._progreso();
    return progreso === null ? 0 : porcentaje(progreso.cargados, progreso.total);
  });
  readonly hayResultados = computed(() => this._resultados().length > 0);
  readonly resumen = computed(() => {
    const resultados = this._resultados();
    return resultados.length === 0 ? '' : resumenSubida(resultados);
  });
  readonly puedeReintentar = computed(() => this._errorEnvio() !== null && !this._subiendo());
  /** Medios aceptados en la última subida (PENDIENTE_METADATOS → «Completar datos»). */
  readonly aceptados = computed<readonly Medio[]>(() =>
    this._resultados()
      .map((r) => (r.resultado === 'ACEPTADO' ? r.medio : null))
      .filter((m): m is Medio => m !== null),
  );

  /**
   * Procesa una selección de archivos: valida y sube los válidos. Tras el éxito, `aceptados` tiene
   * los medios nuevos (para que quien lo usa recargue su listado).
   */
  async seleccionar(archivos: readonly File[]): Promise<ErrorApi | null> {
    if (this._subiendo() || archivos.length === 0) return null;
    this._errorEnvio.set(null);
    if (excedeMaximo(archivos.length)) {
      this._errorSeleccion.set(MENSAJE_DEMASIADOS_ARCHIVOS);
      this._resultados.set([]);
      this.pendiente = null;
      return null;
    }
    this._errorSeleccion.set(null);
    const validos: File[] = [];
    const locales: ResultadoArchivo[] = [];
    for (const archivo of archivos) {
      const motivo = validarArchivo({ nombre: archivo.name, tipo: archivo.type, tamano: archivo.size });
      if (motivo === null) validos.push(archivo);
      else locales.push(rechazoLocal(archivo.name, motivo));
    }
    this.pendiente = { archivos: validos, locales, clave: nuevaClaveIdempotencia() };
    return this.enviar();
  }

  /** Reenvía el último lote fallido con la misma Idempotency-Key (ALT-017). */
  async reintentar(): Promise<ErrorApi | null> {
    if (this.pendiente === null || this._subiendo()) return null;
    this._errorEnvio.set(null);
    return this.enviar();
  }

  /** «Cerrar» la lista de resultados (persiste hasta cerrarla, HANDOFF SCR-039). */
  cerrarResultados(): void {
    this._resultados.set([]);
    this._errorSeleccion.set(null);
    this._errorEnvio.set(null);
    this.pendiente = null;
  }

  private async enviar(): Promise<ErrorApi | null> {
    const lote = this.pendiente;
    if (lote === null) return null;
    if (lote.archivos.length === 0) {
      this._resultados.set(lote.locales);
      this.pendiente = null;
      return null;
    }
    this._subiendo.set(true);
    this._progreso.set({ cargados: 0, total: null });
    this._resultados.set(lote.locales);
    let remotos: readonly ResultadoArchivo[] = [];
    const error = await ejecutar(
      defer(() =>
        this.repo.subir(lote.archivos, lote.clave, (cargados, total) =>
          this._progreso.set({ cargados, total }),
        ),
      ),
      (resultados) => (remotos = resultados),
    );
    this._subiendo.set(false);
    this._progreso.set(null);
    if (error !== null) {
      this._errorEnvio.set(error);
      return error;
    }
    this.pendiente = null;
    this._resultados.set([...lote.locales, ...remotos]);
    return null;
  }
}
