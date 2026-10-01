/**
 * DATA: única puerta HTTP del acceso al panel (MOD-009, /api/v1/panel/auth/**). Usa el cliente
 * generado desde el contrato (Skill_Frontend §27.3). La sesión es una cookie HttpOnly de Django y el
 * CSRF lo añade Angular (withXsrfConfiguration): aquí nunca se leen ni se adjuntan credenciales.
 */
import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';

import { XSRF_COOKIE } from '../../../core/http/proveer-http';
import { PanelAuthService } from '../../../api/services/panel-auth.service';
import {
  ActivacionMfa,
  AutorizacionTratamiento,
  DecisionAutorizacion,
  SesionPanel,
} from '../domain/modelos';
import { anotarEspera } from './espera';
import { mapActivacionMfa, mapAutorizacion, mapSesion } from './panel.mapper';

/** Resultado de registrar la autorización: «No autorizo» cierra la sesión (204, sin cuerpo). */
export type ResultadoAutorizacion = SesionPanel | null;

@Injectable({ providedIn: 'root' })
export class PanelAuthRepositorio {
  private readonly api = inject(PanelAuthService);
  private readonly documento = inject(DOCUMENT);

  /**
   * La cookie `csrftoken` se pide una sola vez antes del login (RULE-029: es la única operación sin
   * sesión que fija cookie). Solo se comprueba si existe: su valor lo usa Angular, no este código.
   */
  async asegurarCsrf(): Promise<void> {
    const cookies = this.documento.cookie ?? '';
    const existe = cookies.split(';').some((c) => c.trim().startsWith(`${XSRF_COOKIE}=`));
    if (!existe) await conEspera(this.api.panelObtenerCsrf());
  }

  async iniciarSesion(usuario: string, contrasena: string, siguiente: string | null): Promise<SesionPanel> {
    const dto = await conEspera(
      this.api.panelIniciarSesion({ body: { usuario, contrasena, siguiente } }),
    );
    return mapSesion(dto);
  }

  async verificarMfa(codigo: string): Promise<SesionPanel> {
    return mapSesion(await conEspera(this.api.panelVerificarMfa({ body: { codigo } })));
  }

  async cerrarSesion(): Promise<void> {
    await this.api.panelCerrarSesion();
  }

  async sesion(): Promise<SesionPanel> {
    return mapSesion(await this.api.panelObtenerSesion());
  }

  async renovarSesion(): Promise<SesionPanel> {
    return mapSesion(await this.api.panelRenovarSesion());
  }

  async cambiarContrasena(actual: string, nueva: string): Promise<SesionPanel> {
    const dto = await this.api.panelCambiarContrasena({
      body: { contrasena_actual: actual, contrasena_nueva: nueva },
    });
    return mapSesion(dto);
  }

  async autorizacion(): Promise<AutorizacionTratamiento> {
    return mapAutorizacion(await this.api.panelObtenerAutorizacion());
  }

  async registrarAutorizacion(
    decision: DecisionAutorizacion,
    versionPolitica: string,
  ): Promise<ResultadoAutorizacion> {
    const respuesta = await this.api.panelRegistrarAutorizacion$Response({
      body: { decision, version_politica: versionPolitica },
    });
    return decision === 'AUTORIZO' && respuesta.body ? mapSesion(respuesta.body) : null;
  }

  async iniciarActivacionMfa(contrasena: string): Promise<ActivacionMfa> {
    const dto = await conEspera(this.api.panelIniciarActivacionMfa({ body: { contrasena } }));
    return mapActivacionMfa(dto);
  }

  async confirmarActivacionMfa(codigo: string): Promise<readonly string[]> {
    return (await this.api.panelConfirmarActivacionMfa({ body: { codigo } })).codigos;
  }

  async desactivarMfa(contrasena: string, codigo: string): Promise<void> {
    await this.api.panelDesactivarMfa({ body: { contrasena, codigo } });
  }

  async regenerarCodigos(codigo: string): Promise<readonly string[]> {
    return (await this.api.panelRegenerarCodigosRecuperacion({ body: { codigo } })).codigos;
  }
}

/** Conserva el tiempo de espera de un 429 (Retry-After) en el error (ver espera.ts). */
async function conEspera<T>(operacion: Promise<T>): Promise<T> {
  try {
    return await operacion;
  } catch (error: unknown) {
    throw anotarEspera(error);
  }
}
