/**
 * Cuentas del equipo (SCR-044/045, FEAT-045, FLOW-015, RULE-015, AC-106/107/108, TKT-024): ciclo de
 * vida de las cuentas del staff (alta con contraseña temporal, cambio de rol, restablecimientos,
 * desactivación, reactivación y anonimización). Solo para el Administrador. El servidor es la
 * autoridad (RULE-015 → 409); estas reglas solo evitan ofrecer acciones que se rechazarían.
 * Puro: sin Angular ni RxJS (Regla 08).
 */
import { ErroresTraducidos, erroresPorCampo, longitudTexto } from './errores-formulario';
import { RolPanel } from './modelos';

export type EstadoCuenta =
  | 'PENDIENTE_ACTIVACION'
  | 'ACTIVA'
  | 'BLOQUEADA_TEMPORAL'
  | 'DESACTIVADA'
  | 'ANONIMIZADA';

export interface CuentaEquipo {
  readonly id: number;
  /** null si está ANONIMIZADA. */
  readonly usuario: string | null;
  readonly nombreVisible: string | null;
  /** Usuario o seudónimo (siempre presente). */
  readonly etiqueta: string;
  readonly rol: RolPanel;
  readonly estado: EstadoCuenta;
  readonly mfaActivo: boolean;
  readonly debeCambiarCredencial: boolean;
  readonly ultimoAccesoEn: Date | null;
  readonly creadoEn: Date;
  readonly desactivadoEn: Date | null;
}

export interface PaginaCuentas {
  readonly cuentas: readonly CuentaEquipo[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
}

/** Respuesta de las operaciones que emiten una contraseña temporal (se muestra una sola vez). */
export interface CuentaConSecreto {
  readonly cuenta: CuentaEquipo;
  readonly contrasenaTemporal: string;
}

export const ETIQUETA_ESTADO_CUENTA: Readonly<Record<EstadoCuenta, string>> = {
  PENDIENTE_ACTIVACION: 'Pendiente de activación',
  ACTIVA: 'Activa',
  BLOQUEADA_TEMPORAL: 'Bloqueada temporalmente',
  DESACTIVADA: 'Desactivada',
  ANONIMIZADA: 'Anonimizada',
};

export type VarianteEstadoCuenta = 'publicado' | 'pendiente' | 'rechazado' | 'retirado' | 'neutral';

export function varianteEstadoCuenta(estado: EstadoCuenta): VarianteEstadoCuenta {
  switch (estado) {
    case 'ACTIVA':
      return 'publicado';
    case 'PENDIENTE_ACTIVACION':
      return 'pendiente';
    case 'BLOQUEADA_TEMPORAL':
      return 'rechazado';
    case 'DESACTIVADA':
      return 'retirado';
    case 'ANONIMIZADA':
      return 'neutral';
  }
}

export const ROLES: readonly RolPanel[] = ['EDITOR', 'ADMINISTRADOR'];

/** Cuenta que aún no completó su primer acceso (tiene una contraseña temporal vigente). */
export function pendienteDeActivacion(cuenta: CuentaEquipo): boolean {
  return cuenta.estado === 'PENDIENTE_ACTIVACION';
}

/**
 * Aviso en la ficha de una cuenta pendiente (QA TKT-024 FALLO-01): si la contraseña temporal se
 * perdió (p. ej. al recargar), no se puede volver a mostrar y hay que emitir otra.
 */
export const AVISO_PENDIENTE_ACTIVACION =
  'Esta cuenta aún no completó su primer acceso. La contraseña temporal solo se mostró una vez: si no la guardaste, emite otra con «Restablecer contraseña».';

export const TEXTO_SALIDA_SECRETO =
  'La contraseña temporal se muestra solo esta vez. Si sales sin guardarla, no podrás volver a verla y tendrás que emitir otra con «Restablecer contraseña».';

export function esAnonimizada(cuenta: CuentaEquipo): boolean {
  return cuenta.estado === 'ANONIMIZADA';
}

// ---------------------------------------------------------------------------------------------
// Acciones de la cuenta (FLOW-015) y RULE-015
// ---------------------------------------------------------------------------------------------
export type AccionCuenta = 'restablecerContrasena' | 'restablecerMfa' | 'desactivar' | 'reactivar' | 'anonimizar';

export const ACCIONES_CUENTA: readonly AccionCuenta[] = [
  'restablecerContrasena',
  'restablecerMfa',
  'desactivar',
  'reactivar',
  'anonimizar',
];

export interface DefinicionAccion {
  readonly etiqueta: string;
  /** Efecto que se describe antes de confirmar (HANDOFF SCR-045, aria). */
  readonly efecto: string;
  readonly confirmar: string;
  readonly destructiva: boolean;
  /** La respuesta incluye una contraseña temporal (OneTimeSecret). */
  readonly emiteSecreto: boolean;
  /** Aviso tras completarse. */
  readonly exito: string;
}

export const DEFINICION_ACCION: Readonly<Record<AccionCuenta, DefinicionAccion>> = {
  restablecerContrasena: {
    etiqueta: 'Restablecer contraseña',
    efecto:
      'Se generará una contraseña temporal nueva y se cerrarán todas sus sesiones. Deberá cambiarla en su próximo acceso.',
    confirmar: 'Restablecer contraseña',
    destructiva: true,
    emiteSecreto: true,
    exito: 'Se restableció la contraseña y se cerraron sus sesiones.',
  },
  restablecerMfa: {
    etiqueta: 'Restablecer verificación en dos pasos',
    efecto:
      'Se eliminará su verificación en dos pasos, se generará una contraseña temporal nueva y se cerrarán todas sus sesiones.',
    confirmar: 'Restablecer verificación',
    destructiva: true,
    emiteSecreto: true,
    exito: 'Se restableció la verificación en dos pasos y se cerraron sus sesiones.',
  },
  desactivar: {
    etiqueta: 'Desactivar',
    efecto: 'Se cerrarán todas sus sesiones de inmediato. Sus datos se anonimizarán en un máximo de 30 días.',
    confirmar: 'Desactivar cuenta',
    destructiva: true,
    emiteSecreto: false,
    exito: 'Cuenta desactivada. Sus sesiones se cerraron.',
  },
  reactivar: {
    etiqueta: 'Reactivar',
    efecto:
      'La cuenta volverá a quedar pendiente de activación con una contraseña temporal nueva que deberá cambiar en su próximo acceso.',
    confirmar: 'Reactivar cuenta',
    destructiva: false,
    emiteSecreto: true,
    exito: 'Cuenta reactivada: queda pendiente de activación.',
  },
  anonimizar: {
    etiqueta: 'Anonimizar ahora',
    efecto:
      'Se eliminarán de forma irreversible su usuario, su nombre, sus credenciales y su verificación en dos pasos. La auditoría conservará un seudónimo.',
    confirmar: 'Anonimizar cuenta',
    destructiva: true,
    emiteSecreto: false,
    exito: 'Cuenta anonimizada.',
  },
};

export const MENSAJE_ULTIMO_ADMIN = 'No puedes desactivar ni cambiar el rol del último administrador activo.';
export const MENSAJE_PROPIA_DESACTIVAR = 'No puedes desactivar tu propia cuenta.';
export const MENSAJE_PROPIO_ROL = 'No puedes cambiar tu propio rol.';
export const MENSAJE_PROPIA_RESTABLECER = 'Tu contraseña y tu verificación en dos pasos se cambian desde Mi cuenta.';

/** Contexto para decidir qué acciones se ofrecen. */
export interface ContextoCuenta {
  /** La cuenta es la de la sesión actual. */
  readonly esPropia: boolean;
  /** Administradores ACTIVOS (null si no se pudo saber: el servidor decide). */
  readonly adminsActivos: number | null;
}

export interface DisponibilidadAccion {
  readonly visible: boolean;
  /** Motivo por el que está deshabilitada (null = habilitada). */
  readonly motivo: string | null;
}

const VIVAS: readonly EstadoCuenta[] = ['PENDIENTE_ACTIVACION', 'ACTIVA', 'BLOQUEADA_TEMPORAL'];

/** RULE-015: la cuenta es el único Administrador activo. */
export function esUltimoAdmin(cuenta: CuentaEquipo, adminsActivos: number | null): boolean {
  return (
    cuenta.rol === 'ADMINISTRADOR' && cuenta.estado === 'ACTIVA' && adminsActivos !== null && adminsActivos <= 1
  );
}

export function disponibilidadAccion(
  accion: AccionCuenta,
  cuenta: CuentaEquipo,
  contexto: ContextoCuenta,
): DisponibilidadAccion {
  const viva = VIVAS.includes(cuenta.estado);
  switch (accion) {
    case 'restablecerContrasena':
      return { visible: viva, motivo: contexto.esPropia ? MENSAJE_PROPIA_RESTABLECER : null };
    case 'restablecerMfa':
      return { visible: viva && cuenta.mfaActivo, motivo: contexto.esPropia ? MENSAJE_PROPIA_RESTABLECER : null };
    case 'desactivar': {
      let motivo: string | null = null;
      if (contexto.esPropia) motivo = MENSAJE_PROPIA_DESACTIVAR;
      else if (esUltimoAdmin(cuenta, contexto.adminsActivos)) motivo = MENSAJE_ULTIMO_ADMIN;
      return { visible: viva, motivo };
    }
    case 'reactivar':
    case 'anonimizar':
      return { visible: cuenta.estado === 'DESACTIVADA', motivo: null };
  }
}

/** Motivo por el que no se puede cambiar el rol (null = se puede). */
export function motivoRolBloqueado(cuenta: CuentaEquipo, contexto: ContextoCuenta): string | null {
  if (esAnonimizada(cuenta) || cuenta.estado === 'DESACTIVADA') return 'El rol de una cuenta desactivada no se puede cambiar.';
  if (contexto.esPropia) return MENSAJE_PROPIO_ROL;
  if (esUltimoAdmin(cuenta, contexto.adminsActivos)) return MENSAJE_ULTIMO_ADMIN;
  return null;
}

/** Mensaje de un 409 de las operaciones de cuenta (código del contrato → texto de la UI). */
export function mensajeConflictoCuenta(codigo: string | null, mensaje: string, accion: AccionCuenta | 'rol'): string {
  if (codigo === 'ultimo_administrador') return MENSAJE_ULTIMO_ADMIN;
  if (codigo === 'operacion_sobre_si_mismo') {
    return accion === 'rol' ? MENSAJE_PROPIO_ROL : MENSAJE_PROPIA_DESACTIVAR;
  }
  return mensaje;
}

// ---------------------------------------------------------------------------------------------
// Formulario (alta y datos)
// ---------------------------------------------------------------------------------------------
export interface FormularioCuenta {
  readonly usuario: string;
  readonly nombreVisible: string;
  readonly rol: RolPanel | '';
}

export type CampoCuenta = keyof FormularioCuenta;

export const CAMPOS_CUENTA: readonly CampoCuenta[] = ['usuario', 'nombreVisible', 'rol'];

export const FORMULARIO_CUENTA_VACIO: FormularioCuenta = { usuario: '', nombreVisible: '', rol: '' };

export const LIMITE_NOMBRE_VISIBLE = 100;

export const AYUDA_USUARIO = 'Entre 3 y 40 caracteres: minúsculas, números, puntos, guiones y guiones bajos. No se puede cambiar después.';

const PATRON_USUARIO = /^[a-z0-9._-]{3,40}$/;

export function formularioDesdeCuenta(cuenta: CuentaEquipo): FormularioCuenta {
  return { usuario: cuenta.usuario ?? '', nombreVisible: cuenta.nombreVisible ?? '', rol: cuenta.rol };
}

export function validarCuenta(f: FormularioCuenta, esAlta: boolean): Partial<Record<CampoCuenta, string>> {
  const errores: Partial<Record<CampoCuenta, string>> = {};
  if (esAlta) {
    const usuario = f.usuario.trim();
    if (usuario === '') errores.usuario = 'Escribe el usuario.';
    else if (!PATRON_USUARIO.test(usuario)) errores.usuario = AYUDA_USUARIO.replace(' No se puede cambiar después.', '');
  }
  const nombre = f.nombreVisible.trim();
  if (nombre === '') errores.nombreVisible = 'Escribe el nombre visible.';
  else if (longitudTexto(nombre) > LIMITE_NOMBRE_VISIBLE) {
    errores.nombreVisible = `Usa como máximo ${LIMITE_NOMBRE_VISIBLE} caracteres.`;
  }
  if (f.rol === '') errores.rol = 'Elige un rol.';
  return errores;
}

export interface EntradaAltaCuenta {
  readonly usuario: string;
  readonly nombreVisible: string;
  readonly rol: RolPanel;
}

export interface EntradaCambioCuenta {
  readonly nombreVisible?: string;
  readonly rol?: RolPanel;
}

export function entradaAlta(f: FormularioCuenta): EntradaAltaCuenta {
  return { usuario: f.usuario.trim(), nombreVisible: f.nombreVisible.trim(), rol: f.rol === '' ? 'EDITOR' : f.rol };
}

/** Solo los campos que cambian (CuentaActualizacionEntrada, minProperties: 1). null = nada que guardar. */
export function entradaCambio(f: FormularioCuenta, cuenta: CuentaEquipo): EntradaCambioCuenta | null {
  const cambio: { nombreVisible?: string; rol?: RolPanel } = {};
  const nombre = f.nombreVisible.trim();
  if (nombre !== (cuenta.nombreVisible ?? '')) cambio.nombreVisible = nombre;
  if (f.rol !== '' && f.rol !== cuenta.rol) cambio.rol = f.rol;
  return Object.keys(cambio).length === 0 ? null : cambio;
}

const CAMPO_API_CUENTA: Readonly<Record<CampoCuenta, string>> = {
  usuario: 'usuario',
  nombreVisible: 'nombre_visible',
  rol: 'rol',
};

export function erroresCuenta(
  campos: Readonly<Record<string, readonly string[]>>,
  mensaje: string,
): ErroresTraducidos<CampoCuenta> {
  return erroresPorCampo(CAMPO_API_CUENTA, campos, mensaje);
}

/** Id de la ruta `/panel/usuarios/:id` (`nuevo` = alta; cualquier otro valor no numérico = 404). */
export function idCuentaDeRuta(valor: string | null): number | 'nuevo' | null {
  if (valor === 'nuevo') return 'nuevo';
  if (valor === null || !/^[1-9]\d{0,17}$/.test(valor)) return null;
  const id = Number(valor);
  return Number.isSafeInteger(id) ? id : null;
}

/** Página `?pagina=` (entero ≥ 1; cualquier otro valor → 1). */
export function paginaDesdeQuery(valor: string | null | undefined): number {
  if (valor === null || valor === undefined || !/^[1-9]\d{0,5}$/.test(valor)) return 1;
  return Number(valor);
}
