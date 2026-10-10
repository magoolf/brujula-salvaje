import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap } from '@angular/router';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelCuentasRepositorio } from '../data/panel-cuentas.repositorio';
import {
  FiltrosAuditoria,
  OpcionActor,
  errorRangoFechas,
  filtrosAuditoriaDesdeQuery,
  hayFiltrosAuditoria,
} from '../domain/auditoria';

const CODIGO_PAGINA_FUERA = 'pagina_fuera_de_rango';

function aRegistro(mapa: ParamMap): Record<string, string | null> {
  const registro: Record<string, string | null> = {};
  for (const clave of mapa.keys) registro[clave] = mapa.get(clave);
  return registro;
}

/**
 * STATE del Registro de auditoría (SCR-046, FEAT-046, FLOW-016, AC-030): solo lectura. Los filtros
 * y la página salen de la URL; la UI los cambia navegando. Un rango de fechas invertido no se
 * consulta. Las cuentas del equipo alimentan el filtro «Actor».
 */
@Injectable()
export class AuditoriaStore {
  private readonly repo = inject(PanelCuentasRepositorio);

  private readonly query = toSignal(inject(ActivatedRoute).queryParamMap, { requireSync: true });

  readonly filtros = computed<FiltrosAuditoria>(() => filtrosAuditoriaDesdeQuery(aRegistro(this.query())));
  readonly errorFechas = computed(() => errorRangoFechas(this.filtros().desde, this.filtros().hasta));

  private readonly recurso = resource({
    params: () => (this.errorFechas() === null ? this.filtros() : undefined),
    loader: ({ params }) => this.repo.auditoria(params),
  });
  private readonly recursoActores = resource({ loader: () => this.repo.actores() });

  readonly pagina = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly paginaFueraDeRango = computed(() => this.error()?.codigo === CODIGO_PAGINA_FUERA);
  readonly conFiltros = computed(() => hayFiltrosAuditoria(this.filtros()));
  readonly actores = computed<readonly OpcionActor[]>(() =>
    this.recursoActores.hasValue() ? this.recursoActores.value() : [],
  );

  recargar(): void {
    this.recurso.reload();
  }
}
