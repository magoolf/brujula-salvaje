import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { MapaDelSitioStore } from '../state/mapa-del-sitio.store';

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

  constructor() {
    this.seo.establecer({
      titulo: 'Mapa del sitio',
      descripcion:
        'Todas las páginas publicadas de Brújula Salvaje: destinos por región, itinerarios, tipos de aventura, guías, colecciones, meses, glosario e información institucional.',
      rutaCanonica: '/mapa-del-sitio',
    });
  }
}
