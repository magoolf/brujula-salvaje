import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { TiposListadoStore } from '../state/tipos-listado.store';

/** SCR-008 Índice de tipos de aventura (FEAT-010, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-tipos-aventura',
  imports: [RouterLink, TarjetaContenido, MedidorDificultad, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [TiposListadoStore],
  templateUrl: './pagina-tipos-aventura.html',
  styleUrl: './pagina-tipos-aventura.css',
})
export class PaginaTiposAventura {
  protected readonly store = inject(TiposListadoStore);
  private readonly seo = inject(Seo);

  constructor() {
    this.seo.establecer({
      titulo: 'Tipos de aventura',
      descripcion: 'Elige cómo quieres vivir la aventura: senderismo, buceo, alta montaña y más.',
    });
  }

  protected conteo(n: number): string {
    return n === 1 ? '1 destino' : `${n} destinos`;
  }
}
