/**
 * DATA: traducción contrato ↔ dominio de las cuentas del equipo y de la auditoría (MOD-013,
 * TKT-024). Los DTO mueren aquí (Regla 04).
 */
import { Cuenta } from '../../../api/models/cuenta';
import { CuentaActualizacionEntrada } from '../../../api/models/cuenta-actualizacion-entrada';
import { CuentaConCredencialTemporal } from '../../../api/models/cuenta-con-credencial-temporal';
import { CuentaCreacionEntrada } from '../../../api/models/cuenta-creacion-entrada';
import { EventoAuditoria as EventoAuditoriaDto } from '../../../api/models/evento-auditoria';
import { PaginaCuenta } from '../../../api/models/pagina-cuenta';
import { PaginaEventoAuditoria } from '../../../api/models/pagina-evento-auditoria';
import { PanelListarAuditoria$Params } from '../../../api/fn/panel-auditoria/panel-listar-auditoria';
import { EventoAuditoria, FiltrosAuditoria, PaginaAuditoria, limitesFechas } from '../domain/auditoria';
import {
  CuentaConSecreto,
  CuentaEquipo,
  EntradaAltaCuenta,
  EntradaCambioCuenta,
  PaginaCuentas,
} from '../domain/cuentas';

const fecha = (valor: string | null | undefined): Date | null => (valor ? new Date(valor) : null);

export function mapCuenta(dto: Cuenta): CuentaEquipo {
  return {
    id: dto.id,
    usuario: dto.usuario ?? null,
    nombreVisible: dto.nombre_visible ?? null,
    etiqueta: dto.etiqueta,
    rol: dto.rol,
    estado: dto.estado,
    mfaActivo: dto.mfa_activo,
    debeCambiarCredencial: dto.debe_cambiar_credencial,
    ultimoAccesoEn: fecha(dto.ultimo_acceso_en),
    creadoEn: new Date(dto.creado_en),
    desactivadoEn: fecha(dto.desactivado_en),
  };
}

export function mapPaginaCuentas(dto: PaginaCuenta): PaginaCuentas {
  return {
    cuentas: dto.resultados.map(mapCuenta),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
  };
}

export function mapCuentaConSecreto(dto: CuentaConCredencialTemporal): CuentaConSecreto {
  return { cuenta: mapCuenta(dto.cuenta), contrasenaTemporal: dto.contrasena_temporal };
}

export function aAltaDto(e: EntradaAltaCuenta): CuentaCreacionEntrada {
  return { usuario: e.usuario, nombre_visible: e.nombreVisible, rol: e.rol };
}

export function aCambioDto(e: EntradaCambioCuenta): CuentaActualizacionEntrada {
  const dto: CuentaActualizacionEntrada = {};
  if (e.nombreVisible !== undefined) dto.nombre_visible = e.nombreVisible;
  if (e.rol !== undefined) dto.rol = e.rol;
  return dto;
}

export function mapEvento(dto: EventoAuditoriaDto): EventoAuditoria {
  return {
    id: dto.id,
    ocurridoEn: new Date(dto.ocurrido_en),
    actor: dto.actor.etiqueta,
    actorId: dto.actor.id,
    accion: dto.accion,
    resultado: dto.resultado,
    tipoEntidad: dto.tipo_entidad ?? null,
    entidadId: dto.entidad_id ?? null,
    entidadTitulo: dto.entidad_titulo ?? null,
    camposCambiados: dto.campos_cambiados ?? [],
    ipTruncada: dto.ip_truncada ?? null,
  };
}

export function mapPaginaAuditoria(dto: PaginaEventoAuditoria): PaginaAuditoria {
  return {
    eventos: dto.resultados.map(mapEvento),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
  };
}

/** Parámetros de la consulta (los filtros vacíos no se envían). */
export function paramsAuditoria(f: FiltrosAuditoria): PanelListarAuditoria$Params {
  const params: PanelListarAuditoria$Params = {};
  const { desde, hasta } = limitesFechas(f);
  if (desde !== null) params.desde = desde;
  if (hasta !== null) params.hasta = hasta;
  if (f.actor !== null) params.actor_id = f.actor;
  if (f.accion !== null) params.accion = f.accion;
  if (f.tipo !== null) params.tipo_entidad = f.tipo;
  if (f.pagina > 1) params.pagina = f.pagina;
  return params;
}
