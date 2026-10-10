import { DOCUMENT } from '@angular/common';
import {
  Component,
  Injector,
  WritableSignal,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import { rutaEditor } from '../domain/contenidos';
import { sinError } from '../domain/errores-formulario';
import { TipoContenido } from '../domain/modelos';
import { RUTA_TABLERO } from '../domain/secciones';
import { ETIQUETA_TIPO_SINGULAR } from '../domain/tablero';
import {
  AVISO_SOLO_ADMIN,
  CAMPOS_CATALOGO,
  CATALOGOS,
  CONTINENTES,
  CampoTextoCatalogo,
  Catalogo,
  DEFINICION_CATALOGO,
  ETIQUETA_CONTINENTE,
  ETIQUETA_ESCALA,
  ElementoCatalogo,
  FORMULARIO_CATALOGO_VACIO,
  FormularioCatalogo,
  NivelEscalaPanel,
  UsoBloqueante,
  erroresCatalogo,
  formularioDesdeElemento,
  formularioDesdeNivel,
  maximoCampo,
  nombreElemento,
  proponerSlugCatalogo,
  textoUsosBloqueo,
} from '../domain/taxonomias';
import { TaxonomiasStore } from '../state/taxonomias.store';
import { AccesoDenegado } from './acceso-denegado';
import { CampoTexto } from './campo-texto';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { DialogoFormulario } from './dialogo-formulario';
import { EnlaceValor } from './enlace-valor';

type CamposTexto = Readonly<Record<CampoTextoCatalogo, WritableSignal<string>>>;

const ETIQUETA_CAMPO: Readonly<Record<CampoTextoCatalogo, string>> = {
  nombre: 'Nombre',
  slug: 'Slug (dirección web)',
  continente: 'Continente',
  orden: 'Orden en los listados',
  codigoIso2: 'Código ISO (2 letras)',
  regionId: 'Región',
  descripcion: 'Descripción',
  codigo: 'Código',
  urlTextoLegal: 'URL del texto legal',
  etiqueta: 'Etiqueta',
};

const AYUDA_CAMPO: Partial<Record<CampoTextoCatalogo, string>> = {
  slug: 'Se propone a partir del nombre. Solo minúsculas sin tildes, números y guiones.',
  orden: 'Número entre 0 y 1000: los menores aparecen primero.',
  codigo: 'Identificador corto, p. ej. CC-BY-4.0.',
  urlTextoLegal: 'Opcional. Dirección completa del texto de la licencia.',
};

const TIPOS_CONTENIDO: readonly string[] = ['DESTINO', 'ITINERARIO', 'GUIA', 'TIPO', 'COLECCION', 'TERMINO', 'PAGINA'];

/** Edición en curso: alta (elemento null) o edición de un elemento o de un nivel de escala. */
type Edicion =
  | { readonly tipo: 'elemento'; readonly elemento: ElementoCatalogo | null }
  | { readonly tipo: 'nivel'; readonly nivel: NivelEscalaPanel };

/**
 * SCR-043 Taxonomías y catálogos (FEAT-044, RULE-007, RULE-014, AC-105, TPL-PANEL-SHELL): pestañas
 * (patrón ARIA tabs con activación manual; < md, un select «Catálogo») reflejadas en la URL
 * (`?catalogo=`), y por pestaña «Nuevo» + DataTable (nombre, estado, acciones Editar/Retirar) con
 * los formularios en un diálogo. Licencias y escalas: solo Administrador (el Editor las ve en solo
 * lectura con el aviso). Retirar algo en uso → ImpactSummary bloqueado con los usos (RULE-007).
 */
@Component({
  selector: 'app-pagina-taxonomias',
  imports: [
    RouterLink,
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    EstadoVacio,
    Insignia,
    AccesoDenegado,
    CampoTexto,
    DialogoConfirmacion,
    DialogoFormulario,
    EnlaceValor,
  ],
  providers: [TaxonomiasStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina" data-testid="pagina-taxonomias">
        <h1 tabindex="-1" #encabezado>Taxonomías y catálogos</h1>

        <div class="selector-movil campo">
          <label for="taxonomias-catalogo">Catálogo</label>
          <select id="taxonomias-catalogo" name="catalogo" class="entrada-texto" data-testid="taxonomias-select" (change)="alElegirCatalogo($event)">
            @for (c of catalogos; track c) {
              <option [value]="c" [selected]="c === store.catalogo()">{{ definiciones[c].etiqueta }}</option>
            }
          </select>
        </div>
        <div class="pestanas" role="tablist" aria-label="Catálogos" data-testid="taxonomias-pestanas">
          @for (c of catalogos; track c; let i = $index) {
            <button
              type="button"
              role="tab"
              class="pestana"
              [id]="'taxonomias-tab-' + c"
              [attr.aria-selected]="c === store.catalogo()"
              [attr.aria-controls]="'taxonomias-panel'"
              [attr.tabindex]="c === store.catalogo() ? 0 : -1"
              [attr.data-testid]="'taxonomias-tab-' + c"
              (click)="void activar(c)"
              (keydown)="alTeclearPestana($event, i)"
            >
              {{ definiciones[c].etiqueta }}
            </button>
          }
        </div>

        <section id="taxonomias-panel" role="tabpanel" class="panel" [attr.aria-labelledby]="'taxonomias-tab-' + store.catalogo()" data-testid="taxonomias-panel">
          <div class="cabecera-pagina">
            <h2>{{ store.definicion().etiqueta }}</h2>
            @if (store.puedeEditar() && store.definicion().admiteAltas) {
              <button type="button" appBoton [deshabilitadoEnfocable]="!enLinea()" data-testid="taxonomias-nuevo" (click)="abrirAlta()">{{ store.definicion().nuevo }}</button>
            }
          </div>

          @if (!store.puedeEditar()) {
            <app-banner variante="info" testId="taxonomias-solo-admin">{{ avisoSoloAdmin }}</app-banner>
          }
          @if (store.avisoExito(); as aviso) {
            <app-banner variante="success" testId="taxonomias-exito" [permitirCerrar]="true" (cerrado)="store.limpiarAvisos()">{{ aviso }}</app-banner>
          }
          @if (store.bloqueo(); as bloqueo) {
            <div class="resumen-errores" role="alert" tabindex="-1" id="taxonomias-bloqueo" data-testid="taxonomias-bloqueo">
              <h3>No se puede retirar</h3>
              <p>{{ bloqueo.mensaje }}</p>
              @if (bloqueo.usos.length > 0) {
                <p>{{ textoUsos(bloqueo.total) }}</p>
                <ul data-testid="taxonomias-bloqueo-usos">
                  @for (uso of bloqueo.usos; track uso.tipo + uso.id) {
                    <li>
                      @if (enlaceUso(uso); as ruta) {
                        <a [routerLink]="ruta">{{ uso.titulo }}</a>
                      } @else {
                        {{ uso.titulo }}
                      }
                      <span class="ayuda">({{ etiquetaUso(uso) }})</span>
                    </li>
                  }
                </ul>
              }
            </div>
          }
          @if (errorAccion(); as mensaje) {
            <app-banner variante="error" testId="taxonomias-error-accion">{{ mensaje }}</app-banner>
          }

          @if (store.catalogo() === 'escalas') {
            @if (store.escalas(); as escalas) {
              @for (grupo of [escalas.dificultad, escalas.presupuesto]; track $index) {
                @if (grupo.length > 0) {
                  <div class="tabla-contenedor" tabindex="0" role="region" [attr.aria-label]="'Escala de ' + etiquetaEscala[grupo[0].escala].toLowerCase()">
                    <table class="tabla" [attr.data-testid]="'taxonomias-tabla-' + grupo[0].escala.toLowerCase()">
                      <caption class="caption-visible">{{ etiquetaEscala[grupo[0].escala] }}</caption>
                      <thead>
                        <tr>
                          <th scope="col">Nivel</th>
                          <th scope="col">Etiqueta</th>
                          <th scope="col">Descripción</th>
                          @if (store.puedeEditar()) {
                            <th scope="col">Acciones</th>
                          }
                        </tr>
                      </thead>
                      <tbody>
                        @for (n of grupo; track n.id) {
                          <tr data-testid="taxonomias-fila">
                            <td data-etiqueta="Nivel" class="numero">{{ n.nivel }}</td>
                            <th scope="row" data-etiqueta="Etiqueta">{{ n.etiqueta }}</th>
                            <td data-etiqueta="Descripción">{{ n.descripcion }}</td>
                            @if (store.puedeEditar()) {
                              <td data-etiqueta="Acciones">
                                <button type="button" appBoton tamano="sm" variante="secondary" [deshabilitadoEnfocable]="!enLinea()" [attr.data-testid]="'taxonomias-editar-nivel-' + n.id" (click)="abrirNivel(n)">
                                  Editar <span class="bs-solo-lectores">{{ etiquetaEscala[n.escala] }} {{ n.nivel }}</span>
                                </button>
                              </td>
                            }
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }
              }
            } @else if (store.error(); as error) {
              <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="taxonomias-error" (reintentar)="store.recargar()" />
            } @else {
              <app-estado-cargando forma="fila" [cantidad]="5" etiqueta="Cargando las escalas…" testId="taxonomias-cargando" />
            }
          } @else {
            @if (store.elementos(); as elementos) {
              @if (elementos.length === 0) {
                <app-estado-vacio [titulo]="'Aún no hay ' + store.definicion().plural" testId="taxonomias-vacio" idTitulo="taxonomias-vacio-titulo">
                  @if (store.puedeEditar()) {
                    <p>Crea el primer elemento con «{{ store.definicion().nuevo }}».</p>
                  }
                </app-estado-vacio>
              } @else {
                <div class="tabla-contenedor" tabindex="0" role="region" [attr.aria-label]="store.definicion().etiqueta">
                  <table class="tabla" data-testid="taxonomias-tabla" [attr.aria-busy]="store.cargando()">
                    <caption class="bs-solo-lectores">{{ store.definicion().etiqueta }}: {{ elementos.length }} elementos</caption>
                    <thead>
                      <tr>
                        <th scope="col">Nombre</th>
                        @switch (store.catalogo()) {
                          @case ('regiones') {
                            <th scope="col">Continente</th>
                            <th scope="col" class="col-secundaria">Orden</th>
                          }
                          @case ('paises') {
                            <th scope="col">Código</th>
                            <th scope="col" class="col-secundaria">Región</th>
                          }
                          @case ('categorias') {
                            <th scope="col" class="col-secundaria">Descripción</th>
                            <th scope="col" class="col-secundaria">Orden</th>
                          }
                          @case ('licencias') {
                            <th scope="col">Permite publicar</th>
                            <th scope="col" class="col-secundaria">Exige atribución</th>
                          }
                        }
                        <th scope="col">Estado</th>
                        @if (store.puedeEditar()) {
                          <th scope="col">Acciones</th>
                        }
                      </tr>
                    </thead>
                    <tbody>
                      @for (e of elementos; track e.id) {
                        <tr data-testid="taxonomias-fila">
                          <th scope="row" data-etiqueta="Nombre">{{ nombre(e) }}</th>
                          @switch (e.catalogo) {
                            @case ('regiones') {
                              <td data-etiqueta="Continente">{{ etiquetaContinente[e.continente] }}</td>
                              <td data-etiqueta="Orden" class="numero col-secundaria">{{ e.orden }}</td>
                            }
                            @case ('paises') {
                              <td data-etiqueta="Código">{{ e.codigoIso2 }}</td>
                              <td data-etiqueta="Región" class="col-secundaria">{{ store.nombreRegion(e.regionId) }}</td>
                            }
                            @case ('categorias') {
                              <td data-etiqueta="Descripción" class="col-secundaria">{{ e.descripcion }}</td>
                              <td data-etiqueta="Orden" class="numero col-secundaria">{{ e.orden }}</td>
                            }
                            @case ('licencias') {
                              <td data-etiqueta="Permite publicar">{{ e.compatiblePublicacion ? 'Sí' : 'No' }}</td>
                              <td data-etiqueta="Exige atribución" class="col-secundaria">{{ e.requiereAtribucion ? 'Sí' : 'No' }}</td>
                            }
                          }
                          <td data-etiqueta="Estado">
                            <app-insignia [variante]="e.activo ? 'publicado' : 'retirado'">{{ e.activo ? 'Activo' : 'Retirado' }}</app-insignia>
                          </td>
                          @if (store.puedeEditar()) {
                            <td data-etiqueta="Acciones">
                              <div class="acciones-fila">
                                <button type="button" appBoton tamano="sm" variante="secondary" [deshabilitadoEnfocable]="!enLinea()" [attr.data-testid]="'taxonomias-editar-' + e.id" (click)="abrirEdicion(e)">
                                  Editar <span class="bs-solo-lectores">{{ nombre(e) }}</span>
                                </button>
                                @if (e.activo) {
                                  <button type="button" appBoton tamano="sm" variante="ghost" [deshabilitadoEnfocable]="!enLinea()" [attr.data-testid]="'taxonomias-retirar-' + e.id" (click)="pedirCambioEstado(e)">
                                    Retirar <span class="bs-solo-lectores">{{ nombre(e) }}</span>
                                  </button>
                                } @else {
                                  <button type="button" appBoton tamano="sm" variante="ghost" [deshabilitadoEnfocable]="!enLinea()" [attr.data-testid]="'taxonomias-reactivar-' + e.id" (click)="pedirCambioEstado(e)">
                                    Reactivar <span class="bs-solo-lectores">{{ nombre(e) }}</span>
                                  </button>
                                }
                              </div>
                            </td>
                          }
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            } @else if (store.error(); as error) {
              <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="taxonomias-error" (reintentar)="store.recargar()" />
            } @else {
              <app-estado-cargando forma="fila" [cantidad]="6" etiqueta="Cargando el catálogo…" testId="taxonomias-cargando" />
            }
          }
        </section>

        <app-dialogo-formulario
          [abierto]="edicion() !== null"
          (abiertoChange)="cerrarEdicion()"
          [titulo]="tituloDialogo()"
          [procesando]="guardando()"
          [respaldoFoco]="encabezado"
          idBase="taxonomias-dialogo"
          (enviar)="guardar()"
        >
          @if (erroresGenerales().length > 0) {
            <div class="resumen-errores" role="alert" data-testid="taxonomias-dialogo-errores">
              @for (mensaje of erroresGenerales(); track $index) {
                <p>{{ mensaje }}</p>
              }
            </div>
          }
          @for (campo of camposVisibles(); track campo) {
            @switch (campo) {
              @case ('continente') {
                <div class="campo">
                  <label for="taxonomias-campo-continente">Continente <span class="obligatorio">(obligatorio)</span></label>
                  <select id="taxonomias-campo-continente" name="continente" class="entrada-texto" aria-required="true" [appEnlaceValor]="texto.continente" [attr.aria-invalid]="errores().continente ? 'true' : null" [attr.aria-describedby]="errores().continente ? 'taxonomias-campo-continente-error' : null" data-testid="taxonomias-campo-continente" (change)="limpiarError('continente')">
                    <option value="" [selected]="texto.continente() === ''">Elige un continente</option>
                    @for (c of continentes; track c) {
                      <option [value]="c" [selected]="texto.continente() === c">{{ etiquetaContinente[c] }}</option>
                    }
                  </select>
                  @if (errores().continente; as mensaje) {
                    <p class="error-campo" id="taxonomias-campo-continente-error">{{ mensaje }}</p>
                  }
                </div>
              }
              @case ('regionId') {
                <div class="campo">
                  <label for="taxonomias-campo-regionId">Región <span class="obligatorio">(obligatorio)</span></label>
                  <select id="taxonomias-campo-regionId" name="region_id" class="entrada-texto" aria-required="true" [appEnlaceValor]="texto.regionId" [attr.aria-invalid]="errores().regionId ? 'true' : null" [attr.aria-describedby]="errores().regionId ? 'taxonomias-campo-regionId-error' : null" data-testid="taxonomias-campo-regionId" (change)="limpiarError('regionId')">
                    <option value="" [selected]="texto.regionId() === ''">Elige una región</option>
                    @for (r of store.regiones(); track r.id) {
                      <option [value]="'' + r.id" [selected]="texto.regionId() === '' + r.id">{{ r.nombre }}{{ r.activo ? '' : ' (retirada)' }}</option>
                    }
                  </select>
                  @if (errores().regionId; as mensaje) {
                    <p class="error-campo" id="taxonomias-campo-regionId-error">{{ mensaje }}</p>
                  }
                </div>
              }
              @default {
                <app-campo-texto
                  [campo]="texto[campo]"
                  [etiqueta]="etiquetaCampo[campo]"
                  [tipo]="campo === 'descripcion' ? 'textarea' : campo === 'urlTextoLegal' ? 'url' : 'text'"
                  [idCampo]="'taxonomias-campo-' + campo"
                  [nombreCampo]="campo"
                  [obligatorio]="campo !== 'urlTextoLegal'"
                  [maximo]="maximo(campo)"
                  [ayuda]="ayudaCampo[campo] ?? null"
                  [error]="errores()[campo] ?? null"
                  [testId]="'taxonomias-campo-' + campo"
                  (editado)="alEditar(campo)"
                />
              }
            }
          }
          @if (store.catalogo() === 'licencias') {
            <fieldset class="grupo">
              <legend>Condiciones</legend>
              <label class="casilla">
                <input type="checkbox" name="compatible_publicacion" [checked]="compatiblePublicacion()" data-testid="taxonomias-campo-compatible" (change)="compatiblePublicacion.set($any($event.target).checked)" />
                Permite publicar las imágenes con esta licencia
              </label>
              <label class="casilla">
                <input type="checkbox" name="requiere_atribucion" [checked]="requiereAtribucion()" data-testid="taxonomias-campo-atribucion" (change)="requiereAtribucion.set($any($event.target).checked)" />
                Exige citar al autor (atribución)
              </label>
            </fieldset>
          }
        </app-dialogo-formulario>

        <app-dialogo-confirmacion
          [abierto]="cambioEstado() !== null"
          (abiertoChange)="cambioEstado.set(null)"
          [titulo]="tituloCambioEstado()"
          [textoConfirmar]="cambioEstado()?.activo ? 'Retirar' : 'Reactivar'"
          [variante]="cambioEstado()?.activo ? 'danger' : 'primary'"
          [procesando]="guardando()"
          [respaldoFoco]="encabezado"
          idBase="taxonomias-dialogo-estado"
          (confirmar)="confirmarCambioEstado()"
        >
          @if (cambioEstado()?.activo) {
            <p>Dejará de poder elegirse en contenido nuevo. Si lo usa contenido publicado, no se podrá retirar hasta quitarlo de ese contenido.</p>
          } @else {
            <p>Volverá a poder elegirse en el contenido.</p>
          }
        </app-dialogo-confirmacion>
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
  styles: `
    .pestanas {
      display: flex;
      flex-wrap: wrap;
      gap: var(--bs-space-1);
      border-bottom: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
    }
    .pestana {
      min-height: var(--bs-size-target);
      padding: var(--bs-space-2) var(--bs-space-3);
      border: 0;
      border-bottom: 3px solid transparent;
      background: none;
      color: var(--bs-color-text-default);
      font: inherit;
      cursor: pointer;
    }
    .pestana[aria-selected='true'] {
      border-bottom-color: var(--bs-color-border-brand);
      font-weight: var(--bs-font-weight-semibold);
    }
    .pestana:hover {
      color: var(--bs-color-text-link-hover);
    }
    .selector-movil {
      display: none;
    }
    @media (max-width: 47.99rem) {
      .selector-movil {
        display: grid;
      }
      .pestanas {
        display: none;
      }
    }
    .panel {
      display: grid;
      gap: var(--bs-space-4);
    }
    .panel h2,
    .resumen-errores h3 {
      margin: 0;
    }
    .caption-visible {
      padding-bottom: var(--bs-space-2);
      text-align: start;
      font-weight: var(--bs-font-weight-semibold);
    }
    .grupo {
      display: grid;
      gap: var(--bs-space-2);
      margin: 0;
      padding: 0;
      border: 0;
    }
    .casilla {
      display: flex;
      align-items: center;
      gap: var(--bs-space-2);
      min-height: var(--bs-size-target);
    }
    @media (forced-colors: active) {
      .pestana[aria-selected='true'] {
        border-bottom-color: Highlight;
      }
    }
  `,
})
export class PaginaTaxonomias {
  protected readonly store = inject(TaxonomiasStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);

  protected readonly catalogos = CATALOGOS;
  protected readonly definiciones = DEFINICION_CATALOGO;
  protected readonly continentes = CONTINENTES;
  protected readonly etiquetaContinente = ETIQUETA_CONTINENTE;
  protected readonly etiquetaEscala = ETIQUETA_ESCALA;
  protected readonly etiquetaCampo = ETIQUETA_CAMPO;
  protected readonly ayudaCampo = AYUDA_CAMPO;
  protected readonly avisoSoloAdmin = AVISO_SOLO_ADMIN;
  protected readonly rutaTablero = RUTA_TABLERO;
  protected readonly nombre = nombreElemento;
  protected readonly textoUsos = textoUsosBloqueo;

  protected readonly texto: CamposTexto = {
    nombre: signal(''),
    slug: signal(''),
    continente: signal(''),
    orden: signal('0'),
    codigoIso2: signal(''),
    regionId: signal(''),
    descripcion: signal(''),
    codigo: signal(''),
    urlTextoLegal: signal(''),
    etiqueta: signal(''),
  };
  protected readonly requiereAtribucion = signal(true);
  protected readonly compatiblePublicacion = signal(true);

  protected readonly edicion = signal<Edicion | null>(null);
  protected readonly cambioEstado = signal<{ elemento: ElementoCatalogo; activo: boolean } | null>(null);
  protected readonly errores = signal<Partial<Record<CampoTextoCatalogo, string>>>({});
  protected readonly erroresGenerales = signal<readonly string[]>([]);
  protected readonly errorAccion = signal<string | null>(null);
  protected readonly guardando = signal(false);
  private slugManual = false;

  protected readonly camposVisibles = computed(() => CAMPOS_CATALOGO[this.store.catalogo()]);
  protected readonly tituloDialogo = computed(() => {
    const edicion = this.edicion();
    const def = this.store.definicion();
    if (edicion === null) return def.etiqueta;
    if (edicion.tipo === 'nivel') return `Editar nivel ${edicion.nivel.nivel} de ${ETIQUETA_ESCALA[edicion.nivel.escala].toLowerCase()}`;
    return edicion.elemento === null ? def.nuevo : `Editar «${nombreElemento(edicion.elemento)}»`;
  });
  protected readonly tituloCambioEstado = computed(() => {
    const cambio = this.cambioEstado();
    if (cambio === null) return '';
    return `¿${cambio.activo ? 'Retirar' : 'Reactivar'} «${nombreElemento(cambio.elemento)}»?`;
  });

  constructor() {
    inject(Seo).establecer({ titulo: 'Taxonomías y catálogos', indexable: false });
    // Al cambiar de pestaña se cierran los diálogos y se limpian los avisos de la anterior.
    effect(() => {
      this.store.catalogo();
      untracked(() => {
        this.edicion.set(null);
        this.cambioEstado.set(null);
        this.errorAccion.set(null);
        this.store.limpiarAvisos();
      });
    });
  }

  protected maximo(campo: CampoTextoCatalogo): number | null {
    return maximoCampo(this.store.catalogo(), campo);
  }

  // ------------------------------------------------------------------ pestañas
  /**
   * Activa una pestaña navegando a `?catalogo=` (enlace directo y «Atrás»). Cambiar de pestaña no es
   * cambiar de vista: el foco que FocoRuta lleva al h1 tras la navegación se devuelve al control que
   * la activó, la pestaña o el select en móvil (WCAG 2.4.3, QA TKT-024 FALLO-02). FocoRuta registra
   * su afterNextRender al emitirse NavigationEnd, antes de que resuelva `navigate`: este va después.
   */
  protected async activar(catalogo: Catalogo, origen: 'pestana' | 'select' = 'pestana'): Promise<void> {
    if (catalogo === this.store.catalogo()) return;
    const ok = await this.router.navigate([], { relativeTo: this.ruta, queryParams: { catalogo } });
    if (!ok) return;
    const id = origen === 'select' ? 'taxonomias-catalogo' : `taxonomias-tab-${catalogo}`;
    afterNextRender(() => this.documento.getElementById(id)?.focus(), { injector: this.injector });
  }

  protected alElegirCatalogo(evento: Event): void {
    const valor = (evento.target as HTMLSelectElement).value;
    const catalogo = CATALOGOS.find((c) => c === valor);
    if (catalogo !== undefined) void this.activar(catalogo, 'select');
  }

  /** Activación manual: las flechas, Inicio y Fin mueven el foco; Enter/Espacio activan (click). */
  protected alTeclearPestana(evento: KeyboardEvent, indice: number): void {
    const total = CATALOGOS.length;
    let destino: number | null = null;
    if (evento.key === 'ArrowRight') destino = (indice + 1) % total;
    else if (evento.key === 'ArrowLeft') destino = (indice - 1 + total) % total;
    else if (evento.key === 'Home') destino = 0;
    else if (evento.key === 'End') destino = total - 1;
    if (destino === null) return;
    evento.preventDefault();
    this.documento.getElementById(`taxonomias-tab-${CATALOGOS[destino]}`)?.focus();
  }

  // ------------------------------------------------------------------ alta y edición
  protected abrirAlta(): void {
    this.rellenar(FORMULARIO_CATALOGO_VACIO);
    this.slugManual = false;
    this.edicion.set({ tipo: 'elemento', elemento: null });
  }

  protected abrirEdicion(elemento: ElementoCatalogo): void {
    this.rellenar(formularioDesdeElemento(elemento));
    this.slugManual = true;
    this.edicion.set({ tipo: 'elemento', elemento });
  }

  protected abrirNivel(nivel: NivelEscalaPanel): void {
    this.rellenar(formularioDesdeNivel(nivel));
    this.edicion.set({ tipo: 'nivel', nivel });
  }

  protected cerrarEdicion(): void {
    if (!this.guardando()) this.edicion.set(null);
  }

  protected alEditar(campo: CampoTextoCatalogo): void {
    this.limpiarError(campo);
    if (campo === 'slug') this.slugManual = true;
    const edicion = this.edicion();
    if (campo === 'nombre' && !this.slugManual && edicion?.tipo === 'elemento' && edicion.elemento === null) {
      this.texto.slug.set(proponerSlugCatalogo(this.store.catalogo(), this.texto.nombre()));
      this.limpiarError('slug');
    }
  }

  protected limpiarError(campo: CampoTextoCatalogo): void {
    this.errores.update((actual) => sinError(actual, campo));
  }

  protected async guardar(): Promise<void> {
    const edicion = this.edicion();
    if (edicion === null || this.guardando() || !this.enLinea()) return;
    const catalogo = this.store.catalogo();
    const formulario = this.formulario();
    this.erroresGenerales.set([]);
    const locales = this.store.validar(catalogo, formulario);
    this.errores.set(locales);
    if (Object.keys(locales).length > 0) {
      this.enfocarPrimerError(catalogo);
      return;
    }
    this.guardando.set(true);
    const error =
      edicion.tipo === 'nivel'
        ? await this.store.guardarNivel(edicion.nivel, formulario)
        : await this.store.guardar(formulario, edicion.elemento);
    this.guardando.set(false);
    if (error === null) {
      this.edicion.set(null);
      return;
    }
    const { porCampo, generales } = erroresCatalogo(error.campos, error.mensaje, catalogo);
    this.errores.set(porCampo);
    this.erroresGenerales.set(generales);
    this.enfocarPrimerError(catalogo);
  }

  // ------------------------------------------------------------------ retirar / reactivar
  protected pedirCambioEstado(elemento: ElementoCatalogo): void {
    this.errorAccion.set(null);
    this.cambioEstado.set({ elemento, activo: elemento.activo });
  }

  protected async confirmarCambioEstado(): Promise<void> {
    const cambio = this.cambioEstado();
    if (cambio === null || this.guardando()) return;
    this.guardando.set(true);
    const error = await this.store.cambiarEstado(cambio.elemento, !cambio.activo);
    this.guardando.set(false);
    this.cambioEstado.set(null);
    if (error !== null) this.errorAccion.set(error.mensaje);
    if (this.store.bloqueo() !== null) {
      afterNextRender(() => this.documento.getElementById('taxonomias-bloqueo')?.focus(), { injector: this.injector });
    }
  }

  protected enlaceUso(uso: UsoBloqueante): string | null {
    return TIPOS_CONTENIDO.includes(uso.tipo) ? rutaEditor(uso.tipo as TipoContenido, uso.id) : null;
  }

  protected etiquetaUso(uso: UsoBloqueante): string {
    return ETIQUETA_TIPO_SINGULAR[uso.tipo as TipoContenido] ?? uso.tipo;
  }

  // ------------------------------------------------------------------ utilidades
  private formulario(): FormularioCatalogo {
    return {
      nombre: this.texto.nombre(),
      slug: this.texto.slug(),
      continente: this.texto.continente(),
      orden: this.texto.orden(),
      codigoIso2: this.texto.codigoIso2(),
      regionId: this.texto.regionId(),
      descripcion: this.texto.descripcion(),
      codigo: this.texto.codigo(),
      urlTextoLegal: this.texto.urlTextoLegal(),
      etiqueta: this.texto.etiqueta(),
      requiereAtribucion: this.requiereAtribucion(),
      compatiblePublicacion: this.compatiblePublicacion(),
    };
  }

  private rellenar(f: FormularioCatalogo): void {
    for (const campo of Object.keys(this.texto) as CampoTextoCatalogo[]) this.texto[campo].set(f[campo]);
    this.requiereAtribucion.set(f.requiereAtribucion);
    this.compatiblePublicacion.set(f.compatiblePublicacion);
    this.errores.set({});
    this.erroresGenerales.set([]);
  }

  private enfocarPrimerError(catalogo: Catalogo): void {
    afterNextRender(
      () => {
        const campo = CAMPOS_CATALOGO[catalogo].find((c) => this.errores()[c] !== undefined);
        if (campo !== undefined) this.documento.getElementById(`taxonomias-campo-${campo}`)?.focus();
      },
      { injector: this.injector },
    );
  }
}
