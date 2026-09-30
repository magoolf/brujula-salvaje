/**
 * DATA: única puerta de entrada HTTP de la feature Itinerarios (Regla 01/02: `HttpClient`/URLs
 * solo aquí, a través del cliente OpenAPI generado).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { PublicoItinerariosService } from '../../../api/services/publico-itinerarios.service';
import { PublicoListarItinerarios$Params } from '../../../api/fn/publico-itinerarios/publico-listar-itinerarios';
import { FiltrosItinerarios, ItinerarioDetalle, PaginaItinerarios } from '../domain/modelos';
import { mapItinerarioDetalle, mapPaginaItinerarios } from './itinerarios.mapper';

function paramsDesdeFiltros(filtros: FiltrosItinerarios): PublicoListarItinerarios$Params {
  return {
    orden: filtros.orden === 'titulo' ? undefined : filtros.orden,
    pagina: filtros.pagina > 1 ? filtros.pagina : undefined,
  };
}

@Injectable({ providedIn: 'root' })
export class ItinerariosRepositorio {
  private readonly itinerarios = inject(PublicoItinerariosService);
  private readonly general = inject(PublicoGeneralService);

  async listar(filtros: FiltrosItinerarios): Promise<PaginaItinerarios> {
    const dto = await this.itinerarios.publicoListarItinerarios(paramsDesdeFiltros(filtros));
    return mapPaginaItinerarios(dto);
  }

  async detalle(slug: string): Promise<ItinerarioDetalle> {
    const dto = await this.itinerarios.publicoObtenerItinerario({ slug });
    return mapItinerarioDetalle(dto);
  }

  /** RULE-010: texto del descargo de responsabilidad, mostrado en toda ficha de itinerario. */
  async textoDescargo(): Promise<string> {
    const dto = await this.general.publicoObtenerConfiguracion();
    return dto.texto_descargo;
  }
}
