import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { InstitucionalRepositorio } from '../data/institucional.repositorio';

function paginaValida(valor: string | null): number {
  const n = Number(valor);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

/** STATE de "Créditos de imágenes" (SCR-021, FEAT-024). */
@Injectable()
export class CreditosStore {
  private readonly repo = inject(InstitucionalRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly pagina$ = toSignal(
    this.ruta.queryParamMap.pipe(map((p) => paginaValida(p.get('pagina')))),
    { requireSync: true },
  );

  // `id` (TKT-016): el valor del SSR viaja en TransferState y el recurso nace resuelto al hidratar
  // (sin esqueleto ni recreación del DOM del servidor). La clave incluye los parámetros iniciales de
  // la URL, así que nunca se sirve un valor transferido de otra URL; y Angular solo la consulta en el
  // primer cálculo del recurso mientras dura la hidratación, nunca al navegar después en el cliente.
  private readonly recurso = resource({
    id: `recurso:creditos:${this.pagina$()}`,
    params: () => this.pagina$(),
    loader: ({ params }) => this.repo.creditos(params),
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
