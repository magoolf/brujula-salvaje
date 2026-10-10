import { Injectable, computed, inject, resource, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { defer, map } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelCuentasRepositorio } from '../data/panel-cuentas.repositorio';
import { nuevaClaveIdempotencia } from '../data/panel-medios.repositorio';
import {
  ACCIONES_CUENTA,
  AccionCuenta,
  CampoCuenta,
  ContextoCuenta,
  CuentaEquipo,
  DEFINICION_ACCION,
  DisponibilidadAccion,
  FormularioCuenta,
  disponibilidadAccion,
  entradaAlta,
  entradaCambio,
  idCuentaDeRuta,
  motivoRolBloqueado,
  paginaDesdeQuery,
  validarCuenta,
} from '../domain/cuentas';
import { SesionPanelStore } from './sesion-panel.store';

const CODIGO_PAGINA_FUERA = 'pagina_fuera_de_rango';

/**
 * STATE de Cuentas del equipo (SCR-044, FEAT-045, AC-105): listado paginado (`?pagina=`), solo
 * Administrador. El 403 de la feature lleva a SCR-048 (Skill_Frontend §12).
 */
@Injectable()
export class CuentasEquipoStore {
  private readonly repo = inject(PanelCuentasRepositorio);
  private readonly sesion = inject(SesionPanelStore);

  private readonly pagina = toSignal(
    inject(ActivatedRoute).queryParamMap.pipe(map((q) => paginaDesdeQuery(q.get('pagina')))),
    { requireSync: true },
  );
  private readonly recurso = resource({
    params: () => this.pagina(),
    loader: ({ params }) => this.repo.listar(params),
  });

  readonly listado = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly paginaFueraDeRango = computed(() => this.error()?.codigo === CODIGO_PAGINA_FUERA);
  /** Usuario de la sesión (para marcar «Tu cuenta»). */
  readonly usuarioSesion = computed(() => this.sesion.sesion()?.usuario ?? null);

  recargar(): void {
    this.recurso.reload();
  }
}

/** Contraseña temporal recién emitida (OneTimeSecret, AC-106): solo en memoria hasta «Ya la guardé». */
export interface SecretoTemporal {
  readonly usuario: string;
  readonly contrasena: string;
  /** Cuenta a la que pertenece (tras el alta se navega a su ficha al confirmar). */
  readonly cuentaId: number;
}

/**
 * STATE del Formulario de cuenta (SCR-045, FEAT-045, FLOW-015, RULE-015, AC-106/107/108): alta,
 * cambio de nombre y rol, y acciones del ciclo de vida. Las acciones que la regla impide se
 * ofrecen deshabilitadas con su motivo; el servidor sigue siendo la autoridad (409).
 */
@Injectable()
export class FormularioCuentaStore {
  private readonly repo = inject(PanelCuentasRepositorio);
  private readonly sesion = inject(SesionPanelStore);

  readonly id = toSignal(
    inject(ActivatedRoute).paramMap.pipe(map((p) => idCuentaDeRuta(p.get('id')))),
    { requireSync: true },
  );

  private readonly _secreto = signal<SecretoTemporal | null>(null);
  private readonly _avisoExito = signal<string | null>(null);
  private claveAlta = nuevaClaveIdempotencia();

  private readonly recursoCuenta = resource({
    params: () => {
      const id = this.id();
      return typeof id === 'number' ? id : undefined;
    },
    loader: ({ params }) => this.repo.obtener(params),
  });
  private readonly recursoAdmins = resource({
    params: () => (typeof this.id() === 'number' ? true : undefined),
    loader: () => this.repo.administradoresActivos(),
  });

  readonly esAlta = computed(() => this.id() === 'nuevo');
  readonly cuenta = computed<CuentaEquipo | null>(() =>
    this.recursoCuenta.hasValue() ? (this.recursoCuenta.value() ?? null) : null,
  );
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recursoCuenta.error();
    return error ? normalizarError(error) : null;
  });
  readonly noEncontrado = computed(() => this.id() === null || this.error()?.categoria === 'no_encontrado');
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly contexto = computed<ContextoCuenta>(() => {
    const cuenta = this.cuenta();
    const usuario = this.sesion.sesion()?.usuario ?? null;
    return {
      esPropia: cuenta !== null && usuario !== null && cuenta.usuario === usuario,
      adminsActivos: this.recursoAdmins.hasValue() ? (this.recursoAdmins.value() ?? null) : null,
    };
  });
  readonly acciones = computed<readonly (DisponibilidadAccion & { accion: AccionCuenta })[]>(() => {
    const cuenta = this.cuenta();
    if (cuenta === null) return [];
    return ACCIONES_CUENTA.map((accion) => ({ accion, ...disponibilidadAccion(accion, cuenta, this.contexto()) })).filter(
      (a) => a.visible,
    );
  });
  readonly motivoRol = computed(() => {
    const cuenta = this.cuenta();
    return cuenta === null ? null : motivoRolBloqueado(cuenta, this.contexto());
  });
  readonly secreto = this._secreto.asReadonly();
  readonly avisoExito = this._avisoExito.asReadonly();

  validar(formulario: FormularioCuenta): Partial<Record<CampoCuenta, string>> {
    return validarCuenta(formulario, this.esAlta());
  }

  /** Alta (FLOW-015): la contraseña temporal se muestra una sola vez (AC-106). */
  async crear(formulario: FormularioCuenta): Promise<ErrorApi | null> {
    this._avisoExito.set(null);
    const entrada = entradaAlta(formulario);
    const error = await ejecutar(defer(() => this.repo.crear(entrada, this.claveAlta)), (resultado) => {
      this._secreto.set({
        usuario: resultado.cuenta.usuario ?? resultado.cuenta.etiqueta,
        contrasena: resultado.contrasenaTemporal,
        cuentaId: resultado.cuenta.id,
      });
    });
    // Solo un fallo de red puede reintentarse con la misma clave (ALT-017); cualquier otra
    // respuesta cierra el intento.
    if (error?.categoria !== 'sin_conexion') this.claveAlta = nuevaClaveIdempotencia();
    return error;
  }

  /** Cambio de nombre visible o rol (solo lo que cambia). */
  async guardar(formulario: FormularioCuenta): Promise<ErrorApi | null> {
    const cuenta = this.cuenta();
    if (cuenta === null) return null;
    this._avisoExito.set(null);
    const cambio = entradaCambio(formulario, cuenta);
    if (cambio === null) {
      this._avisoExito.set('No hay cambios que guardar.');
      return null;
    }
    const error = await ejecutar(defer(() => this.repo.actualizar(cuenta.id, cambio)), (actualizada) => {
      this.recursoCuenta.value.set(actualizada);
      this.recursoAdmins.reload();
      this._avisoExito.set(
        cambio.rol !== undefined
          ? 'Se guardaron los cambios. Sus sesiones abiertas se cerraron por el cambio de rol.'
          : 'Se guardaron los cambios.',
      );
    });
    if (error?.categoria === 'conflicto') this.recargar();
    return error;
  }

  async ejecutarAccion(accion: AccionCuenta): Promise<ErrorApi | null> {
    const cuenta = this.cuenta();
    if (cuenta === null) return null;
    this._avisoExito.set(null);
    const error = await ejecutar(defer(() => this.repo.ejecutarAccion(cuenta.id, accion)), (resultado) => {
      this.recursoCuenta.value.set(resultado.cuenta);
      this.recursoAdmins.reload();
      if (resultado.contrasenaTemporal !== null) {
        this._secreto.set({
          usuario: resultado.cuenta.usuario ?? resultado.cuenta.etiqueta,
          contrasena: resultado.contrasenaTemporal,
          cuentaId: resultado.cuenta.id,
        });
      }
      this._avisoExito.set(DEFINICION_ACCION[accion].exito);
    });
    if (error?.categoria === 'conflicto') this.recargar();
    return error;
  }

  /** «Ya la guardé»: el secreto se descarta y no se puede volver a mostrar. */
  olvidarSecreto(): void {
    this._secreto.set(null);
  }

  recargar(): void {
    this.recursoCuenta.reload();
    this.recursoAdmins.reload();
  }
}
