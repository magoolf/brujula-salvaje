import { Injectable, computed, inject, resource } from '@angular/core';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { MapaDelSitioRepositorio } from '../data/mapa-del-sitio.repositorio';
import { construirSecciones, totalEnlaces } from '../domain/mapa-del-sitio';
import { DatosMapaDelSitio, SeccionMapa } from '../domain/modelos';

/** STATE del Mapa del sitio (SCR-022, FEAT-025, MUST). Solo lectura: no hay comandos de escritura. */
@Injectable()
export class MapaDelSitioStore {
  private readonly repo = inject(MapaDelSitioRepositorio);

  /** Datos del SSR para el primer render del cliente (evita el salto a «cargando», CLS). */
  private readonly inicial = this.repo.datosTransferidos();

  private readonly recurso = resource({
    loader: () => this.repo.obtener(),
  });

  private readonly datos = computed<DatosMapaDelSitio | null>(() => {
    if (this.recurso.hasValue()) return this.recurso.value();
    return this.recurso.error() ? null : this.inicial;
  });

  /** Secciones del mapa; `null` mientras no hay datos. */
  readonly secciones = computed<readonly SeccionMapa[] | null>(() => {
    const datos = this.datos();
    return datos === null ? null : construirSecciones(datos);
  });

  readonly total = computed(() => {
    const secciones = this.secciones();
    return secciones === null ? 0 : totalEnlaces(secciones);
  });

  readonly cargando = computed(() => this.recurso.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recurso.reload();
  }
}
