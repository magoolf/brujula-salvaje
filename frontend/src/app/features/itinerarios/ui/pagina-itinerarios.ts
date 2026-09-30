import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { queryParamsOrden } from '../domain/filtros';
import { OrdenItinerarios } from '../domain/modelos';
import { ItinerariosListadoStore } from '../state/itinerarios-listado.store';

const ETIQUETAS_ORDEN: Record<OrdenItinerarios, string> = {
  titulo: 'A-Z',
  duracion_asc: 'Duración: más cortos primero',
  duracion_desc: 'Duración: más largos primero',
};

/** SCR-006 Listado de itinerarios (FEAT-009, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-itinerarios',
  imports: [RouterLink, TarjetaContenido, MedidorDificultad, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [ItinerariosListadoStore],
  templateUrl: './pagina-itinerarios.html',
  styleUrl: './pagina-itinerarios.css',
})
export class PaginaItinerarios {
  protected readonly store = inject(ItinerariosListadoStore);
  private readonly seo = inject(Seo);

  protected readonly etiquetasOrden = ETIQUETAS_ORDEN;
  protected readonly ordenesDisponibles: readonly OrdenItinerarios[] = [
    'titulo',
    'duracion_asc',
    'duracion_desc',
  ];
  protected readonly filtros = this.store.filtros;

  constructor() {
    this.seo.establecer({
      titulo: 'Itinerarios',
      descripcion: 'Recorre todos los itinerarios de aventura publicados, día a día.',
    });
    if (this.filtros().pagina > 1) {
      this.seo.establecer({ titulo: 'Itinerarios', indexable: false });
    }
  }

  protected queryParamsOrden(orden: OrdenItinerarios) {
    return queryParamsOrden(orden);
  }
}
