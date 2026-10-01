import { DOCUMENT } from '@angular/common';
import { Component, afterNextRender, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { BannerSinConexion } from './core/layout/banner-sin-conexion/banner-sin-conexion';
import { FocoRuta } from './core/layout/foco-ruta';

/**
 * Raíz de la aplicación. El armazón visual depende de la zona (TKT-010, DEC-AUTO-928):
 * - sitio público → ShellPublico (SkipLink, cabecera, main, pie), ruta padre de las rutas públicas;
 * - panel editorial → armazón propio de features/panel (TPL-PANEL-AUTH / TPL-PANEL-SHELL).
 * Aquí solo queda lo común a ambas zonas: el aviso sin conexión (GI-04), la gestión del foco al
 * navegar y la señal de aplicación hidratada para las pruebas E2E.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, BannerSinConexion],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  constructor() {
    inject(FocoRuta).iniciar();
    // Señal de «aplicación hidratada e interactiva» (solo navegador) para las pruebas E2E.
    const documento = inject(DOCUMENT);
    afterNextRender(() => documento.documentElement.setAttribute('data-app-lista', 'true'));
  }
}
