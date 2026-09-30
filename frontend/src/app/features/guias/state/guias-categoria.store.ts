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

  private readonly recursoCategoria = resource({
    params: () => this.slug(),
    loader: ({ params }) => this.repo.categoria(params),
  });

  private readonly recursoGuias = resource({
    params: () => ({ slug: this.slug(), pagina: this.pagina$() }),
    loader: ({ params }) => this.repo.listarGuias(params.slug, params.pagina),
  });

  private readonly recursoOtrasCategorias = resource({ loader: () => this.repo.listarCategorias(1) });

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
