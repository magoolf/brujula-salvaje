import { Injectable, inject } from '@angular/core';

import { PublicoDestinosService } from '../../../api/services/publico-destinos.service';

/**
 * DATA: única puerta de entrada HTTP de la feature Guardados (Regla 01/02). RULE-013 hace que
 * SCR-019 en sí no llame al servidor; la única llamada de esta feature es «Sorpréndeme» (GI-08),
 * ofrecida también en su estado vacío.
 */
@Injectable({ providedIn: 'root' })
export class GuardadosRepositorio {
  private readonly destinos = inject(PublicoDestinosService);

  async destinoAleatorio(): Promise<string> {
    const dto = await this.destinos.publicoObtenerDestinoAleatorio();
    return dto.slug;
  }
}
