import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { ColeccionesListadoStore } from '../state/colecciones-listado.store';

/** SCR-013 Índice de colecciones (FEAT-017, TPL-PUB-LIST, SHOULD). */
@Component({
  selector: 'app-pagina-colecciones',
  imports: [RouterLink, TarjetaContenido, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [ColeccionesListadoStore],
  templateUrl: './pagina-colecciones.html',
  styleUrl: './pagina-colecciones.css',
})
export class PaginaColecciones {
  protected readonly store = inject(ColeccionesListadoStore);
  private readonly seo = inject(Seo);

  constructor() {
    this.seo.establecer({
      titulo: 'Colecciones',
      descripcion: 'Selecciones curadas de destinos e itinerarios por nuestro equipo editorial.',
    });
  }

  protected conteo(n: number): string {
    return n === 1 ? '1 aventura' : `${n} aventuras`;
  }
}
