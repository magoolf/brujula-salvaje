import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { ColeccionesRepositorio } from '../data/colecciones.repositorio';
import { mapAlternativasRetirado } from '../data/colecciones.mapper';
import { ContenidoRetirado } from '../domain/modelos';

/** STATE de la ficha de colección (SCR-014, FEAT-017). Mismo patrón de 404/410 que el resto de fichas. */
@Injectable()
export class ColeccionDetalleStore {
  private readonly repo = inject(ColeccionesRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly slug = toSignal(this.ruta.paramMap.pipe(map((p) => p.get('slug') ?? '')), {
    requireSync: true,
  });

  private readonly recurso = resource({
    params: () => this.slug(),
    loader: ({ params }) => this.repo.detalle(params),
  });

  readonly coleccion = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
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
        typeof listadoPadre === 'string' && listadoPadre.length > 0 ? listadoPadre : '/colecciones',
      alternativas: mapAlternativasRetirado(error.extra['alternativas']),
    };
  });

  recargar(): void {
    this.recurso.reload();
  }
}
