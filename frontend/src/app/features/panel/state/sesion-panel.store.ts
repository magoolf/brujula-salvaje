import { Injectable, computed, inject, signal } from '@angular/core';
import { defer } from 'rxjs';

import { RUTA_ACCESO_PANEL } from '../../../core/auth/destino-seguro';
import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { rutaParaPaso } from '../domain/acceso';
import { DecisionAutorizacion, SesionPanel } from '../domain/modelos';
import { seccionesVisibles } from '../domain/secciones';

const CODIGO_CSRF_INVALIDO = 'csrf_invalido';

/**
 * STATE de la sesión del panel (STATE-004, FLOW-010). Única fuente del rol y del paso pendiente
 * para los guards, el armazón y las pantallas de acceso. Se comparte entre todas las áreas del
 * panel (TKT-022/023/024 la reutilizan). La sesión vive en una cookie HttpOnly del servidor: aquí
 * solo se guarda su estado público (usuario, rol, paso, expiraciones).
 * Todos los comandos pasan por `ejecutar()` y devuelven `ErrorApi | null` (Reglas 11 y 12).
 */
@Injectable({ providedIn: 'root' })
export class SesionPanelStore {
  private readonly repo = inject(PanelAuthRepositorio);

  private readonly _sesion = signal<SesionPanel | null>(null);
  private readonly _cargada = signal(false);

  readonly sesion = this._sesion.asReadonly();
  readonly cargada = this._cargada.asReadonly();
  readonly rol = computed(() => this._sesion()?.rol ?? null);
  readonly pasoPendiente = computed(() => this._sesion()?.pasoPendiente ?? null);
  readonly autenticada = computed(() => this._sesion()?.pasoPendiente === 'NINGUNO');
  /** Siguiente pantalla del FLOW-010 (SCR-030 si no hay sesión). */
  readonly rutaSiguiente = computed(() => {
    const sesion = this._sesion();
    return sesion === null
      ? RUTA_ACCESO_PANEL
      : rutaParaPaso(sesion.pasoPendiente, sesion.redireccion);
  });
  /** Navegación lateral según el rol (los accesos de Administrador se ocultan al Editor). */
  readonly secciones = computed(() => {
    const rol = this.rol();
    return rol === null ? [] : seccionesVisibles(rol);
  });

  /** Relee la sesión del servidor (no renueva la inactividad, AC-109). `null` = sin sesión. */
  async cargar(): Promise<SesionPanel | null> {
    const error = await ejecutar(
      defer(() => this.repo.sesion()),
      (sesion) => this._sesion.set(sesion),
    );
    if (error !== null) this._sesion.set(null);
    this._cargada.set(true);
    return this._sesion();
  }

  /** La primera vez lee la sesión; después usa la conocida (el 401 global corrige la caducidad). */
  async asegurar(): Promise<SesionPanel | null> {
    return this._cargada() ? this._sesion() : this.cargar();
  }

  async iniciarSesion(
    usuario: string,
    contrasena: string,
    siguiente: string | null,
  ): Promise<ErrorApi | null> {
    const intentar = async (): Promise<ErrorApi | null> => {
      const errorCsrf = await ejecutar(defer(() => this.repo.asegurarCsrf()));
      if (errorCsrf !== null) return errorCsrf;
      return ejecutar(
        defer(() => this.repo.iniciarSesion(usuario, contrasena, siguiente)),
        (sesion) => this.fijar(sesion),
      );
    };
    const error = await intentar();
    // QA TKT-010 FALLO-01: un único reintento si el token CSRF no llegó a tiempo. Solo ese código:
    // cualquier otro 403 (u otro error) se devuelve tal cual.
    return error?.codigo === CODIGO_CSRF_INVALIDO ? intentar() : error;
  }

  verificarMfa(codigo: string): Promise<ErrorApi | null> {
    return ejecutar(
      defer(() => this.repo.verificarMfa(codigo)),
      (sesion) => this.fijar(sesion),
    );
  }

  cambiarContrasena(actual: string, nueva: string): Promise<ErrorApi | null> {
    return ejecutar(
      defer(() => this.repo.cambiarContrasena(actual, nueva)),
      (sesion) => this.fijar(sesion),
    );
  }

  /** «No autorizo» cierra la sesión en el servidor (204): se olvida también aquí. */
  registrarAutorizacion(
    decision: DecisionAutorizacion,
    versionPolitica: string,
  ): Promise<ErrorApi | null> {
    return ejecutar(
      defer(() => this.repo.registrarAutorizacion(decision, versionPolitica)),
      (sesion) => (sesion === null ? this.olvidar() : this.fijar(sesion)),
    );
  }

  /** «Seguir conectado» (AC-109): renueva la inactividad, nunca más allá de las 12 h absolutas. */
  renovar(): Promise<ErrorApi | null> {
    return ejecutar(
      defer(() => this.repo.renovarSesion()),
      (sesion) => this.fijar(sesion),
    );
  }

  /**
   * Cierra la sesión en el servidor (FLOW-010 paso 8). Si ya no existía (401), el resultado es el
   * mismo para la persona: se olvida localmente y no se informa error.
   */
  async cerrarSesion(): Promise<ErrorApi | null> {
    const error = await ejecutar(defer(() => this.repo.cerrarSesion()));
    if (error !== null && error.categoria !== 'no_autenticado') return error;
    this.olvidar();
    return null;
  }

  private fijar(sesion: SesionPanel): void {
    this._sesion.set(sesion);
    this._cargada.set(true);
  }

  private olvidar(): void {
    this._sesion.set(null);
    this._cargada.set(true);
  }
}
