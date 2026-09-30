import { Injectable, computed, inject, signal } from '@angular/core';

import { ErrorApi } from '../../http/error-api.model';
import { AlmacenGuardados } from './almacen-guardados';
import {
  ElementoGuardado,
  TipoContenidoGuardable,
  agregarElemento,
  quitarElemento,
} from './elemento-guardado.model';

const ERROR_NO_DISPONIBLE: ErrorApi = {
  tipo: 'guardado_no_disponible',
  categoria: 'desconocido',
  codigo: null,
  mensaje: 'No podemos guardar aventuras en este navegador (almacenamiento no disponible).',
  campos: {},
  traceId: null,
  extra: {},
};

/**
 * Estado global de «Mis aventuras guardadas» (GI-07, FEAT-020). Vive en `core/layout` (como
 * `Conectividad`, GI-04) porque es una interacción global reutilizada por varias features
 * (tarjetas de inicio, listado y ficha de destino, y la propia página de guardados) sin cuenta ni
 * llamada al servidor (RULE-013). Comandos vía Regla 11/12: devuelven `ErrorApi | null`.
 */
@Injectable({ providedIn: 'root' })
export class GuardadosStore {
  private readonly almacen = inject(AlmacenGuardados);

  private readonly _elementos = signal<readonly ElementoGuardado[]>(this.almacen.leer());

  readonly elementos = this._elementos.asReadonly();
  readonly cantidad = computed(() => this._elementos().length);
  /** ALT-011: la UI deshabilita las acciones de guardar cuando esto es `false`. */
  readonly disponible = this.almacen.estaDisponible();

  guardar(elemento: ElementoGuardado): ErrorApi | null {
    if (!this.disponible) return ERROR_NO_DISPONIBLE;
    const siguiente = agregarElemento(this._elementos(), elemento);
    this._elementos.set(siguiente);
    this.almacen.escribir(siguiente);
    return null;
  }

  quitar(tipo: TipoContenidoGuardable, slug: string): ErrorApi | null {
    if (!this.disponible) return ERROR_NO_DISPONIBLE;
    const siguiente = quitarElemento(this._elementos(), tipo, slug);
    this._elementos.set(siguiente);
    this.almacen.escribir(siguiente);
    return null;
  }

  vaciar(): ErrorApi | null {
    if (!this.disponible) return ERROR_NO_DISPONIBLE;
    this._elementos.set([]);
    this.almacen.escribir([]);
    return null;
  }
}
