/**
 * DATA: única puerta de entrada HTTP de la feature Destinos (Regla 01/02: `HttpClient`/URLs solo
 * aquí, a través del cliente OpenAPI generado). Traduce `FiltrosDestinos` (dominio) hacia los
 * `$Params` del cliente y las respuestas hacia el dominio (mapper).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoListarDestinos$Params } from '../../../api/fn/publico-destinos/publico-listar-destinos';
import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { PublicoDestinosService } from '../../../api/services/publico-destinos.service';
import { FiltrosDestinos } from '../domain/modelos';
import {
  mapDestinoDetalle,
  mapFacetas,
  mapMeses,
  mapPaginaDestinos,
  mapPaginaMapa,
} from './destinos.mapper';
import {
  DestinoDetalle,
  FacetasDestinos,
  MesResumen,
  PaginaDestinos,
  PaginaMapa,
  PuntoMapa,
} from '../domain/modelos';

/** Tope defensivo de páginas a recorrer para el mapa (evita bucles si el backend cambiara de forma). */
const LIMITE_PAGINAS_MAPA = 20;

function paramsDesdeFiltros(filtros: FiltrosDestinos): PublicoListarDestinos$Params {
  return {
    tipo: filtros.tipo.length > 0 ? [...filtros.tipo] : undefined,
    region: filtros.region ?? undefined,
    pais: filtros.pais ?? undefined,
    dificultad_min: filtros.dificultadMin ?? undefined,
    dificultad_max: filtros.dificultadMax ?? undefined,
    mes: filtros.mes ?? undefined,
    duracion: filtros.duracion.length > 0 ? [...filtros.duracion] : undefined,
    presupuesto: filtros.presupuesto.length > 0 ? [...filtros.presupuesto] : undefined,
    orden: filtros.orden === 'nombre' ? undefined : filtros.orden,
    pagina: filtros.pagina > 1 ? filtros.pagina : undefined,
  };
}

@Injectable({ providedIn: 'root' })
export class DestinosRepositorio {
  private readonly destinos = inject(PublicoDestinosService);
  private readonly general = inject(PublicoGeneralService);

  async listar(filtros: FiltrosDestinos): Promise<PaginaDestinos> {
    const dto = await this.destinos.publicoListarDestinos(paramsDesdeFiltros(filtros));
    return mapPaginaDestinos(dto);
  }

  async facetas(): Promise<FacetasDestinos> {
    const dto = await this.destinos.publicoObtenerFacetasDestinos();
    return mapFacetas(dto);
  }

  async mapa(pagina: number): Promise<PaginaMapa> {
    const dto = await this.destinos.publicoListarDestinosMapa({ pagina: pagina > 1 ? pagina : undefined });
    return mapPaginaMapa(dto);
  }

  /** El mapa necesita TODOS los destinos con coordenadas, no una página: las recorre y fusiona. */
  async mapaCompleto(): Promise<readonly PuntoMapa[]> {
    const primera = await this.mapa(1);
    const puntos = [...primera.resultados];
    const tope = Math.min(primera.totalPaginas, LIMITE_PAGINAS_MAPA);
    for (let pagina = 2; pagina <= tope; pagina++) {
      const siguiente = await this.mapa(pagina);
      puntos.push(...siguiente.resultados);
    }
    return puntos;
  }

  async detalle(slug: string): Promise<DestinoDetalle> {
    const dto = await this.destinos.publicoObtenerDestino({ slug });
    return mapDestinoDetalle(dto);
  }

  async meses(): Promise<readonly MesResumen[]> {
    const dto = await this.general.publicoObtenerMeses();
    return mapMeses(dto);
  }

  /** RULE-010: texto del descargo de responsabilidad (DATA-023), mostrado en toda ficha de destino. */
  async textoDescargo(): Promise<string> {
    const dto = await this.general.publicoObtenerConfiguracion();
    return dto.texto_descargo;
  }
}
