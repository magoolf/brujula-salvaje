import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CampoBusqueda } from '../../../../shared/ui/campo-busqueda/campo-busqueda';
import { Enlace } from '../../../../shared/ui/enlace/enlace';
import { IlustracionBrujula } from '../../../../shared/ui/ilustracion-brujula/ilustracion-brujula';
import { EstadoHttp } from '../../../seo/estado-http';
import { Seo } from '../../../seo/seo';
import { TITULO_NO_ENCONTRADA } from '../titulos';

/**
 * SCR-023 Error 404 (FEAT-026, FLOW-017; TPL-PUB-ERROR). Responde HTTP 404 real en el SSR y
 * `noindex`. Muestra búsqueda y rutas de salida (Inicio / Destinos / Guías).
 * Los «3 destinos destacados» y «Sorpréndeme*» dependen de datos de features aún no implementadas;
 * según su VIEW_SPEC, si los destacados no están disponibles la sección se omite.
 */
@Component({
  selector: 'app-pagina-no-encontrada',
  imports: [RouterLink, CampoBusqueda, Enlace, IlustracionBrujula],
  template: `
    <section class="error bs-contenedor" data-testid="pagina-no-encontrada">
      <app-ilustracion-brujula [tamano]="120" />
      <h1>No encontramos esta página</h1>
      <p class="texto">
        Puede que el enlace esté mal escrito o que la página nunca haya existido. Sigue explorando
        desde aquí:
      </p>
      <div class="busqueda">
        <app-campo-busqueda
          variante="pagina-error"
          idCampo="busqueda-404"
          testId="no-encontrada-busqueda"
          [etiquetaOculta]="false"
          [soloIcono]="false"
        />
      </div>
      <nav aria-label="Rutas de salida">
        <ul class="salidas">
          <li>
            <a appEnlace variante="standalone" routerLink="/" data-testid="no-encontrada-inicio"
              >Ir al inicio</a
            >
          </li>
          <li>
            <a
              appEnlace
              variante="standalone"
              routerLink="/destinos"
              data-testid="no-encontrada-destinos"
              >Explorar destinos</a
            >
          </li>
          <li>
            <a appEnlace variante="standalone" routerLink="/guias" data-testid="no-encontrada-guias"
              >Ver las guías</a
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
      line-height: var(--bs-typography-body-lg-line-height);
    }
    .busqueda {
      width: min(100%, 36rem);
      text-align: start;
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
export class PaginaNoEncontrada {
  constructor() {
    inject(EstadoHttp).establecer(404);
    inject(Seo).establecer({
      titulo: TITULO_NO_ENCONTRADA,
      descripcion:
        'La página que buscas no existe. Sigue explorando destinos, itinerarios y guías.',
      indexable: false,
    });
  }
}
