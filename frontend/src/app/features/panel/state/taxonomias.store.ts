import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { defer, map } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelConfiguracionRepositorio } from '../data/panel-configuracion.repositorio';
import {
  Bloqueo,
  CampoTextoCatalogo,
  Catalogo,
  DEFINICION_CATALOGO,
  ElementoCatalogo,
  FormularioCatalogo,
  NivelEscalaPanel,
  Region,
  bloqueoDesdeError,
  catalogoDesdeQuery,
  entradaCatalogo,
  entradaConEstado,
  entradaNivel,
  nombreElemento,
  puedeEditarCatalogo,
  validarCatalogo,
} from '../domain/taxonomias';
import { SesionPanelStore } from './sesion-panel.store';

const CODIGO_BLOQUEO = 'dependencia_bloqueante';

/**
 * STATE de Taxonomías y catálogos (SCR-043, FEAT-044, RULE-007, RULE-014): la pestaña sale de la
 * URL (`?catalogo=`), se lee su catálogo y se ofrecen las altas, ediciones, retiros y
 * reactivaciones que permite el rol. Retirar en uso → 409 `dependencia_bloqueante`: el bloqueo
 * (con sus usos) queda en `bloqueo` para el ImpactSummary. Tras cada escritura se relee el
 * catálogo (§7: invalidación en el store).
 */
@Injectable()
export class TaxonomiasStore {
  private readonly repo = inject(PanelConfiguracionRepositorio);
  private readonly sesion = inject(SesionPanelStore);

  readonly catalogo = toSignal(
    inject(ActivatedRoute).queryParamMap.pipe(map((q) => catalogoDesdeQuery(q.get('catalogo')))),
    { requireSync: true },
  );

  private readonly _avisoExito = signal<string | null>(null);
  private readonly _bloqueo = signal<Bloqueo | null>(null);

  private readonly recursoLista = resource({
    params: () => {
      const catalogo = this.catalogo();
      return catalogo === 'escalas' ? undefined : catalogo;
    },
    loader: ({ params }) => this.repo.listar(params),
  });
  private readonly recursoEscalas = resource({
    params: () => (this.catalogo() === 'escalas' ? true : undefined),
    loader: () => this.repo.escalas(),
  });
  /** Regiones para el formulario y la tabla de países. */
  private readonly recursoRegiones = resource({
    params: () => (this.catalogo() === 'paises' ? true : undefined),
    loader: () => this.repo.listar('regiones'),
  });

  readonly definicion = computed(() => DEFINICION_CATALOGO[this.catalogo()]);
  readonly puedeEditar = computed(() => puedeEditarCatalogo(this.sesion.rol(), this.catalogo()));
  readonly elementos = computed<readonly ElementoCatalogo[] | null>(() => {
    if (this.catalogo() === 'escalas') return null;
    return this.recursoLista.hasValue() ? this.recursoLista.value() : null;
  });
  readonly escalas = computed(() => (this.recursoEscalas.hasValue() ? this.recursoEscalas.value() : null));
  readonly regiones = computed<readonly Region[]>(() => {
    const lista = this.recursoRegiones.hasValue() ? this.recursoRegiones.value() : [];
    return lista.filter((e): e is Region => e.catalogo === 'regiones');
  });
  readonly cargando = computed(() =>
    this.catalogo() === 'escalas' ? this.recursoEscalas.isLoading() : this.recursoLista.isLoading(),
  );
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.catalogo() === 'escalas' ? this.recursoEscalas.error() : this.recursoLista.error();
    return error ? normalizarError(error) : null;
  });
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly avisoExito = this._avisoExito.asReadonly();
  readonly bloqueo = this._bloqueo.asReadonly();

  nombreRegion(id: number): string {
    return this.regiones().find((r) => r.id === id)?.nombre ?? `Región #${id}`;
  }

  validar(catalogo: Catalogo, formulario: FormularioCatalogo): Partial<Record<CampoTextoCatalogo, string>> {
    return validarCatalogo(catalogo, formulario);
  }

  /** Alta (elemento null) o edición; la edición conserva el estado activo del elemento. */
  async guardar(formulario: FormularioCatalogo, elemento: ElementoCatalogo | null): Promise<ErrorApi | null> {
    const catalogo = this.catalogo();
    if (catalogo === 'escalas') return null;
    this.limpiarAvisos();
    const entrada = entradaCatalogo(catalogo, formulario, elemento?.activo ?? true);
    const def = DEFINICION_CATALOGO[catalogo];
    return ejecutar(
      defer(() => (elemento === null ? this.repo.crear(entrada) : this.repo.actualizar(elemento.id, entrada))),
      (guardado) => {
        this.recursoLista.reload();
        this._avisoExito.set(
          elemento === null
            ? `Se creó «${nombreElemento(guardado)}» en ${def.etiqueta.toLowerCase()}.`
            : `Se guardaron los cambios de «${nombreElemento(guardado)}».`,
        );
      },
    );
  }

  /** Retirar (activo=false) o reactivar (activo=true). Un retiro bloqueado deja el bloqueo visible. */
  async cambiarEstado(elemento: ElementoCatalogo, activo: boolean): Promise<ErrorApi | null> {
    this.limpiarAvisos();
    const error = await ejecutar(
      defer(() => this.repo.actualizar(elemento.id, entradaConEstado(elemento, activo))),
      (guardado) => {
        this.recursoLista.reload();
        this._avisoExito.set(
          activo ? `«${nombreElemento(guardado)}» vuelve a estar activo.` : `Se retiró «${nombreElemento(guardado)}».`,
        );
      },
    );
    if (error?.codigo === CODIGO_BLOQUEO) {
      this._bloqueo.set(bloqueoDesdeError(error.mensaje, error.extra));
      return null;
    }
    return error;
  }

  async guardarNivel(nivel: NivelEscalaPanel, formulario: FormularioCatalogo): Promise<ErrorApi | null> {
    this.limpiarAvisos();
    return ejecutar(
      defer(() => this.repo.actualizarNivel(nivel.id, entradaNivel(formulario))),
      (guardado) => {
        this.recursoEscalas.reload();
        this._avisoExito.set(`Se guardó el nivel ${guardado.nivel} «${guardado.etiqueta}».`);
      },
    );
  }

  limpiarAvisos(): void {
    this._avisoExito.set(null);
    this._bloqueo.set(null);
  }

  recargar(): void {
    if (this.catalogo() === 'escalas') this.recursoEscalas.reload();
    else this.recursoLista.reload();
  }
}
