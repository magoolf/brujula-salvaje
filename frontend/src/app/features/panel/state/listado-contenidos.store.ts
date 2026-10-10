import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap } from '@angular/router';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import {
  FiltrosContenidos,
  admiteFiltros,
  filtrosContenidosDesdeQuery,
  hayFiltrosContenidos,
  tipoDeRuta,
} from '../domain/contenidos';
import { TipoContenido } from '../domain/modelos';

const CODIGO_PAGINA_FUERA = 'pagina_fuera_de_rango';

function aRegistro(mapa: ParamMap): Record<string, string | null> {
  const registro: Record<string, string | null> = {};
  for (const clave of mapa.keys) registro[clave] = mapa.get(clave);
  return registro;
}

/**
 * STATE del Listado de contenidos (SCR-035, FEAT-033, AP-20): el tipo sale de la ruta
 * (`/panel/contenido/:tipo`) y los filtros y la página de la URL (`?estado=&q=&pagina=`). El store
 * solo lee la URL; la UI cambia los filtros navegando (estado compartible y con «Atrás»).
 */
@Injectable()
export class ListadoContenidosStore {
  private readonly repo = inject(PanelContenidosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly params = toSignal(this.ruta.paramMap, { requireSync: true });
  private readonly query = toSignal(this.ruta.queryParamMap, { requireSync: true });

  /** null si el segmento no es un tipo válido (→ página no encontrada). */
  readonly tipo = computed<TipoContenido | null>(() => tipoDeRuta(this.params().get('tipo')));
  readonly filtros = computed<FiltrosContenidos>(() => {
    const filtros = filtrosContenidosDesdeQuery(aRegistro(this.query()));
    const tipo = this.tipo();
    // Las páginas institucionales solo admiten paginación (contrato).
    return tipo !== null && !admiteFiltros(tipo) ? { ...filtros, estado: null, q: '' } : filtros;
  });

  private readonly listado = resource({
    params: () => {
      const tipo = this.tipo();
      return tipo === null ? undefined : { tipo, filtros: this.filtros() };
    },
    loader: ({ params }) => this.repo.listar(params.tipo, params.filtros),
  });

  readonly pagina = computed(() => (this.listado.hasValue() ? this.listado.value() : null));
  readonly cargando = computed(() => this.listado.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.listado.error();
    return error ? normalizarError(error) : null;
  });
  /** 403 en la feature → SCR-048 (Skill_Frontend §12). */
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly paginaFueraDeRango = computed(() => this.error()?.codigo === CODIGO_PAGINA_FUERA);
  readonly conFiltros = computed(() => hayFiltrosContenidos(this.filtros()));
  /** EMPTY de verdad: «Aún no hay {tipo}» + Nuevo. */
  readonly vacio = computed(() => {
    const pagina = this.pagina();
    return pagina !== null && pagina.total === 0 && !this.conFiltros();
  });
  readonly sinCoincidencias = computed(() => {
    const pagina = this.pagina();
    return pagina !== null && pagina.total === 0 && this.conFiltros();
  });

  recargar(): void {
    this.listado.reload();
  }
}
