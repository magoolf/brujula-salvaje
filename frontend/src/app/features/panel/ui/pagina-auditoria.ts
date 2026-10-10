import { Component, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import {
  ACCIONES_AUDITORIA,
  ETIQUETA_ACCION,
  ETIQUETA_RESULTADO,
  ETIQUETA_TIPO_ENTIDAD,
  EventoAuditoria,
  FILTROS_AUDITORIA_VACIOS,
  TIPOS_ENTIDAD,
  filtrosAuditoriaDesdeQuery,
  formatearFechaBogota,
  queryDesdeFiltrosAuditoria,
  rutaEntidad,
  textoEntidad,
  textoRecuentoAuditoria,
  tieneDetalle,
  varianteResultado,
} from '../domain/auditoria';
import { RUTA_TABLERO } from '../domain/secciones';
import { AuditoriaStore } from '../state/auditoria.store';
import { AccesoDenegado } from './acceso-denegado';
import { EnlaceValor } from './enlace-valor';

/**
 * SCR-046 Registro de auditoría (FEAT-046, FLOW-016, AC-030, THREAT-013, TPL-PANEL-SHELL; solo
 * Administrador): nota de solo lectura y conservación, filtros (Desde, Hasta, Actor, Acción, Tipo)
 * + Limpiar sincronizados con la URL, y DataTable por fecha descendente (Fecha y hora · Actor ·
 * Acción · Entidad enlazada si existe · Resultado · «Ver cambios» desplegable) con paginación.
 * Ninguna acción de edición ni de borrado. < md: filtros en un desplegable y tarjetas.
 */
@Component({
  selector: 'app-pagina-auditoria',
  imports: [RouterLink, Boton, EstadoCargando, EstadoError, EstadoVacio, Insignia, Paginacion, AccesoDenegado, EnlaceValor],
  providers: [AuditoriaStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina" data-testid="pagina-auditoria">
        <h1 tabindex="-1">Registro de auditoría</h1>
        <p class="nota" data-testid="auditoria-nota">Registro de solo lectura. Se conserva 365 días.</p>

        <details class="filtros-plegables" [open]="filtrosAbiertos()" (toggle)="alPlegar($event)">
          <summary>Filtros</summary>
          <form class="formulario filtros" role="search" aria-label="Filtrar el registro de auditoría" novalidate (submit)="aplicar($event)">
            <div class="filtros-campos">
              <div class="campo">
                <label for="auditoria-desde">Desde</label>
                <input id="auditoria-desde" name="desde" type="date" class="entrada-texto" [appEnlaceValor]="desde" [attr.aria-invalid]="store.errorFechas() ? 'true' : null" [attr.aria-describedby]="store.errorFechas() ? 'auditoria-fechas-error' : null" data-testid="auditoria-desde" />
              </div>
              <div class="campo">
                <label for="auditoria-hasta">Hasta</label>
                <input id="auditoria-hasta" name="hasta" type="date" class="entrada-texto" [appEnlaceValor]="hasta" [attr.aria-invalid]="store.errorFechas() ? 'true' : null" [attr.aria-describedby]="store.errorFechas() ? 'auditoria-fechas-error' : null" data-testid="auditoria-hasta" />
              </div>
              <div class="campo">
                <label for="auditoria-actor">Actor</label>
                <select id="auditoria-actor" name="actor" class="entrada-texto" [appEnlaceValor]="actor" data-testid="auditoria-actor">
                  <option value="" [selected]="actor() === ''">Todos</option>
                  @for (a of store.actores(); track a.id) {
                    <option [value]="'' + a.id" [selected]="actor() === '' + a.id">{{ a.etiqueta }}</option>
                  }
                </select>
              </div>
              <div class="campo">
                <label for="auditoria-accion">Acción</label>
                <select id="auditoria-accion" name="accion" class="entrada-texto" [appEnlaceValor]="accion" data-testid="auditoria-accion">
                  <option value="" [selected]="accion() === ''">Todas</option>
                  @for (a of acciones; track a) {
                    <option [value]="a" [selected]="accion() === a">{{ etiquetaAccion[a] }}</option>
                  }
                </select>
              </div>
              <div class="campo">
                <label for="auditoria-tipo">Tipo</label>
                <select id="auditoria-tipo" name="tipo" class="entrada-texto" [appEnlaceValor]="tipo" data-testid="auditoria-tipo">
                  <option value="" [selected]="tipo() === ''">Todos</option>
                  @for (t of tipos; track t) {
                    <option [value]="t" [selected]="tipo() === t">{{ etiquetaTipo[t] }}</option>
                  }
                </select>
              </div>
            </div>
            @if (store.errorFechas(); as mensaje) {
              <p class="error-campo" id="auditoria-fechas-error" data-testid="auditoria-fechas-error">{{ mensaje }}</p>
            }
            <div class="acciones">
              <button type="submit" appBoton variante="secondary" data-testid="auditoria-aplicar">Aplicar filtros</button>
              @if (store.conFiltros()) {
                <a [routerLink]="[]" data-testid="auditoria-limpiar">Limpiar</a>
              }
            </div>
          </form>
        </details>

        @if (store.errorFechas()) {
          <!-- Sin consulta: el error del rango se muestra en los filtros. -->
        } @else if (store.paginaFueraDeRango()) {
          <app-estado-vacio titulo="Esa página no existe" testId="auditoria-pagina-fuera" idTitulo="auditoria-pagina-fuera-titulo">
            <p>El registro tiene menos páginas con estos filtros.</p>
            <div estado-salidas>
              <a [routerLink]="[]" [queryParams]="{ pagina: null }" queryParamsHandling="merge">Ir a la primera página</a>
            </div>
          </app-estado-vacio>
        } @else if (store.error(); as error) {
          <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="auditoria-error" (reintentar)="store.recargar()" />
        } @else if (store.pagina(); as pagina) {
          @if (pagina.total === 0) {
            <app-estado-vacio titulo="No hay eventos con estos filtros" testId="auditoria-vacio" idTitulo="auditoria-vacio-titulo">
              <p>Prueba con otro rango de fechas u otros filtros.</p>
              <div estado-salidas>
                <a [routerLink]="[]" data-testid="auditoria-vacio-limpiar">Limpiar</a>
              </div>
            </app-estado-vacio>
          } @else {
            <p class="recuento" role="status" data-testid="auditoria-recuento">{{ recuento(pagina.total) }}</p>
            <div class="tabla-contenedor" tabindex="0" role="region" aria-label="Eventos de auditoría">
              <table class="tabla" data-testid="auditoria-tabla" [attr.aria-busy]="store.cargando()">
                <caption class="bs-solo-lectores">Eventos de auditoría, del más reciente al más antiguo</caption>
                <thead>
                  <tr>
                    <th scope="col">Fecha y hora</th>
                    <th scope="col">Actor</th>
                    <th scope="col">Acción</th>
                    <th scope="col" class="col-secundaria">Entidad</th>
                    <th scope="col" class="col-secundaria">Resultado</th>
                    <th scope="col" class="col-secundaria">Cambios</th>
                  </tr>
                </thead>
                <tbody>
                  @for (e of pagina.eventos; track e.id) {
                    <tr data-testid="auditoria-fila">
                      <th scope="row" data-etiqueta="Fecha y hora"><time [attr.datetime]="e.ocurridoEn.toISOString()">{{ fecha(e.ocurridoEn) }}</time></th>
                      <td data-etiqueta="Actor">{{ e.actor }}</td>
                      <td data-etiqueta="Acción">{{ etiquetaAccion[e.accion] }}</td>
                      <td data-etiqueta="Entidad" class="col-secundaria">
                        @if (enlace(e); as destino) {
                          <a [routerLink]="destino.ruta" [queryParams]="destino.query" data-testid="auditoria-entidad">{{ entidad(e) }}</a>
                        } @else {
                          {{ entidad(e) }}
                        }
                      </td>
                      <td data-etiqueta="Resultado" class="col-secundaria">
                        <app-insignia [variante]="varianteResultado(e.resultado)">{{ etiquetaResultado[e.resultado] }}</app-insignia>
                      </td>
                      <td data-etiqueta="Cambios" class="col-secundaria">
                        @if (conDetalle(e)) {
                          <button
                            type="button"
                            class="boton-enlace"
                            [attr.aria-expanded]="desplegado() === e.id"
                            [attr.aria-controls]="'auditoria-cambios-' + e.id"
                            [attr.data-testid]="'auditoria-ver-cambios-' + e.id"
                            (click)="alternar(e.id)"
                          >
                            Ver cambios
                          </button>
                          <div class="cambios" [id]="'auditoria-cambios-' + e.id" [hidden]="desplegado() !== e.id">
                            @if (e.camposCambiados.length > 0) {
                              <p>Campos: {{ e.camposCambiados.join(', ') }}</p>
                            }
                            @if (e.ipTruncada; as ip) {
                              <p>Origen (IP truncada): <span class="mono">{{ ip }}</span></p>
                            }
                          </div>
                        } @else {
                          —
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
          <app-estado-cargando forma="fila" [cantidad]="8" etiqueta="Cargando el registro…" testId="auditoria-cargando" />
        }
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
  styles: `
    .filtros-campos {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
      gap: var(--bs-space-3);
    }
    .filtros-plegables summary {
      min-height: var(--bs-size-target);
      display: flex;
      align-items: center;
      font-weight: var(--bs-font-weight-semibold);
      cursor: pointer;
    }
    /* ≥ md los filtros siempre visibles: el resumen del desplegable se oculta. */
    @media (min-width: 48rem) {
      .filtros-plegables summary {
        display: none;
      }
    }
    .cambios[hidden] {
      display: none;
    }
    .cambios {
      margin-top: var(--bs-space-2);
      font-size: var(--bs-typography-body-sm-font-size);
      overflow-wrap: anywhere;
    }
    .cambios p {
      margin: 0;
    }
  `,
})
export class PaginaAuditoria {
  protected readonly store = inject(AuditoriaStore);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);

  protected readonly acciones = ACCIONES_AUDITORIA;
  protected readonly tipos = TIPOS_ENTIDAD;
  protected readonly etiquetaAccion = ETIQUETA_ACCION;
  protected readonly etiquetaTipo = ETIQUETA_TIPO_ENTIDAD;
  protected readonly etiquetaResultado = ETIQUETA_RESULTADO;
  protected readonly rutaTablero = RUTA_TABLERO;
  protected readonly fecha = formatearFechaBogota;
  protected readonly entidad = textoEntidad;
  protected readonly enlace = rutaEntidad;
  protected readonly recuento = textoRecuentoAuditoria;
  protected readonly varianteResultado = varianteResultado;
  protected readonly conDetalle = tieneDetalle;

  protected readonly desde = signal('');
  protected readonly hasta = signal('');
  protected readonly actor = signal('');
  protected readonly accion = signal('');
  protected readonly tipo = signal('');
  protected readonly desplegado = signal<number | null>(null);
  /** ≥ md el <details> está siempre abierto (su resumen se oculta); < md empieza plegado. */
  protected readonly filtrosAbiertos = signal(true);

  constructor() {
    inject(Seo).establecer({ titulo: 'Registro de auditoría', indexable: false });
    // Los campos de filtro siguen a la URL (fuente de verdad).
    effect(() => {
      const f = this.store.filtros();
      this.desde.set(f.desde);
      this.hasta.set(f.hasta);
      this.actor.set(f.actor === null ? '' : String(f.actor));
      this.accion.set(f.accion ?? '');
      this.tipo.set(f.tipo ?? '');
    });
  }

  protected alPlegar(evento: Event): void {
    this.filtrosAbiertos.set((evento.target as HTMLDetailsElement).open);
  }

  protected alternar(id: EventoAuditoria['id']): void {
    this.desplegado.update((actual) => (actual === id ? null : id));
  }

  /** Aplica los filtros navegando (vuelve a la página 1). */
  protected async aplicar(evento: Event): Promise<void> {
    evento.preventDefault();
    const filtros = {
      ...FILTROS_AUDITORIA_VACIOS,
      ...filtrosAuditoriaDesdeQuery({
        desde: this.desde(),
        hasta: this.hasta(),
        actor: this.actor(),
        accion: this.accion(),
        tipo: this.tipo(),
      }),
      pagina: 1,
    };
    await this.router.navigate([], { relativeTo: this.ruta, queryParams: queryDesdeFiltrosAuditoria(filtros) });
  }
}
