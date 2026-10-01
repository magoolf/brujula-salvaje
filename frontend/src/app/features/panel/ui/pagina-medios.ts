import { DOCUMENT } from '@angular/common';
import {
  Component,
  Injector,
  afterNextRender,
  computed,
  inject,
  linkedSignal,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import {
  ETIQUETA_ESTADO_MEDIO,
  EstadoMedio,
  FILTROS_VACIOS,
  conFiltro,
  filtrosDesdeQuery,
  queryDesdeFiltros,
} from '../domain/medios';
import { RUTA_TABLERO } from '../domain/secciones';
import { BibliotecaMediosStore } from '../state/biblioteca-medios.store';
import { AccesoDenegado } from './acceso-denegado';
import { EnlaceValor } from './enlace-valor';
import { MosaicoMedio } from './mosaico-medio';
import { SubidaMedios } from './subida-medios';

const ESTADOS: readonly EstadoMedio[] = ['PENDIENTE_METADATOS', 'DISPONIBLE', 'RETIRADO'];
const MEDIA_FILTROS_ABIERTOS = '(min-width: 48rem)';

/**
 * SCR-039 Biblioteca de medios (FEAT-041/042, FLOW-013, TPL-PANEL-SHELL). h1 «Medios» + «Subir
 * imágenes» (despliega el MediaUploader), filtros (buscar, estado, licencia, en uso) sincronizados
 * con la URL, recuento, rejilla de MediaTile (enlace a SCR-040) y paginación de 48.
 * Estados: carga (esqueletos), vacío («Sube tu primera imagen»), sin coincidencias, error, página
 * fuera de rango y 403 (SCR-048). En móvil los filtros van en un <details> «Filtros».
 */
@Component({
  selector: 'app-pagina-medios',
  imports: [
    RouterLink,
    Boton,
    EstadoCargando,
    EstadoError,
    EstadoVacio,
    Paginacion,
    AccesoDenegado,
    EnlaceValor,
    MosaicoMedio,
    SubidaMedios,
  ],
  providers: [BibliotecaMediosStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina" data-testid="pagina-medios">
        <header class="cabecera-pagina">
          <h1 tabindex="-1">Medios</h1>
          <button
            type="button"
            appBoton
            [attr.aria-expanded]="subidaAbierta()"
            aria-controls="medios-subida"
            data-testid="medios-subir"
            (click)="alternarSubida()"
          >
            Subir imágenes
          </button>
        </header>

        <div id="medios-subida" [hidden]="!subidaAbierta()" class="subida">
          <app-subida-medios variante="biblioteca" idBase="medios-subida" (subidos)="store.recargar()" />
        </div>

        <details class="filtros" [open]="filtrosAbiertos()" (toggle)="alAlternarFiltros($event)" data-testid="medios-filtros">
          <summary>Filtros</summary>
          <form class="formulario" role="search" aria-label="Filtrar medios" novalidate (submit)="aplicar($event)">
            <div class="filtros-campos">
              <div class="campo">
                <label for="medios-q">Buscar por título, texto alternativo o crédito</label>
                <input id="medios-q" name="q" type="search" class="entrada-texto" maxlength="100" [appEnlaceValor]="q" data-testid="medios-q" />
              </div>
              <div class="campo">
                <label for="medios-estado">Estado</label>
                <select id="medios-estado" name="estado" class="entrada-texto" [appEnlaceValor]="estado" data-testid="medios-estado">
                  <option value="" [selected]="estado() === ''">Todos</option>
                  @for (e of estados; track e) {
                    <option [value]="e" [selected]="estado() === e">{{ etiquetaEstado[e] }}</option>
                  }
                </select>
              </div>
              <div class="campo">
                <label for="medios-licencia">Licencia</label>
                <select id="medios-licencia" name="licencia" class="entrada-texto" [appEnlaceValor]="licencia" data-testid="medios-licencia">
                  <option value="" [selected]="licencia() === ''">Todas</option>
                  @for (l of store.licencias(); track l.id) {
                    <option [value]="l.codigo" [selected]="licencia() === l.codigo">{{ l.nombre }}</option>
                  }
                </select>
              </div>
              <div class="campo">
                <label for="medios-en-uso">Uso</label>
                <select id="medios-en-uso" name="en_uso" class="entrada-texto" [appEnlaceValor]="enUso" data-testid="medios-en-uso">
                  <option value="" [selected]="enUso() === ''">Todas</option>
                  <option value="true" [selected]="enUso() === 'true'">En uso</option>
                  <option value="false" [selected]="enUso() === 'false'">Sin usar</option>
                </select>
              </div>
            </div>
            <div class="acciones">
              <button type="submit" appBoton variante="secondary" data-testid="medios-aplicar">Aplicar filtros</button>
              @if (store.conFiltros()) {
                <a [routerLink]="[]" data-testid="medios-limpiar">Quitar filtros</a>
              }
            </div>
          </form>
        </details>

        @if (store.paginaFueraDeRango()) {
          <app-estado-vacio titulo="Esa página no existe" testId="medios-pagina-fuera" idTitulo="medios-pagina-fuera-titulo">
            <p>La lista tiene menos páginas. Vuelve a la primera para ver las imágenes.</p>
            <div estado-salidas>
              <a [routerLink]="[]" [queryParams]="{ pagina: null }" queryParamsHandling="merge">Ir a la primera página</a>
              <a [routerLink]="rutaTablero">Ir al Tablero</a>
            </div>
          </app-estado-vacio>
        } @else if (store.error(); as error) {
          <app-estado-error
            [mensaje]="error.mensaje"
            [anunciar]="true"
            [rutaSalida]="rutaTablero"
            etiquetaSalida="Ir al Tablero"
            testId="medios-error"
            (reintentar)="store.recargar()"
          />
        } @else if (store.pagina(); as pagina) {
          @if (store.bibliotecaVacia()) {
            <app-estado-vacio titulo="Sube tu primera imagen" testId="medios-vacio" idTitulo="medios-vacio-titulo">
              <p>Las imágenes que subas aparecerán aquí para completar sus datos y usarlas en el contenido.</p>
              <div estado-salidas>
                <button type="button" class="boton-enlace" data-testid="medios-vacio-subir" (click)="abrirSubida()">Seleccionar imágenes</button>
                <a [routerLink]="rutaTablero">Ir al Tablero</a>
              </div>
            </app-estado-vacio>
          } @else if (store.sinCoincidencias()) {
            <app-estado-vacio titulo="No hay imágenes con esos filtros" testId="medios-sin-coincidencias" idTitulo="medios-sin-titulo">
              <p>Prueba con otra búsqueda o quita algún filtro.</p>
              <div estado-salidas>
                <a [routerLink]="[]" data-testid="medios-sin-limpiar">Quitar filtros</a>
                <a [routerLink]="rutaTablero">Ir al Tablero</a>
              </div>
            </app-estado-vacio>
          } @else {
            <p class="recuento" data-testid="medios-recuento">{{ recuento() }}</p>
            <ul class="rejilla" aria-label="Imágenes de la biblioteca" data-testid="medios-rejilla" [attr.aria-busy]="store.cargando()">
              @for (medio of pagina.medios; track medio.id) {
                <li><app-mosaico-medio [medio]="medio" /></li>
              }
            </ul>
            <app-paginacion [paginaActual]="pagina.pagina" [totalPaginas]="pagina.totalPaginas" />
          }
        } @else {
          <app-estado-cargando forma="tarjeta" [cantidad]="10" etiqueta="Cargando imágenes…" testId="medios-cargando" />
        }
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-medios.css'],
  styles: `
    .pagina {
      display: grid;
      gap: var(--bs-space-5);
    }
    .filtros summary {
      min-height: var(--bs-size-target);
      display: flex;
      align-items: center;
      font-weight: var(--bs-font-weight-semibold);
      cursor: pointer;
    }
    .filtros .formulario {
      padding-top: var(--bs-space-3);
    }
  `,
})
export class PaginaMedios {
  protected readonly store = inject(BibliotecaMediosStore);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  protected readonly estados = ESTADOS;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO_MEDIO;
  protected readonly rutaTablero = RUTA_TABLERO;
  protected readonly subidaAbierta = signal(false);
  protected readonly filtrosAbiertos = signal(true);

  // Valores del formulario de filtros: siguen a la URL y se aplican al enviar.
  protected readonly q = linkedSignal(() => this.store.filtros().q);
  protected readonly estado = linkedSignal<string>(() => this.store.filtros().estado ?? '');
  protected readonly licencia = linkedSignal<string>(() => this.store.filtros().licencia ?? '');
  protected readonly enUso = linkedSignal<string>(() => {
    const enUso = this.store.filtros().enUso;
    return enUso === null ? '' : String(enUso);
  });

  protected readonly recuento = computed(() => {
    const total = this.store.pagina()?.total ?? 0;
    return total === 1 ? '1 imagen' : `${total} imágenes`;
  });

  constructor() {
    inject(Seo).establecer({ titulo: 'Medios', indexable: false });
    // Filtros desplegados desde md; en móvil, plegados en «Filtros» (HANDOFF RESPONSIVE).
    afterNextRender(() => {
      const ventana = this.documento.defaultView;
      if (typeof ventana?.matchMedia === 'function') {
        this.filtrosAbiertos.set(ventana.matchMedia(MEDIA_FILTROS_ABIERTOS).matches);
      }
    });
  }

  protected alternarSubida(): void {
    this.subidaAbierta.update((abierta) => !abierta);
  }

  protected abrirSubida(): void {
    this.subidaAbierta.set(true);
    afterNextRender(
      () => this.documento.querySelector<HTMLElement>('[data-testid="subida-seleccionar"]')?.focus(),
      { injector: this.injector },
    );
  }

  protected alAlternarFiltros(evento: Event): void {
    this.filtrosAbiertos.set((evento.target as HTMLDetailsElement).open);
  }

  /** Aplica los filtros navegando: la URL es la fuente de verdad (y vuelve a la página 1). */
  protected async aplicar(evento: Event): Promise<void> {
    evento.preventDefault();
    const filtros = conFiltro(FILTROS_VACIOS, {
      ...filtrosDesdeQuery({
        q: this.q(),
        estado: this.estado(),
        licencia: this.licencia(),
        en_uso: this.enUso(),
      }),
      pagina: 1,
    });
    await this.router.navigate([], { relativeTo: this.ruta, queryParams: queryDesdeFiltros(filtros) });
  }
}
