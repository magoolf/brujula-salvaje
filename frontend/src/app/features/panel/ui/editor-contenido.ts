import { DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  ETIQUETA_MOTIVO_REVISION,
  Requisito,
  textoCompletitud,
  textoRequisito,
  tituloResumenErrores,
} from '../domain/ciclo-editorial';
import {
  DEFINICION_TIPO,
  ETIQUETA_ACCION,
  rutaEditor,
  rutaListado,
  rutaVistaPrevia,
  tituloEditor,
} from '../domain/contenidos';
import { formatearFechaHora } from '../domain/fechas';
import {
  ChecklistItemForm,
  DiaForm,
  ElementoColeccionForm,
  FormularioContenido,
  FuenteForm,
  LIMITES,
  MESES,
  MINIMOS,
  MedioRef,
  OpcionCatalogo,
  RefContenido,
  alternarNumero,
  anadirSinDuplicados,
  anuncioMovido,
  etiquetaCampo,
  fechaLocal,
  hayCambios,
  idCampo,
  idDestinoCampo,
  indicadorDias,
  moverEn,
  nuevaClaveLista,
  proponerSlug,
  quitarEn,
  reemplazarEn,
  seccionDeCampo,
  seccionesDe,
  textoMinimo,
  validarFormato,
} from '../domain/formulario-contenido';
import { EstadoEditorial, TipoContenido } from '../domain/modelos';
import { ETIQUETA_ESTADO, ETIQUETA_TIPO_SINGULAR, varianteEstado } from '../domain/tablero';
import { EditorContenidoStore } from '../state/editor-contenido.store';
import { PublicacionStore } from '../state/publicacion.store';
import { AccesoDenegado } from './acceso-denegado';
import { BuscadorContenidos } from './buscador-contenidos';
import { CampoTexto } from './campo-texto';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { DialogoPublicacion } from './dialogo-publicacion';
import { DialogoRetiro } from './dialogo-retiro';
import { EditorTextoEnriquecido } from './editor-texto-enriquecido';
import { EnlaceValor } from './enlace-valor';
import { MediosContenido } from './medios-contenido';
import { ModeloFormulario } from './modelo-formulario';
import { PaginaNoEncontradaPanel } from './pagina-no-encontrada-panel';

/** Espera tras salir de un campo antes de recalcular los requisitos (y mínimo entre cálculos). */
const ESPERA_REQUISITOS_MS = 1500;
const INTERVALO_REQUISITOS_MS = 3000;

type Confirmacion = 'eliminar' | 'reactivar' | 'recargar' | 'restaurar' | 'salir' | null;

/** Tipos que se buscan como relacionados (FEAT-039) y como elementos de colección (RULE-024). */
const TIPOS_RELACIONABLES: readonly TipoContenido[] = ['DESTINO', 'ITINERARIO', 'GUIA', 'TIPO', 'COLECCION'];
const TIPOS_COLECCIONABLES: readonly TipoContenido[] = ['DESTINO', 'ITINERARIO'];

/**
 * SCR-036 Editor de contenido (FEAT-034..040, FEAT-050, FLOW-011/012/013/016) para los 7 tipos:
 * una sola página con secciones (DEC-AUTO-076), navegación de secciones, StatusBar con las acciones
 * de STATE-001 y el CompletenessPanel, ConflictBanner (AC-110), aviso de cambios sin guardar
 * (ALT-026), sin conexión (guardar deshabilitado, datos conservados) y diálogos de SCR-038.
 * Los valores del formulario viven en `ModeloFormulario` (señales de la UI); los comandos, en
 * EditorContenidoStore y PublicacionStore (provistos aquí: una instancia por contenido).
 */
@Component({
  selector: 'app-editor-contenido',
  imports: [
    RouterLink,
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    Insignia,
    AccesoDenegado,
    BuscadorContenidos,
    CampoTexto,
    DialogoConfirmacion,
    DialogoPublicacion,
    DialogoRetiro,
    EditorTextoEnriquecido,
    EnlaceValor,
    MediosContenido,
    PaginaNoEncontradaPanel,
  ],
  providers: [EditorContenidoStore, PublicacionStore],
  host: { '(keydown)': 'alTeclear($event)', '(focusout)': 'alSalirDeCampo()' },
  templateUrl: './editor-contenido.html',
  styleUrls: ['./panel-formularios.css', './editor-contenido.css'],
})
export class EditorContenido {
  protected readonly store = inject(EditorContenidoStore);
  protected readonly publicacion = inject(PublicacionStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly router = inject(Router);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly seo = inject(Seo);

  protected readonly tipo: TipoContenido = this.store.tipo() ?? 'DESTINO';
  protected readonly m = new ModeloFormulario(this.tipo);
  protected readonly def = DEFINICION_TIPO[this.tipo];
  protected readonly secciones = seccionesDe(this.tipo);
  protected readonly meses = MESES;
  protected readonly limites = LIMITES;
  protected readonly minimos = MINIMOS;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO;
  protected readonly etiquetaTipo = ETIQUETA_TIPO_SINGULAR;
  protected readonly etiquetaMotivo = ETIQUETA_MOTIVO_REVISION;
  protected readonly etiquetaAccion = ETIQUETA_ACCION;
  protected readonly hoy = fechaLocal(new Date());
  protected readonly id = idCampo;
  protected readonly etiqueta = etiquetaCampo;
  protected readonly textoReq = textoRequisito;
  protected readonly variante = varianteEstado;
  protected readonly fechaHora = formatearFechaHora;
  protected readonly rutaListado = rutaListado(this.tipo);
  protected readonly textoMinimo = textoMinimo;

  /** Último valor guardado o cargado (para «Cambios sin guardar»). */
  private readonly base = signal<FormularioContenido | null>(null);
  private readonly erroresLocales = signal<Readonly<Record<string, string>>>({});
  protected readonly resumenVisible = signal(false);
  protected readonly anuncio = signal('');
  protected readonly dialogoPublicacion = signal(false);
  protected readonly dialogoRetiro = signal(false);
  protected readonly confirmacion = signal<Confirmacion>(null);
  protected readonly revisionARestaurar = signal<{ numero: number; fecha: Date } | null>(null);
  protected readonly diaAbierto = signal<string | null>(null);
  protected readonly masAcciones = signal(false);
  /** Slug editado a mano: deja de proponerse desde el título (RULE-008). */
  private slugManual = false;
  private resolverSalida: ((salir: boolean) => void) | null = null;
  private temporizadorRequisitos: ReturnType<typeof setTimeout> | null = null;
  private ultimoCalculo = 0;

  protected readonly valor = this.m.valor;
  protected readonly sucio = computed(() => {
    const base = this.base();
    return base !== null && hayCambios(this.valor(), base);
  });
  protected readonly errores = computed<Readonly<Record<string, string>>>(() => ({
    ...this.store.erroresServidor(),
    ...this.erroresLocales(),
  }));
  protected readonly listaErrores = computed(() =>
    Object.entries(this.errores()).map(([campo, mensaje]) => ({ campo, mensaje })),
  );
  protected readonly tituloResumen = computed(() =>
    tituloResumenErrores('guardar', this.listaErrores().length),
  );
  protected readonly titulo = computed(() =>
    tituloEditor(this.tipo, this.store.esNuevo() ? null : this.valor().titulo || (this.store.contenido()?.formulario.titulo ?? '')),
  );
  protected readonly acciones = this.store.acciones;
  protected readonly soloLectura = computed(() => this.acciones()?.soloLectura ?? false);
  protected readonly estado = computed<EstadoEditorial | null>(() => this.store.contenido()?.estado ?? null);
  protected readonly requisitos = this.store.requisitos;
  protected readonly textoCompletitud = computed(() => {
    const r = this.requisitos();
    return r === null ? 'Guarda el borrador para comprobar los requisitos.' : textoCompletitud(r);
  });
  protected readonly estadoGuardado = computed(() => {
    if (this.store.guardando()) return 'Guardando…';
    if (this.sucio()) return 'Cambios sin guardar';
    const guardado = this.store.guardadoEn();
    return guardado === null ? '' : `Guardado a las ${guardado.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}`;
  });
  /** Secciones con requisitos pendientes (icono Pendiente en la navegación de secciones). */
  protected readonly seccionesPendientes = computed(() => {
    const pendientes = new Set<string>();
    for (const r of this.requisitos()?.pendientes ?? []) {
      const seccion = seccionDeCampo(this.tipo, r.campo);
      if (seccion) pendientes.add(seccion.id);
    }
    return pendientes;
  });
  protected readonly textoConfirmacion = computed(() => {
    switch (this.confirmacion()) {
      case 'eliminar':
        return {
          titulo: '¿Eliminar este borrador?',
          texto: 'Se borrará definitivamente. Esta acción no se puede deshacer.',
          confirmar: 'Eliminar borrador',
          cancelar: 'Cancelar',
          variante: 'danger' as const,
        };
      case 'reactivar':
        return {
          titulo: 'Reactivar como borrador',
          texto: 'Volverá a borrador y conservará su dirección. Para que vuelva al sitio tendrás que publicarlo de nuevo.',
          confirmar: 'Reactivar como borrador',
          cancelar: 'Cancelar',
          variante: 'primary' as const,
        };
      case 'recargar':
        return {
          titulo: '¿Recargar la versión actual?',
          texto: 'Se descartarán tus cambios no guardados en este formulario.',
          confirmar: 'Recargar',
          cancelar: 'Cancelar',
          variante: 'danger' as const,
        };
      case 'restaurar': {
        const revision = this.revisionARestaurar();
        return {
          titulo: `Restaurar la revisión ${revision?.numero ?? ''}`,
          texto: `Se cargará la revisión del ${revision ? formatearFechaHora(revision.fecha) : ''} en el formulario. No cambia nada público hasta que publiques o actualices.`,
          confirmar: 'Restaurar en el formulario',
          cancelar: 'Cancelar',
          variante: 'primary' as const,
        };
      }
      default:
        return {
          titulo: 'Tienes cambios sin guardar',
          texto: 'Si sales ahora, se perderán.',
          confirmar: 'Salir sin guardar',
          cancelar: 'Seguir editando',
          variante: 'danger' as const,
        };
    }
  });
  protected readonly principalesPosibles = computed(() =>
    this.store.tiposAventura().filter((t) => this.m.tipos().includes(t.id)),
  );
  protected readonly indicador = computed(() => indicadorDias(this.valor()));
  protected readonly palabrasMinimas = this.tipo === 'DESTINO' ? MINIMOS.palabrasDescripcionDestino : null;
  protected readonly excluidosRelaciones = computed(() => {
    const propio = this.store.id();
    return [
      ...this.m.relaciones().map((r) => `${r.tipo}:${r.id}`),
      ...(propio === null ? [] : [`${this.tipo}:${propio}`]),
    ];
  });
  protected readonly excluidosElementos = computed(() =>
    this.m.elementos().map((e) => `${e.contenido.tipo}:${e.contenido.id}`),
  );
  protected readonly excluidosDestinos = computed(() => this.m.destinos().map((d) => `DESTINO:${d.id}`));
  protected readonly excluidosTerminos = computed(() => this.m.terminos().map((t) => `TERMINO:${t.id}`));
  protected readonly ubicacion = computed(() => {
    const lat = Number(this.m.texto.latitud().replace(',', '.'));
    const lon = Number(this.m.texto.longitud().replace(',', '.'));
    if (this.m.texto.latitud().trim() === '' || this.m.texto.longitud().trim() === '') return null;
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
    return { x: ((lon + 180) / 360) * 360, y: ((90 - lat) / 180) * 180, lat, lon };
  });

  // Búsquedas de los Combobox (delegan en el store).
  protected readonly buscarRelacionados = (q: string) => this.store.buscar(TIPOS_RELACIONABLES, q, 'PUBLICADO');
  protected readonly buscarElementos = (q: string) => this.store.buscar(TIPOS_COLECCIONABLES, q, 'PUBLICADO');
  protected readonly buscarDestinos = (q: string) => this.store.buscar(['DESTINO'], q, null, true);
  protected readonly buscarTerminos = (q: string) => this.store.buscar(['TERMINO'], q, null, true);

  constructor() {
    // Carga inicial del formulario: el borrador en memoria (vista previa o sesión expirada) o el del
    // servidor / vacío. Solo una vez por instancia: después, los valores son del usuario.
    effect(() => {
      const inicial = this.store.formularioInicial();
      if (inicial === null || untracked(this.base) !== null) return;
      untracked(() => {
        const memoria = this.store.tomarDeMemoria();
        this.fijarBase(inicial);
        if (memoria !== null) {
          this.m.cargar(memoria.formulario);
          this.store.fijarAviso('Recuperamos los cambios sin guardar de este formulario.');
          if (memoria.version !== null && memoria.version !== this.store.contenido()?.version) {
            this.store.marcarConflicto();
          }
        }
      });
    });
    // Revisión restaurada (FEAT-050): se aplica a los controles; queda como cambio sin guardar.
    effect(() => {
      const restaurado = this.store.restaurado();
      if (restaurado === null) return;
      untracked(() => {
        this.m.cargar(restaurado.formulario);
        this.store.restauracionAplicada();
      });
    });
    // RULE-008: el slug se propone desde el título mientras no se edite a mano ni esté bloqueado.
    effect(() => {
      const titulo = this.m.texto.titulo();
      untracked(() => {
        if (this.slugManual || this.store.contenido()?.slugBloqueado || this.tipo === 'PAGINA') return;
        if (this.base() === null) return;
        this.m.texto.slug.set(proponerSlug(titulo));
      });
    });
    effect(() => {
      const titulo = this.titulo();
      untracked(() => this.seo.establecer({ titulo, indexable: false }));
    });
    // Cierre de pestaña con cambios sin guardar: diálogo nativo del navegador (ALT-026).
    const ventana = this.documento.defaultView;
    const alDescargar = (evento: BeforeUnloadEvent): void => {
      if (this.sucio()) evento.preventDefault();
    };
    ventana?.addEventListener('beforeunload', alDescargar);
    inject(DestroyRef).onDestroy(() => {
      ventana?.removeEventListener('beforeunload', alDescargar);
      if (this.temporizadorRequisitos !== null) clearTimeout(this.temporizadorRequisitos);
    });
  }

  // ------------------------------------------------------------------ salida (canDeactivate)
  /**
   * ALT-026: con cambios sin guardar se pide confirmación. A la vista previa se va sin preguntar
   * (el formulario queda en memoria) y, si la sesión expiró (→ SCR-030), el formulario se conserva
   * en memoria para recuperarlo al volver (ALT-014).
   */
  puedeSalir(destino: string): boolean | Promise<boolean> {
    if (!this.sucio()) return true;
    if (destino.startsWith('/panel/acceso') || destino.includes('/vista-previa')) {
      this.store.guardarEnMemoria(this.valor());
      return true;
    }
    this.confirmacion.set('salir');
    return new Promise<boolean>((resolver) => (this.resolverSalida = resolver));
  }

  protected responderSalida(salir: boolean): void {
    this.confirmacion.set(null);
    if (salir) this.base.set(this.valor());
    this.resolverSalida?.(salir);
    this.resolverSalida = null;
  }

  // ------------------------------------------------------------------ edición
  protected alEditarSlug(): void {
    this.slugManual = true;
    this.limpiarError('slug');
  }

  protected limpiarError(campo: string): void {
    if (this.erroresLocales()[campo] !== undefined) {
      const { [campo]: _, ...resto } = this.erroresLocales();
      this.erroresLocales.set(resto);
    }
    this.store.limpiarErrorServidor(campo);
  }

  protected error(campo: string): string | null {
    return this.errores()[campo] ?? null;
  }

  protected alternarTipo(id: number): void {
    this.m.tipos.update((tipos) => alternarNumero(tipos, id));
    const principal = Number(this.m.texto.tipoPrincipal());
    if (principal && !this.m.tipos().includes(principal)) this.m.texto.tipoPrincipal.set('');
    this.limpiarError('tipos');
  }

  protected alternarMes(mes: number): void {
    this.m.meses.update((meses) => alternarNumero(meses, mes));
    this.limpiarError('meses');
  }

  protected fijarTexto(campo: keyof ModeloFormulario['texto'], valor: string): void {
    this.m.texto[campo].set(valor);
    this.limpiarError(campo);
  }

  protected valorDe(evento: Event): string {
    return (evento.target as HTMLInputElement).value;
  }

  // Listas -------------------------------------------------------------------------------------
  protected anadirFuente(): void {
    const fuente: FuenteForm = { clave: nuevaClaveLista('fuente'), titulo: '', url: '', entidadEditora: '', fechaConsulta: '' };
    this.m.fuentes.update((l) => [...l, fuente]);
    this.enfocarTras(idCampo(`fuentes.${this.m.fuentes().length - 1}.titulo`));
  }

  protected editarFuente(i: number, campo: keyof Omit<FuenteForm, 'clave'>, evento: Event): void {
    this.m.fuentes.update((l) => reemplazarEn(l, i, { ...l[i], [campo]: this.valorDe(evento) }));
    this.limpiarError(`fuentes.${i}.${campo}`);
  }

  protected anadirDia(): void {
    const dia: DiaForm = {
      clave: nuevaClaveLista('dia'),
      titulo: '',
      actividades: '',
      distanciaKm: '',
      desnivelPositivo: '',
      desnivelNegativo: '',
      alojamiento: '',
      consejos: '',
    };
    this.m.dias.update((l) => [...l, dia]);
    this.diaAbierto.set(dia.clave);
    this.enfocarTras(idCampo(`dias.${this.m.dias().length - 1}.titulo`));
  }

  protected editarDia(i: number, campo: keyof Omit<DiaForm, 'clave'>, valor: string): void {
    this.m.dias.update((l) => reemplazarEn(l, i, { ...l[i], [campo]: valor }));
    this.limpiarError(`dias.${i}.${campo}`);
  }

  protected anadirItem(): void {
    const item: ChecklistItemForm = { clave: nuevaClaveLista('item'), texto: '', grupo: '', esencial: false };
    this.m.checklist.update((l) => [...l, item]);
    this.enfocarTras(idCampo(`checklist.${this.m.checklist().length - 1}.texto`));
  }

  protected editarItem(i: number, campo: 'texto' | 'grupo', evento: Event): void {
    this.m.checklist.update((l) => reemplazarEn(l, i, { ...l[i], [campo]: this.valorDe(evento) }));
    this.limpiarError(`checklist.${i}.${campo}`);
  }

  protected alternarEsencial(i: number): void {
    this.m.checklist.update((l) => reemplazarEn(l, i, { ...l[i], esencial: !l[i].esencial }));
  }

  protected anadirElemento(ref: RefContenido): void {
    const elemento: ElementoColeccionForm = { clave: nuevaClaveLista('elemento'), contenido: ref, nota: '' };
    this.m.elementos.update((l) => (l.length >= LIMITES.elementos ? l : [...l, elemento]));
    this.limpiarError('elementos');
  }

  protected editarNota(i: number, evento: Event): void {
    this.m.elementos.update((l) => reemplazarEn(l, i, { ...l[i], nota: this.valorDe(evento) }));
    this.limpiarError(`elementos.${i}.nota`);
  }

  protected anadirRelacion(ref: RefContenido): void {
    this.m.relaciones.update((l) => anadirSinDuplicados(l, [ref], LIMITES.relaciones));
    this.limpiarError('relaciones');
  }

  protected anadirDestinoGuia(ref: RefContenido): void {
    this.m.destinos.update((l) => anadirSinDuplicados(l, [ref], LIMITES.destinosGuia));
    this.limpiarError('destinos');
  }

  protected elegirDestinoItinerario(ref: RefContenido): void {
    this.m.destino.set(ref);
    this.limpiarError('destino');
  }

  protected anadirTermino(ref: RefContenido): void {
    const opcion: OpcionCatalogo = { id: ref.id, nombre: ref.titulo };
    this.m.terminos.update((l) => anadirSinDuplicados(l, [opcion], LIMITES.terminos));
    this.limpiarError('terminos');
  }

  /** Subir/Bajar de cualquier lista ordenable (alternativa sin arrastre, WCAG 2.5.7). */
  protected moverEnLista<T>(
    lista: { (): readonly T[]; set(v: readonly T[]): void },
    nombre: string,
    indice: number,
    desplazamiento: number,
    prefijoId: string,
  ): void {
    const actual = lista();
    const destino = indice + desplazamiento;
    if (destino < 0 || destino >= actual.length) return;
    lista.set(moverEn(actual, indice, destino));
    this.anuncio.set(anuncioMovido(nombre, destino + 1, actual.length));
    const sentido = desplazamiento < 0 ? 'subir' : 'bajar';
    const alterno = desplazamiento < 0 ? 'bajar' : 'subir';
    afterNextRender(
      () => {
        const boton = this.documento.getElementById(`${prefijoId}-${sentido}-${destino}`) as HTMLButtonElement | null;
        (boton && !boton.disabled ? boton : this.documento.getElementById(`${prefijoId}-${alterno}-${destino}`))?.focus();
      },
      { injector: this.injector },
    );
  }

  protected quitarDeLista<T>(lista: { (): readonly T[]; set(v: readonly T[]): void }, indice: number, nombre: string): void {
    lista.set(quitarEn(lista(), indice));
    this.anuncio.set(`${nombre} quitado de la lista.`);
  }

  protected alCambiarPortada(medio: MedioRef | null): void {
    this.m.portada.set(medio);
    this.limpiarError('portada');
  }

  protected alCambiarGaleria(galeria: readonly MedioRef[]): void {
    this.m.galeria.set(galeria);
    this.limpiarError('galeria');
  }

  // ------------------------------------------------------------------ requisitos y teclado
  /** CompletenessPanel: se recalcula al salir de cada campo (con espera y sin ruido). */
  protected alSalirDeCampo(): void {
    if (!this.sucio() || !this.enLinea() || this.store.esNuevo() && this.valor().titulo.trim() === '') return;
    if (this.temporizadorRequisitos !== null) clearTimeout(this.temporizadorRequisitos);
    const espera = Math.max(ESPERA_REQUISITOS_MS, this.ultimoCalculo + INTERVALO_REQUISITOS_MS - Date.now());
    this.temporizadorRequisitos = setTimeout(() => {
      this.temporizadorRequisitos = null;
      this.ultimoCalculo = Date.now();
      void this.store.comprobarRequisitos(this.valor());
    }, espera);
  }

  /** Ctrl/Cmd+S = Guardar borrador (HANDOFF SCR-036 keyboard). */
  protected alTeclear(evento: KeyboardEvent): void {
    if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 's') {
      evento.preventDefault();
      if (this.acciones()?.guardarBorrador || this.acciones()?.principal === 'GUARDAR_PAGINA') void this.guardar();
    }
  }

  // ------------------------------------------------------------------ comandos
  /** Valida el formato y muestra el ErrorSummary si hay errores. */
  private validar(): boolean {
    const errores = validarFormato(this.valor(), fechaLocal(new Date()));
    this.erroresLocales.set(errores);
    const hay = Object.keys(errores).length > 0;
    this.mostrarResumen(hay);
    return !hay;
  }

  private mostrarResumen(visible: boolean): void {
    this.resumenVisible.set(visible);
    if (visible) {
      afterNextRender(() => this.documento.getElementById('editor-resumen-errores')?.focus(), {
        injector: this.injector,
      });
    }
  }

  async guardar(): Promise<boolean> {
    if (!this.enLinea() || this.store.guardando() || !this.validar()) return false;
    const error = await this.store.guardar(this.valor());
    if (error !== null) {
      this.mostrarResumen(Object.keys(this.store.erroresServidor()).length > 0);
      return false;
    }
    const contenido = this.store.contenido();
    if (contenido === null) return false;
    if (this.store.esNuevo()) {
      // Alta: se abre el editor del contenido creado (la URL pasa a /{id}).
      this.base.set(this.valor());
      this.store.dejarAviso(`Borrador guardado a las ${new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}.`);
      await this.router.navigateByUrl(rutaEditor(this.tipo, contenido.id), { replaceUrl: true });
      return true;
    }
    this.fijarBase(contenido.formulario);
    this.anuncio.set('Cambios guardados.');
    return true;
  }

  protected async vistaPrevia(): Promise<void> {
    this.store.guardarEnMemoria(this.valor());
    await this.router.navigateByUrl(rutaVistaPrevia(this.tipo, this.store.id()));
  }

  protected async accionPrincipal(): Promise<void> {
    const accion = this.acciones()?.principal;
    if (accion === 'GUARDAR_PAGINA') {
      await this.guardar();
    } else if (accion === 'REACTIVAR') {
      this.confirmacion.set('reactivar');
    } else if (accion === 'PUBLICAR' || accion === 'ACTUALIZAR') {
      await this.abrirPublicacion();
    }
  }

  /**
   * «Publicar» (BORRADOR): primero guarda los cambios pendientes (el análisis evalúa el estado
   * guardado). «Actualizar publicación» (PUBLICADO): valida el formato y analiza el formulario.
   */
  private async abrirPublicacion(): Promise<void> {
    if (!this.enLinea()) return;
    const contenido = this.store.contenido();
    if (contenido === null) return;
    if (contenido.estado === 'BORRADOR' && this.sucio()) {
      if (!(await this.guardar())) return;
    } else if (!this.validar()) {
      return;
    }
    const actual = this.store.contenido();
    if (actual === null) return;
    this.publicacion.limpiarExito();
    this.dialogoPublicacion.set(true);
    await this.publicacion.analizar(actual, this.valor());
  }

  protected async confirmarPublicacion(): Promise<void> {
    const contenido = this.store.contenido();
    if (contenido === null) return;
    const { error, contenido: actualizado } = await this.publicacion.confirmar(contenido, this.valor());
    if (error !== null) {
      if (this.publicacion.conflicto() !== null) this.store.marcarConflicto();
      return;
    }
    if (actualizado !== null) {
      this.store.fijar(actualizado);
      this.fijarBase(actualizado.formulario);
    } else if ((await this.store.releer()) === null) {
      const releido = this.store.contenido();
      if (releido !== null) this.fijarBase(releido.formulario);
    }
    this.store.recargarRevisiones();
    this.dialogoPublicacion.set(false);
    this.publicacion.cerrar();
  }

  protected async reintentarPublicacion(): Promise<void> {
    const contenido = this.store.contenido();
    if (contenido === null) return;
    if (this.publicacion.analisis() === null) await this.publicacion.analizar(contenido, this.valor());
    else await this.confirmarPublicacion();
  }

  protected async abrirRetiro(): Promise<void> {
    this.masAcciones.set(false);
    const contenido = this.store.contenido();
    if (contenido === null || !this.enLinea()) return;
    this.publicacion.limpiarExito();
    this.dialogoRetiro.set(true);
    await this.publicacion.cargarImpacto(contenido);
  }

  protected async confirmarRetiro(motivo: string): Promise<void> {
    const contenido = this.store.contenido();
    if (contenido === null) return;
    const error = await this.publicacion.retirar(contenido, motivo);
    if (error !== null) {
      if (this.publicacion.conflicto() !== null) this.store.marcarConflicto();
      return;
    }
    if ((await this.store.releer()) === null) {
      const releido = this.store.contenido();
      if (releido !== null) this.fijarBase(releido.formulario);
    }
    this.store.recargarRevisiones();
    this.dialogoRetiro.set(false);
    this.publicacion.cerrar();
  }

  protected cerrarDialogoPublicacion(abierto: boolean): void {
    this.dialogoPublicacion.set(abierto);
    if (!abierto) this.publicacion.cerrar();
  }

  protected cerrarDialogoRetiro(abierto: boolean): void {
    this.dialogoRetiro.set(abierto);
    if (!abierto) this.publicacion.cerrar();
  }

  protected pedirEliminar(): void {
    this.masAcciones.set(false);
    this.confirmacion.set('eliminar');
  }

  protected async confirmar(): Promise<void> {
    const tipo = this.confirmacion();
    if (tipo === 'eliminar') {
      if ((await this.store.eliminar()) === null) {
        this.base.set(this.valor());
        this.confirmacion.set(null);
        this.store.dejarAviso(`Se eliminó el borrador «${this.valor().titulo}».`);
        await this.router.navigateByUrl(this.rutaListado);
        return;
      }
    } else if (tipo === 'reactivar') {
      if ((await this.store.reactivar()) === null) {
        const contenido = this.store.contenido();
        if (contenido !== null) this.fijarBase(contenido.formulario);
        this.store.recargarRevisiones();
      }
    } else if (tipo === 'recargar') {
      if ((await this.store.recargar()) === null) {
        const contenido = this.store.contenido();
        if (contenido !== null) this.fijarBase(contenido.formulario);
      }
    } else if (tipo === 'restaurar') {
      const revision = this.revisionARestaurar();
      if (revision !== null) await this.store.restaurar(revision.numero, this.valor());
      this.revisionARestaurar.set(null);
    }
    this.confirmacion.set(null);
  }

  protected pedirRestaurar(numero: number, fecha: Date): void {
    this.revisionARestaurar.set({ numero, fecha });
    this.confirmacion.set('restaurar');
  }

  protected cerrarConfirmacion(abierto: boolean): void {
    if (abierto) return;
    if (this.confirmacion() === 'salir') this.responderSalida(false);
    else this.confirmacion.set(null);
  }

  /** Enlace del ErrorSummary o del CompletenessPanel: lleva el foco al campo (abre su día). */
  protected irACampo(campo: string): void {
    this.dialogoPublicacion.set(false);
    this.publicacion.cerrar();
    const [raiz, indice] = campo.split('.');
    if (raiz === 'dias' && indice !== undefined) {
      const dia = this.m.dias()[Number(indice)];
      if (dia) this.diaAbierto.set(dia.clave);
    }
    afterNextRender(
      () => {
        const elemento =
          this.documento.getElementById(idDestinoCampo(campo)) ??
          this.documento.getElementById(idCampo(raiz)) ??
          this.documento.getElementById(`seccion-${seccionDeCampo(this.tipo, campo)?.id ?? 'identidad'}-titulo`);
        elemento?.closest('details')?.setAttribute('open', '');
        elemento?.scrollIntoView({ block: 'center' });
        (elemento as HTMLElement | null)?.focus();
      },
      { injector: this.injector },
    );
  }

  protected irASeccion(evento: Event, idSeccion: string): void {
    evento.preventDefault();
    const titulo = this.documento.getElementById(`seccion-${idSeccion}-titulo`);
    titulo?.scrollIntoView({ block: 'start' });
    titulo?.focus();
  }

  protected alElegirSeccion(evento: Event): void {
    this.irASeccion(evento, (evento.target as HTMLSelectElement).value);
  }

  protected requisitoPendiente(r: Requisito): string {
    return textoRequisito(r);
  }

  protected enlaceEditor(ref: Pick<RefContenido, 'tipo' | 'id'>): string {
    return rutaEditor(ref.tipo, ref.id);
  }

  private fijarBase(formulario: FormularioContenido): void {
    this.m.cargar(formulario);
    this.base.set(this.m.valor());
    this.erroresLocales.set({});
    this.resumenVisible.set(false);
    this.slugManual = formulario.slug !== '' && formulario.slug !== proponerSlug(formulario.titulo);
  }

  private enfocarTras(id: string): void {
    afterNextRender(() => this.documento.getElementById(id)?.focus(), { injector: this.injector });
  }
}
