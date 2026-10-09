import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { defer, map } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import {
  CampoCatalogacion,
  FormularioCatalogacion,
  Medio,
  entradaDesdeFormulario,
  licenciasAsignables,
  puedeReactivar,
  puedeRetirar,
  validarCatalogacion,
} from '../domain/medios';

/** Id de la ruta `/panel/medios/:id` (un id no numérico es un 404, sin pedir nada). */
function idDeRuta(valor: string | null): number | null {
  if (valor === null || !/^[1-9]\d{0,17}$/.test(valor)) return null;
  const id = Number(valor);
  return Number.isSafeInteger(id) ? id : null;
}

/**
 * STATE del Detalle de medio (SCR-040, FEAT-042, FLOW-013 pasos 5-6, RULE-005, AC-117):
 * medio, usos (paginados) y licencias; comandos catalogar, retirar y reactivar. Tras cada escritura
 * el store fija el medio devuelto por la API y relee los usos (§7: invalidación en el store).
 */
@Injectable()
export class DetalleMedioStore {
  private readonly repo = inject(PanelMediosRepositorio);

  private readonly id = toSignal(
    inject(ActivatedRoute).paramMap.pipe(map((p) => idDeRuta(p.get('id')))),
    { requireSync: true },
  );
  private readonly _paginaUsos = signal(1);
  private readonly _avisoExito = signal<string | null>(null);

  private readonly recursoMedio = resource({
    params: () => this.id() ?? undefined,
    loader: ({ params }) => this.repo.obtener(params),
  });
  private readonly recursoUsos = resource({
    params: () => {
      const id = this.id();
      return id === null ? undefined : { id, pagina: this._paginaUsos() };
    },
    loader: ({ params }) => this.repo.usos(params.id, params.pagina),
  });
  private readonly catalogoLicencias = resource({ loader: () => this.repo.licencias() });

  readonly medio = computed<Medio | null>(() =>
    this.recursoMedio.hasValue() ? (this.recursoMedio.value() ?? null) : null,
  );
  readonly cargando = computed(() => this.recursoMedio.isLoading() && this.medio() === null);
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recursoMedio.error();
    return error ? normalizarError(error) : null;
  });
  readonly noEncontrado = computed(
    () => this.id() === null || this.error()?.categoria === 'no_encontrado',
  );
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly usos = computed(() => (this.recursoUsos.hasValue() ? this.recursoUsos.value() : null));
  readonly cargandoUsos = computed(() => this.recursoUsos.isLoading());
  readonly errorUsos = computed(() => (this.recursoUsos.error() ? true : false));
  readonly licencias = computed(() => {
    const catalogo = this.catalogoLicencias.hasValue() ? this.catalogoLicencias.value() : [];
    return licenciasAsignables(catalogo, this.medio()?.licencia ?? null);
  });
  readonly errorLicencias = computed(() => (this.catalogoLicencias.error() ? true : false));
  readonly puedeRetirar = computed(() => {
    const medio = this.medio();
    return medio !== null && puedeRetirar(medio);
  });
  readonly puedeReactivar = computed(() => {
    const medio = this.medio();
    return medio !== null && puedeReactivar(medio);
  });
  readonly avisoExito = this._avisoExito.asReadonly();

  validar(formulario: FormularioCatalogacion): Partial<Record<CampoCatalogacion, string>> {
    const medio = this.medio();
    return medio === null ? {} : validarCatalogacion(formulario, medio.estado);
  }

  async catalogar(formulario: FormularioCatalogacion): Promise<ErrorApi | null> {
    const medio = this.medio();
    if (medio === null) return null;
    this._avisoExito.set(null);
    const estadoAnterior = medio.estado;
    return ejecutar(
      defer(() => this.repo.catalogar(medio.id, entradaDesdeFormulario(formulario))),
      (actualizado) => {
        this.fijar(actualizado);
        this._avisoExito.set(
          actualizado.estado === 'DISPONIBLE' && estadoAnterior !== 'DISPONIBLE'
            ? 'Imagen disponible.'
            : 'Guardaste los datos de la imagen.',
        );
      },
    );
  }

  /** 409 `medio_en_uso`: se releen el medio y los usos para mostrar el bloqueo actualizado. */
  async retirar(): Promise<ErrorApi | null> {
    const medio = this.medio();
    if (medio === null) return null;
    this._avisoExito.set(null);
    const error = await ejecutar(
      defer(() => this.repo.retirar(medio.id)),
      (actualizado) => {
        this.fijar(actualizado);
        this._avisoExito.set('Retiraste la imagen. Ya no se puede usar en contenido nuevo.');
      },
    );
    if (error?.categoria === 'conflicto') this.recargar();
    return error;
  }

  async reactivar(): Promise<ErrorApi | null> {
    const medio = this.medio();
    if (medio === null) return null;
    this._avisoExito.set(null);
    return ejecutar(
      defer(() => this.repo.reactivar(medio.id)),
      (actualizado) => {
        this.fijar(actualizado);
        this._avisoExito.set('Reactivaste la imagen. Completa sus datos para volver a usarla.');
      },
    );
  }

  irAPaginaUsos(pagina: number): void {
    const usos = this.usos();
    const total = usos?.totalPaginas ?? 1;
    this._paginaUsos.set(Math.min(Math.max(1, pagina), Math.max(1, total)));
  }

  recargar(): void {
    this.recursoMedio.reload();
    this.recursoUsos.reload();
  }

  private fijar(medio: Medio): void {
    this.recursoMedio.value.set(medio);
    this.recursoUsos.reload();
  }
}
