import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';

/**
 * ST-NOTFOUND dentro del panel: una ruta /panel/** que no existe (todavía) muestra este estado en
 * el armazón del panel con salida al Tablero, en lugar de la 404 pública.
 */
@Component({
  selector: 'app-pagina-no-encontrada-panel',
  imports: [RouterLink, Boton],
  template: `
    <section class="no-encontrada" data-testid="panel-no-encontrada" aria-labelledby="panel-404-titulo">
      <h1 id="panel-404-titulo" tabindex="-1">No encontramos esta página del panel</h1>
      <p>Revisa la dirección o vuelve al tablero para seguir trabajando.</p>
      <a appBoton routerLink="/panel" data-testid="panel-no-encontrada-tablero">Ir al tablero</a>
    </section>
  `,
  styles: `
    .no-encontrada {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-4);
      max-width: 35rem;
      margin-inline: auto;
      padding-block: var(--bs-space-10);
      text-align: center;
    }
    h1 {
      outline: none;
    }
  `,
})
export class PaginaNoEncontradaPanel {
  constructor() {
    inject(Seo).establecer({ titulo: 'Página no encontrada', indexable: false });
  }
}
