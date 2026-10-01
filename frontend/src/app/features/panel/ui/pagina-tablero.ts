import { DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  ETIQUETA_ESTADO,
  ETIQUETA_TIPO,
  ETIQUETA_TIPO_SINGULAR,
  totalConteo,
  varianteEstado,
} from '../domain/tablero';
import { TableroStore } from '../state/tablero.store';
import { AccesoDenegado } from './acceso-denegado';

/**
 * SCR-034 Tablero (FEAT-033/049, AC_TKT010_09): alertas (la del Responsable solo llega al
 * Administrador), accesos rápidos según el rol, conteos por tipo y estado, últimos cambios y salud
 * editorial*. Estados cargando / vacío / error / 403 (SCR-048).
 */
@Component({
  selector: 'app-pagina-tablero',
  imports: [
    DatePipe,
    RouterLink,
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    EstadoVacio,
    Insignia,
    AccesoDenegado,
  ],
  providers: [TableroStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina" data-testid="pagina-tablero">
        <header class="cabecera">
          <h1 tabindex="-1">Tablero</h1>
          @if (store.nombreVisible(); as nombre) {
            <p class="saludo">Hola, {{ nombre }}.</p>
          }
        </header>

        @if (store.error(); as error) {
          <app-estado-error
            [mensaje]="error.mensaje"
            [anunciar]="true"
            rutaSalida="/panel/cuenta"
            etiquetaSalida="Ir a Mi cuenta"
            testId="tablero-error"
            (reintentar)="store.recargar()"
          />
        } @else if (store.tablero(); as tablero) {
          @for (alerta of store.alertas(); track alerta.codigo) {
            <app-banner variante="warning" [testId]="'tablero-alerta-' + alerta.codigo">
              {{ alerta.mensaje }}
              @if (alerta.enlace; as enlace) {
                <a banner-accion [routerLink]="enlace">Revisar</a>
              }
            </app-banner>
          }

          @if (store.accesosRapidos().length > 0) {
            <section aria-labelledby="tablero-accesos" class="bloque">
              <h2 id="tablero-accesos">Accesos rápidos</h2>
              <ul class="accesos" data-testid="tablero-accesos">
                @for (acceso of store.accesosRapidos(); track acceso.id) {
                  <li>
                    <a appBoton variante="secondary" [routerLink]="acceso.ruta" [attr.data-testid]="'tablero-acceso-' + acceso.id">{{
                      acceso.etiqueta
                    }}</a>
                  </li>
                }
              </ul>
            </section>
          }

          @if (store.vacio()) {
            <app-estado-vacio titulo="Aún no hay contenido" testId="tablero-vacio" idTitulo="tablero-vacio-titulo">
              <p>Cuando el equipo cree el primer contenido, aquí verás su estado y los últimos cambios.</p>
              <div estado-salidas>
                <a routerLink="/panel/cuenta">Revisar Mi cuenta</a>
                <a href="/">Ver el sitio público</a>
              </div>
            </app-estado-vacio>
          } @else {
            <section aria-labelledby="tablero-conteos" class="bloque">
              <h2 id="tablero-conteos">Contenido por estado</h2>
              <div class="tabla-contenedor" tabindex="0" role="region" aria-labelledby="tablero-conteos">
                <table class="tabla" data-testid="tablero-conteos">
                  <thead>
                    <tr>
                      <th scope="col">Tipo</th>
                      <th scope="col">{{ etiquetaEstado.BORRADOR }}</th>
                      <th scope="col">{{ etiquetaEstado.PUBLICADO }}</th>
                      <th scope="col">{{ etiquetaEstado.RETIRADO }}</th>
                      <th scope="col">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (conteo of tablero.conteos; track conteo.tipo) {
                      <tr [attr.data-testid]="'tablero-conteo-' + conteo.tipo">
                        <th scope="row">{{ etiquetaTipo[conteo.tipo] }}</th>
                        <td>{{ conteo.borrador }}</td>
                        <td>{{ conteo.publicado }}</td>
                        <td>{{ conteo.retirado }}</td>
                        <td>{{ total(conteo) }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </section>

            <section aria-labelledby="tablero-recientes" class="bloque">
              <h2 id="tablero-recientes">Últimos cambios</h2>
              @if (tablero.recientes.length === 0) {
                <p class="ayuda">Todavía no hay cambios recientes.</p>
              } @else {
                <ul class="recientes" data-testid="tablero-recientes">
                  @for (contenido of tablero.recientes; track contenido.tipo + contenido.id) {
                    <li class="reciente">
                      <p class="titulo">{{ contenido.titulo }}</p>
                      <p class="meta">
                        <span>{{ etiquetaTipoSingular[contenido.tipo] }}</span>
                        <app-insignia [variante]="variante(contenido.estado)">{{ etiquetaEstado[contenido.estado] }}</app-insignia>
                        <span
                          >{{ contenido.actualizadoPor }} ·
                          <time [attr.datetime]="contenido.actualizadoEn.toISOString()">{{
                            contenido.actualizadoEn | date: 'medium'
                          }}</time></span
                        >
                      </p>
                      @if (contenido.urlPublica; as url) {
                        <a [href]="url" target="_blank" rel="noopener"
                          >Ver en el sitio <span class="bs-solo-lectores">{{ contenido.titulo }} (se abre en una pestaña nueva)</span></a
                        >
                      }
                    </li>
                  }
                </ul>
              }
            </section>
          }

          @if (store.mostrarSalud() && tablero.saludEditorial; as salud) {
            <section aria-labelledby="tablero-salud" class="bloque" data-testid="tablero-salud">
              <h2 id="tablero-salud">Salud editorial</h2>
              <ul class="salud">
                @if (salud.revisionesAntiguas.length > 0) {
                  <li>{{ salud.revisionesAntiguas.length }} contenidos con la fecha de revisión antigua.</li>
                }
                @if (salud.mediosPendientesMetadatos > 0) {
                  <li>{{ salud.mediosPendientesMetadatos }} medios pendientes de datos.</li>
                }
                @if (salud.mediosSinUso > 0) {
                  <li>{{ salud.mediosSinUso }} medios sin uso.</li>
                }
                @if (salud.coleccionesBajoMinimo.length > 0) {
                  <li>{{ salud.coleccionesBajoMinimo.length }} colecciones por debajo del mínimo de elementos.</li>
                }
                @if (salud.contenidosConPocosRelacionados.length > 0) {
                  <li>{{ salud.contenidosConPocosRelacionados.length }} contenidos con pocos relacionados.</li>
                }
              </ul>
            </section>
          }
        } @else {
          <app-estado-cargando forma="fila" [cantidad]="4" etiqueta="Cargando el tablero…" testId="tablero-cargando" />
        }
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .pagina {
      display: grid;
      gap: var(--bs-space-6);
    }
    .cabecera {
      display: grid;
      gap: var(--bs-space-1);
    }
    h1 {
      outline: none;
    }
    .saludo {
      color: var(--bs-color-text-muted);
    }
    .bloque {
      display: grid;
      gap: var(--bs-space-3);
    }
    .accesos {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--bs-space-3);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    @media (min-width: 48rem) {
      .accesos {
        display: flex;
        flex-wrap: wrap;
      }
    }
    .tabla-contenedor {
      overflow-x: auto;
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
    }
    .tabla {
      width: 100%;
      border-collapse: collapse;
      font-variant-numeric: tabular-nums;
    }
    .tabla th,
    .tabla td {
      padding: var(--bs-space-2) var(--bs-space-3);
      border-bottom: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      text-align: end;
    }
    .tabla th:first-child {
      text-align: start;
    }
    .recientes {
      display: grid;
      gap: var(--bs-space-2);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .reciente {
      display: grid;
      gap: var(--bs-space-1);
      padding: var(--bs-space-3) var(--bs-space-4);
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
    }
    .titulo {
      font-weight: var(--bs-font-weight-semibold);
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-2);
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-muted);
    }
    .salud {
      margin: 0;
      padding-inline-start: var(--bs-space-5);
    }
  `,
})
export class PaginaTablero {
  protected readonly store = inject(TableroStore);
  protected readonly etiquetaTipo = ETIQUETA_TIPO;
  protected readonly etiquetaTipoSingular = ETIQUETA_TIPO_SINGULAR;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO;
  protected readonly total = totalConteo;
  protected readonly variante = varianteEstado;

  constructor() {
    inject(Seo).establecer({ titulo: 'Tablero', indexable: false });
  }
}
