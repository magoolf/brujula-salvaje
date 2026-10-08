import { DOCUMENT, Location } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { MapaDelSitioStore } from '../state/mapa-del-sitio.store';

const RUTA_MAPA = '/mapa-del-sitio';
const ID_SECCION = 'seccion-';

/**
 * SCR-022 Mapa del sitio HTML (FEAT-025, MUST, TPL-PUB-LIST). Segunda vía, junto con Inicio, por
 * la que toda página publicada es alcanzable (RULE-030, OBJ-001, AC-025).
 */
@Component({
  selector: 'app-pagina-mapa-del-sitio',
  imports: [RouterLink, EstadoCargando, EstadoError],
  providers: [MapaDelSitioStore],
  templateUrl: './pagina-mapa-del-sitio.html',
  styleUrl: './pagina-mapa-del-sitio.css',
})
export class PaginaMapaDelSitio {
  protected readonly store = inject(MapaDelSitioStore);
  private readonly seo = inject(Seo);
  private readonly documento = inject(DOCUMENT);
  private readonly location = inject(Location);

  constructor() {
    this.seo.establecer({
      titulo: 'Mapa del sitio',
      descripcion:
        'Todas las páginas publicadas de Brújula Salvaje: destinos por región, itinerarios, tipos de aventura, guías, colecciones, meses, glosario e información institucional.',
      rutaCanonica: RUTA_MAPA,
    });
  }

  /**
   * Href completo del índice interno: con `<base href="/">` un `#seccion-x` relativo resolvería a
   * `/#seccion-x` (Inicio). Sin JS (SSR sin hidratar) el navegador hace la navegación de fragmento.
   */
  protected rutaSeccion(id: string): string {
    return `${RUTA_MAPA}#${ID_SECCION}${id}`;
  }

  /**
   * Salto dentro de la página sin pasar por el Router: una navegación del Router dispararía
   * FocoRuta (foco al h1, que devuelve el scroll arriba). Se lleva la vista y el foco al h2 de la
   * sección (tabindex=-1, para que el lector lo anuncie y el Tab siga desde ahí) y se deja el
   * fragmento en la URL para que sea compartible. Clics con modificador se respetan (nueva pestaña).
   */
  protected irASeccion(evento: MouseEvent, id: string): void {
    if (evento.button !== 0 || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) {
      return;
    }
    const titulo = this.documento.getElementById(`titulo-${id}`);
    const seccion = this.documento.getElementById(`${ID_SECCION}${id}`);
    if (titulo === null || seccion === null) return;
    evento.preventDefault();
    seccion.scrollIntoView({ block: 'start' });
    if (!titulo.hasAttribute('tabindex')) titulo.setAttribute('tabindex', '-1');
    titulo.focus({ preventScroll: true });
    this.location.replaceState(this.rutaSeccion(id));
  }
}
