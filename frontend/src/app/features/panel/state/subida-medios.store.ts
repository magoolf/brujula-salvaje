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

/** Bytes enviados del lote: los archivos ya subidos más la fracción del que está en curso. */
interface Progreso {
  readonly cargados: number;
  readonly total: number | null;
}

/** Archivo en curso dentro del lote (1-based) para «Subiendo 3 de 10…». */
export interface PosicionSubida {
  readonly actual: number;
  readonly total: number;
}

/**
 * Lote pendiente: los archivos válidos, una Idempotency-Key POR ARCHIVO y el índice del siguiente
 * que falta por subir (un reintento continúa desde ahí con la misma clave, ALT-017).
 */
interface Lote {
  readonly archivos: readonly File[];
  readonly claves: readonly string[];
  readonly locales: readonly ResultadoArchivo[];
  readonly remotos: ResultadoArchivo[];
  siguiente: number;
}

/**
 * STATE de la subida de imágenes (MediaUploader; FLOW-013, FEAT-041, ALT-017/020/021). Una instancia
 * por componente de subida (biblioteca SCR-039 o pestaña «Subir» del selector SCR-041).
 * - Validación previa en el cliente (tipo y tamaño) antes de enviar: los rechazos locales aparecen
 *   en la misma lista de resultados, sin llegar a subirse.
 * - Más de 10 archivos: se rechaza la selección completa, sin subir ninguno.
 * - TKT-072 (OBS-QA071-03, DEC-AUTO-1324): UN ARCHIVO POR PETICIÓN, en secuencia. El servidor
 *   valida, sanea y codifica cada foto de forma síncrona (≈ 13 s por foto de cámara en el contenedor):
 *   un lote de 10 en una sola petición superaba los 120 s de gunicorn y el worker moría sin
 *   respuesta. Así cada petición dura lo que una foto, el resultado de cada archivo aparece en cuanto
 *   llega y el servidor solo retiene en memoria los derivados de una foto (OBS-QA071-04). En
 *   secuencia y no en paralelo: el backend tiene una cuota de 1,5 CPU y dos fotos a la vez solo
 *   alargarían cada petición. El contrato no cambia (`panelSubirMedios` admite 1..10 archivos).
 * - Cada archivo lleva su Idempotency-Key: si uno falla (red o error del servidor), la subida se
 *   detiene en él, se conservan los resultados ya obtenidos y «Reintentar» continúa desde ese archivo
 *   con la misma clave (ALT-017), sin repetir los ya subidos.
 * Comandos con `ejecutar()` y `ErrorApi | null` (Reglas 11 y 12).
 */
@Injectable()
export class SubidaMediosStore {
  private readonly repo = inject(PanelMediosRepositorio);

  private readonly _resultados = signal<readonly ResultadoArchivo[]>([]);
  private readonly _subiendo = signal(false);
  private readonly _progreso = signal<Progreso | null>(null);
  private readonly _posicion = signal<PosicionSubida | null>(null);
  private readonly _errorSeleccion = signal<string | null>(null);
  private readonly _errorEnvio = signal<ErrorApi | null>(null);
  private readonly _archivoFallido = signal<string | null>(null);
  /** Lote pendiente de completar o de reintento. */
  private pendiente: Lote | null = null;

  readonly resultados = this._resultados.asReadonly();
  readonly subiendo = this._subiendo.asReadonly();
  readonly posicion = this._posicion.asReadonly();
  readonly errorSeleccion = this._errorSeleccion.asReadonly();
  readonly errorEnvio = this._errorEnvio.asReadonly();
  /** Nombre del archivo cuyo envío falló (el error de `errorEnvio` es de ese archivo). */
  readonly archivoFallido = this._archivoFallido.asReadonly();
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
   * Procesa una selección de archivos: valida y sube los válidos, uno por petición. Tras el éxito,
   * `aceptados` tiene los medios nuevos (para que quien lo usa recargue su listado).
   */
  async seleccionar(archivos: readonly File[]): Promise<ErrorApi | null> {
    if (this._subiendo() || archivos.length === 0) return null;
    this._errorEnvio.set(null);
    this._archivoFallido.set(null);
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
    this.pendiente = {
      archivos: validos,
      claves: validos.map(() => nuevaClaveIdempotencia()),
      locales,
      remotos: [],
      siguiente: 0,
    };
    return this.enviar();
  }

  /** Continúa el lote desde el archivo que falló, con su misma Idempotency-Key (ALT-017). */
  async reintentar(): Promise<ErrorApi | null> {
    if (this.pendiente === null || this._subiendo()) return null;
    this._errorEnvio.set(null);
    this._archivoFallido.set(null);
    return this.enviar();
  }

  /** «Cerrar» la lista de resultados (persiste hasta cerrarla, HANDOFF SCR-039). */
  cerrarResultados(): void {
    this._resultados.set([]);
    this._errorSeleccion.set(null);
    this._errorEnvio.set(null);
    this._archivoFallido.set(null);
    this.pendiente = null;
  }

  private async enviar(): Promise<ErrorApi | null> {
    const lote = this.pendiente;
    if (lote === null) return null;
    this._resultados.set([...lote.locales, ...lote.remotos]);
    if (lote.siguiente >= lote.archivos.length) {
      this.pendiente = null;
      return null;
    }
    const tamanos = lote.archivos.map((a) => Math.max(a.size, 1));
    const totalBytes = tamanos.reduce((suma, t) => suma + t, 0);
    this._subiendo.set(true);
    try {
      while (lote.siguiente < lote.archivos.length) {
        const indice = lote.siguiente;
        const archivo = lote.archivos[indice];
        const previos = tamanos.slice(0, indice).reduce((suma, t) => suma + t, 0);
        this._posicion.set({ actual: indice + 1, total: lote.archivos.length });
        this._progreso.set({ cargados: previos, total: totalBytes });
        let remotos: readonly ResultadoArchivo[] = [];
        const error = await ejecutar(
          defer(() =>
            this.repo.subir([archivo], lote.claves[indice], (cargados, total) => {
              const fraccion = total !== null && total > 0 ? Math.min(1, cargados / total) : 0;
              this._progreso.set({ cargados: previos + fraccion * tamanos[indice], total: totalBytes });
            }),
          ),
          (resultados) => (remotos = resultados),
        );
        if (error !== null) {
          this._errorEnvio.set(error);
          this._archivoFallido.set(archivo.name);
          return error;
        }
        lote.remotos.push(...remotos);
        lote.siguiente = indice + 1;
        this._resultados.set([...lote.locales, ...lote.remotos]);
      }
      this.pendiente = null;
      return null;
    } finally {
      this._subiendo.set(false);
      this._progreso.set(null);
      this._posicion.set(null);
    }
  }
}
