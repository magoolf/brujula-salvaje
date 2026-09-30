import { Routes } from '@angular/router';

import { TITULO_NO_ENCONTRADA } from './core/layout/paginas/titulos';

/**
 * Rutas del sitio público (BLUEPRINT §10). TKT-008 añade Inicio, Destinos (listado, mapa, ficha),
 * Cuándo ir y Guardados; TKT-009/010 añaden el resto. El comodín (404) queda siempre al final.
 * `/destinos/mapa` va antes de `/destinos/:slug` para no ser capturada como slug.
 */
export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Inicio',
    loadComponent: () =>
      import('./features/inicio/ui/pagina-inicio').then((m) => m.PaginaInicio),
  },
  {
    path: 'destinos/mapa',
    title: 'Mapa de destinos',
    loadComponent: () =>
      import('./features/destinos/ui/pagina-mapa-destinos').then((m) => m.PaginaMapaDestinos),
  },
  {
    path: 'destinos',
    title: 'Explorar destinos',
    loadComponent: () =>
      import('./features/destinos/ui/pagina-destinos').then((m) => m.PaginaDestinos),
  },
  {
    path: 'destinos/:slug',
    title: 'Destino',
    loadComponent: () =>
      import('./features/destinos/ui/pagina-destino').then((m) => m.PaginaDestino),
  },
  {
    path: 'cuando-ir',
    title: '¿Dónde ir cada mes?',
    loadComponent: () =>
      import('./features/destinos/ui/pagina-cuando-ir').then((m) => m.PaginaCuandoIr),
  },
  {
    path: 'cuando-ir/:mes',
    title: 'Destinos del mes',
    loadComponent: () =>
      import('./features/destinos/ui/pagina-destinos-del-mes').then(
        (m) => m.PaginaDestinosDelMes,
      ),
  },
  {
    path: 'guardados',
    title: 'Mis aventuras guardadas',
    loadComponent: () =>
      import('./features/guardados/ui/pagina-guardados').then((m) => m.PaginaGuardados),
  },
  {
    path: '**',
    title: TITULO_NO_ENCONTRADA,
    loadComponent: () =>
      import('./core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada').then(
        (m) => m.PaginaNoEncontrada,
      ),
  },
];
