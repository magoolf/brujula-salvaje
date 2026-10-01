import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap } from '@angular/router';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import { FiltrosMedios, filtrosDesdeQuery, hayFiltros } from '../domain/medios';

const CODIGO_PAGINA_FUERA = 'pagina_fuera_de_rango';

function aRegistro(mapa: ParamMap): Record<string, string | null> {
  const registro: Record<string, string | null> = {};
  for (const clave of mapa.keys) registro[clave] = mapa.get(clave);
  return registro;
}

/**
 * STATE de la Biblioteca de medios (SCR-039, FEAT-041/042, AP-22). Los filtros y la página viven en
 * la URL (`?estado=&licencia=&q=&en_uso=&pagina=`): el store solo LEE `queryParamMap` y carga la
 * página correspondiente; la UI cambia los filtros navegando (estado compartible y con «Atrás»).
 * Se provee en la página (no en root) para que `ActivatedRoute` sea la ruta activa.
 */
@Injectable()
export class BibliotecaMediosStore {
  private readonly repo = inject(PanelMediosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly query = toSignal(this.ruta.queryParamMap, { requireSync: true });

  readonly filtros = computed<FiltrosMedios>(() => filtrosDesdeQuery(aRegistro(this.query())));

  private readonly listado = resource({
    params: () => this.filtros(),
    loader: ({ params }) => this.repo.listar(params),
  });
  private readonly catalogoLicencias = resource({ loader: () => this.repo.licencias() });

  readonly pagina = computed(() => (this.listado.hasValue() ? this.listado.value() : null));
  readonly cargando = computed(() => this.listado.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.listado.error();
    return error ? normalizarError(error) : null;
  });
  /** 403 en la feature → SCR-048 (Skill_Frontend §12). */
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  /** Página inexistente (p. ej. tras borrar filtros): se ofrece volver a la primera. */
  readonly paginaFueraDeRango = computed(() => this.error()?.codigo === CODIGO_PAGINA_FUERA);
  readonly licencias = computed(() =>
    this.catalogoLicencias.hasValue() ? this.catalogoLicencias.value() : [],
  );
  readonly conFiltros = computed(() => hayFiltros(this.filtros()));
  /** Biblioteca vacía de verdad (sin filtros): «Sube tu primera imagen». */
  readonly bibliotecaVacia = computed(() => {
    const pagina = this.pagina();
    return pagina !== null && pagina.total === 0 && !this.conFiltros();
  });
  readonly sinCoincidencias = computed(() => {
    const pagina = this.pagina();
    return pagina !== null && pagina.total === 0 && this.conFiltros();
  });

  /** Tras subir o ante un error, se vuelve a leer la página actual (§7: el store invalida). */
  recargar(): void {
    this.listado.reload();
  }
}
