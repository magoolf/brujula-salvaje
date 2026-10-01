/**
 * DATA: única puerta HTTP de los medios del panel (MOD-011, /api/v1/panel/medios/** y el catálogo
 * de licencias de solo lectura). Usa el cliente generado desde el contrato (Skill_Frontend §27.3).
 *
 * La subida (FLOW-013) es la única operación que no pasa por el método generado: este no expone el
 * progreso del envío. Se construye con el `RequestBuilder` generado y la ruta del contrato
 * (`panelSubirMedios.PATH`), así que la URL, el multipart y la cabecera Idempotency-Key siguen
 * saliendo del contrato; el XSRF lo añade Angular (withXsrfConfiguration) como en el resto.
 */
import { HttpClient, HttpEvent, HttpEventType, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, filter, map, tap } from 'rxjs';

import { ApiConfiguration } from '../../../api/api-configuration';
import { panelSubirMedios } from '../../../api/fn/panel-medios/panel-subir-medios';
import { ResultadoSubida } from '../../../api/models/resultado-subida';
import { RequestBuilder } from '../../../api/request-builder';
import { PanelConfiguracionService } from '../../../api/services/panel-configuracion.service';
import { PanelMediosService } from '../../../api/services/panel-medios.service';
import {
  EntradaCatalogacion,
  FiltrosMedios,
  LicenciaCatalogo,
  Medio,
  PaginaMedios,
  PaginaUsos,
  ResultadoArchivo,
} from '../domain/medios';
import {
  aCatalogacionDto,
  mapLicencia,
  mapMedio,
  mapPaginaMedios,
  mapPaginaUsos,
  mapResultadoSubida,
  paramsListado,
} from './medios.mapper';

/** Páginas máximas del catálogo de licencias que se leen (100 por página, contrato). */
const PAGINAS_LICENCIAS = 20;

/** Progreso del envío de una subida (bytes). `total` es null si el navegador no lo conoce. */
export type AlProgresar = (cargados: number, total: number | null) => void;

@Injectable({ providedIn: 'root' })
export class PanelMediosRepositorio {
  private readonly api = inject(PanelMediosService);
  private readonly configuracion = inject(PanelConfiguracionService);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(ApiConfiguration);

  async listar(filtros: FiltrosMedios): Promise<PaginaMedios> {
    return mapPaginaMedios(await this.api.panelListarMedios(paramsListado(filtros)));
  }

  async obtener(id: number): Promise<Medio> {
    return mapMedio(await this.api.panelObtenerMedio({ id }));
  }

  async usos(id: number, pagina = 1): Promise<PaginaUsos> {
    return mapPaginaUsos(
      await this.api.panelListarUsosMedio({ id, pagina: pagina > 1 ? pagina : undefined }),
    );
  }

  async catalogar(id: number, entrada: EntradaCatalogacion): Promise<Medio> {
    return mapMedio(await this.api.panelCatalogarMedio({ id, body: aCatalogacionDto(entrada) }));
  }

  async retirar(id: number): Promise<Medio> {
    return mapMedio(await this.api.panelRetirarMedio({ id }));
  }

  async reactivar(id: number): Promise<Medio> {
    return mapMedio(await this.api.panelReactivarMedio({ id }));
  }

  /** Catálogo de licencias (DATA-015; el Editor lo lee, solo el Administrador lo edita). */
  async licencias(): Promise<readonly LicenciaCatalogo[]> {
    const todas: LicenciaCatalogo[] = [];
    for (let pagina = 1; pagina <= PAGINAS_LICENCIAS; pagina++) {
      const dto = await this.configuracion.panelListarLicencias(pagina > 1 ? { pagina } : {});
      todas.push(...dto.resultados.map(mapLicencia));
      if (dto.siguiente === null || pagina >= dto.total_paginas) break;
    }
    return todas;
  }

  /**
   * Sube 1..10 archivos (FLOW-013). Emite una sola vez, con el resultado por archivo; el progreso
   * del envío se informa con `alProgresar`. `claveIdempotencia` protege del doble envío (ALT-017).
   */
  subir(
    archivos: readonly File[],
    claveIdempotencia: string,
    alProgresar: AlProgresar,
  ): Observable<readonly ResultadoArchivo[]> {
    const rb = new RequestBuilder(this.apiConfig.rootUrl, panelSubirMedios.PATH, 'post');
    rb.header('Idempotency-Key', claveIdempotencia, {});
    rb.body({ archivos: [...archivos] }, 'multipart/form-data');
    const peticion = rb.build<FormData>({
      responseType: 'json',
      accept: 'application/json',
      reportProgress: true,
    });
    return this.http.request<ResultadoSubida>(peticion).pipe(
      tap((evento: HttpEvent<ResultadoSubida>) => {
        if (evento.type === HttpEventType.UploadProgress) {
          alProgresar(evento.loaded, evento.total ?? null);
        }
      }),
      filter((evento): evento is HttpResponse<ResultadoSubida> => evento instanceof HttpResponse),
      map((respuesta) => mapResultadoSubida(respuesta.body ?? { resultados: [] })),
    );
  }
}

/**
 * Clave Idempotency-Key (UUID v4) con `crypto.getRandomValues`, disponible también fuera de un
 * contexto seguro (a diferencia de `crypto.randomUUID`).
 */
export function nuevaClaveIdempotencia(aleatorio: Crypto = globalThis.crypto): string {
  const bytes = aleatorio.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
