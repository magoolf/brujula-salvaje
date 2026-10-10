import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap } from '@angular/router';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { ResultadoConsulta, validarConsulta } from '../../../shared/ui/campo-busqueda/validar-consulta';
import { BusquedaRepositorio } from '../data/busqueda.repositorio';
import { QueryParamsBusqueda, filtrosDesdeQueryParams } from '../domain/filtros';
import { FiltrosBusqueda } from '../domain/modelos';

function paramMapARegistro(mapa: ParamMap): QueryParamsBusqueda {
  const registro: Record<string, string | readonly string[]> = {};
  for (const clave of mapa.keys) {
    const valores = mapa.getAll(clave);
    registro[clave] = valores.length > 1 ? valores : (valores[0] ?? '');
  }
  return registro;
}

/**
 * STATE de "Resultados de búsqueda" (SCR-017, FEAT-016). `q`/`tipo`/`pagina` viven en la URL
 * (RULE-018/019). AC-020: `q` fuera de 2..100 caracteres no dispara ninguna petición (validación
 * en el cliente con la misma función que usa `CampoBusqueda`, DEC-AUTO-048); el mensaje en línea se
 * deriva de `validacion()`, nunca de un error HTTP.
 *
 * NO usa `providedIn: 'root'`: se provee en `PaginaBusqueda` para que `inject(ActivatedRoute)`
 * resuelva contra la ruta activa.
 */
@Injectable()
export class BusquedaStore {
  private readonly repo = inject(BusquedaRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly queryParamMap = toSignal(this.ruta.queryParamMap, { requireSync: true });

  readonly filtros = computed<FiltrosBusqueda>(() =>
    filtrosDesdeQueryParams(paramMapARegistro(this.queryParamMap())),
  );

  /** `null` si nunca se envió una consulta (primera visita a `/buscar` sin `q`). */
  readonly validacion = computed<ResultadoConsulta | null>(() => {
    const q = this.filtros().q;
    if (q === '') return null;
    return validarConsulta(q);
  });

  // `id` (TKT-016): el valor del SSR viaja en TransferState y el recurso nace resuelto al hidratar
  // (sin esqueleto ni recreación del DOM del servidor). La clave incluye los parámetros iniciales de
  // la URL, así que nunca se sirve un valor transferido de otra URL; y Angular solo la consulta en el
  // primer cálculo del recurso mientras dura la hidratación, nunca al navegar después en el cliente.
  // En la búsqueda la clave lleva la consulta y todos los filtros de la URL inicial.
  private readonly recursoAgrupada = resource({
    id: `recurso:busqueda-agrupada:${JSON.stringify(this.filtros())}`,
    params: () => {
      const f = this.filtros();
      const v = this.validacion();
      return f.tipo === null && v?.valida ? v.consulta : undefined;
    },
    loader: ({ params }) => this.repo.buscar(params),
  });

  // `id` (TKT-016): ver el comentario de `recursoAgrupada`.
  private readonly recursoGrupo = resource({
    id: `recurso:busqueda-grupo:${JSON.stringify(this.filtros())}`,
    params: () => {
      const f = this.filtros();
      const v = this.validacion();
      return f.tipo !== null && v?.valida ? { tipo: f.tipo, q: v.consulta, pagina: f.pagina } : undefined;
    },
    loader: ({ params }) => this.repo.buscarPorGrupo(params.tipo, params.q, params.pagina),
  });

  readonly agrupada = computed(() =>
    this.recursoAgrupada.hasValue() ? this.recursoAgrupada.value() : null,
  );
  readonly grupo = computed(() => (this.recursoGrupo.hasValue() ? this.recursoGrupo.value() : null));
  readonly cargando = computed(() => this.recursoAgrupada.isLoading() || this.recursoGrupo.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.filtros().tipo === null ? this.recursoAgrupada.error() : this.recursoGrupo.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recursoAgrupada.reload();
    this.recursoGrupo.reload();
  }
}
