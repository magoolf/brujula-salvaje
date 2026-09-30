import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { TiposAventuraRepositorio } from '../data/tipos-aventura.repositorio';

function paginaValida(valor: string | null): number {
  const n = Number(valor);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

/**
 * STATE de "Índice de tipos de aventura" (SCR-008, FEAT-010). Solo pagina (sin orden ni filtros,
 * a diferencia de Destinos/Itinerarios): el número de página vive en la URL.
 *
 * NO usa `providedIn: 'root'`: se provee en `PaginaTiposAventura` para que `inject(ActivatedRoute)`
 * resuelva contra la ruta activa.
 */
@Injectable()
export class TiposListadoStore {
  private readonly repo = inject(TiposAventuraRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly pagina$ = toSignal(
    this.ruta.queryParamMap.pipe(map((p) => paginaValida(p.get('pagina')))),
    { requireSync: true },
  );

  private readonly recurso = resource({
    params: () => this.pagina$(),
    loader: ({ params }) => this.repo.listar(params),
  });

  readonly pagina = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recurso.reload();
  }
}
