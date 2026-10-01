import { DOCUMENT, Location } from '@angular/common';
import { Component, afterNextRender, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  NavigationCancel,
  NavigationEnd,
  NavigationError,
  NavigationStart,
  Router,
  RouterOutlet,
} from '@angular/router';
import { filter, map } from 'rxjs';

import { BannerSinConexion } from './core/layout/banner-sin-conexion/banner-sin-conexion';
import { FocoRuta } from './core/layout/foco-ruta';
import { ShellPublico } from './core/layout/shell-publico/shell-publico';
import { esZonaPanel } from './core/layout/shell-publico/zona';

/**
 * Raíz de la aplicación. El armazón depende de la zona (TKT-010):
 * - sitio público → ShellPublico (SkipLink, cabecera, main con el router-outlet, pie);
 * - panel editorial (/panel/**) → router-outlet sin chrome público: el panel trae su armazón
 *   (TPL-PANEL-AUTH / TPL-PANEL-SHELL).
 * Las rutas son planas (app.routes.ts): no hay ruta de layout, para que la extracción de rutas del
 * SSR conserve los modulepreload de cada ruta y el título sea el mismo en SSR y en cliente.
 * La zona inicial sale de la URL de la petición (Location, también en SSR e hidratación) y se
 * actualiza al empezar y terminar cada navegación (el panel no se enlaza desde el sitio público, así
 * que cruzar de zona dentro de la SPA es excepcional).
 * Común a ambas zonas: el aviso sin conexión (GI-04), el foco al navegar y la señal de hidratación.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, BannerSinConexion, ShellPublico],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly router = inject(Router);

  protected readonly enPanel = toSignal(
    this.router.events.pipe(
      filter(
        (e) =>
          e instanceof NavigationStart ||
          e instanceof NavigationEnd ||
          e instanceof NavigationCancel ||
          e instanceof NavigationError,
      ),
      map((e) => esZonaPanel(e instanceof NavigationStart ? e.url : this.router.url)),
    ),
    { initialValue: esZonaPanel(inject(Location).path()) },
  );

  constructor() {
    inject(FocoRuta).iniciar();
    // Señal de «aplicación hidratada e interactiva» (solo navegador) para las pruebas E2E.
    const documento = inject(DOCUMENT);
    afterNextRender(() => documento.documentElement.setAttribute('data-app-lista', 'true'));
  }
}
