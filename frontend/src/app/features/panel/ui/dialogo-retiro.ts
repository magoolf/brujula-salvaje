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
  signal,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { ETIQUETA_DESTACADO, LONGITUD_MAXIMA_MOTIVO, motivoValido } from '../domain/ciclo-editorial';
import { rutaEditor } from '../domain/contenidos';
import { RefContenido } from '../domain/formulario-contenido';
import { ETIQUETA_TIPO_SINGULAR } from '../domain/tablero';
import { PublicacionStore } from '../state/publicacion.store';

/**
 * SCR-038 variante «Retirar» (FEAT-037, FLOW-012, RULE-007/025, AC-112/127/128): alertdialog con
 * el ImpactSummary (itinerarios y tipos que se retirarán en cascada, colecciones, destacados y
 * enlaces entrantes), motivo obligatorio (foco inicial; «Solo lo verá el equipo») y «Retirar»
 * (danger, deshabilitado sin motivo). Si hay usos que bloquean (RULE-007) o la cascada de un tipo
 * está bloqueada por itinerarios publicados de otros destinos, variante bloqueada: solo «Entendido».
 * Si el servidor calcula otra cascada al confirmar (409 impacto_modificado), se muestra la nueva.
 */
@Component({
  selector: 'app-dialogo-retiro',
  imports: [RouterLink, Banner, Boton],
  template: `
    <dialog
      #dialogo
      class="dialogo dialogo-md"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="dialogo-retiro-titulo"
      data-testid="dialogo-retiro"
      (cancel)="alCancelar($event)"
    >
      <div class="dialogo-cuerpo">
        <h2 id="dialogo-retiro-titulo" #encabezado tabindex="-1">Retirar «{{ titulo() }}»</h2>
        @if (store.fase() === 'analizando') {
          <p role="status" data-testid="retiro-calculando">Calculando el impacto…</p>
        } @else if (store.impacto(); as impacto) {
          @if (store.impactoModificado()) {
            <app-banner variante="warning" testId="retiro-impacto-modificado">
              El impacto cambió mientras confirmabas. Revísalo y vuelve a confirmar.
            </app-banner>
          }
          @if (store.conflicto() !== null) {
            <app-banner variante="error" testId="retiro-conflicto">
              Otra persona guardó cambios en este contenido. Recarga la versión actual antes de retirarlo.
            </app-banner>
          } @else if (store.error(); as error) {
            <app-banner variante="error" testId="retiro-error">
              {{ error.mensaje }} El contenido sigue en su estado anterior.
              <button banner-accion type="button" appBoton tamano="sm" variante="secondary" (click)="intentar()">Reintentar</button>
            </app-banner>
          }

          <div class="impacto" data-testid="retiro-impacto">
            @if (impacto.bloqueos.length > 0) {
              <p class="titulo-errores" data-testid="retiro-bloqueado">No se puede retirar: lo usa contenido publicado.</p>
              <ul>
                @for (uso of impacto.bloqueos; track uso.tipoEntidad + uso.id) {
                  <li>{{ uso.titulo }}</li>
                }
              </ul>
            }
            @for (bloqueo of impacto.bloqueosCascada; track bloqueo.tipoAventura.id) {
              <p class="titulo-errores" data-testid="retiro-bloqueo-cascada">
                El tipo «{{ bloqueo.tipoAventura.titulo }}» se quedaría sin destinos publicados, pero lo usan
                {{ bloqueo.totalItinerarios }} itinerarios publicados de otros destinos. Quítales el tipo y vuelve a intentarlo:
              </p>
              <ul>
                @for (it of bloqueo.itinerarios; track it.id) {
                  <li><a [routerLink]="enlaceEditor(it)" (click)="cerrar()">{{ it.titulo }}</a></li>
                }
              </ul>
            }
            @if (impacto.itinerariosEnCascada.length > 0) {
              <section aria-labelledby="retiro-itinerarios" data-testid="retiro-itinerarios">
                <h3 id="retiro-itinerarios">Se retirarán también estos itinerarios</h3>
                <ul>
                  @for (it of impacto.itinerariosEnCascada; track it.id) {
                    <li>{{ it.titulo }}</li>
                  }
                </ul>
              </section>
            }
            @if (impacto.tiposEnCascada.length > 0) {
              <section aria-labelledby="retiro-tipos" data-testid="retiro-tipos">
                <h3 id="retiro-tipos">Se retirarán también estos tipos de aventura</h3>
                <p class="ayuda">Se quedarían sin destinos publicados (RULE-025).</p>
                <ul>
                  @for (tipo of impacto.tiposEnCascada; track tipo.id) {
                    <li>{{ tipo.titulo }}</li>
                  }
                </ul>
              </section>
            }
            @if (impacto.colecciones.length > 0) {
              <p>Desaparecerá de estas colecciones: {{ nombres(impacto.colecciones) }}.</p>
            }
            @for (seccion of impacto.destacados; track seccion) {
              <p>Sale de «{{ etiquetaDestacado[seccion] }}» (se completa con otro contenido).</p>
            }
            @if (impacto.enlacesEntrantes > 0) {
              <p>{{ impacto.enlacesEntrantes === 1 ? '1 página lo enlaza.' : impacto.enlacesEntrantes + ' páginas lo enlazan.' }}</p>
            }
            @if (sinImpacto()) {
              <p data-testid="retiro-sin-impacto">No afecta a otros contenidos.</p>
            }
            <p class="ayuda">Su página pública mostrará «contenido no disponible» (410).</p>
          </div>

          @if (bloqueado()) {
            <div class="acciones">
              <button type="button" appBoton variante="secondary" data-testid="retiro-entendido" (click)="cerrar()">Entendido</button>
            </div>
          } @else {
            <div class="campo">
              <label for="retiro-motivo">Motivo del retiro (solo lo verá el equipo) <span class="obligatorio">(obligatorio)</span></label>
              <textarea
                #motivoCampo
                id="retiro-motivo"
                name="motivo"
                class="entrada-texto"
                rows="3"
                [attr.maxlength]="maximo"
                aria-required="true"
                data-testid="retiro-motivo"
                [value]="motivo()"
                (input)="motivo.set($any($event.target).value)"
              ></textarea>
            </div>
            @if (!enLinea()) {
              <p class="ayuda">Sin conexión: no se puede retirar ahora.</p>
            }
            <div class="acciones">
              <button
                type="button"
                appBoton
                variante="danger"
                data-testid="retiro-confirmar"
                [cargando]="store.fase() === 'confirmando'"
                [disabled]="!puedeRetirar()"
                (click)="intentar()"
              >
                {{ store.fase() === 'confirmando' ? 'Retirando…' : 'Retirar' }}
              </button>
              <button type="button" appBoton variante="secondary" data-testid="retiro-cancelar" [disabled]="store.fase() === 'confirmando'" (click)="cerrar()">
                Cancelar
              </button>
            </div>
          }
        } @else {
          @if (store.error(); as error) {
            <app-banner variante="error" testId="retiro-error">{{ error.mensaje }}</app-banner>
          }
          <div class="acciones">
            <button type="button" appBoton variante="secondary" (click)="cerrar()">Volver al editor</button>
          </div>
        }
      </div>
    </dialog>
  `,
  styleUrls: ['./panel-formularios.css', './dialogos-ciclo.css'],
})
export class DialogoRetiro {
  readonly abierto = input(false);
  readonly abiertoChange = output<boolean>();
  readonly titulo = input.required<string>();
  /** Confirmar con el motivo escrito (el editor ejecuta el retiro con el store). */
  readonly retirar = output<string>();

  protected readonly store = inject(PublicacionStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private readonly campoMotivo = viewChild<ElementRef<HTMLTextAreaElement>>('motivoCampo');
  private readonly encabezado = viewChild.required<ElementRef<HTMLHeadingElement>>('encabezado');
  private origen: HTMLElement | null = null;
  protected readonly maximo = LONGITUD_MAXIMA_MOTIVO;
  protected readonly etiquetaDestacado = ETIQUETA_DESTACADO;
  protected readonly etiquetaTipo = ETIQUETA_TIPO_SINGULAR;
  protected readonly motivo = signal('');

  protected readonly bloqueado = computed(() => {
    const impacto = this.store.impacto();
    return impacto !== null && !impacto.retirable;
  });
  protected readonly puedeRetirar = computed(
    () => this.store.retirable() && motivoValido(this.motivo()) && this.enLinea(),
  );
  protected readonly sinImpacto = computed(() => {
    const i = this.store.impacto();
    return (
      i !== null &&
      i.itinerariosEnCascada.length === 0 &&
      i.tiposEnCascada.length === 0 &&
      i.colecciones.length === 0 &&
      i.destacados.length === 0 &&
      i.enlacesEntrantes === 0 &&
      i.bloqueos.length === 0 &&
      i.bloqueosCascada.length === 0
    );
  });

  constructor() {
    effect(() => {
      const abierto = this.abierto();
      const dialogo = this.dialogo().nativeElement;
      if (abierto && !dialogo.open) {
        this.origen = this.documento.activeElement as HTMLElement | null;
        this.motivo.set('');
        dialogo.showModal();
        this.encabezado().nativeElement.focus();
      } else if (!abierto && dialogo.open) {
        dialogo.close();
        this.origen?.focus();
        this.origen = null;
      }
    });
    // Con el impacto calculado, el foco va al motivo (o al título si está bloqueado).
    effect(() => {
      if (this.store.fase() === 'lista' && this.abierto() && this.store.impacto() !== null) {
        afterNextRender(
          () => (this.campoMotivo()?.nativeElement ?? this.encabezado().nativeElement).focus(),
          { injector: this.injector },
        );
      }
    });
  }

  protected nombres(refs: readonly RefContenido[]): string {
    return refs.map((r) => r.titulo).join(', ');
  }

  protected enlaceEditor(ref: Pick<RefContenido, 'tipo' | 'id'>): string {
    return rutaEditor(ref.tipo, ref.id);
  }

  protected intentar(): void {
    if (!this.puedeRetirar()) return;
    this.retirar.emit(this.motivo());
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
