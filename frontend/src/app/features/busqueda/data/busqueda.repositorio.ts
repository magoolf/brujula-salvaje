/**
 * DATA: única puerta de entrada HTTP de la feature Búsqueda (Regla 01/02).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoBusquedaService } from '../../../api/services/publico-busqueda.service';
import { BusquedaAgrupadaVista, GrupoResultado, PaginaResultados } from '../domain/modelos';
import { mapBusquedaAgrupada, mapPaginaResultados } from './busqueda.mapper';

const GRUPO_A_API: Record<GrupoResultado, 'destinos' | 'itinerarios' | 'guias' | 'tipos'> = {
  destinos: 'destinos',
  itinerarios: 'itinerarios',
  guias: 'guias',
  tipos: 'tipos',
};

@Injectable({ providedIn: 'root' })
export class BusquedaRepositorio {
  private readonly busqueda = inject(PublicoBusquedaService);

  async buscar(q: string): Promise<BusquedaAgrupadaVista> {
    const dto = await this.busqueda.publicoBuscar({ q });
    return mapBusquedaAgrupada(dto);
  }

  async buscarPorGrupo(grupo: GrupoResultado, q: string, pagina: number): Promise<PaginaResultados> {
    const dto = await this.busqueda.publicoBuscarPorGrupo({
      grupo: GRUPO_A_API[grupo],
      q,
      pagina: pagina > 1 ? pagina : undefined,
    });
    return mapPaginaResultados(dto);
  }
}
