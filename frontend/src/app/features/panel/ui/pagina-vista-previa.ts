import { Component, computed, effect, inject, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ID_CONTENIDO_PRINCIPAL } from '../../../core/layout/navegacion';
import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { SkipLink } from '../../../shared/ui/skip-link/skip-link';
import { textoCompletitud, textoRequisito } from '../domain/ciclo-editorial';
import { formatearFechaLarga } from '../domain/fechas';
import { MARCA_VISTA_PREVIA, tituloDocumentoVistaPrevia } from '../domain/vista-previa';
import { VistaPreviaStore } from '../state/vista-previa.store';
import { PaginaNoEncontradaPanel } from './pagina-no-encontrada-panel';

/**
 * SCR-037 Vista previa (FEAT-035, TPL-PANEL-FULL): franja fija «VISTA PREVIA – NO PUBLICADO»
 * (role=region «Vista previa») con «Volver al editor» y la plantilla pública del tipo con los datos
 * del formulario, sin persistir. noindex y título «Vista previa (no publicado) — {título}». Los
 * enlaces a otros contenidos llevan a sus versiones públicas. El texto enriquecido es HTML de lista
 * blanca saneado por el servidor (RULE-022) que Angular vuelve a sanear al enlazarlo con [innerHTML]
 * (como en las páginas públicas; sin bypassSecurityTrust).
 */
@Component({
  selector: 'app-pagina-vista-previa',
  imports: [RouterLink, EstadoCargando, ImagenResponsiva, SkipLink, PaginaNoEncontradaPanel],
  providers: [VistaPreviaStore],
  template: `
    <app-skip-link [destino]="idContenido" texto="Saltar al contenido" />
    <div class="franja" role="region" aria-label="Vista previa" data-testid="vista-previa-franja">
      <p>
        <strong data-testid="vista-previa-marca">{{ marca() }}</strong>
        @if (vista(); as v) {
          @if (!v.requisitos.cumple) {
            <span class="pendiente">· {{ completitud() }}</span>
          }
        }
      </p>
      <a class="volver" [routerLink]="store.rutaEditor()" data-testid="vista-previa-volver">Volver al editor</a>
    </div>
    <main [id]="idContenido" tabindex="-1" class="principal" data-testid="vista-previa">
      @if (store.noEncontrado()) {
        <app-pagina-no-encontrada-panel />
      } @else if (store.sinDatos()) {
        <div class="estado">
          <h1>No hay nada que previsualizar</h1>
          <p>Abre la vista previa desde el editor para ver los datos del formulario.</p>
          <a [routerLink]="store.rutaEditor()">Volver al editor</a>
        </div>
      } @else if (store.error(); as error) {
        <div class="estado" data-testid="vista-previa-error">
          <h1>No pudimos preparar la vista previa</h1>
          <p>{{ error.mensaje }}</p>
          <p><button type="button" class="boton-enlace" (click)="store.recargar()">Reintentar</button> · <a [routerLink]="store.rutaEditor()">Volver al editor</a></p>
        </div>
      } @else if (vista(); as v) {
        <article class="plantilla" [attr.data-tipo]="v.tipo">
          <header class="encabezado">
            @if (v.antetitulo; as ante) {
              <p class="antetitulo">{{ ante }}</p>
            }
            <h1 data-testid="vista-previa-titulo">{{ v.titulo }}</h1>
            @if (v.resumen; as resumen) {
              <p class="resumen">{{ resumen }}</p>
            }
            @if (revision(); as fecha) {
              <p class="meta">Revisado el {{ fecha }}</p>
            }
          </header>
          @if (v.portada; as portada) {
            <figure class="portada">
              <app-imagen-responsiva [src]="portada.src" [alt]="portada.alt" [ancho]="portada.ancho" [alto]="portada.alto" [derivados]="portada.derivados" sizes="(min-width: 64rem) 960px, 100vw" />
              @if (portada.credito; as credito) {
                <figcaption>{{ portada.pie ? portada.pie + ' · ' : '' }}Foto: {{ credito }}</figcaption>
              }
            </figure>
          }
          @if (v.datos.length > 0) {
            <section aria-labelledby="vp-datos">
              <h2 id="vp-datos">Datos clave</h2>
              <dl class="datos">
                @for (d of v.datos; track d.etiqueta) {
                  <div><dt>{{ d.etiqueta }}</dt><dd>{{ d.valor }}</dd></div>
                }
              </dl>
            </section>
          }
          @for (b of v.bloques; track b.titulo) {
            <section [attr.aria-label]="b.titulo">
              <h2>{{ b.titulo }}</h2>
              <div class="cuerpo-enriquecido" [innerHTML]="b.html"></div>
            </section>
          }
          @for (lista of v.listas; track lista.titulo) {
            <section [attr.aria-label]="lista.titulo">
              <h2>{{ lista.titulo }}</h2>
              @if (lista.ordenada) {
                <ol class="lista">
                  @for (e of lista.elementos; track $index) {
                    <li>
                      <p class="titulo-elemento">{{ e.titulo }}</p>
                      @if (e.html; as html) {
                        <div class="cuerpo-enriquecido" [innerHTML]="html"></div>
                      }
                      @if (e.detalle; as detalle) {
                        <p class="meta">{{ detalle }}</p>
                      }
                    </li>
                  }
                </ol>
              } @else {
                <ul class="lista">
                  @for (e of lista.elementos; track $index) {
                    <li>
                      {{ e.titulo }}
                      @if (e.destacado) { <strong>(esencial)</strong> }
                      @if (e.detalle; as detalle) { <span class="meta"> · {{ detalle }}</span> }
                    </li>
                  }
                </ul>
              }
            </section>
          }
          @if (v.galeria.length > 0) {
            <section aria-labelledby="vp-galeria">
              <h2 id="vp-galeria">Galería</h2>
              <ul class="galeria">
                @for (img of v.galeria; track img.src) {
                  <li><app-imagen-responsiva [src]="img.src" [alt]="img.alt" [ancho]="img.ancho" [alto]="img.alto" [derivados]="img.derivados" sizes="(min-width: 48rem) 33vw, 100vw" /></li>
                }
              </ul>
            </section>
          }
          @if (v.enlaces.length > 0) {
            <section aria-labelledby="vp-enlaces">
              <h2 id="vp-enlaces">Sigue explorando</h2>
              <ul>
                @for (e of v.enlaces; track e.ruta) {
                  <li><a [href]="e.ruta" data-testid="vista-previa-enlace">{{ e.titulo }}</a></li>
                }
              </ul>
            </section>
          }
          @if (v.fuentes.length > 0) {
            <section aria-labelledby="vp-fuentes">
              <h2 id="vp-fuentes">Fuentes</h2>
              <ul>
                @for (f of v.fuentes; track $index) {
                  <li>
                    @if (f.url; as url) {
                      <a [href]="url" rel="noopener noreferrer">{{ f.titulo }} <span class="bs-solo-lectores">(sitio externo)</span></a>
                    } @else {
                      {{ f.titulo }}
                    }
                    @if (f.entidad; as entidad) { <span class="meta"> · {{ entidad }}</span> }
                  </li>
                }
              </ul>
            </section>
          }
          @if (!v.requisitos.cumple && v.requisitos.pendientes.length > 0) {
            <section aria-labelledby="vp-pendientes" class="pendientes" data-testid="vista-previa-pendientes">
              <h2 id="vp-pendientes">Faltan datos para publicar</h2>
              <ul>
                @for (p of v.requisitos.pendientes; track $index) {
                  <li>{{ texto(p) }}</li>
                }
              </ul>
              <a [routerLink]="store.rutaEditor()">Completar en el editor</a>
            </section>
          }
        </article>
      } @else {
        <app-estado-cargando forma="linea" [cantidad]="8" etiqueta="Preparando la vista previa…" testId="vista-previa-cargando" />
      }
    </main>
  `,
  styles: `
    :host {
      display: block;
      min-height: 100dvh;
      background: var(--bs-color-bg-canvas);
    }
    .franja {
      position: sticky;
      top: 0;
      z-index: var(--bs-z-sticky);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--bs-space-2) var(--bs-space-4);
      padding: var(--bs-space-2) var(--bs-space-4);
      background: var(--bs-color-bg-inverse);
      color: var(--bs-color-text-inverse);
    }
    .franja a {
      color: var(--bs-color-text-inverse);
      font-weight: var(--bs-font-weight-semibold);
    }
    .volver {
      min-height: var(--bs-size-target);
      display: inline-flex;
      align-items: center;
    }
    .pendiente {
      margin-inline-start: var(--bs-space-2);
    }
    .principal {
      max-width: 60rem;
      margin: 0 auto;
      padding: var(--bs-space-6, 1.5rem) var(--bs-space-4) var(--bs-space-12);
    }
    .plantilla,
    .estado {
      display: grid;
      gap: var(--bs-space-6, 1.5rem);
    }
    .encabezado {
      display: grid;
      gap: var(--bs-space-2);
    }
    h1 {
      font-family: var(--bs-typography-h1-font-family);
      font-size: var(--bs-typography-h1-font-size);
      font-weight: var(--bs-typography-h1-font-weight);
      line-height: var(--bs-typography-h1-line-height);
    }
    h2 {
      font-family: var(--bs-typography-h2-font-family);
      font-size: var(--bs-typography-h2-font-size);
      font-weight: var(--bs-typography-h2-font-weight);
      line-height: var(--bs-typography-h2-line-height);
      margin-bottom: var(--bs-space-2);
    }
    .antetitulo,
    .meta {
      color: var(--bs-color-text-muted);
    }
    .resumen {
      font-size: var(--bs-typography-body-lg-font-size);
      line-height: var(--bs-typography-body-lg-line-height);
    }
    .portada {
      margin: 0;
    }
    .portada figcaption {
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-muted);
    }
    .datos {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
      gap: var(--bs-space-3);
      margin: 0;
    }
    .datos dt {
      font-weight: var(--bs-font-weight-semibold);
    }
    .datos dd {
      margin: 0;
    }
    .cuerpo-enriquecido {
      max-width: var(--bs-size-measure-prose);
      line-height: var(--bs-typography-body-lg-line-height);
    }
    .lista {
      display: grid;
      gap: var(--bs-space-3);
    }
    .titulo-elemento {
      font-weight: var(--bs-font-weight-semibold);
    }
    .galeria {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
      gap: var(--bs-space-3);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .pendientes {
      padding: var(--bs-space-4);
      border: var(--bs-border-width-strong) solid var(--bs-color-status-warning-fg);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-status-warning-bg);
    }
    .boton-enlace {
      padding: 0;
      border: 0;
      background: none;
      color: var(--bs-color-text-link);
      font: inherit;
      text-decoration: underline;
      cursor: pointer;
    }
  `,
})
export class PaginaVistaPrevia {
  protected readonly store = inject(VistaPreviaStore);
  private readonly seo = inject(Seo);
  protected readonly idContenido = ID_CONTENIDO_PRINCIPAL;
  protected readonly vista = this.store.vista;
  protected readonly marca = computed(() => this.vista()?.marca ?? MARCA_VISTA_PREVIA);
  protected readonly completitud = computed(() => {
    const vista = this.vista();
    return vista === null ? '' : textoCompletitud(vista.requisitos);
  });
  protected readonly revision = computed(() => {
    const fecha = this.vista()?.revision;
    return fecha ? formatearFechaLarga(new Date(`${fecha}T12:00:00`)) : null;
  });
  protected readonly texto = textoRequisito;

  constructor() {
    effect(() => {
      const titulo = this.vista()?.titulo ?? '';
      untracked(() => this.seo.establecer({ titulo: tituloDocumentoVistaPrevia(titulo), indexable: false }));
    });
  }
}
