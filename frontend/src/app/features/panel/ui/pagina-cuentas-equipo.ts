import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { CuentaEquipo, ETIQUETA_ESTADO_CUENTA, esAnonimizada, varianteEstadoCuenta } from '../domain/cuentas';
import { formatearFechaHora } from '../domain/fechas';
import { RUTA_TABLERO, RUTA_USUARIOS, ETIQUETA_ROL } from '../domain/secciones';
import { CuentasEquipoStore } from '../state/cuentas-equipo.store';
import { AccesoDenegado } from './acceso-denegado';

/**
 * SCR-044 Cuentas del equipo (FEAT-045, FLOW-015, AC-105, THREAT-025, TPL-PANEL-SHELL; solo
 * Administrador): h1 + «Nueva cuenta» y DataTable (Usuario · Nombre visible · Rol · Estado ·
 * Verificación en dos pasos · Último acceso). Las cuentas ANONIMIZADAS se muestran con su
 * seudónimo en cursiva y sin enlace. < md: tarjetas.
 */
@Component({
  selector: 'app-pagina-cuentas-equipo',
  imports: [RouterLink, Boton, EstadoCargando, EstadoError, EstadoVacio, Insignia, Paginacion, AccesoDenegado],
  providers: [CuentasEquipoStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina" data-testid="pagina-cuentas">
        <header class="cabecera-pagina">
          <h1 tabindex="-1">Cuentas del equipo</h1>
          <a appBoton [routerLink]="rutaNueva" data-testid="cuentas-nueva">Nueva cuenta</a>
        </header>

        @if (store.paginaFueraDeRango()) {
          <app-estado-vacio titulo="Esa página no existe" testId="cuentas-pagina-fuera" idTitulo="cuentas-pagina-fuera-titulo">
            <p>La lista tiene menos páginas.</p>
            <div estado-salidas>
              <a [routerLink]="[]">Ir a la primera página</a>
            </div>
          </app-estado-vacio>
        } @else if (store.error(); as error) {
          <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="cuentas-error" (reintentar)="store.recargar()" />
        } @else if (store.listado(); as listado) {
          <p class="recuento" role="status" data-testid="cuentas-recuento">{{ listado.total === 1 ? '1 cuenta' : listado.total + ' cuentas' }}</p>
          <div class="tabla-contenedor" tabindex="0" role="region" aria-label="Cuentas del equipo">
            <table class="tabla" data-testid="cuentas-tabla" [attr.aria-busy]="store.cargando()">
              <caption class="bs-solo-lectores">Cuentas del equipo con su rol, estado, verificación en dos pasos y último acceso</caption>
              <thead>
                <tr>
                  <th scope="col">Usuario</th>
                  <th scope="col">Nombre visible</th>
                  <th scope="col">Rol</th>
                  <th scope="col">Estado</th>
                  <th scope="col" class="col-secundaria">Verificación en dos pasos</th>
                  <th scope="col" class="col-secundaria">Último acceso</th>
                </tr>
              </thead>
              <tbody>
                @for (c of listado.cuentas; track c.id) {
                  <tr data-testid="cuentas-fila">
                    <th scope="row" data-etiqueta="Usuario">
                      @if (anonimizada(c)) {
                        <em data-testid="cuentas-seudonimo">{{ c.etiqueta }}</em>
                      } @else {
                        <a [routerLink]="rutaCuenta(c)" [attr.data-testid]="'cuentas-enlace-' + c.id">{{ c.etiqueta }}</a>
                        @if (c.usuario === store.usuarioSesion()) {
                          <span class="ayuda"> (tu cuenta)</span>
                        }
                      }
                    </th>
                    <td data-etiqueta="Nombre visible">{{ c.nombreVisible ?? '—' }}</td>
                    <td data-etiqueta="Rol">{{ etiquetaRol[c.rol] }}</td>
                    <td data-etiqueta="Estado"><app-insignia [variante]="variante(c.estado)">{{ etiquetaEstado[c.estado] }}</app-insignia></td>
                    <td data-etiqueta="Verificación en dos pasos" class="col-secundaria">{{ c.mfaActivo ? 'Sí' : 'No' }}</td>
                    <td data-etiqueta="Último acceso" class="col-secundaria">
                      @if (c.ultimoAccesoEn; as fecha) {
                        <time [attr.datetime]="fecha.toISOString()">{{ fechaHora(fecha) }}</time>
                      } @else {
                        Nunca
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <app-paginacion [paginaActual]="listado.pagina" [totalPaginas]="listado.totalPaginas" />
        } @else {
          <app-estado-cargando forma="fila" [cantidad]="6" etiqueta="Cargando las cuentas…" testId="cuentas-cargando" />
        }
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
})
export class PaginaCuentasEquipo {
  protected readonly store = inject(CuentasEquipoStore);
  protected readonly rutaNueva = `${RUTA_USUARIOS}/nuevo`;
  protected readonly rutaTablero = RUTA_TABLERO;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO_CUENTA;
  protected readonly etiquetaRol = ETIQUETA_ROL;
  protected readonly variante = varianteEstadoCuenta;
  protected readonly anonimizada = esAnonimizada;
  protected readonly fechaHora = formatearFechaHora;

  constructor() {
    inject(Seo).establecer({ titulo: 'Cuentas del equipo', indexable: false });
  }

  protected rutaCuenta(cuenta: CuentaEquipo): string {
    return `${RUTA_USUARIOS}/${cuenta.id}`;
  }
}
