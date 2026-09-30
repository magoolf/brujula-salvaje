/**
 * DATA: única puerta de entrada HTTP de la feature Glosario (Regla 01/02).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoGlosarioCreditosService } from '../../../api/services/publico-glosario-creditos.service';
import { PaginaGlosario } from '../domain/modelos';
import { mapPaginaGlosario } from './glosario.mapper';

@Injectable({ providedIn: 'root' })
export class GlosarioRepositorio {
  private readonly servicio = inject(PublicoGlosarioCreditosService);

  async listar(pagina: number): Promise<PaginaGlosario> {
    const dto = await this.servicio.publicoListarGlosario({ pagina: pagina > 1 ? pagina : undefined });
    return mapPaginaGlosario(dto);
  }
}
