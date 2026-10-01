/**
 * Soporte de las E2E del panel editorial (TKT-010).
 *
 * Cuentas de prueba: no existe un comando de gestión para crear cuentas del staff, así que se
 * crean con `docker compose exec backend python manage.py shell` usando el modelo y los helpers
 * del dominio del backend (set_password, mfa.nuevo_secreto/cifrar_secreto, política vigente), nunca
 * SQL directo. El script se envía por stdin: la contraseña (aleatoria, generada en cada ejecución,
 * nunca en el repositorio) no aparece en la línea de órdenes. Usuarios con sufijo aleatorio porque
 * las cuentas no se pueden borrar (CHG-DB-002).
 *
 * Requiere `E2E_COMPOSE_PROJECT` (proyecto de Compose del stack bajo prueba, p. ej. brujula-tkt010)
 * y `E2E_BASE_URL`. Sin ellos, las pruebas del panel se omiten con el motivo.
 *
 * Límite real del login (`panel-login`, 10/min por IP, DEC-AUTO-111): las pruebas que no tratan del
 * login entran por la API (page.request comparte las cookies con la página) y reintentan tras el
 * Retry-After de un 429 `limite_tasa`.
 */
import { execFileSync } from 'node:child_process';
import { createHmac, randomBytes } from 'node:crypto';
import { resolve } from 'node:path';

import { APIResponse, Page, expect, test } from '@playwright/test';

export const PROYECTO_COMPOSE = process.env['E2E_COMPOSE_PROJECT'] ?? '';
const RAIZ_REPO = resolve(__dirname, '..', '..');
const API = '/api/v1/panel';

export function omitirSinStack(): void {
  test.skip(
    PROYECTO_COMPOSE === '' || !process.env['E2E_BASE_URL'],
    'Requiere E2E_BASE_URL y E2E_COMPOSE_PROJECT (stack de Compose con backend real).',
  );
}

export type Rol = 'EDITOR' | 'ADMINISTRADOR';

export interface OpcionesCuenta {
  readonly rol?: Rol;
  readonly conMfa?: boolean;
  readonly debeCambiar?: boolean;
  readonly autorizada?: boolean;
}

export interface CuentaPrueba {
  readonly usuario: string;
  contrasena: string;
  secreto: string | null;
  readonly nombre: string;
  /** Último periodo TOTP usado (el servidor rechaza reutilizarlo). */
  ultimoPeriodo: number;
}

/** Crea una cuenta ACTIVA del staff en el backend del stack bajo prueba. */
export function crearCuenta(opciones: OpcionesCuenta = {}): CuentaPrueba {
  const rol = opciones.rol ?? 'EDITOR';
  const conMfa = opciones.conMfa ?? false;
  const sufijo = randomBytes(5).toString('hex');
  const usuario = `e2e.${rol === 'ADMINISTRADOR' ? 'admin' : 'editor'}.${sufijo}`;
  const contrasena = `e2e-${randomBytes(12).toString('base64url')}`;
  const nombre = `Prueba E2E ${sufijo}`;
  const script = `
import json
from django.utils import timezone
from apps.cuentas import mfa, selectors
from apps.cuentas.models import CuentaStaff, EstadoCuenta
autorizada = ${opciones.autorizada === false ? 'False' : 'True'}
cuenta = CuentaStaff(usuario=${JSON.stringify(usuario)}, nombre_visible=${JSON.stringify(nombre)},
    rol=${JSON.stringify(rol)}, debe_cambiar_credencial=${opciones.debeCambiar ? 'True' : 'False'})
cuenta.estado = EstadoCuenta.ACTIVA if autorizada else EstadoCuenta.PENDIENTE_ACTIVACION
if autorizada:
    cuenta.autorizacion_otorgada_en = timezone.now()
    cuenta.autorizacion_version_politica = selectors.politica_vigente().version
secreto = None
if ${conMfa ? 'True' : 'False'}:
    secreto = mfa.nuevo_secreto()
    cuenta.secreto_mfa = mfa.cifrar_secreto(secreto)
    cuenta.mfa_activo = True
cuenta.set_password(${JSON.stringify(contrasena)})
cuenta.save()
print("E2E_CUENTA=" + json.dumps({"secreto": secreto}))
`;
  const salida = execFileSync(
    'docker',
    ['compose', '-p', PROYECTO_COMPOSE, 'exec', '-T', 'backend', 'python', 'manage.py', 'shell'],
    { cwd: RAIZ_REPO, input: script, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] },
  );
  const linea = salida.split(/\r?\n/).find((l) => l.startsWith('E2E_CUENTA='));
  if (!linea) throw new Error('No se pudo crear la cuenta de prueba');
  const { secreto } = JSON.parse(linea.slice('E2E_CUENTA='.length)) as { secreto: string | null };
  return { usuario, contrasena, secreto, nombre, ultimoPeriodo: 0 };
}

// ---------------------------------------------------------------------------------------------
// TOTP (RFC 6238: HMAC-SHA1, 6 dígitos, 30 s), igual que apps/cuentas/mfa.py
// ---------------------------------------------------------------------------------------------
function base32(texto: string): Buffer {
  const alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const c of texto.replace(/=+$/, '').toUpperCase()) {
    bits += alfabeto.indexOf(c).toString(2).padStart(5, '0');
  }
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}

export function codigoTotp(secreto: string, periodo: number): string {
  const contador = Buffer.alloc(8);
  contador.writeBigUInt64BE(BigInt(periodo));
  const digest = createHmac('sha1', base32(secreto)).update(contador).digest();
  const desplazamiento = digest[digest.length - 1] & 0x0f;
  const numero = digest.readUInt32BE(desplazamiento) & 0x7fffffff;
  return (numero % 1_000_000).toString().padStart(6, '0');
}

/**
 * Código aún no usado: el servidor acepta el periodo actual ±1 y rechaza repetir un periodo, así
 * que se usa el siguiente al último consumido (esperando solo si ya se gastó el actual + 1).
 */
export async function siguienteCodigo(cuenta: CuentaPrueba, secreto = cuenta.secreto): Promise<string> {
  if (!secreto) throw new Error('La cuenta no tiene secreto TOTP');
  for (;;) {
    const actual = Math.floor(Date.now() / 30_000);
    const periodo = Math.max(actual, cuenta.ultimoPeriodo + 1);
    if (periodo <= actual + 1) {
      cuenta.ultimoPeriodo = periodo;
      return codigoTotp(secreto, periodo);
    }
    await new Promise((r) => setTimeout(r, 2_000));
  }
}

// ---------------------------------------------------------------------------------------------
// Entrada por la API con reintento ante el límite de tasa
// ---------------------------------------------------------------------------------------------
async function csrf(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  return cookies.find((c) => c.name === 'csrftoken')?.value ?? '';
}

/** Respuesta de la API o de la página (misma forma para lo que se consulta aquí). */
interface RespuestaHttp {
  status(): number;
  json(): Promise<unknown>;
  headers(): Record<string, string>;
}

async function esperarSiLimite(respuesta: RespuestaHttp): Promise<boolean> {
  if (respuesta.status() !== 429) return false;
  const cuerpo = (await respuesta.json().catch(() => ({}))) as { code?: string };
  if (cuerpo.code !== 'limite_tasa') return false;
  const segundos = Number(respuesta.headers()['retry-after'] ?? '10');
  await new Promise((r) => setTimeout(r, (Number.isFinite(segundos) ? segundos + 1 : 11) * 1000));
  return true;
}

async function postConReintento(page: Page, ruta: string, datos: unknown): Promise<APIResponse> {
  for (let intento = 0; intento < 8; intento++) {
    const respuesta = await page.request.post(`${API}${ruta}`, {
      data: datos,
      headers: { 'X-CSRFToken': await csrf(page) },
    });
    if (!(await esperarSiLimite(respuesta))) return respuesta;
  }
  throw new Error(`Límite de tasa persistente en ${ruta}`);
}

export async function asegurarCsrf(page: Page): Promise<void> {
  if (await csrf(page)) return;
  for (let intento = 0; intento < 8; intento++) {
    const respuesta = await page.request.get(`${API}/auth/csrf`);
    if (!(await esperarSiLimite(respuesta))) {
      expect(respuesta.status()).toBe(204);
      return;
    }
  }
}

/** Intento de login por la API (sin completar pasos): devuelve la respuesta. */
export async function loginApi(page: Page, usuario: string, contrasena: string): Promise<APIResponse> {
  await asegurarCsrf(page);
  return postConReintento(page, '/auth/login', { usuario, contrasena });
}

/** Login completo por la API (con el segundo factor si la cuenta lo tiene). */
export async function entrarPorApi(page: Page, cuenta: CuentaPrueba): Promise<void> {
  const login = await loginApi(page, cuenta.usuario, cuenta.contrasena);
  expect(login.status(), await login.text()).toBe(200);
  const estado = (await login.json()) as { paso_pendiente: string };
  if (estado.paso_pendiente === 'MFA') {
    const verificar = await postConReintento(page, '/auth/mfa/verificar', {
      codigo: await siguienteCodigo(cuenta),
    });
    expect(verificar.status(), await verificar.text()).toBe(200);
  }
}

/**
 * Login por la interfaz (SCR-030). Si el servidor aplica el límite por origen (no el bloqueo de la
 * cuenta), espera y reintenta: el límite es del entorno de prueba compartido, no del caso.
 */
export async function entrarPorUi(
  page: Page,
  usuario: string,
  contrasena: string,
  envio: 'clic' | 'enter' = 'clic',
): Promise<void> {
  for (let intento = 0; intento < 8; intento++) {
    await page.getByTestId('acceso-usuario').fill(usuario);
    await page.getByTestId('acceso-contrasena').fill(contrasena);
    const login = page
      .waitForResponse((r) => r.url().endsWith(`${API}/auth/login`))
      .catch(() => null);
    const csrfLimitado = page
      .waitForResponse((r) => r.url().endsWith(`${API}/auth/csrf`) && r.status() === 429)
      .catch(() => null);
    if (envio === 'enter') await page.getByTestId('acceso-contrasena').press('Enter');
    else await page.getByTestId('acceso-entrar').click();
    const respuesta = await Promise.race([login, csrfLimitado]);
    if (respuesta === null || !(await esperarSiLimite(respuesta))) return;
  }
  throw new Error('Límite de tasa persistente en el login por la interfaz');
}

/** Espera a que la SPA esté hidratada (App marca html[data-app-lista]). */
export async function irA(page: Page, ruta: string): Promise<void> {
  await page.goto(ruta);
  await page.locator('html[data-app-lista="true"]').waitFor({ state: 'attached' });
}
