import { defineConfig, devices } from '@playwright/test';

/**
 * E2E (Skill_Frontend §27.6, Skill_QA): Playwright + axe sobre el SSR real.
 * - `E2E_BASE_URL` apunta a un entorno ya levantado (p. ej. el proxy de Compose:
 *   http://127.0.0.1:8080). Si no se define, se construye la app y se arranca el servidor SSR
 *   local en 127.0.0.1:4300 (sin proxy: las pruebas de CSP simulan la cabecera x-csp-nonce).
 */
const PUERTO = Number(process.env['E2E_PORT'] ?? 4300);
const URL_BASE = process.env['E2E_BASE_URL'] ?? `http://127.0.0.1:${PUERTO}`;
const EN_CI = Boolean(process.env['CI']);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: EN_CI,
  retries: EN_CI ? 1 : 0,
  workers: EN_CI ? 2 : 4,
  reporter: EN_CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: URL_BASE,
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1280, height: 800 } },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'], viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: process.env['E2E_BASE_URL']
    ? undefined
    : {
        command: 'npx ng build && node dist/brujula-salvaje/server/server.mjs',
        url: `${URL_BASE}/healthz`,
        reuseExistingServer: !EN_CI,
        timeout: 240_000,
        env: {
          PORT: String(PUERTO),
          NG_ALLOWED_HOSTS: 'localhost,127.0.0.1',
          NG_CLI_ANALYTICS: 'false',
        },
      },
});
