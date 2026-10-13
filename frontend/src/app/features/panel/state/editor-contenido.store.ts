import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { defer } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { erroresDeFormulario } from '../data/contenidos.mapper';
import { nuevaClaveIdempotencia } from '../data/panel-medios.repositorio';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import { RequisitosPublicacion } from '../domain/ciclo-editorial';
import {
  AccionesEditor,
  ContenidoEditable,
  EscalasContenido,
  accionesEditor,
  nivelesPorDefecto,
  puedeEditarPagina,
  tipoDeRuta,
} from '../domain/contenidos';
import {
  ErroresFormulario,
  FormularioContenido,
  ResultadoBusqueda,
  enriquecerReferencias,
  formularioVacio,
} from '../domain/formulario-contenido';
import { EstadoEditorial, TipoContenido } from '../domain/modelos';
import { BorradorEnMemoria, MemoriaEditor } from './memoria-editor';
import { SesionPanelStore } from './sesion-panel.store';

const CONFLICTO_VERSION = 'conflicto_version';

/** Id de la ruta (`nuevo` → null; un id no numérico es un 404 sin pedir nada). */
export function idDeSegmento(valor: string | null): number | null | 'invalido' {
  if (valor === 'nuevo') return null;
  if (valor === null || !/^[1-9]\d{0,17}$/.test(valor)) return 'invalido';
  const id = Number(valor);
  return Number.isSafeInteger(id) ? id : 'invalido';
}

/** Tipos de cada catálogo que necesita el formulario. */
const CON_PAISES: readonly TipoContenido[] = ['DESTINO'];
const CON_TIPOS: readonly TipoContenido[] = ['DESTINO', 'ITINERARIO', 'GUIA'];
const CON_CATEGORIAS: readonly TipoContenido[] = ['GUIA'];
const CON_ESCALAS: readonly TipoContenido[] = ['DESTINO', 'ITINERARIO', 'TIPO'];

/**
 * STATE del Editor de contenido (SCR-036, FEAT-034..040, FEAT-050, FLOW-011/012): contenido y
 * catálogos, guardado con bloqueo optimista (ALT-016, AC-110), eliminación de borradores,
 * reactivación, revisiones y restauración, y requisitos de publicación (CompletenessPanel). Los
 * valores del formulario los posee la UI (señales de los controles): los comandos los reciben como
 * `FormularioContenido` y devuelven `ErrorApi | null` (Regla 12). Se provee en la página.
 */
@Injectable()
export class EditorContenidoStore {
  private readonly repo = inject(PanelContenidosRepositorio);
  private readonly memoria = inject(MemoriaEditor);
  private readonly sesion = inject(SesionPanelStore);
  private readonly params = toSignal(inject(ActivatedRoute).paramMap, { requireSync: true });

  // 1. Señales privadas
  private readonly _contenido = signal<ContenidoEditable | null>(null);
  private readonly _guardando = signal(false);
  private readonly _procesando = signal(false);
  private readonly _guardadoEn = signal<Date | null>(null);
  private readonly _erroresServidor = signal<ErroresFormulario>({});
  private readonly _conflicto = signal(false);
  private readonly _errorGuardado = signal<ErrorApi | null>(null);
  private readonly _requisitosFormulario = signal<RequisitosPublicacion | null>(null);
  private readonly _paginaRevisiones = signal(1);
  private readonly _restaurado = signal<{ numero: number; formulario: FormularioContenido } | null>(null);
  private readonly _aviso = signal<string | null>(this.memoria.tomarAviso());

  // 2. Recursos de lectura
  readonly tipo = computed<TipoContenido | null>(() => tipoDeRuta(this.params().get('tipo')));
  private readonly segmentoId = computed(() => idDeSegmento(this.params().get('id')));

  private readonly recursoContenido = resource({
    params: () => {
      const tipo = this.tipo();
      const id = this.segmentoId();
      return tipo === null || id === null || id === 'invalido' ? undefined : { tipo, id };
    },
    loader: ({ params }) => this.repo.obtener(params.tipo, params.id),
  });
  private readonly recursoRevisiones = resource({
    params: () => {
      const contenido = this.contenido();
      // Sin acceso (403 o página legal con Editor, RULE-014/TKT-050) no se pide el historial: el
      // servidor respondería 403 y la vista es SCR-048 (QA TKT-050 OBS-QA050-01).
      if (contenido === null || this.accesoDenegado()) return undefined;
      return {
        tipo: contenido.tipo,
        id: contenido.id,
        pagina: this._paginaRevisiones(),
        version: contenido.version,
      };
    },
    loader: ({ params }) => this.repo.revisiones(params.tipo, params.id, params.pagina),
  });
  private readonly recursoPaises = resource({
    params: () => (this.necesita(CON_PAISES) ? true : undefined),
    loader: () => this.repo.paises(),
  });
  private readonly recursoTipos = resource({
    params: () => (this.necesita(CON_TIPOS) ? true : undefined),
    loader: () => this.repo.tiposAventura(),
  });
  private readonly recursoCategorias = resource({
    params: () => (this.necesita(CON_CATEGORIAS) ? true : undefined),
    loader: () => this.repo.categoriasGuia(),
  });
  private readonly recursoEscalas = resource({
    params: () => (this.necesita(CON_ESCALAS) ? true : undefined),
    loader: () => this.repo.escalas(),
  });

  // 3. Estado público de solo lectura
  /** El contenido del servidor (el recurso o el último devuelto por una escritura). */
  readonly contenido = computed<ContenidoEditable | null>(() => {
    const local = this._contenido();
    if (local !== null) return local;
    return this.recursoContenido.hasValue() ? (this.recursoContenido.value() ?? null) : null;
  });
  readonly esNuevo = computed(() => this.segmentoId() === null);
  readonly id = computed(() => this.contenido()?.id ?? null);
  readonly cargando = computed(() => !this.esNuevo() && this.contenido() === null && this.recursoContenido.isLoading());
  readonly errorCarga = computed<ErrorApi | null>(() => {
    const error = this.recursoContenido.error();
    return error ? normalizarError(error) : null;
  });
  readonly noEncontrado = computed(
    () =>
      this.tipo() === null ||
      this.segmentoId() === 'invalido' ||
      this.errorCarga()?.categoria === 'no_encontrado' ||
      // Las páginas institucionales no se crean (AC-033).
      (this.esNuevo() && this.tipo() === 'PAGINA'),
  );
  /** 403 o página legal para un Editor → SCR-048 (RULE-014). */
  readonly accesoDenegado = computed(() => {
    if (this.errorCarga()?.categoria === 'permiso_denegado') return true;
    const contenido = this.contenido();
    return contenido !== null && !puedeEditarPagina(this.sesion.rol(), contenido.soloAdministrador);
  });
  readonly acciones = computed<AccionesEditor | null>(() => {
    const tipo = this.tipo();
    if (tipo === null) return null;
    const contenido = this.contenido();
    return accionesEditor({
      tipo,
      estado: contenido?.estado ?? null,
      nuncaPublicado: contenido?.nuncaPublicado ?? true,
    });
  });
  readonly guardando = this._guardando.asReadonly();
  /** Transición o eliminación en curso (doble clic neutralizado, ALT-017). */
  readonly procesando = this._procesando.asReadonly();
  readonly guardadoEn = this._guardadoEn.asReadonly();
  readonly erroresServidor = this._erroresServidor.asReadonly();
  readonly conflicto = this._conflicto.asReadonly();
  readonly errorGuardado = this._errorGuardado.asReadonly();
  readonly aviso = this._aviso.asReadonly();
  /** Requisitos de publicación: los del último cálculo sobre el formulario o los del guardado. */
  readonly requisitos = computed<RequisitosPublicacion | null>(
    () => this._requisitosFormulario() ?? this.contenido()?.requisitos ?? null,
  );
  readonly revisiones = computed(() =>
    this.recursoRevisiones.hasValue() ? this.recursoRevisiones.value() : null,
  );
  readonly cargandoRevisiones = computed(() => this.recursoRevisiones.isLoading());
  readonly errorRevisiones = computed(() => this.recursoRevisiones.error() !== undefined);
  readonly restaurado = this._restaurado.asReadonly();
  readonly paises = computed(() => (this.recursoPaises.hasValue() ? this.recursoPaises.value() : []));
  readonly tiposAventura = computed(() => (this.recursoTipos.hasValue() ? this.recursoTipos.value() : []));
  readonly categorias = computed(() =>
    this.recursoCategorias.hasValue() ? this.recursoCategorias.value() : [],
  );
  readonly escalas = computed<EscalasContenido>(() =>
    this.recursoEscalas.hasValue()
      ? this.recursoEscalas.value()
      : { dificultad: nivelesPorDefecto(5), presupuesto: nivelesPorDefecto(4) },
  );
  readonly errorCatalogos = computed(
    () =>
      this.recursoPaises.error() !== undefined ||
      this.recursoTipos.error() !== undefined ||
      this.recursoCategorias.error() !== undefined,
  );

  /** Formulario inicial: el del servidor o, en el alta, vacío. */
  readonly formularioInicial = computed<FormularioContenido | null>(() => {
    const tipo = this.tipo();
    if (tipo === null) return null;
    if (this.esNuevo()) return formularioVacio(tipo);
    return this.contenido()?.formulario ?? null;
  });

  // 4. Comandos
  /**
   * «Guardar borrador» / «Guardar cambios» / guardado previo a publicar (FLOW-011 paso 3): crea el
   * contenido o lo actualiza con su `version`. Ante 409 conflicto_version muestra el aviso sin
   * sobrescribir (AC-110); los 400 se traducen a errores por campo.
   */
  async guardar(formulario: FormularioContenido): Promise<ErrorApi | null> {
    if (this._guardando()) return null;
    const contenido = this.contenido();
    this._guardando.set(true);
    this._errorGuardado.set(null);
    this._aviso.set(null);
    const operacion =
      contenido === null
        ? defer(() => this.repo.crear(formulario, nuevaClaveIdempotencia()))
        : defer(() => this.repo.actualizar(contenido.id, formulario, contenido.version));
    const error = await ejecutar(operacion, (guardado) => {
      this.fijar(guardado);
      this._guardadoEn.set(new Date());
      this._erroresServidor.set({});
    });
    this._guardando.set(false);
    if (error !== null) this.registrarError(error);
    return error;
  }

  /** Fija el contenido devuelto por una escritura (Actualizar publicación, transiciones). */
  fijar(contenido: ContenidoEditable): void {
    this._contenido.set(contenido);
    this._requisitosFormulario.set(null);
    this._conflicto.set(false);
  }

  /** Tras publicar, retirar o reactivar: relee el contenido (estado, versión, slug fijado). */
  async releer(): Promise<ErrorApi | null> {
    const contenido = this.contenido();
    if (contenido === null) return null;
    return ejecutar(defer(() => this.repo.obtener(contenido.tipo, contenido.id)), (nuevo) => this.fijar(nuevo));
  }

  /** «Recargar» del ConflictBanner: descarta los cambios locales y lee la versión actual. */
  async recargar(): Promise<ErrorApi | null> {
    this._erroresServidor.set({});
    this._errorGuardado.set(null);
    const error = await this.releer();
    if (error === null) this._conflicto.set(false);
    return error;
  }

  marcarConflicto(): void {
    this._conflicto.set(true);
  }

  /** Eliminar borrador nunca publicado (DEC-AUTO-045). */
  async eliminar(): Promise<ErrorApi | null> {
    const contenido = this.contenido();
    if (contenido === null || this._procesando()) return null;
    this._procesando.set(true);
    const error = await ejecutar(defer(() => this.repo.eliminar(contenido.tipo, contenido.id, contenido.version)));
    this._procesando.set(false);
    if (error !== null) this.registrarError(error);
    return error;
  }

  /** RETIRADO → BORRADOR conservando el slug (FLOW-012). */
  async reactivar(): Promise<ErrorApi | null> {
    const contenido = this.contenido();
    if (contenido === null || this._procesando()) return null;
    this._procesando.set(true);
    let error = await ejecutar(
      defer(() => this.repo.reactivar(contenido.tipo, contenido.id, contenido.version, nuevaClaveIdempotencia())),
    );
    if (error === null) {
      error = await this.releer();
      this._aviso.set('Reactivaste el contenido como borrador. Edítalo y vuelve a publicarlo cuando esté listo.');
    } else {
      this.registrarError(error);
    }
    this._procesando.set(false);
    return error;
  }

  /**
   * Carga una revisión en el formulario (FEAT-050, AC-121): no cambia nada público hasta guardar y
   * publicar o actualizar. La UI recoge `restaurado()` y lo aplica a sus controles.
   */
  async restaurar(numero: number, actual: FormularioContenido): Promise<ErrorApi | null> {
    const contenido = this.contenido();
    if (contenido === null || this._procesando()) return null;
    this._procesando.set(true);
    const error = await ejecutar(defer(() => this.repo.restaurar(contenido.tipo, contenido.id, numero)), (r) => {
      this._restaurado.set({ numero: r.numero, formulario: enriquecerReferencias(r.formulario, actual) });
      if (r.versionActual !== contenido.version) this._conflicto.set(true);
      this._aviso.set(
        `Se cargó la revisión ${r.numero} en el formulario. No cambia nada público hasta que guardes y publiques o actualices.`,
      );
    });
    this._procesando.set(false);
    return error;
  }

  /** La UI ya aplicó la revisión restaurada a sus controles. */
  restauracionAplicada(): void {
    this._restaurado.set(null);
  }

  /**
   * CompletenessPanel: recalcula los requisitos sobre el formulario sin guardar con la vista previa
   * (no persiste nada, DEC-AUTO-114). Si falla (formato aún inválido, límite de tasa) se conservan
   * los últimos requisitos conocidos.
   */
  async comprobarRequisitos(formulario: FormularioContenido): Promise<ErrorApi | null> {
    const tipo = this.tipo();
    if (tipo === null || tipo === 'TERMINO') return null;
    return ejecutar(defer(() => this.repo.vistaPrevia(formulario, this.id())), (vista) =>
      this._requisitosFormulario.set(vista.requisitos),
    );
  }

  irAPaginaRevisiones(pagina: number): void {
    const total = this.revisiones()?.totalPaginas ?? 1;
    this._paginaRevisiones.set(Math.min(Math.max(1, pagina), Math.max(1, total)));
  }

  recargarRevisiones(): void {
    this.recursoRevisiones.reload();
  }

  fijarAviso(aviso: string | null): void {
    this._aviso.set(aviso);
  }

  /** Aviso para la pantalla a la que se navega (el alta abre el editor del contenido creado). */
  dejarAviso(aviso: string): void {
    this.memoria.dejarAviso(aviso);
  }

  /**
   * Búsqueda para los Combobox (relacionados, destino, elementos, términos). Lectura sin efectos:
   * devuelve los resultados o el mensaje del error, nunca lanza.
   */
  async buscar(
    tipos: readonly TipoContenido[],
    q: string,
    estado: EstadoEditorial | null,
    sinRetirados = false,
  ): Promise<ResultadoBusqueda> {
    try {
      const resultados = await this.repo.buscar(tipos, q.trim().slice(0, 100), estado);
      return {
        resultados: sinRetirados ? resultados.filter((r) => r.estado !== 'RETIRADO') : resultados,
        error: null,
      };
    } catch (error: unknown) {
      return { resultados: [], error: normalizarError(error).mensaje };
    }
  }

  /** Errores del servidor que la UI acaba de mostrar y que el usuario corrige campo a campo. */
  limpiarErrorServidor(campo: string): void {
    if (this._erroresServidor()[campo] === undefined) return;
    const { [campo]: _, ...resto } = this._erroresServidor();
    this._erroresServidor.set(resto);
  }

  /** Formulario sin guardar en memoria (Vista previa, sesión expirada: ALT-014). */
  guardarEnMemoria(formulario: FormularioContenido): void {
    const tipo = this.tipo();
    if (tipo === null) return;
    this.memoria.guardar(tipo, this.id(), { formulario, version: this.contenido()?.version ?? null });
  }

  tomarDeMemoria(): BorradorEnMemoria | null {
    const tipo = this.tipo();
    return tipo === null ? null : this.memoria.tomar(tipo, this.id());
  }

  /** Clasifica un error de escritura: conflicto de versión, errores por campo o general. */
  registrarError(error: ErrorApi): void {
    if (error.codigo === CONFLICTO_VERSION) {
      this._conflicto.set(true);
      return;
    }
    if (error.categoria === 'validacion' || error.categoria === 'regla_negocio') {
      const porCampo = erroresDeFormulario(error.campos);
      this._erroresServidor.set(porCampo);
      if (Object.keys(porCampo).length > 0) return;
    }
    if (error.categoria !== 'no_autenticado') this._errorGuardado.set(error);
  }

  private necesita(tipos: readonly TipoContenido[]): boolean {
    const tipo = this.tipo();
    return tipo !== null && tipos.includes(tipo);
  }
}
