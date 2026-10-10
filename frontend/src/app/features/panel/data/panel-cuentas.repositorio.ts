/**
 * DATA: única puerta HTTP de las cuentas del equipo y de la auditoría (MOD-013, TKT-024):
 * /api/v1/panel/cuentas/** y /api/v1/panel/auditoria (solo Administrador). Cliente generado desde
 * el contrato (Skill_Frontend §27.3). La contraseña temporal solo viaja en la respuesta y no se
 * guarda en ningún sitio de esta capa (AC-106).
 */
import { Injectable, inject } from '@angular/core';

import { PanelAuditoriaService } from '../../../api/services/panel-auditoria.service';
import { PanelCuentasService } from '../../../api/services/panel-cuentas.service';
import { FiltrosAuditoria, OpcionActor, PaginaAuditoria } from '../domain/auditoria';
import {
  AccionCuenta,
  CuentaConSecreto,
  CuentaEquipo,
  EntradaAltaCuenta,
  EntradaCambioCuenta,
  PaginaCuentas,
} from '../domain/cuentas';
import {
  aAltaDto,
  aCambioDto,
  mapCuenta,
  mapCuentaConSecreto,
  mapPaginaAuditoria,
  mapPaginaCuentas,
  paramsAuditoria,
} from './cuentas.mapper';

/** Páginas máximas que se leen para el filtro de actores (50 por página, contrato). */
const PAGINAS_ACTORES = 10;

/** Resultado de una acción: la cuenta y, si la operación la emite, la contraseña temporal. */
export interface ResultadoAccionCuenta {
  readonly cuenta: CuentaEquipo;
  readonly contrasenaTemporal: string | null;
}

@Injectable({ providedIn: 'root' })
export class PanelCuentasRepositorio {
  private readonly api = inject(PanelCuentasService);
  private readonly auditoriaApi = inject(PanelAuditoriaService);

  async listar(pagina: number): Promise<PaginaCuentas> {
    return mapPaginaCuentas(await this.api.panelListarCuentas(pagina > 1 ? { pagina } : {}));
  }

  /** Número de Administradores ACTIVOS (RULE-015: no se ofrece desactivar ni degradar al último). */
  async administradoresActivos(): Promise<number> {
    const pagina = await this.api.panelListarCuentas({ estado: 'ACTIVA', rol: 'ADMINISTRADOR' });
    return pagina.total;
  }

  async obtener(id: number): Promise<CuentaEquipo> {
    return mapCuenta(await this.api.panelObtenerCuenta({ id }));
  }

  async crear(entrada: EntradaAltaCuenta, claveIdempotencia: string): Promise<CuentaConSecreto> {
    return mapCuentaConSecreto(
      await this.api.panelCrearCuenta({ 'Idempotency-Key': claveIdempotencia, body: aAltaDto(entrada) }),
    );
  }

  async actualizar(id: number, entrada: EntradaCambioCuenta): Promise<CuentaEquipo> {
    return mapCuenta(await this.api.panelActualizarCuenta({ id, body: aCambioDto(entrada) }));
  }

  async ejecutarAccion(id: number, accion: AccionCuenta): Promise<ResultadoAccionCuenta> {
    switch (accion) {
      case 'restablecerContrasena':
        return this.conSecreto(this.api.panelRestablecerContrasenaCuenta({ id }));
      case 'restablecerMfa':
        return this.conSecreto(this.api.panelRestablecerMfaCuenta({ id }));
      case 'reactivar':
        return this.conSecreto(this.api.panelReactivarCuenta({ id }));
      case 'desactivar':
        return { cuenta: mapCuenta(await this.api.panelDesactivarCuenta({ id })), contrasenaTemporal: null };
      case 'anonimizar':
        return { cuenta: mapCuenta(await this.api.panelAnonimizarCuenta({ id })), contrasenaTemporal: null };
    }
  }

  private async conSecreto(
    peticion: Promise<Parameters<typeof mapCuentaConSecreto>[0]>,
  ): Promise<ResultadoAccionCuenta> {
    const { cuenta, contrasenaTemporal } = mapCuentaConSecreto(await peticion);
    return { cuenta, contrasenaTemporal };
  }

  // ---------------------------------------------------------------- auditoría (SCR-046)
  async auditoria(filtros: FiltrosAuditoria): Promise<PaginaAuditoria> {
    return mapPaginaAuditoria(await this.auditoriaApi.panelListarAuditoria(paramsAuditoria(filtros)));
  }

  /** Cuentas del equipo como opciones del filtro «Actor» (incluidas las anonimizadas: seudónimo). */
  async actores(): Promise<readonly OpcionActor[]> {
    const actores: OpcionActor[] = [];
    for (let pagina = 1; pagina <= PAGINAS_ACTORES; pagina++) {
      const dto = await this.api.panelListarCuentas(pagina > 1 ? { pagina } : {});
      actores.push(...dto.resultados.map((c) => ({ id: c.id, etiqueta: c.etiqueta })));
      if (dto.siguiente === null || pagina >= dto.total_paginas) break;
    }
    return actores.sort((a, b) => a.etiqueta.localeCompare(b.etiqueta, 'es'));
  }
}
