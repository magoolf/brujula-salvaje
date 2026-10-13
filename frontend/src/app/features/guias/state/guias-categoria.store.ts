import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { GuiasRepositorio } from '../data/guias.repositorio';

function paginaValida(valor: string | null): number {
  const n = Number(valor);
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

/**
 * STATE de "Categoría de guías" (SCR-011, FEAT-012). Una categoría sin guías publicadas responde
 * 404 en `GET /categorias-guia/{slug}` (contrato) → se trata igual que cualquier 404 público
 * (SCR-023, Regla 13: se deriva del `ErrorApi`, nunca de un `if` sobre el status).
 *
 * NO usa `providedIn: 'root'`: se provee en `PaginaCategoriaGuias` (mismo motivo documentado en
 * destinos/state/destino-detalle.store.ts).
 */
@Injectable()
export class GuiasCategoriaStore {
  private readonly repo = inject(GuiasRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly slug = toSignal(this.ruta.paramMap.pipe(map((p) => p.get('slug') ?? '')), {
    requireSync: true,
  });
  private readonly pagina$ = toSignal(
    this.ruta.queryParamMap.pipe(map((p) => paginaValida(p.get('pagina')))),
    { requireSync: true },
  );

  // `id` (TKT-016): el valor del SSR viaja en TransferState y el recurso nace resuelto al hidratar
  // (sin esqueleto ni recreación del DOM del servidor). La clave incluye los parámetros iniciales de
  // la URL, así que nunca se sirve un valor transferido de otra URL; y Angular solo la consulta en el
  // primer cálculo del recurso mientras dura la hidratación, nunca al navegar después en el cliente.
  private readonly recursoCategoria = resource({
    id: `recurso:guias-categoria:${this.slug()}`,
    params: () => this.slug(),
    loader: ({ params }) => this.repo.categoria(params),
  });

  // `id` (TKT-016): ver el comentario de `recursoCategoria`.
  private readonly recursoGuias = resource({
    id: `recurso:guias-de-categoria:${this.slug()}:${this.pagina$()}`,
    params: () => ({ slug: this.slug(), pagina: this.pagina$() }),
    loader: ({ params }) => this.repo.listarGuias(params.slug, params.pagina),
  });

  // `id` (TKT-016): ver el comentario de `recursoCategoria`.
  private readonly recursoOtrasCategorias = resource({
    id: 'recurso:guias-otras-categorias',
    loader: () => this.repo.listarCategorias(1),
  });

  readonly categoria = computed(() =>
    this.recursoCategoria.hasValue() ? this.recursoCategoria.value() : null,
  );
  readonly guias = computed(() => (this.recursoGuias.hasValue() ? this.recursoGuias.value() : null));
  readonly otrasCategorias = computed(() => {
    const pagina = this.recursoOtrasCategorias.hasValue() ? this.recursoOtrasCategorias.value() : null;
    if (pagina === null) return [];
    return pagina.resultados.filter((c) => c.slug !== this.slug());
  });

  readonly cargando = computed(() => this.recursoCategoria.isLoading() || this.recursoGuias.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recursoCategoria.error();
    return error ? normalizarError(error) : null;
  });

  readonly esNoEncontrado = computed(() => this.error()?.categoria === 'no_encontrado');

  recargar(): void {
    this.recursoCategoria.reload();
    this.recursoGuias.reload();
  }
}
