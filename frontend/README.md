# Brújula Salvaje: frontend

Angular 22.2.0 con SSR (Node 24.21.0, Express 5), zoneless, componentes standalone y Signals. Generado con `ng new brujula-salvaje --directory frontend --ssr` (TKT-002).

## Scripts

| Script | Qué hace |
|---|---|
| `npm ci` | Instala exactamente lo que fija `package-lock.json`. Todas las versiones van sin `^`/`~` y `.npmrc` tiene `save-exact=true`. |
| `npm run lint` | `eslint . --max-warnings=0`: reglas 01-06, 08-10 y 13 de Skill_Frontend §13, más las de seguridad de §27.4. |
| `npm run typecheck` | `tsc --noEmit` sobre la app, las pruebas unitarias y las E2E. |
| `npm test` | Vitest con cobertura. Umbrales: `domain/` ≥ 90 %, `state/` ≥ 80 %, global ≥ 70 % (`vitest-base.config.mts`). |
| `npm run build` | Build de producción SSR: `dist/brujula-salvaje/{browser,server/server.mjs}`. |
| `npm run api:generate` | Regenera `src/app/api/**` desde `../contracts/openapi.yaml` con ng-openapi-gen 1.1.0. No se editan a mano. |
| `npm run tokens:generate` | Regenera `src/styles/tokens.css` desde `../docs/03_diseno/tokens.json`. |
| `npm run e2e` | Playwright en chromium, firefox y webkit, con axe. Sin `E2E_BASE_URL`, compila y arranca el SSR en 127.0.0.1:4300. |

Para comprobar que el cliente generado coincide con el contrato: `npm run api:generate && git diff --exit-code -- src/app/api`.

## Estructura

```
src/app/
├── api/        cliente y DTO GENERADOS (solo los importa data/ de cada feature)
├── core/
│   ├── http/   provideHttpClient (fetch + XSRF csrftoken/X-CSRFToken), traceparent,
│   │           reenvío SSR (API_INTERNAL_URL), ErrorApi (RFC 9457), ejecutar()
│   ├── auth/   401 global del panel y validación de `siguiente`
│   ├── forms/  aErroresDeCampo
│   ├── layout/ shell (cabecera GI-01, pie GI-02, aviso sin conexión GI-04), páginas 404/410/500
│   ├── seo/    title/meta/canónica/Open Graph/JSON-LD, código HTTP del SSR
│   └── observabilidad/  ErrorHandler global sin PII
├── shared/ui/  componentes base del Design System
└── features/   los crean los tickets TKT-008..010 y del panel ({ui,state,data,domain})
```

## Recursos vendorizados (sin CDN, CON-003)

| Recurso | Origen | Licencia | SHA-256 |
|---|---|---|---|
| `public/fonts/bricolage-grotesque-latin-wght-normal.woff2` | `@fontsource-variable/bricolage-grotesque@5.3.0` | SIL OFL 1.1 (`public/fonts/OFL-bricolage-grotesque.txt`) | `a97804dc9fbe5fc972a08018c5eda4dab7ef2346f64c57e61419d05e6de4ea1c` |
| `public/fonts/source-sans-3-latin-wght-normal.woff2` | `@fontsource-variable/source-sans-3@5.3.0` | SIL OFL 1.1 (`public/fonts/OFL-source-sans-3.txt`) | `7a19a7027e125257d310c6dbd78ae3a30b5ea1e3794d60b12bb28227a003bfda` |
| `public/fonts/source-sans-3-latin-wght-italic.woff2` | `@fontsource-variable/source-sans-3@5.3.0` | SIL OFL 1.1 | `9a15dafc2c2b2414aaa9d6c30830d9aab4361329d8495b1574633603b994b411` |
| Iconos (`src/app/shared/ui/icono/iconos-lucide.ts`) | `lucide-static@1.48.0` (`icon-nodes.json`) | ISC (`src/app/shared/ui/icono/LICENSE-lucide.txt`) | n/a |

## SSR y CSP

- `GET /healthz` responde 200 sin llamar a la API.
- El nonce CSP llega del proxy en la cabecera `x-csp-nonce`. Solo se aceptan valores con el formato esperado, y se aplica a los `<script>` y `<style>` en línea.
- La producción desactiva `inlineCritical`. La hidratación incremental y el event replay también están desactivados, porque inyectan un `<script>` en línea sin nonce.
- `RenderMode.Server` para las rutas públicas y `RenderMode.Client` para `panel/**`.
- Si el renderizado falla, se sirve `public/500.html` con HTTP 500.
