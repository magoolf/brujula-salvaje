import { Injectable, computed, inject, resource } from '@angular/core';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { DestinosRepositorio } from '../data/destinos.repositorio';

/** STATE del mapa de destinos (SCR-003, FEAT-005): un único recurso con todos los puntos. */
@Injectable({ providedIn: 'root' })
export class MapaStore {
  private readonly repo = inject(DestinosRepositorio);

  // `id` (TKT-016): ver destinos-listado.store.ts (hidratación sin esqueleto ni recreación del DOM).
  private readonly recurso = resource({
    id: 'recurso:destinos-mapa',
    loader: () => this.repo.mapaCompleto(),
  });

  // `hasValue()` evita que `.value()` lance al leerlo mientras el recurso está en error (sin
  // valor previo cargado con éxito).
  readonly puntos = computed(() => (this.recurso.hasValue() ? this.recurso.value() : []));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recurso.reload();
  }
}
