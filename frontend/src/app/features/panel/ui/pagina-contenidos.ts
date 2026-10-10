import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import {
  ContenidoResumen,
  DEFINICION_TIPO,
  FILTROS_CONTENIDOS_VACIOS,
  LONGITUD_MAXIMA_Q,
  admiteFiltros,
  filtrosContenidosDesdeQuery,
  paginaSoloAdministrador,
  puedeCrear,
  puedeEditarPagina,
  queryDesdeFiltrosContenidos,
  rutaEditor,
  textoCaption,
  textoListadoVacio,
  textoNuevo,
  textoRecuento,
} from '../domain/contenidos';
import { formatearFechaHora, formatearFechaLarga } from '../domain/fechas';
import { EstadoEditorial } from '../domain/modelos';
import { RUTA_TABLERO } from '../domain/secciones';
import { ETIQUETA_ESTADO, varianteEstado } from '../domain/tablero';
import { ListadoContenidosStore } from '../state/listado-contenidos.store';
import { MemoriaEditor } from '../state/memoria-editor';
import { SesionPanelStore } from '../state/sesion-panel.store';
import { AccesoDenegado } from './acceso-denegado';
import { EnlaceValor } from './enlace-valor';
import { PaginaNoEncontradaPanel } from './pagina-no-encontrada-panel';

const ESTADOS: readonly EstadoEditorial[] = ['BORRADOR', 'PUBLICADO', 'RETIRADO'];

/**
 * SCR-035 Listado de contenidos (FEAT-033, AP-20, TPL-PANEL-SHELL): h1 con el tipo en plural +
 * «Nuevo {tipo}», filtros (texto y estado) sincronizados con la URL, recuento role=status, tabla
 * (Título · Estado · Revisión · Última modificación · Publicado · Acciones «Ver en el sitio») ordenada
 * por última modificación descendente y paginación de 50. En móvil la tabla se muestra como
 * tarjetas. Páginas institucionales: sin «Nuevo» ni filtros; las legales, solo Administrador.
 */
@Component({
  selector: 'app-pagina-contenidos',
  imports: [
    RouterLink,
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    EstadoVacio,
    Insignia,
    Paginacion,
    AccesoDenegado,
    EnlaceValor,
    PaginaNoEncontradaPanel,
  ],
  providers: [ListadoContenidosStore],
  template: `
    @if (store.tipo(); as tipo) {
      @if (store.accesoDenegado()) {
        <app-acceso-denegado />
      } @else {
        <div class="pagina" data-testid="pagina-contenidos" [attr.data-tipo]="tipo">
          <header class="cabecera-pagina">
            <h1 tabindex="-1">{{ def().plural }}</h1>
            @if (creable()) {
              <a appBoton [routerLink]="rutaNuevo()" data-testid="contenidos-nuevo">{{ textoNuevo() }}</a>
            }
          </header>

          @if (aviso(); as texto) {
            <app-banner variante="success" testId="contenidos-aviso" [permitirCerrar]="true" (cerrado)="aviso.set(null)">{{ texto }}</app-banner>
          }

          @if (conFiltros()) {
            <form class="formulario filtros" role="search" [attr.aria-label]="'Filtrar ' + def().plural.toLowerCase()" novalidate (submit)="aplicar($event)">
              <div class="filtros-campos">
                <div class="campo">
                  <label for="contenidos-q">Buscar por título</label>
                  <input id="contenidos-q" name="q" type="search" class="entrada-texto" [attr.maxlength]="maximoQ" [appEnlaceValor]="q" data-testid="contenidos-q" />
                </div>
                <div class="campo">
                  <label for="contenidos-estado">Estado</label>
                  <select id="contenidos-estado" name="estado" class="entrada-texto" [appEnlaceValor]="estado" data-testid="contenidos-estado">
                    <option value="" [selected]="estado() === ''">Todos</option>
                    @for (e of estados; track e) {
                      <option [value]="e" [selected]="estado() === e">{{ etiquetaEstado[e] }}</option>
                    }
                  </select>
                </div>
              </div>
              <div class="acciones">
                <button type="submit" appBoton variante="secondary" data-testid="contenidos-aplicar">Aplicar filtros</button>
                @if (store.conFiltros()) {
                  <a [routerLink]="[]" data-testid="contenidos-limpiar">Limpiar</a>
                }
              </div>
            </form>
          }

          @if (store.paginaFueraDeRango()) {
            <app-estado-vacio titulo="Esa página no existe" testId="contenidos-pagina-fuera" idTitulo="contenidos-pagina-fuera-titulo">
              <p>La lista tiene menos páginas.</p>
              <div estado-salidas>
                <a [routerLink]="[]" [queryParams]="{ pagina: null }" queryParamsHandling="merge">Ir a la primera página</a>
              </div>
            </app-estado-vacio>
          } @else if (store.error(); as error) {
            <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="contenidos-error" (reintentar)="store.recargar()" />
          } @else if (store.pagina(); as pagina) {
            @if (store.vacio()) {
              <app-estado-vacio [titulo]="textoVacio()" testId="contenidos-vacio" idTitulo="contenidos-vacio-titulo">
                <p>Cuando el equipo los cree, aparecerán aquí.</p>
                <div estado-salidas>
                  @if (creable()) {
                    <a [routerLink]="rutaNuevo()" data-testid="contenidos-vacio-nuevo">{{ textoNuevo() }}</a>
                  }
                  <a [routerLink]="rutaTablero">Ir al Tablero</a>
                </div>
              </app-estado-vacio>
            } @else if (store.sinCoincidencias()) {
              <app-estado-vacio titulo="Ningún resultado con estos filtros" testId="contenidos-sin-coincidencias" idTitulo="contenidos-sin-titulo">
                <p>Prueba con otra búsqueda o cambia el estado.</p>
                <div estado-salidas>
                  <a [routerLink]="[]" data-testid="contenidos-sin-limpiar">Limpiar</a>
                </div>
              </app-estado-vacio>
            } @else {
              <p class="recuento" role="status" data-testid="contenidos-recuento">{{ recuento() }}</p>
              <div class="tabla-contenedor" tabindex="0" role="region" [attr.aria-label]="caption()">
                <table class="tabla" data-testid="contenidos-tabla" [attr.aria-busy]="store.cargando()">
                  <caption class="bs-solo-lectores">{{ caption() }}</caption>
                  <thead>
                    <tr>
                      <th scope="col">Título</th>
                      <th scope="col">Estado</th>
                      <th scope="col" class="col-secundaria">Revisión</th>
                      <th scope="col">Última modificación</th>
                      <th scope="col" class="col-secundaria">Publicado</th>
                      <th scope="col" class="col-secundaria">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (c of pagina.contenidos; track c.id) {
                      <tr data-testid="contenidos-fila">
                        <th scope="row" data-etiqueta="Título">
                          @if (editable(c)) {
                            <a [routerLink]="enlaceEditar(c)" data-testid="contenidos-editar">{{ c.titulo }}</a>
                          } @else {
                            <span>{{ c.titulo }}</span>
                            <app-insignia variante="neutral" data-testid="contenidos-solo-admin">Solo administrador</app-insignia>
                          }
                        </th>
                        <td data-etiqueta="Estado"><app-insignia [variante]="variante(c.estado)">{{ etiquetaEstado[c.estado] }}</app-insignia></td>
                        <td data-etiqueta="Revisión" class="col-secundaria">{{ fechaRevision(c) }}</td>
                        <td data-etiqueta="Última modificación">
                          {{ c.actualizadoPor }} · <time [attr.datetime]="c.actualizadoEn.toISOString()">{{ fechaHora(c.actualizadoEn) }}</time>
                        </td>
                        <td data-etiqueta="Publicado" class="col-secundaria">{{ c.publicado ? 'Sí' : 'No' }}</td>
                        <td data-etiqueta="Acciones" class="col-secundaria">
                          @if (c.urlPublica; as url) {
                            <a [href]="url" target="_blank" rel="noopener" data-testid="contenidos-ver-sitio">
                              Ver en el sitio <span class="bs-solo-lectores">{{ c.titulo }} (se abre en una pestaña nueva)</span>
                            </a>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
              <app-paginacion [paginaActual]="pagina.pagina" [totalPaginas]="pagina.totalPaginas" />
            }
          } @else {
            <app-estado-cargando forma="fila" [cantidad]="8" etiqueta="Cargando contenidos…" testId="contenidos-cargando" />
          }
        </div>
      }
    } @else {
      <app-pagina-no-encontrada-panel />
    }
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .pagina {
      display: grid;
      gap: var(--bs-space-5);
    }
    .cabecera-pagina {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--bs-space-3);
    }
    .filtros-campos {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
      gap: var(--bs-space-3);
    }
    .tabla-contenedor {
      overflow-x: auto;
    }
    .tabla {
      width: 100%;
      border-collapse: collapse;
    }
    .tabla th,
    .tabla td {
      padding: var(--bs-space-2) var(--bs-space-3);
      border-bottom: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      text-align: start;
      vertical-align: top;
    }
    .tabla thead th {
      font-weight: var(--bs-font-weight-semibold);
      color: var(--bs-color-text-muted);
    }
    .tabla tbody th {
      font-weight: var(--bs-font-weight-semibold);
    }
    .tabla tbody th app-insignia {
      margin-inline-start: var(--bs-space-2);
    }
    /* < md: tarjetas por fila (DEC-AUTO-070) */
    @media (max-width: 47.99rem) {
      .tabla thead {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0 0 0 0);
      }
      .tabla,
      .tabla tbody,
      .tabla tr,
      .tabla th,
      .tabla td {
        display: block;
      }
      .tabla tr {
        margin-bottom: var(--bs-space-3);
        padding: var(--bs-space-3);
        border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
        border-radius: var(--bs-radius-md);
      }
      .tabla th,
      .tabla td {
        border: 0;
        padding: var(--bs-space-1) 0;
      }
      .tabla td::before {
        content: attr(data-etiqueta) ': ';
        font-weight: var(--bs-font-weight-semibold);
      }
    }
    /* md-lg: Título, Estado y Modificación */
    @media (min-width: 48rem) and (max-width: 63.99rem) {
      .col-secundaria {
        display: none;
      }
    }
  `,
})
export class PaginaContenidos {
  protected readonly store = inject(ListadoContenidosStore);
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly seo = inject(Seo);
  protected readonly estados = ESTADOS;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO;
  protected readonly variante = varianteEstado;
  protected readonly fechaHora = formatearFechaHora;
  protected readonly rutaTablero = RUTA_TABLERO;
  protected readonly maximoQ = LONGITUD_MAXIMA_Q;
  /** Aviso de la pantalla anterior (p. ej. «Se eliminó el borrador…»). */
  protected readonly aviso = signal<string | null>(inject(MemoriaEditor).tomarAviso());

  protected readonly q = signal('');
  protected readonly estado = signal('');

  protected readonly def = computed(() => DEFINICION_TIPO[this.store.tipo() ?? 'DESTINO']);
  protected readonly creable = computed(() => {
    const tipo = this.store.tipo();
    return tipo !== null && puedeCrear(tipo);
  });
  protected readonly conFiltros = computed(() => {
    const tipo = this.store.tipo();
    return tipo !== null && admiteFiltros(tipo);
  });
  protected readonly rutaNuevo = computed(() => rutaEditor(this.store.tipo() ?? 'DESTINO', null));
  protected readonly textoNuevo = computed(() => textoNuevo(this.store.tipo() ?? 'DESTINO'));
  protected readonly textoVacio = computed(() => textoListadoVacio(this.store.tipo() ?? 'DESTINO'));
  protected readonly caption = computed(() => textoCaption(this.store.tipo() ?? 'DESTINO'));
  protected readonly recuento = computed(() =>
    textoRecuento(this.store.pagina()?.total ?? 0, this.store.tipo() ?? 'DESTINO'),
  );

  constructor() {
    effect(() => {
      const plural = this.def().plural;
      untracked(() => this.seo.establecer({ titulo: plural, indexable: false }));
    });
    // Los campos de filtro siguen a la URL (sin linkedSignal, AC_TKT022_06).
    effect(() => {
      const filtros = this.store.filtros();
      this.q.set(filtros.q);
      this.estado.set(filtros.estado ?? '');
    });
  }

  protected editable(c: ContenidoResumen): boolean {
    return c.tipo !== 'PAGINA' || puedeEditarPagina(this.sesion.rol(), paginaSoloAdministrador(c.slug));
  }

  protected enlaceEditar(c: ContenidoResumen): string {
    return rutaEditor(c.tipo, c.id);
  }

  protected fechaRevision(c: ContenidoResumen): string {
    return c.fechaRevision ? formatearFechaLarga(new Date(`${c.fechaRevision}T12:00:00`)) : '—';
  }

  /** Aplica los filtros navegando: la URL es la fuente de verdad (y vuelve a la página 1). */
  protected async aplicar(evento: Event): Promise<void> {
    evento.preventDefault();
    const filtros = {
      ...FILTROS_CONTENIDOS_VACIOS,
      ...filtrosContenidosDesdeQuery({ q: this.q(), estado: this.estado() }),
      pagina: 1,
    };
    await this.router.navigate([], { relativeTo: this.ruta, queryParams: queryDesdeFiltrosContenidos(filtros) });
  }
}
