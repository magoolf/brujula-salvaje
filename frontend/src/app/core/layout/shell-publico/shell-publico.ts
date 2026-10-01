import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { SkipLink } from '../../../shared/ui/skip-link/skip-link';
import { CabeceraSitio } from '../cabecera-sitio/cabecera-sitio';
import { ID_CONTENIDO_PRINCIPAL } from '../navegacion';
import { PieSitio } from '../pie-sitio/pie-sitio';

/**
 * Shell del sitio público (GI-01..GI-03): SkipLink → cabecera fija → main → pie, con landmarks
 * header/nav/main/footer en todas las vistas públicas. Es la ruta padre de todas las rutas
 * públicas (TKT-010, DEC-AUTO-928): el panel editorial (/panel/**) tiene su propio armazón
 * (TPL-PANEL-AUTH / TPL-PANEL-SHELL) y no se renderiza dentro de este.
 */
@Component({
  selector: 'app-shell-publico',
  imports: [RouterOutlet, SkipLink, CabeceraSitio, PieSitio],
  templateUrl: './shell-publico.html',
  styleUrl: './shell-publico.css',
})
export class ShellPublico {
  protected readonly idContenido = ID_CONTENIDO_PRINCIPAL;
}
