import { Component, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Enlace } from '../../../../shared/ui/enlace/enlace';
import { IlustracionBrujula } from '../../../../shared/ui/ilustracion-brujula/ilustracion-brujula';
import { EstadoHttp } from '../../../seo/estado-http';
import { NOMBRE_MARCA } from '../../../seo/marca';
import { Seo } from '../../../seo/seo';
import { TITULO_CONTENIDO_RETIRADO } from '../titulos';

/**
 * SCR-024 Contenido retirado, genérica (FEAT-026, DEC-AUTO-040; TPL-PUB-ERROR). Fija HTTP 410 en
 * el SSR y `noindex`. La feature de detalle la renderiza cuando la API responde 410
 * (`ProblemaRetirado`) y proyecta las ≥3 alternativas afines (tarjetas) y, si aplica, la acción
 * «Quitar de guardados*». Siempre ofrece el listado padre e Inicio como salida.
 */
@Component({
  selector: 'app-pagina-contenido-retirado',
  imports: [RouterLink, Enlace, IlustracionBrujula],
  template: `
    <section class="error bs-contenedor" data-testid="pagina-contenido-retirado">
      <app-ilustracion-brujula [tamano]="120" />
      <h1>Este contenido ya no está disponible</h1>
      <p class="texto">Lo retiramos de {{ marca }}. Estas aventuras se le parecen:</p>
      <div class="avisos"><ng-content select="[retirado-aviso]" /></div>
      <section class="alternativas" aria-labelledby="retirado-alternativas">
        <h2 id="retirado-alternativas">Aventuras parecidas</h2>
        <div class="rejilla"><ng-content /></div>
      </section>
      <nav aria-label="Rutas de salida">
        <ul class="salidas">
          <li>
            <a
              appEnlace
              variante="standalone"
              [routerLink]="rutaListadoPadre()"
              data-testid="retirado-listado-padre"
            >
              {{ etiquetaListadoPadre() }}
            </a>
          </li>
          <li>
            <a appEnlace variante="standalone" routerLink="/" data-testid="retirado-inicio"
              >Ir al inicio</a
            >
          </li>
        </ul>
      </nav>
    </section>
  `,
  styles: `
    .error {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-6);
      padding-block: var(--bs-space-12);
      text-align: center;
    }
    .texto {
      max-width: var(--bs-size-measure-prose);
      font-size: var(--bs-typography-body-lg-font-size);
    }
    .alternativas {
      display: grid;
      gap: var(--bs-space-4);
      width: 100%;
      text-align: start;
    }
    .alternativas:has(.rejilla:empty) {
      display: none;
    }
    .rejilla {
      display: grid;
      gap: var(--bs-grid-gutter-xs);
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 18rem), 1fr));
    }
    .salidas {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: var(--bs-space-2) var(--bs-space-8);
      margin: 0;
      padding: 0;
      list-style: none;
    }
  `,
})
export class PaginaContenidoRetirado {
  /** Ruta del listado padre (`listado_padre` del 410, p. ej. `/destinos`). */
  readonly rutaListadoPadre = input('/');
  readonly etiquetaListadoPadre = input('Volver al listado');

  protected readonly marca = NOMBRE_MARCA;

  constructor() {
    inject(EstadoHttp).establecer(410);
    inject(Seo).establecer({ titulo: TITULO_CONTENIDO_RETIRADO, indexable: false });
  }
}
