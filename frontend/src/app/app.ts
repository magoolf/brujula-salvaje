import { DOCUMENT } from '@angular/common';
import { Component, afterNextRender, computed, inject } from '@angular/core';

import { BannerSinConexion } from './core/layout/banner-sin-conexion/banner-sin-conexion';
import { FocoRuta } from './core/layout/foco-ruta';
import { ShellPublico } from './core/layout/shell-publico/shell-publico';
import { ZonaActiva } from './core/layout/shell-publico/zona-activa';
import { ZonaOutlet } from './core/layout/shell-publico/zona-outlet';

/**
 * Raíz de la aplicación. El armazón depende de la zona (TKT-010):
 * - sitio público → ShellPublico (SkipLink, cabecera, main con el router-outlet, pie);
 * - panel editorial (/panel/**) → router-outlet sin chrome público: el panel trae su armazón
 *   (TPL-PANEL-AUTH / TPL-PANEL-SHELL).
 * Las rutas son planas (app.routes.ts): no hay ruta de layout, para que la extracción de rutas del
 * SSR conserve los modulepreload de cada ruta y el título sea el mismo en SSR y en cliente.
 * La zona la lleva ZonaActiva: en el primer render sale de la URL (también en SSR e hidratación) y
 * después solo cambia cuando el router activa una ruta de la otra zona (ZonaOutlet), nunca al
 * empezar la navegación (QA TKT-010 ciclo 2, HALLAZGO-ZONA).
 * Común a ambas zonas: el aviso sin conexión (GI-04), el foco al navegar y la señal de hidratación.
 */
@Component({
  selector: 'app-root',
  imports: [ZonaOutlet, BannerSinConexion, ShellPublico],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly zonaActiva = inject(ZonaActiva);

  protected readonly enPanel = computed(() => this.zonaActiva.zona() === 'panel');

  constructor() {
    inject(FocoRuta).iniciar();
    // Señal de «aplicación hidratada e interactiva» (solo navegador) para las pruebas E2E.
    const documento = inject(DOCUMENT);
    afterNextRender(() => documento.documentElement.setAttribute('data-app-lista', 'true'));
  }
}
