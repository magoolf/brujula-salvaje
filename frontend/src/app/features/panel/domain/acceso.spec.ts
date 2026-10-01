import { ErrorApi } from '../../../core/http/error-api.model';
import {
  MENSAJE_CODIGO_INVALIDO,
  MENSAJE_CREDENCIALES,
  MENSAJE_MOTIVO,
  RUTA_AUTORIZACION,
  RUTA_CUENTA,
  RUTA_VERIFICACION_MFA,
  agruparClave,
  esCodigoTotpValido,
  esCodigoVerificacionValido,
  esPasoDeCuentaObligatorio,
  esReautenticacionFallida,
  mensajeFalloAcceso,
  motivoAcceso,
  normalizarCodigoMfa,
  rutaParaPaso,
  segundosDeEspera,
} from './acceso';

function error(parcial: Partial<ErrorApi>): ErrorApi {
  return {
    tipo: 'x',
    categoria: 'desconocido',
    codigo: null,
    mensaje: 'Mensaje del servidor.',
    campos: {},
    traceId: null,
    extra: {},
    ...parcial,
  };
}

describe('dominio de acceso (FLOW-010)', () => {
  it('AC_TKT010_01 sin pasos pendientes va al destino seguro o al Tablero (AC-115)', () => {
    expect(rutaParaPaso('NINGUNO', '/panel')).toBe('/panel');
    expect(rutaParaPaso('NINGUNO', '/panel/cuenta')).toBe('/panel/cuenta');
    expect(rutaParaPaso('NINGUNO', null)).toBe('/panel');
  });

  it('AC_TKT010_07 un siguiente externo o malicioso cae en el Tablero', () => {
    expect(rutaParaPaso('NINGUNO', 'https://evil.example/panel')).toBe('/panel');
    expect(rutaParaPaso('NINGUNO', '//evil.example')).toBe('/panel');
  });

  it('AC_TKT010_03/04/05 cada paso pendiente lleva a su pantalla (SCR-031 → 032 → 033)', () => {
    expect(rutaParaPaso('MFA', '/panel/x')).toBe(RUTA_VERIFICACION_MFA);
    expect(rutaParaPaso('CAMBIO_CREDENCIAL', null)).toBe(RUTA_CUENTA);
    expect(rutaParaPaso('CONFIGURAR_MFA', null)).toBe(RUTA_CUENTA);
    expect(rutaParaPaso('AUTORIZACION', null)).toBe(RUTA_AUTORIZACION);
  });

  it('AC_TKT010_04 el modo obligatorio de Mi cuenta aplica al cambio de contraseña y al MFA del Admin', () => {
    expect(esPasoDeCuentaObligatorio('CAMBIO_CREDENCIAL')).toBe(true);
    expect(esPasoDeCuentaObligatorio('CONFIGURAR_MFA')).toBe(true);
    expect(esPasoDeCuentaObligatorio('NINGUNO')).toBe(false);
    expect(esPasoDeCuentaObligatorio('AUTORIZACION')).toBe(false);
  });

  it('AC_TKT010_01 motivo de SCR-030: solo «cerrada» o «expirada»', () => {
    expect(motivoAcceso('cerrada')).toBe('cerrada');
    expect(motivoAcceso('expirada')).toBe('expirada');
    expect(motivoAcceso('<script>')).toBeNull();
    expect(motivoAcceso(null)).toBeNull();
    expect(MENSAJE_MOTIVO.cerrada).toBe('Cerraste sesión.');
  });

  it('AC_TKT010_03 normaliza y valida códigos TOTP y de recuperación', () => {
    expect(normalizarCodigoMfa(' 123 456 ')).toBe('123456');
    expect(normalizarCodigoMfa('ab12-cd34')).toBe('AB12-CD34');
    expect(esCodigoVerificacionValido('123456')).toBe(true);
    expect(esCodigoVerificacionValido('AB12-CD34')).toBe(true);
    expect(esCodigoVerificacionValido('12345')).toBe(false);
    expect(esCodigoVerificacionValido('AB12CD34')).toBe(false);
    expect(esCodigoTotpValido('123456')).toBe(true);
    expect(esCodigoTotpValido('AB12-CD34')).toBe(false);
  });

  it('AC_TKT010_06 la clave manual se agrupa de 4 en 4', () => {
    expect(agruparClave('ABCDEFGHIJKLMNOP')).toBe('ABCD EFGH IJKL MNOP');
    expect(agruparClave('ABCDEF')).toBe('ABCD EF');
    expect(agruparClave('')).toBe('');
  });
});

describe('mensajes de fallo de acceso (THREAT-018, ALT-012/013)', () => {
  it('AC_TKT010_02 credenciales inválidas → mensaje genérico (no revela si la cuenta existe)', () => {
    expect(mensajeFalloAcceso(error({ codigo: 'credenciales_invalidas', categoria: 'no_autenticado' }))).toBe(
      MENSAJE_CREDENCIALES,
    );
    expect(mensajeFalloAcceso(error({ categoria: 'validacion', codigo: 'validacion' }))).toBe(
      MENSAJE_CREDENCIALES,
    );
    expect(mensajeFalloAcceso(error({ categoria: 'no_autenticado', codigo: 'no_autenticado' }))).toBe(
      MENSAJE_CREDENCIALES,
    );
  });

  it('AC_TKT010_02 bloqueo temporal → mensaje genérico con el tiempo de espera (Retry-After)', () => {
    const bloqueo = error({
      codigo: 'acceso_bloqueado_temporalmente',
      categoria: 'limite_tasa',
      extra: { reintentar_en_segundos: 840 },
    });
    expect(mensajeFalloAcceso(bloqueo)).toBe(
      'Por seguridad, el acceso está bloqueado temporalmente. Inténtalo de nuevo en 14 minutos.',
    );
    expect(segundosDeEspera(bloqueo)).toBe(840);
    expect(
      mensajeFalloAcceso(error({ codigo: 'acceso_bloqueado_temporalmente', categoria: 'limite_tasa' })),
    ).toContain('en unos minutos');
  });

  it('AC_TKT010_02 límite de tasa por origen → mensaje con espera (1 minuto como mínimo)', () => {
    const limite = error({ codigo: 'limite_tasa', categoria: 'limite_tasa', extra: { reintentar_en_segundos: 20 } });
    expect(mensajeFalloAcceso(limite)).toBe('Demasiados intentos seguidos. Inténtalo de nuevo en 1 minuto.');
    expect(segundosDeEspera(error({ extra: { reintentar_en_segundos: 'x' } }))).toBeNull();
    expect(segundosDeEspera(error({ extra: { reintentar_en_segundos: 0 } }))).toBeNull();
  });

  it('AC_TKT010_03 código MFA inválido → «El código no es válido.»', () => {
    expect(mensajeFalloAcceso(error({ codigo: 'mfa_invalido', categoria: 'no_autenticado' }))).toBe(
      MENSAJE_CODIGO_INVALIDO,
    );
  });

  it('sin conexión o error del servidor → el mensaje normalizado', () => {
    expect(mensajeFalloAcceso(error({ categoria: 'sin_conexion', mensaje: 'Sin conexión.' }))).toBe('Sin conexión.');
  });

  it('AC_TKT010_06 DEC-AUTO-215: credenciales_invalidas en la reautenticación es error de campo', () => {
    expect(esReautenticacionFallida(error({ codigo: 'credenciales_invalidas' }))).toBe(true);
    expect(esReautenticacionFallida(error({ codigo: 'sesion_expirada' }))).toBe(false);
  });
});
