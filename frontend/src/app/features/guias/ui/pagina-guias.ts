import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { GuiasListadoStore } from '../state/guias-listado.store';

/** SCR-010 Índice de guías (FEAT-012, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-guias',
  imports: [RouterLink, TarjetaContenido, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [GuiasListadoStore],
  templateUrl: './pagina-guias.html',
  styleUrl: './pagina-guias.css',
})
export class PaginaGuias {
  protected readonly store = inject(GuiasListadoStore);
  private readonly seo = inject(Seo);

  constructor() {
    this.seo.establecer({
      titulo: 'Guías expertas',
      descripcion: 'Aprende por temas: seguridad, equipo, técnica y consejos de nuestro equipo editorial.',
    });
  }
}
