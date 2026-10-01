/**
 * Reglas puras del acceso al panel (FLOW-010, FEAT-029..032, RULE-017, THREAT-001/018).
 */
import { RUTA_ACCESO_PANEL, destinoTrasAcceso } from '../../../core/auth/destino-seguro';
import { ErrorApi } from '../../../core/http/error-api.model';
import { PasoPendiente } from './modelos';

export const RUTA_VERIFICACION_MFA = `${RUTA_ACCESO_PANEL}/verificacion`;
export const RUTA_AUTORIZACION = '/panel/autorizacion';
export const RUTA_CUENTA = '/panel/cuenta';
export const RUTA_ACCESO_DENEGADO = '/panel/acceso-denegado';

/**
 * Siguiente pantalla del FLOW-010 según el paso pendiente: SCR-031 (MFA) → SCR-032 en modo
 * obligatorio (cambio de contraseña o configurar MFA del Administrador) → SCR-033 (autorización)
 * → destino interno seguro o SCR-034 (AC-115).
 */
export function rutaParaPaso(paso: PasoPendiente, redireccion: string | null | undefined): string {
  switch (paso) {
    case 'MFA':
      return RUTA_VERIFICACION_MFA;
    case 'CAMBIO_CREDENCIAL':
    case 'CONFIGURAR_MFA':
      return RUTA_CUENTA;
    case 'AUTORIZACION':
      return RUTA_AUTORIZACION;
    case 'NINGUNO':
      return destinoTrasAcceso(redireccion);
  }
}

/** SCR-032 en modo obligatorio (no permite navegar a otras pantallas, BLUEPRINT SCR-032). */
export function esPasoDeCuentaObligatorio(paso: PasoPendiente): boolean {
  return paso === 'CAMBIO_CREDENCIAL' || paso === 'CONFIGURAR_MFA';
}

/** Mensaje de SCR-030 tras volver de un cierre o de una expiración (FLOW-010 paso 8, ALT-014). */
export type MotivoAcceso = 'cerrada' | 'expirada';

export function motivoAcceso(valor: string | null | undefined): MotivoAcceso | null {
  return valor === 'cerrada' || valor === 'expirada' ? valor : null;
}

export const MENSAJE_MOTIVO: Readonly<Record<MotivoAcceso, string>> = {
  cerrada: 'Cerraste sesión.',
  expirada: 'Tu sesión expiró por inactividad. Vuelve a entrar para continuar.',
};

/** Código TOTP de 6 dígitos o código de recuperación XXXX-XXXX (contrato MfaVerificacionEntrada). */
const PATRON_CODIGO_VERIFICACION = /^([0-9]{6}|[A-Z0-9]{4}-[A-Z0-9]{4})$/;
const PATRON_CODIGO_TOTP = /^[0-9]{6}$/;

/** Quita espacios y pasa a mayúsculas lo que la persona escribe o pega. */
export function normalizarCodigoMfa(texto: string): string {
  return texto.replace(/\s+/g, '').toUpperCase();
}

export function esCodigoVerificacionValido(codigo: string): boolean {
  return PATRON_CODIGO_VERIFICACION.test(codigo);
}

export function esCodigoTotpValido(codigo: string): boolean {
  return PATRON_CODIGO_TOTP.test(codigo);
}

/** Clave manual del TOTP agrupada de 4 en 4 para leerla y copiarla (HANDOFF SCR-032). */
export function agruparClave(clave: string): string {
  return (clave.match(/.{1,4}/g) ?? []).join(' ');
}

export const MENSAJE_CREDENCIALES = 'Usuario o contraseña incorrectos.';
export const MENSAJE_CODIGO_INVALIDO = 'El código no es válido.';
export const MENSAJE_CODIGO_FORMATO =
  'Escribe los 6 dígitos de tu aplicación o un código de recuperación (XXXX-XXXX).';
export const MENSAJE_TOTP_FORMATO = 'Escribe los 6 dígitos que muestra tu aplicación.';

/** Segundos de espera anotados por data/ desde la cabecera Retry-After (si llegó). */
export function segundosDeEspera(error: ErrorApi): number | null {
  const valor = error.extra['reintentar_en_segundos'];
  return typeof valor === 'number' && Number.isFinite(valor) && valor > 0 ? valor : null;
}

function esperaEnTexto(segundos: number | null): string {
  if (segundos === null) return 'en unos minutos';
  const minutos = Math.ceil(segundos / 60);
  return minutos <= 1 ? 'en 1 minuto' : `en ${minutos} minutos`;
}

/**
 * Mensaje de fallo del login y de la verificación (THREAT-018): nunca revela si la cuenta existe;
 * el bloqueo se explica de forma genérica con el tiempo de espera (ALT-012/013).
 */
export function mensajeFalloAcceso(error: ErrorApi): string {
  switch (error.codigo) {
    case 'acceso_bloqueado_temporalmente':
      return `Por seguridad, el acceso está bloqueado temporalmente. Inténtalo de nuevo ${esperaEnTexto(
        segundosDeEspera(error),
      )}.`;
    case 'limite_tasa':
      return `Demasiados intentos seguidos. Inténtalo de nuevo ${esperaEnTexto(
        segundosDeEspera(error),
      )}.`;
    case 'mfa_invalido':
      return MENSAJE_CODIGO_INVALIDO;
    case 'credenciales_invalidas':
      return MENSAJE_CREDENCIALES;
  }
  if (error.categoria === 'validacion' || error.categoria === 'no_autenticado') {
    return MENSAJE_CREDENCIALES;
  }
  return error.mensaje;
}

/** El 401 de reautenticación (DEC-AUTO-215) es un error del campo contraseña, no una expulsión. */
export function esReautenticacionFallida(error: ErrorApi): boolean {
  return error.codigo === 'credenciales_invalidas';
}
