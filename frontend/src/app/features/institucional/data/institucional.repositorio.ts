/**
 * DATA: única puerta de entrada HTTP de la feature Institucional (Regla 01/02).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { PublicoGlosarioCreditosService } from '../../../api/services/publico-glosario-creditos.service';
import { ConfiguracionVista, EscalasVista, PaginaCreditos, PaginaInstitucionalVista, SlugInstitucional } from '../domain/modelos';
import { mapConfiguracion, mapEscalas, mapPaginaCreditos, mapPaginaInstitucional } from './institucional.mapper';

@Injectable({ providedIn: 'root' })
export class InstitucionalRepositorio {
  private readonly general = inject(PublicoGeneralService);
  private readonly glosarioCreditos = inject(PublicoGlosarioCreditosService);

  async pagina(slug: SlugInstitucional): Promise<PaginaInstitucionalVista> {
    const dto = await this.general.publicoObtenerPaginaInstitucional({ slug });
    return mapPaginaInstitucional(dto);
  }

  async escalas(): Promise<EscalasVista> {
    const dto = await this.general.publicoObtenerEscalas();
    return mapEscalas(dto);
  }

  async configuracion(): Promise<ConfiguracionVista> {
    const dto = await this.general.publicoObtenerConfiguracion();
    return mapConfiguracion(dto);
  }

  async creditos(pagina: number): Promise<PaginaCreditos> {
    const dto = await this.glosarioCreditos.publicoListarCreditos({ pagina: pagina > 1 ? pagina : undefined });
    return mapPaginaCreditos(dto);
  }
}
