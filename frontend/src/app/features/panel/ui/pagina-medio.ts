import { DOCUMENT } from '@angular/common';
import {
  Component,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  WritableSignal,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import { formatearFechaHora } from '../domain/fechas';
import {
  CampoCatalogacion,
  ETIQUETA_ESTADO_MEDIO,
  ETIQUETA_PENDIENTE,
  ETIQUETA_ROL_USO,
  ETIQUETA_TIPO_USO,
  FormularioCatalogacion,
  LONGITUD_MAXIMA,
  Medio,
  derivadoPara,
  erroresCatalogacion,
  formatearPeso,
  formularioDesdeMedio,
  nombreMedio,
  srcsetDe,
  varianteEstadoMedio,
} from '../domain/medios';
import { ETIQUETA_ESTADO, varianteEstado } from '../domain/tablero';
import { RUTA_MEDIOS } from '../domain/secciones';
import { DetalleMedioStore } from '../state/detalle-medio.store';
import { AccesoDenegado } from './acceso-denegado';
import { CampoTexto } from './campo-texto';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { EnlaceValor } from './enlace-valor';
import { PaginaNoEncontradaPanel } from './pagina-no-encontrada-panel';

const ORDEN_CAMPOS: readonly CampoCatalogacion[] = [
  'tituloInterno',
  'textoAlternativo',
  'pieDeFoto',
  'autorCredito',
  'fuenteUrl',
  'licenciaId',
];
const ID_CAMPO: Readonly<Record<CampoCatalogacion, string>> = {
  tituloInterno: 'medio-titulo',
  textoAlternativo: 'medio-alt',
  pieDeFoto: 'medio-pie',
  autorCredito: 'medio-credito',
  fuenteUrl: 'medio-fuente',
  licenciaId: 'medio-licencia',
};
const GUIA_ALT =
  'Describe lo que muestra la foto como se lo contarías a alguien que no la ve. No empieces con «Imagen de».';

/**
 * SCR-040 Detalle de medio (FEAT-042, FLOW-013 pasos 5-6, RULE-005/021, AC-117, TPL-PANEL-SHELL).
 * ≥ lg dos columnas: imagen + ficha técnica (dimensiones, peso, derivados) | formulario de
 * catalogación (título interno, texto alternativo ≤250 con contador y guía, pie, autor/crédito,
 * URL de la fuente, licencia) + «Guardar», «Usado en» y la zona «Retirar medio» (bloqueada si el
 * medio está en uso por contenido publicado). Los errores 400/422 de la API se muestran por campo.
 */
@Component({
  selector: 'app-pagina-medio',
  imports: [
    RouterLink,
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    Insignia,
    AccesoDenegado,
    CampoTexto,
    DialogoConfirmacion,
    EnlaceValor,
    PaginaNoEncontradaPanel,
  ],
  providers: [DetalleMedioStore],
  templateUrl: './pagina-medio.html',
  styleUrls: ['./panel-formularios.css', './pagina-medio.css'],
})
export class PaginaMedio {
  protected readonly store = inject(DetalleMedioStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly seo = inject(Seo);

  protected readonly rutaMedios = RUTA_MEDIOS;
  protected readonly id = ID_CAMPO;
  protected readonly maximo = LONGITUD_MAXIMA;
  protected readonly guiaAlt = GUIA_ALT;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO_MEDIO;
  protected readonly etiquetaPendiente = ETIQUETA_PENDIENTE;
  protected readonly etiquetaTipoUso = ETIQUETA_TIPO_USO;
  protected readonly etiquetaRolUso = ETIQUETA_ROL_USO;
  protected readonly etiquetaEstadoEditorial = ETIQUETA_ESTADO;
  protected readonly varianteEditorial = varianteEstado;
  protected readonly fechaHora = formatearFechaHora;
  protected readonly peso = formatearPeso;

  // Formulario (EnlaceValor): se rellena con el medio cargado y tras cada guardado.
  protected readonly tituloInterno = signal('');
  protected readonly textoAlternativo = signal('');
  protected readonly pieDeFoto = signal('');
  protected readonly autorCredito = signal('');
  protected readonly fuenteUrl = signal('');
  protected readonly licenciaId = signal('');

  protected readonly errores = signal<Partial<Record<CampoCatalogacion, string>>>({});
  protected readonly erroresGenerales = signal<readonly string[]>([]);
  protected readonly guardando = signal(false);
  protected readonly confirmarRetiro = signal(false);
  protected readonly confirmarReactivacion = signal(false);
  protected readonly procesando = signal(false);
  protected readonly errorAccion = signal<string | null>(null);
  protected readonly fallaImagen = signal(false);

  protected readonly nombre = computed(() => {
    const medio = this.store.medio();
    return medio === null ? 'Detalle de medio' : nombreMedio(medio);
  });
  protected readonly variante = computed(() => {
    const medio = this.store.medio();
    return medio === null ? 'pendiente' : varianteEstadoMedio(medio.estado);
  });
  protected readonly vista = computed(() => {
    const medio = this.store.medio();
    if (medio === null) return null;
    const derivado = derivadoPara(medio.derivados, 960);
    return derivado === null ? null : { src: derivado.url, srcset: srcsetDe(medio.derivados) };
  });
  protected readonly pendiente = computed(() => this.store.medio()?.estado === 'PENDIENTE_METADATOS');
  protected readonly retirado = computed(() => this.store.medio()?.estado === 'RETIRADO');
  protected readonly licenciaIncompatible = computed(
    () => this.store.medio()?.pendientes.includes('licencia_incompatible') ?? false,
  );
  protected readonly enUsoPublicado = computed(() => this.store.medio()?.enUsoPublicado ?? false);
  protected readonly altObligatorio = computed(() => this.store.medio()?.estado === 'DISPONIBLE');

  constructor() {
    this.seo.establecer({ titulo: 'Detalle de medio', indexable: false });
    // Rellena el formulario con el medio cargado y tras cada guardado (solo escribe señales).
    effect(() => {
      const medio = this.store.medio();
      if (medio === null) return;
      this.rellenar(medio);
      this.seo.establecer({ titulo: `${nombreMedio(medio)} · Medios`, indexable: false });
    });
  }

  /** Al editar un campo desaparece su error (límite 3 de EnlaceValor, QA TKT-010 c2). */
  protected limpiarError(campo: CampoCatalogacion): void {
    if (this.errores()[campo] === undefined) return;
    this.errores.update((actual) => {
      const copia = { ...actual };
      delete copia[campo];
      return copia;
    });
  }

  protected async guardar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.guardando() || !this.enLinea()) return;
    const formulario = this.formulario();
    this.erroresGenerales.set([]);
    this.errorAccion.set(null);
    const locales = this.store.validar(formulario);
    this.errores.set(locales);
    if (Object.keys(locales).length > 0) {
      this.enfocarPrimerError();
      return;
    }
    this.guardando.set(true);
    const error = await this.store.catalogar(formulario);
    this.guardando.set(false);
    if (error === null) return;
    const { porCampo, generales } = erroresCatalogacion(error.campos, error.mensaje);
    this.errores.set(porCampo);
    this.erroresGenerales.set(generales);
    this.enfocarPrimerError();
  }

  protected async retirar(): Promise<void> {
    await this.ejecutarAccion(() => this.store.retirar(), this.confirmarRetiro);
  }

  protected async reactivar(): Promise<void> {
    await this.ejecutarAccion(() => this.store.reactivar(), this.confirmarReactivacion);
  }

  protected alFallarImagen(): void {
    this.fallaImagen.set(true);
  }

  private async ejecutarAccion(
    accion: () => Promise<{ mensaje: string } | null>,
    dialogo: WritableSignal<boolean>,
  ): Promise<void> {
    if (this.procesando()) return;
    this.procesando.set(true);
    this.errorAccion.set(null);
    const error = await accion();
    this.procesando.set(false);
    dialogo.set(false);
    if (error !== null) this.errorAccion.set(error.mensaje);
  }

  private formulario(): FormularioCatalogacion {
    return {
      tituloInterno: this.tituloInterno(),
      textoAlternativo: this.textoAlternativo(),
      pieDeFoto: this.pieDeFoto(),
      autorCredito: this.autorCredito(),
      fuenteUrl: this.fuenteUrl(),
      licenciaId: this.licenciaId(),
    };
  }

  private rellenar(medio: Medio): void {
    const datos = formularioDesdeMedio(medio);
    this.tituloInterno.set(datos.tituloInterno);
    this.textoAlternativo.set(datos.textoAlternativo);
    this.pieDeFoto.set(datos.pieDeFoto);
    this.autorCredito.set(datos.autorCredito);
    this.fuenteUrl.set(datos.fuenteUrl);
    this.licenciaId.set(datos.licenciaId);
    this.fallaImagen.set(false);
  }

  /** Lleva el foco al primer campo con error (o al resumen si solo hay errores generales). */
  private enfocarPrimerError(): void {
    afterNextRender(
      () => {
        const campo = ORDEN_CAMPOS.find((c) => this.errores()[c] !== undefined);
        const destino = campo
          ? this.documento.getElementById(ID_CAMPO[campo])
          : this.documento.getElementById('medio-errores');
        destino?.focus();
      },
      { injector: this.injector },
    );
  }
}
