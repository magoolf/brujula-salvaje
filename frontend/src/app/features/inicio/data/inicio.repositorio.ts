import { Injectable, inject } from '@angular/core';

import { PublicoDestinosService } from '../../../api/services/publico-destinos.service';
import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { Inicio } from '../domain/modelos';
import { mapInicio } from './inicio.mapper';

/** DATA: única puerta de entrada HTTP de la feature Inicio (Regla 01/02). */
@Injectable({ providedIn: 'root' })
export class InicioRepositorio {
  private readonly general = inject(PublicoGeneralService);
  private readonly destinos = inject(PublicoDestinosService);

  async obtener(): Promise<Inicio> {
    const dto = await this.general.publicoObtenerInicio();
    return mapInicio(dto);
  }

  /** FEAT-051/GI-08 «Sorpréndeme»: slug de un destino publicado al azar. */
  async destinoAleatorio(): Promise<string> {
    const dto = await this.destinos.publicoObtenerDestinoAleatorio();
    return dto.slug;
  }
}
