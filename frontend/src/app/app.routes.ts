import { Routes } from '@angular/router';

import { TITULO_NO_ENCONTRADA } from './core/layout/paginas/titulos';
import { DATOS_ZONA_PANEL } from './core/layout/shell-publico/zona';

/**
 * Rutas del sitio público (BLUEPRINT §10). TKT-008 añade Inicio, Destinos (listado, mapa, ficha),
 * Cuándo ir y Guardados; TKT-009 añade Itinerarios, Tipos de aventura, Guías, Colecciones,
 * Glosario, Búsqueda e Institucional (créditos incluidos). El comodín (404) queda siempre al
 * final. `/destinos/mapa` va antes de `/destinos/:slug` para no ser capturada como slug; mismo
 * criterio para `/guias/categoria/:slug` antes de `/guias/:slug`.
 */
const RUTAS_PUBLICAS: Routes = [
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
    path: 'itinerarios',
    title: 'Itinerarios',
    loadComponent: () =>
      import('./features/itinerarios/ui/pagina-itinerarios').then((m) => m.PaginaItinerarios),
  },
  {
    path: 'itinerarios/:slug',
    title: 'Itinerario',
    loadComponent: () =>
      import('./features/itinerarios/ui/pagina-itinerario').then((m) => m.PaginaItinerario),
  },
  {
    path: 'tipos-de-aventura',
    title: 'Tipos de aventura',
    loadComponent: () =>
      import('./features/tipos-aventura/ui/pagina-tipos-aventura').then(
        (m) => m.PaginaTiposAventura,
      ),
  },
  {
    path: 'tipos-de-aventura/:slug',
    title: 'Tipo de aventura',
    loadComponent: () =>
      import('./features/tipos-aventura/ui/pagina-tipo-aventura').then(
        (m) => m.PaginaTipoAventura,
      ),
  },
  {
    path: 'guias',
    title: 'Guías expertas',
    loadComponent: () => import('./features/guias/ui/pagina-guias').then((m) => m.PaginaGuias),
  },
  {
    path: 'guias/categoria/:slug',
    title: 'Categoría de guías',
    loadComponent: () =>
      import('./features/guias/ui/pagina-categoria-guias').then((m) => m.PaginaCategoriaGuias),
  },
  {
    path: 'guias/:slug',
    title: 'Guía',
    loadComponent: () => import('./features/guias/ui/pagina-guia').then((m) => m.PaginaGuia),
  },
  {
    path: 'colecciones',
    title: 'Colecciones',
    loadComponent: () =>
      import('./features/colecciones/ui/pagina-colecciones').then((m) => m.PaginaColecciones),
  },
  {
    path: 'colecciones/:slug',
    title: 'Colección',
    loadComponent: () =>
      import('./features/colecciones/ui/pagina-coleccion').then((m) => m.PaginaColeccion),
  },
  {
    path: 'glosario',
    title: 'Glosario',
    loadComponent: () =>
      import('./features/glosario/ui/pagina-glosario').then((m) => m.PaginaGlosario),
  },
  {
    path: 'buscar',
    title: 'Buscar',
    loadComponent: () =>
      import('./features/busqueda/ui/pagina-busqueda').then((m) => m.PaginaBusqueda),
  },
  {
    path: 'acerca-de',
    title: 'Acerca de',
    data: { slug: 'acerca-de' },
    loadComponent: () =>
      import('./features/institucional/ui/pagina-institucional').then(
        (m) => m.PaginaInstitucional,
      ),
  },
  {
    path: 'politica-de-tratamiento-de-datos',
    title: 'Política de tratamiento de datos',
    data: { slug: 'politica-de-tratamiento-de-datos' },
    loadComponent: () =>
      import('./features/institucional/ui/pagina-institucional').then(
        (m) => m.PaginaInstitucional,
      ),
  },
  {
    path: 'politica-de-cookies',
    title: 'Política de cookies',
    data: { slug: 'politica-de-cookies' },
    loadComponent: () =>
      import('./features/institucional/ui/pagina-institucional').then(
        (m) => m.PaginaInstitucional,
      ),
  },
  {
    path: 'aviso-legal',
    title: 'Aviso legal',
    data: { slug: 'aviso-legal' },
    loadComponent: () =>
      import('./features/institucional/ui/pagina-institucional').then(
        (m) => m.PaginaInstitucional,
      ),
  },
  {
    path: 'creditos',
    title: 'Créditos de imágenes',
    loadComponent: () =>
      import('./features/institucional/ui/pagina-creditos').then((m) => m.PaginaCreditos),
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

/**
 * Rutas de la aplicación (TKT-010). Configuración PLANA, igual que antes del panel salvo la entrada
 * `panel` (QA TKT-010 ciclo 1, FALLO-02 y OBS-04): una ruta padre con path '' (layout) hacía que la
 * extracción de rutas de @angular/ssr registrara '/' con los metadatos del padre —sin modulepreload
 * de Inicio— y que el título del SSR difiriera del cliente. El armazón visual de cada zona lo
 * decide App (ver app.ts):
 * - `/panel/**`: panel editorial, carga diferida; sus rutas hijas viven en
 *   features/panel/ui/panel.routes.ts. Solo cliente (app.routes.server.ts). `data` marca la zona
 *   del panel para ZonaOutlet (core/layout/shell-publico/zona.ts).
 * - resto: sitio público dentro de ShellPublico; el comodín 404 sigue siendo la última ruta.
 */
export const routes: Routes = [
  {
    path: 'panel',
    data: DATOS_ZONA_PANEL,
    loadChildren: () => import('./features/panel/ui/panel.routes').then((m) => m.RUTAS_PANEL),
  },
  ...RUTAS_PUBLICAS,
];
