import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { DestinosRepositorio } from '../data/destinos.repositorio';
import { mapAlternativasRetirado } from '../data/destinos.mapper';
import { DestinoRetirado } from '../domain/modelos';

/**
 * STATE de la ficha de destino (SCR-004, FEAT-006). El slug se lee de `ActivatedRoute.paramMap`
 * (reactivo: los enlaces "Sigue explorando" navegan entre fichas reutilizando el mismo componente
 * de ruta). DEC-AUTO-040/AC-028: inexistente → 404 (SCR-023), retirado → 410 (SCR-024) con sus
 * alternativas; ambos se derivan del `ErrorApi` normalizado, nunca de un `if` sobre el status HTTP
 * en la UI (Regla 13).
 *
 * NO usa `providedIn: 'root'`: un servicio tree-shakable en la raíz resuelve sus propias
 * dependencias (`inject(ActivatedRoute)`) contra el inyector RAÍZ de la app, no contra el de quien
 * lo pide (`PaginaDestino`) — por eso siempre vería la ruta raíz («») y nunca el segmento
 * `destinos/:slug` (bug real verificado con datos reales: slug siempre vacío → 404 constante).
 * Se provee en el propio componente (`providers: [DestinoDetalleStore]`) para que su inyector sea
 * el de la ruta activa, con una instancia nueva por activación (correcto: es estado de esa ruta).
 */
@Injectable()
export class DestinoDetalleStore {
  private readonly repo = inject(DestinosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly slug = toSignal(this.ruta.paramMap.pipe(map((p) => p.get('slug') ?? '')), {
    requireSync: true,
  });

  // `id` (TKT-016): el valor del SSR viaja en TransferState y el recurso nace resuelto al hidratar
  // (sin esqueleto ni recreación del DOM del servidor). La clave incluye los parámetros iniciales de
  // la URL, así que nunca se sirve un valor transferido de otra URL; y Angular solo la consulta en el
  // primer cálculo del recurso mientras dura la hidratación, nunca al navegar después en el cliente.
  private readonly recurso = resource({
    id: `recurso:destino-detalle:${this.slug()}`,
    params: () => this.slug(),
    loader: ({ params }) => this.repo.detalle(params),
  });

  /** RULE-010: se pide una sola vez (sin `params`, el recurso no depende del slug). */
  private readonly recursoDescargo = resource({
    id: 'recurso:destino-descargo',
    loader: () => this.repo.textoDescargo(),
  });
  // `hasValue()` evita que `.value()` lance al leerlo mientras el recurso está en error.
  readonly descargo = computed(() =>
    this.recursoDescargo.hasValue() ? this.recursoDescargo.value() : null,
  );

  readonly destino = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  readonly esNoEncontrado = computed(() => this.error()?.categoria === 'no_encontrado');
  readonly esRetirado = computed(() => this.error()?.categoria === 'retirado');

  readonly retirado = computed<DestinoRetirado | null>(() => {
    const error = this.error();
    if (error === null || error.categoria !== 'retirado') return null;
    const listadoPadre = error.extra['listado_padre'];
    return {
      rutaListadoPadre: typeof listadoPadre === 'string' && listadoPadre.length > 0 ? listadoPadre : '/destinos',
      alternativas: mapAlternativasRetirado(error.extra['alternativas']),
    };
  });

  recargar(): void {
    this.recurso.reload();
  }
}
