import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import {
  FILTROS_VACIOS,
  FiltrosMedios,
  Medio,
  ModoSeleccion,
  alternarSeleccion,
  conFiltro,
  esSeleccionable,
  mover,
} from '../domain/medios';

export interface ConfiguracionSelector {
  readonly modo: ModoSeleccion;
  readonly maximo: number | null;
  readonly permitirNoDisponibles: boolean;
  readonly seleccionInicial: readonly Medio[];
}

/**
 * STATE del Selector de medios (SCR-041, FEAT-034/041). A diferencia de la biblioteca, los filtros
 * viven en memoria (el selector es un diálogo sobre otra pantalla y no debe tocar su URL). Por
 * defecto lista los DISPONIBLES (RULE-005); la selección conserva el orden en que se eligió y se
 * puede reordenar (galería). La lista solo se carga mientras el diálogo está abierto.
 */
@Injectable()
export class SelectorMediosStore {
  private readonly repo = inject(PanelMediosRepositorio);

  private readonly _activo = signal(false);
  private readonly _filtros = signal<FiltrosMedios>({ ...FILTROS_VACIOS, estado: 'DISPONIBLE' });
  private readonly _seleccion = signal<readonly Medio[]>([]);
  private readonly _config = signal<ConfiguracionSelector>({
    modo: 'varios',
    maximo: null,
    permitirNoDisponibles: false,
    seleccionInicial: [],
  });

  private readonly listado = resource({
    params: () => (this._activo() ? this._filtros() : undefined),
    loader: ({ params }) => this.repo.listar(params),
  });
  private readonly catalogoLicencias = resource({
    params: () => (this._activo() ? true : undefined),
    loader: () => this.repo.licencias(),
  });

  readonly filtros = this._filtros.asReadonly();
  readonly seleccion = this._seleccion.asReadonly();
  readonly modo = computed(() => this._config().modo);
  readonly pagina = computed(() => (this.listado.hasValue() ? (this.listado.value() ?? null) : null));
  readonly cargando = computed(() => this.listado.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.listado.error();
    return error ? normalizarError(error) : null;
  });
  readonly licencias = computed(() =>
    this.catalogoLicencias.hasValue() ? (this.catalogoLicencias.value() ?? []) : [],
  );
  readonly vacio = computed(() => this.pagina()?.total === 0);
  readonly idsSeleccionados = computed(() => new Set(this._seleccion().map((m) => m.id)));
  readonly limiteAlcanzado = computed(() => {
    const { maximo, modo } = this._config();
    return modo === 'varios' && maximo !== null && this._seleccion().length >= maximo;
  });

  /** Abre el selector con su configuración (la selección parte de la del editor). */
  abrir(config: ConfiguracionSelector): void {
    this._config.set(config);
    this._seleccion.set(config.seleccionInicial);
    this._filtros.set({ ...FILTROS_VACIOS, estado: config.permitirNoDisponibles ? null : 'DISPONIBLE' });
    this._activo.set(true);
  }

  cerrar(): void {
    this._activo.set(false);
  }

  seleccionable(medio: Medio): boolean {
    return esSeleccionable(medio, this._config().permitirNoDisponibles);
  }

  alternar(medio: Medio): void {
    if (!this.seleccionable(medio)) return;
    const { modo, maximo } = this._config();
    this._seleccion.update((actual) => alternarSeleccion(actual, medio, modo, maximo));
  }

  quitar(id: number): void {
    this._seleccion.update((actual) => actual.filter((m) => m.id !== id));
  }

  moverSeleccion(desde: number, hasta: number): void {
    this._seleccion.update((actual) => mover(actual, desde, hasta));
  }

  filtrar(cambio: Partial<FiltrosMedios>): void {
    this._filtros.update((actual) => conFiltro(actual, cambio));
  }

  irAPagina(pagina: number): void {
    const total = this.pagina()?.totalPaginas ?? 1;
    this._filtros.update((actual) => ({ ...actual, pagina: Math.min(Math.max(1, pagina), total) }));
  }

  /** Tras subir desde el propio selector: relee la lista. */
  recargar(): void {
    this.listado.reload();
  }

  /**
   * «Usar la existente» de un duplicado (ALT-021): trae el medio y lo selecciona si se puede.
   * Si no es seleccionable (p. ej. pendiente de datos) devuelve un error de regla de negocio.
   */
  async usarExistente(id: number): Promise<ErrorApi | null> {
    let medio: Medio | null = null;
    const error = await ejecutar(
      defer(() => this.repo.obtener(id)),
      (encontrado) => (medio = encontrado),
    );
    if (error !== null) return error;
    const existente = medio as Medio | null;
    if (existente === null || !this.seleccionable(existente)) {
      return {
        tipo: 'regla_negocio',
        categoria: 'regla_negocio',
        codigo: 'medio_no_disponible',
        mensaje: 'Esa imagen aún no está disponible: completa sus datos en Medios para usarla.',
        campos: {},
        traceId: null,
        extra: {},
      };
    }
    if (!this.idsSeleccionados().has(existente.id)) this.alternar(existente);
    return null;
  }
}
