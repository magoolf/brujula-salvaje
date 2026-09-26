import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Boton } from '../../../../shared/ui/boton/boton';
import { CampoBusqueda } from '../../../../shared/ui/campo-busqueda/campo-busqueda';
import { Enlace } from '../../../../shared/ui/enlace/enlace';
import { IlustracionBrujula } from '../../../../shared/ui/ilustracion-brujula/ilustracion-brujula';
import { NOMBRE_MARCA } from '../../../seo/marca';
import { Seo } from '../../../seo/seo';
import { sitioWebJsonLd } from '../../../seo/datos-estructurados';

/**
 * Estado vacío de SCR-001 Inicio («Contenido en preparación», VIEW_SPEC SCR-001 estados_UI.empty):
 * se muestra en la ruta raíz mientras no existe la feature de Inicio (TKT-008 sustituye esta ruta
 * por features/inicio). Ofrece la acción principal, la búsqueda y enlaces institucionales.
 */
@Component({
  selector: 'app-pagina-en-preparacion',
  imports: [RouterLink, Boton, CampoBusqueda, Enlace, IlustracionBrujula],
  template: `
    <section class="preparacion bs-contenedor" data-testid="pagina-en-preparacion">
      <app-ilustracion-brujula [tamano]="120" />
      <p class="bs-overline marca">{{ marca }}</p>
      <h1>Contenido en preparación</h1>
      <p class="texto">Mientras tanto, conoce cómo trabajamos.</p>
      <a appBoton variante="accent" tamano="lg" routerLink="/destinos" data-testid="preparacion-explorar">Explorar destinos</a>
      <div class="busqueda">
        <app-campo-busqueda variante="grande" idCampo="busqueda-inicio" testId="preparacion-busqueda" [soloIcono]="false" />
      </div>
      <nav aria-label="Institucional">
        <ul class="salidas">
          <li><a appEnlace variante="standalone" routerLink="/acerca-de" data-testid="preparacion-acerca-de">Acerca de y metodología</a></li>
          <li><a appEnlace variante="standalone" routerLink="/mapa-del-sitio" data-testid="preparacion-mapa-del-sitio">Mapa del sitio</a></li>
        </ul>
      </nav>
    </section>
  `,
  styles: `
    .preparacion {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-6);
      padding-block: var(--bs-space-section);
      text-align: center;
    }
    .marca { color: var(--bs-color-text-accent); }
    .texto {
      max-width: var(--bs-size-measure-prose);
      font-size: var(--bs-typography-body-lg-font-size);
    }
    .busqueda {
      width: min(100%, 36rem);
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
export class PaginaEnPreparacion {
  protected readonly marca = NOMBRE_MARCA;

  constructor() {
    const seo = inject(Seo);
    seo.establecer({
      titulo: 'Inicio',
      descripcion: `${NOMBRE_MARCA}: destinos, itinerarios y guías expertas de viajes de aventura.`,
      rutaCanonica: '/',
      datosEstructurados: sitioWebJsonLd(seo.origen(), NOMBRE_MARCA, 'es-CO'),
    });
  }
}
