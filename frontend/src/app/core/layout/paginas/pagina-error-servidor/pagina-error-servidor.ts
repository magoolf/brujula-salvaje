import { DOCUMENT } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Boton } from '../../../../shared/ui/boton/boton';
import { IlustracionBrujula } from '../../../../shared/ui/ilustracion-brujula/ilustracion-brujula';
import { EstadoHttp } from '../../../seo/estado-http';
import { Seo } from '../../../seo/seo';
import { TITULO_ERROR_SERVIDOR } from '../titulos';


/**
 * SCR-025 Error 500 (FEAT-026; TPL-PUB-ERROR). Sin dependencias de datos: solo texto, CSS y SVG.
 * Fija HTTP 500 en el SSR. «Reintentar» recarga la URL actual; «Ir al inicio» es un enlace real.
 * Si el propio renderizado falla, el servidor responde con la versión estática public/500.html.
 */
@Component({
  selector: 'app-pagina-error-servidor',
  imports: [RouterLink, Boton, IlustracionBrujula],
  template: `
    <section class="error bs-contenedor" data-testid="pagina-error-servidor">
      <app-ilustracion-brujula [tamano]="120" />
      <h1>Tuvimos un problema de nuestro lado</h1>
      <p class="texto">No es tu culpa. Vuelve a intentarlo en unos segundos.</p>
      <div class="acciones">
        <button type="button" appBoton data-testid="error-servidor-reintentar" (click)="reintentar()">Reintentar</button>
        <a appBoton variante="secondary" routerLink="/" data-testid="error-servidor-inicio">Ir al inicio</a>
      </div>
    </section>
  `,
  styles: `
    .error {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-6);
      max-width: 40rem;
      padding-block: var(--bs-space-12);
      text-align: center;
    }
    .texto {
      font-size: var(--bs-typography-body-lg-font-size);
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: var(--bs-space-3);
    }
  `,
})
export class PaginaErrorServidor {
  private readonly documento = inject(DOCUMENT);

  constructor() {
    inject(EstadoHttp).establecer(500);
    inject(Seo).establecer({ titulo: TITULO_ERROR_SERVIDOR, indexable: false });
  }

  protected reintentar(): void {
    this.documento.defaultView?.location.reload();
  }
}
