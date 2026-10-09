import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, ParamMap } from '@angular/router';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { DestinosRepositorio } from '../data/destinos.repositorio';
import { QueryParamsDestinos, filtrosDesdeQueryParams } from '../domain/filtros';
import { FiltrosDestinos } from '../domain/modelos';

function paramMapARegistro(mapa: ParamMap): QueryParamsDestinos {
  const registro: Record<string, string | readonly string[]> = {};
  for (const clave of mapa.keys) {
    const valores = mapa.getAll(clave);
    registro[clave] = valores.length > 1 ? valores : (valores[0] ?? '');
  }
  return registro;
}

/**
 * STATE de "Explorar destinos" (SCR-002, FEAT-003/004). El estado de filtros vive en la URL
 * (FEAT-004): este store solo LEE `ActivatedRoute.queryParamMap` (vía Signals) y dispara los
 * recursos de listado y facetas; no expone comandos de escritura porque cada filtro es un enlace
 * real (Regla 03: estado público solo lectura).
 *
 * NO usa `providedIn: 'root'` (ver la explicación completa en `destino-detalle.store.ts`): se
 * provee en `PaginaDestinos` para que `inject(ActivatedRoute)` resuelva contra la ruta activa.
 */
@Injectable()
export class DestinosListadoStore {
  private readonly repo = inject(DestinosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly queryParamMap = toSignal(this.ruta.queryParamMap, { requireSync: true });

  readonly filtros = computed<FiltrosDestinos>(() =>
    filtrosDesdeQueryParams(paramMapARegistro(this.queryParamMap())),
  );

  // `id` (TKT-016): el valor del SSR viaja en TransferState y el recurso nace resuelto en la
  // hidratación, así que la plantilla reutiliza el DOM del servidor en vez de pasar por el
  // esqueleto (layout shift del pie) y recrear el listado. Solo se usa en la primera hidratación.
  private readonly recursoListado = resource({
    id: 'recurso:destinos-listado',
    params: () => this.filtros(),
    loader: ({ params }) => this.repo.listar(params),
  });

  private readonly recursoFacetas = resource({
    id: 'recurso:destinos-facetas',
    loader: () => this.repo.facetas(),
  });

  // `hasValue()` evita que `.value()` lance al leerlo mientras el recurso está en error.
  readonly pagina = computed(() =>
    this.recursoListado.hasValue() ? this.recursoListado.value() : null,
  );
  readonly facetas = computed(() =>
    this.recursoFacetas.hasValue() ? this.recursoFacetas.value() : null,
  );
  readonly cargando = computed(() => this.recursoListado.isLoading());
  readonly cargandoFacetas = computed(() => this.recursoFacetas.isLoading());

  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recursoListado.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recursoListado.reload();
  }
}
