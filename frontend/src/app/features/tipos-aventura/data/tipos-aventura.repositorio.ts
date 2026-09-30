/**
 * DATA: única puerta de entrada HTTP de la feature Tipos de aventura (Regla 01/02).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { PublicoTiposService } from '../../../api/services/publico-tipos.service';
import { PaginaTipos, TipoDetalle } from '../domain/modelos';
import { mapPaginaTipos, mapTipoDetalle } from './tipos-aventura.mapper';

@Injectable({ providedIn: 'root' })
export class TiposAventuraRepositorio {
  private readonly tipos = inject(PublicoTiposService);
  private readonly general = inject(PublicoGeneralService);

  async listar(pagina: number): Promise<PaginaTipos> {
    const dto = await this.tipos.publicoListarTiposAventura({ pagina: pagina > 1 ? pagina : undefined });
    return mapPaginaTipos(dto);
  }

  async detalle(slug: string): Promise<TipoDetalle> {
    const dto = await this.tipos.publicoObtenerTipoAventura({ slug });
    return mapTipoDetalle(dto);
  }

  /** RULE-010: texto del descargo de responsabilidad. */
  async textoDescargo(): Promise<string> {
    const dto = await this.general.publicoObtenerConfiguracion();
    return dto.texto_descargo;
  }
}
