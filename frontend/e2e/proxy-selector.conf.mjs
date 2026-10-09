/**
 * Proxy del servidor de desarrollo para las E2E del Selector de medios (TKT-022, DEC-DEV-022-01).
 *
 * El banco de pruebas del selector (/panel/desarrollo/selector-medios) solo existe en desarrollo:
 * se sirve con `ng serve` y la API (/api/**) se reenvía al proxy de Compose del stack bajo prueba,
 * así las pruebas usan el backend, la BD y la sesión reales. Uso (desde frontend/):
 *
 *   E2E_SELECTOR_API=http://127.0.0.1:18242 npx ng serve --port 4310 \
 *     --proxy-config e2e/proxy-selector.conf.mjs
 *
 * El origen del servidor de desarrollo (http://127.0.0.1:4310) debe estar en
 * DJANGO_CSRF_TRUSTED_ORIGINS del stack (el navegador envía Origin en las escrituras).
 */
const destino = process.env['E2E_SELECTOR_API'] ?? 'http://127.0.0.1:8080';

export default {
  '/api': { target: destino, secure: false, changeOrigin: false },
  '/health': { target: destino, secure: false, changeOrigin: false },
};
