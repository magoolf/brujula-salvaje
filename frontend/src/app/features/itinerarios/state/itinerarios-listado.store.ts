import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap } from '@angular/router';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { ItinerariosRepositorio } from '../data/itinerarios.repositorio';
import { QueryParamsItinerarios, filtrosDesdeQueryParams } from '../domain/filtros';
import { FiltrosItinerarios } from '../domain/modelos';

function paramMapARegistro(mapa: ParamMap): QueryParamsItinerarios {
  const registro: Record<string, string | readonly string[]> = {};
  for (const clave of mapa.keys) {
    const valores = mapa.getAll(clave);
    registro[clave] = valores.length > 1 ? valores : (valores[0] ?? '');
  }
  return registro;
}

/**
 * STATE de "Listado de itinerarios" (SCR-006, FEAT-009). El orden y la página viven en la URL
 * (mismo patrón que Destinos): este store solo LEE `ActivatedRoute.queryParamMap` y dispara el
 * recurso de listado; no expone comandos de escritura (Regla 03).
 *
 * NO usa `providedIn: 'root'`: se provee en `PaginaItinerarios` para que `inject(ActivatedRoute)`
 * resuelva contra la ruta activa (ver la explicación completa en destinos/state/destino-detalle.store.ts).
 */
@Injectable()
export class ItinerariosListadoStore {
  private readonly repo = inject(ItinerariosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly queryParamMap = toSignal(this.ruta.queryParamMap, { requireSync: true });

  readonly filtros = computed<FiltrosItinerarios>(() =>
    filtrosDesdeQueryParams(paramMapARegistro(this.queryParamMap())),
  );

  private readonly recursoListado = resource({
    params: () => this.filtros(),
    loader: ({ params }) => this.repo.listar(params),
  });

  readonly pagina = computed(() => (this.recursoListado.hasValue() ? this.recursoListado.value() : null));
  readonly cargando = computed(() => this.recursoListado.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recursoListado.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recursoListado.reload();
  }
}
