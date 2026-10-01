import { Routes } from '@angular/router';

import { isDevMode } from '@angular/core';

import { AccesoDenegado } from './acceso-denegado';
import { CargaPanel } from './carga-panel';
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
  sesionSinResolverMatch,
} from './panel-guard';
import { ShellPanel } from './shell-panel';

/**
 * Rutas del panel editorial bajo /panel (BLUEPRINT §10; DEC-ESTRUCTURA-02). app.routes.ts solo las
 * carga en diferido: cada ticket del panel añade aquí sus rutas y su entrada en
 * domain/secciones.ts, sin tocar el armazón.
 *
 * Primero, la ruta de carga (QA TKT-010 OBS-C3-01): solo coincide mientras la sesión no se ha leído
 * nunca (carga completa de cualquier /panel/**) y muestra el armazón mínimo hasta repetir la
 * navegación con la sesión resuelta. Después, dos armazones hermanos con path '' (el router prueba
 * el segundo si ningún hijo del primero coincide):
 *  1. LayoutAcceso (TPL-PANEL-AUTH): acceso, MFA, autorización y Mi cuenta en modo obligatorio.
 *  2. ShellPanel (TPL-PANEL-SHELL): exige sesión completa; cada ruta hija declara su rol mínimo
 *     con `data: { rolMinimo: 'ADMINISTRADOR' }` cuando es solo de Administrador (SCR-048 si no).
 */
export const RUTAS_PANEL: Routes = [
  {
    path: '**',
    title: 'Cargando el panel',
    canMatch: [sesionSinResolverMatch],
    component: CargaPanel,
  },
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
      // MOD-011 (TKT-022): Editor y Administrador (sin rolMinimo). Carga diferida: el Tablero no
      // arrastra el código de medios.
      {
        path: 'medios',
        title: 'Medios',
        loadComponent: () => import('./pagina-medios').then((m) => m.PaginaMedios),
      },
      {
        path: 'medios/:id',
        title: 'Detalle de medio',
        loadComponent: () => import('./pagina-medio').then((m) => m.PaginaMedio),
      },
      // Banco de pruebas del Selector de medios (SCR-041) solo en desarrollo: su pantalla anfitriona
      // (SCR-036, TKT-023) aún no existe. En producción la ruta no se registra (DEC-DEV-022-01).
      ...(isDevMode()
        ? [
            {
              path: 'desarrollo/selector-medios',
              title: 'Banco de pruebas del selector de medios',
              loadComponent: () =>
                import('./banco-selector-medios').then((m) => m.BancoSelectorMedios),
            },
          ]
        : []),
      // TKT-023 (contenidos) y TKT-024 (inicio, taxonomías, configuración, cuentas, auditoría)
      // añaden sus rutas aquí, antes del comodín.
      { path: '**', title: 'Página no encontrada', component: PaginaNoEncontradaPanel },
    ],
  },
];
