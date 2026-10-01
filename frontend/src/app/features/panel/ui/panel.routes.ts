import { Routes } from '@angular/router';

import { AccesoDenegado } from './acceso-denegado';
import { LayoutAcceso } from './layout-acceso';
import { PaginaAcceso } from './pagina-acceso';
import { PaginaAutorizacion } from './pagina-autorizacion';
import { PaginaCuenta } from './pagina-cuenta';
import { PaginaNoEncontradaPanel } from './pagina-no-encontrada-panel';
import { PaginaTablero } from './pagina-tablero';
import { PaginaVerificacionMfa } from './pagina-verificacion-mfa';
import {
  accesoGuard,
  conSegmentosMatch,
  cuentaObligatoriaMatch,
  pasoGuard,
  rolGuard,
  sesionCompletaGuard,
} from './panel-guard';
import { ShellPanel } from './shell-panel';

/**
 * Rutas del panel editorial bajo /panel (BLUEPRINT §10; DEC-ESTRUCTURA-02). app.routes.ts solo las
 * carga en diferido: cada ticket del panel añade aquí sus rutas y su entrada en
 * domain/secciones.ts, sin tocar el armazón.
 *
 * Dos armazones hermanos con path '' (el router prueba el segundo si ningún hijo del primero
 * coincide):
 *  1. LayoutAcceso (TPL-PANEL-AUTH): acceso, MFA, autorización y Mi cuenta en modo obligatorio.
 *  2. ShellPanel (TPL-PANEL-SHELL): exige sesión completa; cada ruta hija declara su rol mínimo
 *     con `data: { rolMinimo: 'ADMINISTRADOR' }` cuando es solo de Administrador (SCR-048 si no).
 */
export const RUTAS_PANEL: Routes = [
  {
    path: '',
    component: LayoutAcceso,
    canMatch: [conSegmentosMatch],
    children: [
      {
        path: 'acceso',
        title: 'Acceso al panel editorial',
        canActivate: [accesoGuard],
        component: PaginaAcceso,
      },
      {
        path: 'acceso/verificacion',
        title: 'Verificación en dos pasos',
        canActivate: [pasoGuard('MFA')],
        component: PaginaVerificacionMfa,
      },
      {
        path: 'autorizacion',
        title: 'Autorización de tratamiento de datos',
        canActivate: [pasoGuard('AUTORIZACION')],
        component: PaginaAutorizacion,
      },
      {
        path: 'cuenta',
        title: 'Mi cuenta',
        canMatch: [cuentaObligatoriaMatch],
        component: PaginaCuenta,
      },
    ],
  },
  {
    path: '',
    component: ShellPanel,
    canActivate: [sesionCompletaGuard],
    canActivateChild: [rolGuard],
    children: [
      { path: '', pathMatch: 'full', title: 'Tablero', component: PaginaTablero },
      { path: 'cuenta', title: 'Mi cuenta', component: PaginaCuenta },
      { path: 'acceso-denegado', title: 'Acceso denegado', component: AccesoDenegado },
      // TKT-022 (medios), TKT-023 (contenidos) y TKT-024 (inicio, taxonomías, configuración,
      // cuentas, auditoría) añaden sus rutas aquí, antes del comodín.
      { path: '**', title: 'Página no encontrada', component: PaginaNoEncontradaPanel },
    ],
  },
];
