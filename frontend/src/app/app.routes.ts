import { Routes } from '@angular/router';

import { TITULO_NO_ENCONTRADA } from './core/layout/paginas/titulos';

/**
 * Rutas iniciales (TKT-002). Las features públicas (TKT-008..010) añaden sus rutas del sitemap
 * (BLUEPRINT §10) antes del comodín, que debe quedar siempre al final (SCR-023, HTTP 404).
 */
export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Inicio',
    loadComponent: () =>
      import('./core/layout/paginas/pagina-en-preparacion/pagina-en-preparacion').then((m) => m.PaginaEnPreparacion),
  },
  {
    path: '**',
    title: TITULO_NO_ENCONTRADA,
    loadComponent: () =>
      import('./core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada').then((m) => m.PaginaNoEncontrada),
  },
];
