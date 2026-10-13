import { DOCUMENT } from '@angular/common';
import { Component, Injector, afterNextRender, computed, effect, inject, signal, untracked } from '@angular/core';

import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import {
  AVISO_RESPONSABLE_VACIO,
  CAMPOS_CONFIGURACION,
  CampoConfiguracion,
  FormularioConfiguracion,
  LIMITES_CONFIGURACION,
  erroresConfiguracion,
  hayCambiosConfiguracion,
  responsableIncompleto,
} from '../domain/configuracion-sitio';
import { sinError } from '../domain/errores-formulario';
import { RUTA_TABLERO } from '../domain/secciones';
import { ConfiguracionSitioStore } from '../state/configuracion-sitio.store';
import { AccesoDenegado } from './acceso-denegado';
import { CampoTexto } from './campo-texto';
import { ControlSalida } from './control-salida';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { ConSalidaControlada } from './salida-editor.guard';

const ID_CAMPO: Readonly<Record<CampoConfiguracion, string>> = {
  nombreMarca: 'config-marca',
  lema: 'config-lema',
  textoDescargo: 'config-descargo',
  responsableNombre: 'config-responsable-nombre',
  responsableIdentificacion: 'config-responsable-id',
  responsableDomicilio: 'config-responsable-domicilio',
  responsableCanalAtencion: 'config-responsable-canal',
};

/**
 * SCR-047 Configuración del sitio (FEAT-047, RULE-014, AC-070, TPL-PANEL-SHELL; solo
 * Administrador): secciones Marca (nombre, lema), Descargo de responsabilidad (textarea con vista
 * previa del DisclaimerBlock) y Responsable del tratamiento (nombre o razón social, identificación,
 * domicilio y canal de atención) + «Guardar». Responsable incompleto → aviso del marcador
 * [RESPONSABLE POR DEFINIR]. Confirma al salir con cambios sin guardar.
 */
@Component({
  selector: 'app-pagina-configuracion',
  imports: [Banner, Boton, EstadoCargando, EstadoError, AccesoDenegado, CampoTexto, DialogoConfirmacion],
  providers: [ConfiguracionSitioStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina ancho-720" data-testid="pagina-configuracion">
        <h1 tabindex="-1">Configuración del sitio</h1>

        @if (store.configuracion()) {
          @if (store.avisoExito(); as aviso) {
            <app-banner variante="success" testId="config-exito" [permitirCerrar]="true" (cerrado)="store.descartarAviso()">{{ aviso }}</app-banner>
          }
          @if (responsableVacio()) {
            <app-banner variante="warning" testId="config-responsable-vacio">{{ avisoResponsable }}</app-banner>
          }
          @if (erroresGenerales().length > 0) {
            <div id="config-errores" class="resumen-errores" tabindex="-1" role="alert" data-testid="config-errores">
              <h2>No se pudo guardar</h2>
              <ul>
                @for (mensaje of erroresGenerales(); track $index) {
                  <li>{{ mensaje }}</li>
                }
              </ul>
            </div>
          }

          <form class="formulario" novalidate (submit)="guardar($event)" data-testid="config-formulario">
            <section class="seccion" aria-labelledby="config-marca-titulo">
              <h2 id="config-marca-titulo">Marca</h2>
              <app-campo-texto [campo]="campos.nombreMarca" etiqueta="Nombre de la marca" [idCampo]="id.nombreMarca" nombreCampo="nombre_marca" [obligatorio]="true" [maximo]="limites.nombreMarca" [error]="errores().nombreMarca ?? null" testId="config-campo-marca" (editado)="limpiarError('nombreMarca')" />
              <app-campo-texto [campo]="campos.lema" etiqueta="Lema" [idCampo]="id.lema" nombreCampo="lema" [maximo]="limites.lema" ayuda="Opcional. Una frase corta que acompaña a la marca." [error]="errores().lema ?? null" testId="config-campo-lema" (editado)="limpiarError('lema')" />
            </section>

            <section class="seccion" aria-labelledby="config-descargo-titulo">
              <h2 id="config-descargo-titulo">Descargo de responsabilidad</h2>
              <app-campo-texto [campo]="campos.textoDescargo" etiqueta="Texto del descargo" tipo="textarea" [idCampo]="id.textoDescargo" nombreCampo="texto_descargo" [obligatorio]="true" [maximo]="limites.textoDescargo" ayuda="Se muestra en las fichas de destinos e itinerarios, antes de la información práctica." [error]="errores().textoDescargo ?? null" testId="config-campo-descargo" (editado)="limpiarError('textoDescargo')" />
              <div class="vista-descargo" data-testid="config-vista-descargo">
                <p class="etiqueta-campo">Vista previa</p>
                <aside class="descargo" aria-labelledby="config-vista-descargo-titulo">
                  <h3 id="config-vista-descargo-titulo">Antes de salir a la aventura</h3>
                  <p>{{ campos.textoDescargo() || 'Escribe el texto del descargo para verlo aquí.' }}</p>
                </aside>
              </div>
            </section>

            <section class="seccion" aria-labelledby="config-responsable-titulo">
              <h2 id="config-responsable-titulo">Responsable del tratamiento</h2>
              <p class="ayuda">Aparece en la política de privacidad y en las páginas legales.</p>
              <app-campo-texto [campo]="campos.responsableNombre" etiqueta="Nombre o razón social" [idCampo]="id.responsableNombre" nombreCampo="responsable_nombre" [maximo]="limites.responsableNombre" [error]="errores().responsableNombre ?? null" testId="config-campo-responsable-nombre" (editado)="limpiarError('responsableNombre')" />
              <app-campo-texto [campo]="campos.responsableIdentificacion" etiqueta="Identificación (NIT o documento)" [idCampo]="id.responsableIdentificacion" nombreCampo="responsable_identificacion" [maximo]="limites.responsableIdentificacion" [error]="errores().responsableIdentificacion ?? null" testId="config-campo-responsable-id" (editado)="limpiarError('responsableIdentificacion')" />
              <app-campo-texto [campo]="campos.responsableDomicilio" etiqueta="Domicilio" [idCampo]="id.responsableDomicilio" nombreCampo="responsable_domicilio" [maximo]="limites.responsableDomicilio" [error]="errores().responsableDomicilio ?? null" testId="config-campo-responsable-domicilio" (editado)="limpiarError('responsableDomicilio')" />
              <app-campo-texto [campo]="campos.responsableCanalAtencion" etiqueta="Canal de atención" [idCampo]="id.responsableCanalAtencion" nombreCampo="responsable_canal_atencion" [maximo]="limites.responsableCanalAtencion" ayuda="Correo electrónico o dirección web donde se atienden las consultas sobre datos personales." [error]="errores().responsableCanalAtencion ?? null" testId="config-campo-responsable-canal" (editado)="limpiarError('responsableCanalAtencion')" />
            </section>

            <div class="acciones">
              <button type="submit" appBoton [cargando]="guardando()" [deshabilitadoEnfocable]="!enLinea()" data-testid="config-guardar">
                {{ guardando() ? 'Guardando…' : 'Guardar' }}
              </button>
              @if (!enLinea()) {
                <p class="ayuda">Sin conexión: podrás guardar cuando vuelva.</p>
              }
            </div>
          </form>

          <app-dialogo-confirmacion
            [abierto]="salida.abierta()"
            (abiertoChange)="salida.responder(false)"
            titulo="¿Salir sin guardar?"
            textoConfirmar="Salir sin guardar"
            idBase="config-dialogo-salir"
            (confirmar)="salida.responder(true)"
          >
            <p>Se perderán los cambios de la configuración que aún no guardaste.</p>
          </app-dialogo-confirmacion>
        } @else if (store.error(); as error) {
          <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="config-error" (reintentar)="store.recargar()" />
        } @else {
          <app-estado-cargando forma="linea" [cantidad]="6" etiqueta="Cargando la configuración…" testId="config-cargando" />
        }
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
  styles: `
    .vista-descargo {
      display: grid;
      gap: var(--bs-space-2);
    }
    .descargo {
      padding: var(--bs-space-4);
      border-inline-start: 4px solid var(--bs-color-status-warning-fg);
      background: var(--bs-color-status-warning-bg);
      white-space: pre-line;
      overflow-wrap: anywhere;
    }
    .descargo h3 {
      margin: 0 0 var(--bs-space-2);
      font-size: var(--bs-typography-body-font-size);
    }
    .descargo p {
      margin: 0;
    }
  `,
})
export class PaginaConfiguracion implements ConSalidaControlada {
  protected readonly store = inject(ConfiguracionSitioStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);

  protected readonly id = ID_CAMPO;
  protected readonly limites = LIMITES_CONFIGURACION;
  protected readonly avisoResponsable = AVISO_RESPONSABLE_VACIO;
  protected readonly rutaTablero = RUTA_TABLERO;

  protected readonly campos = {
    nombreMarca: signal(''),
    lema: signal(''),
    textoDescargo: signal(''),
    responsableNombre: signal(''),
    responsableIdentificacion: signal(''),
    responsableDomicilio: signal(''),
    responsableCanalAtencion: signal(''),
  };
  protected readonly errores = signal<Partial<Record<CampoConfiguracion, string>>>({});
  protected readonly erroresGenerales = signal<readonly string[]>([]);
  protected readonly guardando = signal(false);

  private readonly formulario = computed<FormularioConfiguracion>(() => ({
    nombreMarca: this.campos.nombreMarca(),
    lema: this.campos.lema(),
    textoDescargo: this.campos.textoDescargo(),
    responsableNombre: this.campos.responsableNombre(),
    responsableIdentificacion: this.campos.responsableIdentificacion(),
    responsableDomicilio: this.campos.responsableDomicilio(),
    responsableCanalAtencion: this.campos.responsableCanalAtencion(),
  }));
  /** AC-070: el aviso refleja los datos guardados (los que ven las páginas legales). */
  protected readonly responsableVacio = computed(() => {
    const guardado = this.store.guardado();
    return guardado !== null && responsableIncompleto(guardado);
  });
  protected readonly salida = new ControlSalida(() =>
    hayCambiosConfiguracion(this.formulario(), this.store.guardado()),
  );

  constructor() {
    inject(Seo).establecer({ titulo: 'Configuración del sitio', indexable: false });
    // Rellena el formulario con lo cargado y con lo que devuelve cada guardado.
    effect(() => {
      const guardado = this.store.guardado();
      if (guardado === null) return;
      untracked(() => {
        for (const campo of CAMPOS_CONFIGURACION) this.campos[campo].set(guardado[campo]);
      });
    });
  }

  puedeSalir(): boolean | Promise<boolean> {
    return this.salida.puedeSalir();
  }

  protected limpiarError(campo: CampoConfiguracion): void {
    this.errores.update((actual) => sinError(actual, campo));
  }

  protected async guardar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.guardando() || !this.enLinea()) return;
    const formulario = this.formulario();
    this.erroresGenerales.set([]);
    const locales = this.store.validar(formulario);
    this.errores.set(locales);
    if (Object.keys(locales).length > 0) {
      this.enfocarPrimerError();
      return;
    }
    this.guardando.set(true);
    const error = await this.store.guardar(formulario);
    this.guardando.set(false);
    if (error === null) return;
    const { porCampo, generales } = erroresConfiguracion(error.campos, error.mensaje);
    this.errores.set(porCampo);
    this.erroresGenerales.set(generales);
    this.enfocarPrimerError();
  }

  private enfocarPrimerError(): void {
    afterNextRender(
      () => {
        const campo = CAMPOS_CONFIGURACION.find((c) => this.errores()[c] !== undefined);
        const destino = this.documento.getElementById(campo ? ID_CAMPO[campo] : 'config-errores');
        destino?.focus();
      },
      { injector: this.injector },
    );
  }
}
