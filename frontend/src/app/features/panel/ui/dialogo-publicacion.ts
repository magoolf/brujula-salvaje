import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  input,
  output,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { textoRequisito, tituloResumenErrores } from '../domain/ciclo-editorial';
import { ContenidoEditable, DEFINICION_TIPO, rutaEditor } from '../domain/contenidos';
import { FormularioContenido, RefContenido, proponerSlug } from '../domain/formulario-contenido';
import { formatearFechaLarga } from '../domain/fechas';
import { ETIQUETA_TIPO_SINGULAR } from '../domain/tablero';
import { PublicacionStore } from '../state/publicacion.store';

/**
 * SCR-038 variante «Publicar / Actualizar publicación» (FEAT-036, FLOW-011/012, CHG-BP-001):
 * 1) «Comprobando requisitos…»; 2a) ErrorSummary enlazado a los campos (y a las entidades
 * co-publicadas o que bloquean la cascada) con «Volver al editor»; 2b) resumen (URL final con aviso
 * de slug fijo, «Se publicarán también», tipos que se retirarán en cascada) + «Confirmar». Esc
 * deshabilitado mientras procesa; doble clic neutralizado (ALT-017). Usa el PublicacionStore de la
 * página.
 */
@Component({
  selector: 'app-dialogo-publicacion',
  imports: [RouterLink, Banner, Boton],
  template: `
    <dialog
      #dialogo
      class="dialogo dialogo-md"
      aria-modal="true"
      aria-labelledby="dialogo-publicacion-titulo"
      data-testid="dialogo-publicacion"
      (cancel)="alCancelar($event)"
    >
      <div class="dialogo-cuerpo">
        <h2 id="dialogo-publicacion-titulo" #titulo tabindex="-1">{{ tituloDialogo() }}</h2>

        @switch (store.fase()) {
          @case ('analizando') {
            <p role="status" data-testid="publicacion-comprobando">Comprobando requisitos…</p>
          }
          @default {
            @if (store.conflicto() !== null) {
              <app-banner variante="error" testId="publicacion-conflicto">
                Otra persona guardó cambios mientras preparabas la publicación. Recarga la versión actual
                antes de volver a intentarlo.
                @for (ref of store.conflicto() ?? []; track ref.tipo + ref.id) {
                  <span> {{ etiquetaTipo[ref.tipo] }} «{{ ref.titulo }}».</span>
                }
              </app-banner>
            } @else if (store.error(); as error) {
              <app-banner variante="error" testId="publicacion-error">
                {{ error.mensaje }} El contenido sigue en su estado anterior.
                <button banner-accion type="button" appBoton tamano="sm" variante="secondary" data-testid="publicacion-reintentar" (click)="reintentar()">
                  Reintentar
                </button>
              </app-banner>
            }
            @if (store.impactoModificado()) {
              <app-banner variante="warning" testId="publicacion-impacto-modificado">
                El impacto cambió mientras confirmabas. Revísalo y vuelve a confirmar.
              </app-banner>
            }

            @if (store.totalPendientes() > 0) {
              <div class="resumen-errores" data-testid="publicacion-errores">
                <p class="titulo-errores">{{ tituloErrores() }}</p>
                @if (store.pendientesPrincipal().length > 0) {
                  <ul>
                    @for (req of store.pendientesPrincipal(); track $index) {
                      <li>
                        <a href="#" (click)="$event.preventDefault(); irACampo.emit(req.campo)" data-testid="publicacion-error-campo">{{ texto(req) }}</a>
                        @for (ref of req.referencias; track ref.tipo + ref.id) {
                          <span> · <a [routerLink]="enlaceEditor(ref)" (click)="cerrar()">{{ etiquetaTipo[ref.tipo] }} «{{ ref.titulo }}»</a></span>
                        }
                      </li>
                    }
                  </ul>
                }
                @for (entidad of store.pendientesCopublicacion(); track entidad.id) {
                  <p class="entidad">
                    {{ etiquetaTipo[entidad.tipo] }}
                    <a [routerLink]="enlaceEditor(entidad)" (click)="cerrar()">«{{ entidad.titulo }}»</a> (se publicaría también):
                  </p>
                  <ul data-testid="publicacion-errores-copublicacion">
                    @for (req of entidad.errores; track $index) {
                      <li>{{ texto(req) }}</li>
                    }
                  </ul>
                }
                @for (bloqueo of store.analisis()?.bloqueosCascada ?? []; track bloqueo.tipoAventura.id) {
                  <p class="entidad" data-testid="publicacion-bloqueo-cascada">
                    El tipo «{{ bloqueo.tipoAventura.titulo }}» se quedaría sin destinos publicados, pero no puede
                    retirarse porque lo usan {{ bloqueo.totalItinerarios }} itinerarios publicados. Quítales el tipo y vuelve a intentarlo:
                  </p>
                  <ul>
                    @for (it of bloqueo.itinerarios; track it.id) {
                      <li><a [routerLink]="enlaceEditor(it)" (click)="cerrar()">{{ it.titulo }}</a></li>
                    }
                  </ul>
                }
              </div>
              <div class="acciones">
                <button type="button" appBoton variante="secondary" data-testid="publicacion-volver" (click)="cerrar()">Volver al editor</button>
              </div>
            } @else if (store.analisis(); as analisis) {
              <dl class="resumen" data-testid="publicacion-resumen">
                <dt>Título</dt>
                <dd>{{ formulario().titulo }}</dd>
                @if (urlFinal(); as url) {
                  <dt>Dirección pública</dt>
                  <dd class="mono">{{ url }}</dd>
                }
                @if (formulario().fechaRevision) {
                  <dt>Fecha de revisión</dt>
                  <dd>{{ fechaRevision() }}</dd>
                }
              </dl>
              @if (avisoSlug()) {
                <p class="ayuda" data-testid="publicacion-aviso-slug">La dirección quedará fija al publicar por primera vez (no se podrá cambiar).</p>
              }
              @if (analisis.copublicacion.length > 0) {
                <section aria-labelledby="publicacion-copublicacion" data-testid="publicacion-copublicacion">
                  <h3 id="publicacion-copublicacion">Se publicarán también</h3>
                  <ul>
                    @for (tipo of analisis.copublicacion; track tipo.id) {
                      <li>{{ etiquetaTipo[tipo.tipo] }} «{{ tipo.titulo }}»</li>
                    }
                  </ul>
                </section>
              }
              @if (analisis.tiposEnCascada.length > 0) {
                <section aria-labelledby="publicacion-cascada" data-testid="publicacion-cascada">
                  <h3 id="publicacion-cascada">Se retirarán en cascada</h3>
                  <p class="ayuda">Estos tipos de aventura se quedarían sin destinos publicados.</p>
                  <ul>
                    @for (tipo of analisis.tiposEnCascada; track tipo.id) {
                      <li>{{ tipo.titulo }}</li>
                    }
                  </ul>
                </section>
              }
              @if (!enLinea()) {
                <p class="ayuda" data-testid="publicacion-sin-conexion">Sin conexión: no se puede confirmar ahora.</p>
              }
              <div class="acciones">
                <button
                  type="button"
                  appBoton
                  data-testid="publicacion-confirmar"
                  [cargando]="store.fase() === 'confirmando'"
                  [disabled]="!store.confirmable() || !enLinea()"
                  (click)="confirmar.emit()"
                >
                  {{ store.fase() === 'confirmando' ? textoProcesando() : textoConfirmar() }}
                </button>
                <button type="button" appBoton variante="secondary" data-testid="publicacion-cancelar" [disabled]="store.fase() === 'confirmando'" (click)="cerrar()">
                  Cancelar
                </button>
              </div>
            } @else {
              <div class="acciones">
                <button type="button" appBoton variante="secondary" (click)="cerrar()">Volver al editor</button>
              </div>
            }
          }
        }
      </div>
    </dialog>
  `,
  styleUrls: ['./panel-formularios.css', './dialogos-ciclo.css'],
})
export class DialogoPublicacion {
  readonly abierto = input(false);
  readonly abiertoChange = output<boolean>();
  readonly contenido = input.required<ContenidoEditable>();
  readonly formulario = input.required<FormularioContenido>();
  /** Confirmar (el editor ejecuta la operación con el store y su formulario). */
  readonly confirmar = output<void>();
  /** Reintentar tras un fallo de red (el editor repite el análisis o la confirmación). */
  readonly reintentarOperacion = output<void>();
  /** Enlace del ErrorSummary: cierra el diálogo y enfoca el campo. */
  readonly irACampo = output<string>();

  protected readonly store = inject(PublicacionStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private readonly titulo = viewChild.required<ElementRef<HTMLHeadingElement>>('titulo');
  private origen: HTMLElement | null = null;
  protected readonly etiquetaTipo = ETIQUETA_TIPO_SINGULAR;

  private readonly actualizar = computed(() => this.contenido().estado === 'PUBLICADO');
  protected readonly tituloDialogo = computed(() =>
    this.actualizar()
      ? `Actualizar la publicación de «${this.formulario().titulo}»`
      : `Publicar «${this.formulario().titulo}»`,
  );
  protected readonly textoConfirmar = computed(() =>
    this.actualizar() ? 'Actualizar publicación' : 'Confirmar publicación',
  );
  protected readonly textoProcesando = computed(() => (this.actualizar() ? 'Actualizando…' : 'Publicando…'));
  protected readonly tituloErrores = computed(() =>
    tituloResumenErrores(this.actualizar() ? 'actualizar' : 'publicar', this.store.totalPendientes()),
  );
  protected readonly urlFinal = computed(() => {
    const tipo = this.contenido().tipo;
    if (tipo === 'PAGINA') return null;
    const slug = this.formulario().slug.trim() || proponerSlug(this.formulario().titulo);
    return slug === '' ? null : `${DEFINICION_TIPO[tipo].prefijoPublico}${slug}`;
  });
  protected readonly avisoSlug = computed(() => !this.contenido().slugBloqueado && !this.actualizar());
  protected readonly fechaRevision = computed(() => {
    const fecha = this.formulario().fechaRevision;
    return fecha ? formatearFechaLarga(new Date(`${fecha}T12:00:00`)) : '';
  });

  constructor() {
    effect(() => {
      const abierto = this.abierto();
      const dialogo = this.dialogo().nativeElement;
      if (abierto && !dialogo.open) {
        this.origen = this.documento.activeElement as HTMLElement | null;
        dialogo.showModal();
        this.titulo().nativeElement.focus();
      } else if (!abierto && dialogo.open) {
        dialogo.close();
        this.origen?.focus();
        this.origen = null;
      }
    });
    // Al terminar el análisis, el foco va al título del resultado (HANDOFF SCR-038).
    effect(() => {
      if (this.store.fase() === 'lista' && this.abierto()) {
        afterNextRender(() => this.titulo().nativeElement.focus(), { injector: this.injector });
      }
    });
  }

  protected texto = textoRequisito;

  protected enlaceEditor(ref: Pick<RefContenido, 'tipo' | 'id'>): string {
    return rutaEditor(ref.tipo, ref.id);
  }

  protected reintentar(): void {
    this.reintentarOperacion.emit();
  }

  protected cerrar(): void {
    if (this.store.fase() === 'confirmando') return;
    this.abiertoChange.emit(false);
  }

  protected alCancelar(evento: Event): void {
    evento.preventDefault();
    this.cerrar();
  }
}
