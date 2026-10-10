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
 * Límite real del login (`panel-login`, 10/min por IP para /auth/csrf y /auth/login juntos,
 * DEC-AUTO-111): todos los workers y motores salen de la misma IP, así que el límite es compartido.
 * Por eso (TKT-022, F-02):
 * - las pruebas que no tratan del login entran por la API (page.request comparte las cookies con la
 *   página) y reintentan tras el Retry-After de un 429 `limite_tasa`;
 * - cada espera por el límite AMPLÍA el timeout del caso en lo que dura (no consume su presupuesto:
 *   el límite es del entorno compartido, no del caso);
 * - las pruebas a las que les basta «un editor con sesión» reutilizan una sesión por worker y origen
 *   (`entrarComoEditorCompartido`) en lugar de crear cuenta y entrar en cada caso.
 *
 * Requisitos del entorno (OBS-03):
 * - stack de Compose levantado con la semilla cargada
 *   (`docker compose -p <proyecto> exec backend python manage.py cargar_semilla`);
 * - si el stack se sirve por http (sin TLS, p. ej. http://127.0.0.1:<puerto>), el `.env` local debe
 *   tener `DJANGO_SESSION_COOKIE_SECURE=false` y `DJANGO_CSRF_COOKIE_SECURE=false`; si no, el
 *   navegador descarta las cookies `Secure` y ningún login se mantiene;
 * - las E2E del selector (SCR-041) requieren además `E2E_SELECTOR_URL` (ver
 *   panel-selector-medios.spec.ts).
 */
import { execFileSync } from 'node:child_process';
import { createHmac, randomBytes } from 'node:crypto';
import { resolve } from 'node:path';

import { APIResponse, Cookie, Page, errors, expect, test } from '@playwright/test';

export const PROYECTO_COMPOSE = process.env['E2E_COMPOSE_PROJECT'] ?? '';
const RAIZ_REPO = resolve(__dirname, '..', '..');
const API = '/api/v1/panel';

/**
 * `expect` de las suites de medios (TKT-022, QA ciclo 2): con 4 workers, los navegadores (sobre todo
 * Firefox) quedan sin CPU mientras pintan rejillas con decenas de miniaturas y suben imágenes; el
 * proxy registra respuestas de 15-30 ms que el navegador procesa varios segundos después. 15 s de
 * margen para las aserciones web-first evitan fallos por la carga del equipo, no por el producto.
 */
export const expectPanel = expect.configure({ timeout: 15_000 });

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

/**
 * Errores transitorios del motor de Docker (Docker Desktop responde 500 a la API mientras otros
 * proyectos se construyen o arrancan): el `exec` no llegó a ejecutarse y se repite.
 */
const ERROR_DOCKER_TRANSITORIO = /500 Internal Server Error|error during connect/;

function shellBackend(script: string): string {
  for (let intento = 1; ; intento++) {
    try {
      return execFileSync(
        'docker',
        ['compose', '-p', PROYECTO_COMPOSE, 'exec', '-T', 'backend', 'python', 'manage.py', 'shell'],
        { cwd: RAIZ_REPO, input: script, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] },
      );
    } catch (error) {
      if (intento >= 3 || !(error instanceof Error) || !ERROR_DOCKER_TRANSITORIO.test(error.message)) throw error;
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 3_000 * intento);
    }
  }
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
  const salida = shellBackend(script);
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
/**
 * Con 4 workers y 3 motores compitiendo por 10 peticiones/min, un caso puede perder varias ventanas
 * seguidas; como cada espera amplía el timeout, el tope solo evita un bucle infinito.
 */
const MAX_REINTENTOS_LIMITE = 20;

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
  const esperaMs = (Number.isFinite(segundos) ? segundos + 1 : 11) * 1000;
  ampliarTimeout(esperaMs);
  await new Promise((r) => setTimeout(r, esperaMs));
  return true;
}

/** Suma la espera impuesta por el límite (más un margen) al timeout del caso en curso. */
function ampliarTimeout(esperaMs: number): void {
  const info = test.info();
  if (info.timeout > 0) info.setTimeout(info.timeout + esperaMs + 2_000);
}

/**
 * Errores de transporte de una conexión keep-alive que el otro extremo cerró mientras estaba ociosa
 * (p. ej. tras esperar ~30 s el Retry-After del límite, el reenvío de puertos de Docker la cierra y
 * APIRequestContext la reutiliza: «socket hang up»). La petición no llegó al servidor: se repite.
 */
const ERROR_CONEXION_OCIOSA = /socket hang up|ECONNRESET|EPIPE/;

async function conReintentoRed<T>(peticion: () => Promise<T>): Promise<T> {
  for (let intento = 1; ; intento++) {
    try {
      return await peticion();
    } catch (error) {
      if (intento >= 3 || !(error instanceof Error) || !ERROR_CONEXION_OCIOSA.test(error.message)) throw error;
    }
  }
}

async function postConReintento(page: Page, ruta: string, datos: unknown): Promise<APIResponse> {
  for (let intento = 0; intento < MAX_REINTENTOS_LIMITE; intento++) {
    const token = await csrf(page);
    const respuesta = await conReintentoRed(() =>
      page.request.post(`${API}${ruta}`, { data: datos, headers: { 'X-CSRFToken': token } }),
    );
    if (!(await esperarSiLimite(respuesta))) return respuesta;
  }
  throw new Error(`Límite de tasa persistente en ${ruta}`);
}

export async function asegurarCsrf(page: Page): Promise<void> {
  if (await csrf(page)) return;
  for (let intento = 0; intento < MAX_REINTENTOS_LIMITE; intento++) {
    const respuesta = await conReintentoRed(() => page.request.get(`${API}/auth/csrf`));
    if (!(await esperarSiLimite(respuesta))) {
      expect(respuesta.status()).toBe(204);
      return;
    }
  }
  throw new Error('Límite de tasa persistente en /auth/csrf');
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

// ---------------------------------------------------------------------------------------------
// Sesión de editor compartida por worker (F-02)
// ---------------------------------------------------------------------------------------------
/**
 * Cookies de la sesión de editor de este worker. Las cookies son del host (no del puerto), así que
 * el stack y el `ng serve` del selector las comparten; si apuntan a backends distintos, la comprobación
 * de vigencia lo detecta y se vuelve a entrar.
 */
let sesionEditor: Cookie[] | null = null;

/** Margen mínimo de vigencia (inactividad) para reutilizar una sesión guardada. */
const VIGENCIA_MINIMA_MS = 5 * 60_000;

async function sesionVigente(page: Page, rol: Rol = 'EDITOR'): Promise<boolean> {
  const respuesta = await conReintentoRed(() => page.request.get(`${API}/auth/sesion`));
  if (respuesta.status() !== 200) return false;
  const estado = (await respuesta.json()) as { rol: string; paso_pendiente: string; expira_inactividad_en: string };
  return (
    estado.rol === rol &&
    estado.paso_pendiente === 'NINGUNO' &&
    Date.parse(estado.expira_inactividad_en) - Date.now() > VIGENCIA_MINIMA_MS
  );
}

/** Reintentos máximos de una lectura del panel limitada por el borde (cada uno espera Retry-After). */
const MAX_REINTENTOS_BORDE = 10;

/**
 * El limitador `por_ip` del borde (20 r/s, ráfaga 60; infra/proxy/nginx.conf) es por IP, y en las E2E
 * todos los workers salen de 127.0.0.1: 4 casos pintando a la vez rejillas de hasta 48 miniaturas
 * (TKT-OPS-023) agotan un cupo que en producción es de cada visitante. La interfaz responde bien
 * (alerta «Has superado el límite de peticiones» con «Reintentar»), pero el caso no prueba eso.
 * Para las lecturas del panel hechas por la página (GET bajo /api/v1/panel, salvo /auth/**, cuyo
 * límite propio sí se prueba), un 429 del borde (Retry-After: 1) se reintenta tras la espera, que
 * amplía el timeout del caso. Las escrituras y los 429 del backend llegan a la página sin tocar.
 */
async function absorberLimiteBorde(page: Page): Promise<void> {
  await page.route(/\/api\/v1\/panel\/(?!auth\/)/, async (ruta) => {
    if (ruta.request().method() !== 'GET') return ruta.fallback();
    for (let intento = 1; ; intento++) {
      const respuesta = await ruta.fetch().catch(() => null);
      if (!respuesta) return ruta.fallback();
      const deBorde = respuesta.status() === 429 && respuesta.headers()['retry-after'] === '1';
      if (!deBorde || intento > MAX_REINTENTOS_BORDE) return ruta.fulfill({ response: respuesta });
      const esperaMs = 1_000 * intento;
      try {
        ampliarTimeout(esperaMs);
      } catch {
        // El caso ya terminó (p. ej. una miniatura rezagada al cerrar la página): nada que ampliar.
      }
      await new Promise((r) => setTimeout(r, esperaMs));
      if (page.isClosed()) return;
    }
  });
}

/**
 * Deja la página con la sesión de un EDITOR activo sin MFA. Para las pruebas en las que la cuenta es
 * irrelevante: el worker crea una cuenta y entra una sola vez, y los casos siguientes reutilizan esas
 * cookies (si la sesión sigue vigente) en vez de gastar 2 peticiones del límite `panel-login` cada uno.
 * Las pruebas que dependen de la cuenta (rol, MFA, cambio de credencial, cierre de sesión…) siguen
 * usando crearCuenta + entrarPorApi.
 */
export async function entrarComoEditorCompartido(page: Page): Promise<void> {
  await absorberLimiteBorde(page);
  if (sesionEditor) {
    await page.context().addCookies(sesionEditor);
    if (await sesionVigente(page)) return;
    await page.context().clearCookies();
    sesionEditor = null;
  }
  await entrarPorApi(page, crearCuenta());
  sesionEditor = await page.context().cookies();
}

/** Sesión de Administrador de este worker (TKT-024) y su cuenta (para las reglas sobre la propia cuenta). */
let sesionAdmin: { cookies: Cookie[]; cuenta: CuentaPrueba } | null = null;

/**
 * Como `entrarComoEditorCompartido`, con un ADMINISTRADOR activo con MFA (obligatorio para el rol,
 * DEC-AUTO-037). Devuelve la cuenta con la que se entró.
 */
export async function entrarComoAdminCompartido(page: Page): Promise<CuentaPrueba> {
  await absorberLimiteBorde(page);
  if (sesionAdmin) {
    await page.context().addCookies(sesionAdmin.cookies);
    if (await sesionVigente(page, 'ADMINISTRADOR')) return sesionAdmin.cuenta;
    await page.context().clearCookies();
    sesionAdmin = null;
  }
  const cuenta = crearCuenta({ rol: 'ADMINISTRADOR', conMfa: true });
  await entrarPorApi(page, cuenta);
  sesionAdmin = { cookies: await page.context().cookies(), cuenta };
  return cuenta;
}

/**
 * Espera a que terminen las transiciones y animaciones finitas en curso (las infinitas, p. ej. un
 * indicador de carga, se ignoran). axe mide el color calculado: en mitad de una transición
 * (p. ej. el fondo de un botón que se habilita, --bs-motion-duration-fast) capturaría un fotograma
 * intermedio con contraste insuficiente que la persona nunca ve estable (TKT-022, F-01).
 */
export async function esperarTransiciones(page: Page): Promise<void> {
  await page.evaluate(async () => {
    // Dos fotogramas: el cambio de estado ya se ha pintado y sus transiciones están registradas.
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
    const finitas = document
      .getAnimations()
      .filter((a) => Number.isFinite(Number(a.effect?.getComputedTiming().endTime ?? Infinity)));
    await Promise.allSettled(finitas.map((a) => a.finished));
  });
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
  for (let intento = 0; intento < MAX_REINTENTOS_LIMITE; intento++) {
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

/** Tiempo máximo de una navegación de irA antes de reintentarla una vez. */
const TIMEOUT_NAVEGACION_MS = 30_000;

/**
 * Navega y espera a que la SPA esté hidratada (App marca html[data-app-lista]); esa marca, no el
 * evento `load`, es la condición de «página lista».
 *
 * QA TKT-022 ciclo 2: en Firefox, con un contexto nuevo, Playwright a veces no recibe los eventos de
 * la navegación aunque el servidor entregó el documento y todos sus recursos (traza: 200 en todo, la
 * SPA llegó a consultar /auth/sesion) y `goto` espera hasta agotar el caso. Por eso la navegación
 * tiene su propio límite y se reintenta UNA vez; un SSR realmente colgado sigue fallando.
 */
export async function irA(page: Page, ruta: string): Promise<void> {
  for (let intento = 1; ; intento++) {
    try {
      await page.goto(ruta, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_NAVEGACION_MS });
      break;
    } catch (error) {
      if (intento >= 2 || !(error instanceof errors.TimeoutError)) throw error;
    }
  }
  await page.locator('html[data-app-lista="true"]').waitFor({ state: 'attached' });
}
