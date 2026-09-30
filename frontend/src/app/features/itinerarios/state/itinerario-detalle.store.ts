import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { ItinerariosRepositorio } from '../data/itinerarios.repositorio';
import { mapAlternativasRetirado } from '../data/itinerarios.mapper';
import { ContenidoRetirado } from '../domain/modelos';

/**
 * STATE de la ficha de itinerario (SCR-007, FEAT-008). El slug se lee de `ActivatedRoute.paramMap`
 * de forma reactiva (navegación entre fichas vía "Sigue explorando"). 404 → esNoEncontrado; 410 →
 * esRetirado con sus alternativas (también cuando el destino padre fue retirado en cascada,
 * RULE-007): ambos derivados del `ErrorApi` normalizado, nunca de un `if` sobre el status HTTP
 * (Regla 13).
 *
 * NO usa `providedIn: 'root'` (mismo motivo documentado en destinos/state/destino-detalle.store.ts):
 * se provee en el propio componente de ruta.
 */
@Injectable()
export class ItinerarioDetalleStore {
  private readonly repo = inject(ItinerariosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly slug = toSignal(this.ruta.paramMap.pipe(map((p) => p.get('slug') ?? '')), {
    requireSync: true,
  });

  private readonly recurso = resource({
    params: () => this.slug(),
    loader: ({ params }) => this.repo.detalle(params),
  });

  /** RULE-010: se pide una sola vez (sin `params`, el recurso no depende del slug). */
  private readonly recursoDescargo = resource({ loader: () => this.repo.textoDescargo() });
  readonly descargo = computed(() =>
    this.recursoDescargo.hasValue() ? this.recursoDescargo.value() : null,
  );

  readonly itinerario = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  readonly esNoEncontrado = computed(() => this.error()?.categoria === 'no_encontrado');
  readonly esRetirado = computed(() => this.error()?.categoria === 'retirado');

  readonly retirado = computed<ContenidoRetirado | null>(() => {
    const error = this.error();
    if (error === null || error.categoria !== 'retirado') return null;
    const listadoPadre = error.extra['listado_padre'];
    return {
      rutaListadoPadre:
        typeof listadoPadre === 'string' && listadoPadre.length > 0 ? listadoPadre : '/itinerarios',
      alternativas: mapAlternativasRetirado(error.extra['alternativas']),
    };
  });

  recargar(): void {
    this.recurso.reload();
  }
}
