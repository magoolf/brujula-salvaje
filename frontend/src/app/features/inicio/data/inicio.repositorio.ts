import { isPlatformServer } from '@angular/common';
import { Injectable, PLATFORM_ID, TransferState, inject, makeStateKey } from '@angular/core';

import { Inicio as InicioDto } from '../../../api/models/inicio';
import { PublicoDestinosService } from '../../../api/services/publico-destinos.service';
import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { Inicio } from '../domain/modelos';
import { mapInicio } from './inicio.mapper';

/**
 * CLS real medido en Inicio (QA, ciclo 1/3): sin `withHttpTransferCache` a nivel de app (fuera de
 * mis `archivos_permitidos`), la hidratación repite la petición HTTP del cliente ya hecha en SSR;
 * mientras esa segunda petición está en vuelo, el `resource()` del store nace sin valor y la
 * plantilla de Inicio colapsa sus secciones (vuelve a "cargando") para luego volver a expandirlas
 * cuando la respuesta llega — el propio footer se desplaza. `TransferState` es la pieza general de
 * Angular para puentear server→cliente (independiente de `withHttpTransferCache`, que es solo un
 * atajo para HTTP): se guarda la respuesta cruda en SSR y se reutiliza una sola vez en el cliente,
 * sin una segunda petición de red ni el hueco de "sin valor" que causaba el colapso.
 */
const CLAVE_INICIO = makeStateKey<InicioDto>('publico-inicio');

/** DATA: única puerta de entrada HTTP de la feature Inicio (Regla 01/02). */
@Injectable({ providedIn: 'root' })
export class InicioRepositorio {
  private readonly general = inject(PublicoGeneralService);
  private readonly destinos = inject(PublicoDestinosService);
  private readonly transferencia = inject(TransferState);
  private readonly esServidor = isPlatformServer(inject(PLATFORM_ID));

  async obtener(): Promise<Inicio> {
    const transferido = this.transferencia.get(CLAVE_INICIO, null);
    if (transferido !== null) {
      // Solo sirve para la primera hidratación: se consume una vez para no quedar obsoleto si
      // luego se llama a recargar() en el propio cliente.
      this.transferencia.remove(CLAVE_INICIO);
      return mapInicio(transferido);
    }
    const dto = await this.general.publicoObtenerInicio();
    if (this.esServidor) {
      this.transferencia.set(CLAVE_INICIO, dto);
    }
    return mapInicio(dto);
  }

  /** FEAT-051/GI-08 «Sorpréndeme»: slug de un destino publicado al azar. */
  async destinoAleatorio(): Promise<string> {
    const dto = await this.destinos.publicoObtenerDestinoAleatorio();
    return dto.slug;
  }
}
