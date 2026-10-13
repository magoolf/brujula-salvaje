import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { InstitucionalRepositorio } from '../data/institucional.repositorio';
import { SlugInstitucional } from '../domain/modelos';

/**
 * STATE de la plantilla "Página institucional" (SCR-020, FEAT-023): reutilizada por las 4 rutas
 * legales/informativas (`/acerca-de`, `/politica-de-tratamiento-de-datos`, `/politica-de-cookies`,
 * `/aviso-legal`), cada una registrada en `app.routes.ts` con `data: { slug }`. El slug se lee de
 * `ActivatedRoute.data` (dato estático de la ruta, no un parámetro de URL).
 *
 * Solo `/acerca-de` necesita las escalas (Metodología) y solo `/politica-de-tratamiento-de-datos`
 * necesita la configuración (Responsable): ambos recursos se piden siempre (coste marginal bajo,
 * ya cacheados por HttpClient de otras páginas) y la UI decide qué mostrar según el slug.
 */
@Injectable()
export class PaginaInstitucionalStore {
  private readonly repo = inject(InstitucionalRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly slug = toSignal(
    this.ruta.data.pipe(map((d) => d['slug'] as SlugInstitucional)),
    { requireSync: true },
  );

  // `id` (TKT-016): el valor del SSR viaja en TransferState y el recurso nace resuelto al hidratar
  // (sin esqueleto ni recreación del DOM del servidor). La clave incluye los parámetros iniciales de
  // la URL, así que nunca se sirve un valor transferido de otra URL; y Angular solo la consulta en el
  // primer cálculo del recurso mientras dura la hidratación, nunca al navegar después en el cliente.
  private readonly recurso = resource({
    id: `recurso:pagina-institucional:${this.slug()}`,
    params: () => this.slug(),
    loader: ({ params }) => this.repo.pagina(params),
  });

  // `id` (TKT-016): ver el comentario de `recurso`.
  private readonly recursoEscalas = resource({
    id: 'recurso:institucional-escalas',
    loader: () => this.repo.escalas(),
  });
  private readonly recursoConfiguracion = resource({
    id: 'recurso:institucional-configuracion',
    loader: () => this.repo.configuracion(),
  });

  readonly pagina = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly escalas = computed(() => (this.recursoEscalas.hasValue() ? this.recursoEscalas.value() : null));
  readonly configuracion = computed(() =>
    this.recursoConfiguracion.hasValue() ? this.recursoConfiguracion.value() : null,
  );
  readonly cargando = computed(() => this.recurso.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recurso.reload();
  }
}
