import { DOCUMENT } from '@angular/common';
import { Component, afterNextRender, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { BannerSinConexion } from './core/layout/banner-sin-conexion/banner-sin-conexion';
import { CabeceraSitio } from './core/layout/cabecera-sitio/cabecera-sitio';
import { FocoRuta } from './core/layout/foco-ruta';
import { ID_CONTENIDO_PRINCIPAL } from './core/layout/navegacion';
import { PieSitio } from './core/layout/pie-sitio/pie-sitio';
import { SkipLink } from './shared/ui/skip-link/skip-link';

/**
 * Shell global del sitio público (GI-01..GI-04): SkipLink → cabecera fija → main → pie, más el
 * aviso sin conexión. Landmarks header/nav/main/footer en todas las vistas.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SkipLink, CabeceraSitio, PieSitio, BannerSinConexion],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly idContenido = ID_CONTENIDO_PRINCIPAL;

  constructor() {
    inject(FocoRuta).iniciar();
    // Señal de «aplicación hidratada e interactiva» (solo navegador) para las pruebas E2E.
    const documento = inject(DOCUMENT);
    afterNextRender(() => documento.documentElement.setAttribute('data-app-lista', 'true'));
  }
}
