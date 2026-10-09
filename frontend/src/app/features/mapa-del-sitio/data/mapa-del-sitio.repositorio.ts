/**
 * DATA: única puerta de entrada HTTP de la feature Mapa del sitio (Regla 01/02). Compone los
 * endpoints públicos existentes del contrato (sin cambiarlo):
 * - GET /api/v1/publico/indice (AP-12): todas las páginas publicadas, paginado de 1000 en 1000.
 * - GET /api/v1/publico/meses: los 12 meses de «¿Dónde ir cada mes?».
 * - GET /api/v1/publico/glosario: los términos (el índice no incluye TERMINO; propuesta CHG-API en
 *   el handoff de TKT-019), paginado de 100 en 100.
 */
import { isPlatformServer } from '@angular/common';
import { Injectable, PLATFORM_ID, TransferState, inject, makeStateKey } from '@angular/core';

import { PaginaMeta } from '../../../api/models/pagina-meta';
import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { PublicoGlosarioCreditosService } from '../../../api/services/publico-glosario-creditos.service';
import { DatosMapaDelSitio, EntradaIndiceVista, TerminoVista } from '../domain/modelos';
import { mapEntradaIndice, mapMeses, mapTermino } from './mapa-del-sitio.mapper';

/**
 * CLS (Skill_UI_UX §47.2): sin puente servidor→cliente, el `resource()` del store nace sin valor al
 * hidratar y la página vuelve a «cargando» antes de repintar lo que ya traía el SSR (CLS ≈ 0,42
 * medido en este ticket). Mismo patrón que InicioRepositorio: el SSR guarda los datos ya
 * traducidos en TransferState y el cliente los usa (una sola vez) para su primer render.
 */
const CLAVE_MAPA = makeStateKey<DatosMapaDelSitio>('publico-mapa-del-sitio');

/** Tope defensivo de páginas por listado (1000 entradas/página en el índice, 100 en el glosario). */
export const MAX_PAGINAS = 20;

/**
 * Pide la página 1 y, en paralelo, el resto hasta `total_paginas` (con el tope MAX_PAGINAS).
 * La página 1 se pide sin el parámetro `pagina` (misma URL cacheable que el resto del sitio).
 */
async function todasLasPaginas<P extends PaginaMeta, T>(
  pedir: (pagina: number | undefined) => Promise<P>,
  extraer: (pagina: P, numero: number) => readonly T[],
): Promise<T[]> {
  const primera = await pedir(undefined);
  const total = Math.min(primera.total_paginas, MAX_PAGINAS);
  const resto = await Promise.all(
    Array.from({ length: Math.max(total - 1, 0) }, (_, i) => pedir(i + 2)),
  );
  return [primera, ...resto].flatMap((p, i) => [...extraer(p, i + 1)]);
}

@Injectable({ providedIn: 'root' })
export class MapaDelSitioRepositorio {
  private readonly general = inject(PublicoGeneralService);
  private readonly glosario = inject(PublicoGlosarioCreditosService);
  private readonly transferencia = inject(TransferState);
  private readonly esServidor = isPlatformServer(inject(PLATFORM_ID));

  /** Datos que el SSR dejó para la hidratación (sin consumirlos); `null` si no hay. */
  datosTransferidos(): DatosMapaDelSitio | null {
    return this.transferencia.get(CLAVE_MAPA, null);
  }

  async obtener(): Promise<DatosMapaDelSitio> {
    const transferidos = this.datosTransferidos();
    if (transferidos !== null) {
      // Se consume una vez: recargar() en el cliente vuelve a pedir datos frescos.
      this.transferencia.remove(CLAVE_MAPA);
      return transferidos;
    }
    const [entradas, meses, terminos] = await Promise.all([
      this.entradas(),
      this.general.publicoObtenerMeses().then(mapMeses),
      this.terminos(),
    ]);
    const datos: DatosMapaDelSitio = { entradas, meses, terminos };
    if (this.esServidor) {
      this.transferencia.set(CLAVE_MAPA, datos);
    }
    return datos;
  }

  private entradas(): Promise<EntradaIndiceVista[]> {
    return todasLasPaginas(
      (pagina) => this.general.publicoListarIndice({ pagina }),
      (p) => p.resultados.map(mapEntradaIndice),
    );
  }

  private terminos(): Promise<TerminoVista[]> {
    return todasLasPaginas(
      (pagina) => this.glosario.publicoListarGlosario({ pagina }),
      (p, numero) => p.resultados.map((t) => mapTermino(t, numero)),
    );
  }
}
