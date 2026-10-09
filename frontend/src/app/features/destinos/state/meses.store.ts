import { Injectable, computed, inject, resource } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { map } from 'rxjs';

import { normalizarError } from '../../../core/http/normalizar-error';
import { ErrorApi } from '../../../core/http/error-api.model';
import { DestinosRepositorio } from '../data/destinos.repositorio';
import { FILTROS_VACIOS } from '../domain/filtros';

/** STATE de «¿Dónde ir cada mes?» (SCR-015, FEAT-018): los 12 meses con su destacado. */
@Injectable({ providedIn: 'root' })
export class MesesIndiceStore {
  private readonly repo = inject(DestinosRepositorio);

  // `id` (TKT-016): ver destinos-listado.store.ts (hidratación sin esqueleto ni recreación del DOM).
  private readonly recurso = resource({
    id: 'recurso:destinos-meses',
    loader: () => this.repo.meses(),
  });

  // `hasValue()` evita que `.value()` lance al leerlo mientras el recurso está en error.
  readonly meses = computed(() => (this.recurso.hasValue() ? this.recurso.value() : []));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
}

/**
 * STATE de «Destinos del mes» (SCR-016): los destinos cuya mejor época incluye `{mes}`.
 * NO usa `providedIn: 'root'` (ver la explicación completa en `destino-detalle.store.ts`): se
 * provee en `PaginaDestinosDelMes` para que `inject(ActivatedRoute)` resuelva contra la ruta activa.
 */
@Injectable()
export class DestinosDelMesStore {
  private readonly repo = inject(DestinosRepositorio);
  private readonly ruta = inject(ActivatedRoute);

  private readonly parametroMes = toSignal(
    this.ruta.paramMap.pipe(map((p) => p.get('mes') ?? '')),
    { requireSync: true },
  );

  /** `null` si el segmento de ruta no es un mes válido 1-12 (ST-NOTFOUND, SCR-016). */
  readonly mes = computed<number | null>(() => {
    const n = Number(this.parametroMes());
    return Number.isInteger(n) && n >= 1 && n <= 12 ? n : null;
  });

  private readonly recurso = resource({
    id: `recurso:destinos-del-mes:${this.mes()}`,
    params: () => this.mes(),
    loader: ({ params }) =>
      params === null
        ? Promise.resolve(null)
        : this.repo.listar({ ...FILTROS_VACIOS, mes: params }),
  });

  // `hasValue()` evita que `.value()` lance al leerlo mientras el recurso está en error.
  readonly pagina = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
}
