/**
 * DATA: única puerta de entrada HTTP de la feature Colecciones (Regla 01/02).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoColeccionesService } from '../../../api/services/publico-colecciones.service';
import { ColeccionDetalle, PaginaColecciones } from '../domain/modelos';
import { mapColeccionDetalle, mapPaginaColecciones } from './colecciones.mapper';

@Injectable({ providedIn: 'root' })
export class ColeccionesRepositorio {
  private readonly colecciones = inject(PublicoColeccionesService);

  async listar(pagina: number): Promise<PaginaColecciones> {
    const dto = await this.colecciones.publicoListarColecciones({ pagina: pagina > 1 ? pagina : undefined });
    return mapPaginaColecciones(dto);
  }

  async detalle(slug: string): Promise<ColeccionDetalle> {
    const dto = await this.colecciones.publicoObtenerColeccion({ slug });
    return mapColeccionDetalle(dto);
  }
}
