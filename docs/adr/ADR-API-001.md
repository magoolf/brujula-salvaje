# ADR-API-001 — Autenticación y sesión del panel editorial: sesión Django + CSRF (sin JWT)

| Campo | Valor |
|---|---|
| Estado | PROPOSED (Autoridad Delegada, CLAUDE.md §0.2) |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-003 |
| Contrato | `contracts/openapi.yaml` (securitySchemes `sesionPanel`, `csrfToken`; tag `panel-auth`) |
| Trazabilidad | Skill_Backend §12.2; Skill_Frontend (XSRF de Angular con sesión Django); BLUEPRINT §5, §12, STATE-003, STATE-004, FLOW-010, FLOW-015, RULE-017, RULE-029, DEC-AUTO-036/037/038/049; THREAT-001, 002, 003, 004, 014, 017, 018, 020, 025, 027; AC-029, 055, 056, 105..109, 115, 119; DB_HANDOFF (`sesion_panel`, ADR-DB-005) |
| DEC-AUTO | 101, 102, 119 (ORIGEN: EXPANSIÓN_AUTÓNOMA, reversibles) |

## Contexto
- [HECHO] Hay dos superficies: sitio público anónimo, sin cookies (CON-001, RULE-029, AC-060), y un panel editorial para 1-5 personas con los roles EDITOR y ADMINISTRADOR (DEC-AUTO-035).
- [HECHO] Skill_Backend §12.2 fija por defecto la sesión Django con cookie `HttpOnly; Secure; SameSite=Lax` + CSRF para una SPA del mismo sitio. JWT solo se permite con un ADR justificado (terceros o móvil).
- [HECHO] Skill_Frontend configura `withXsrfConfiguration({cookieName: 'csrftoken', headerName: 'X-CSRFToken'})` y hace las llamadas al mismo origen a través del reverse proxy.
- [HECHO] DB_HANDOFF guarda las sesiones en `app.sesion_panel` con `cuenta_id`, lo que permite invalidar todas las sesiones de una cuenta (DEC-AUTO-089).
- [HECHO] No hay clientes de terceros, ni app móvil, ni correo o SMS (§20, §31).

## Alternativas
| Alternativa | Pros | Contras |
|---|---|---|
| **Sesión Django en el servidor + cookie HttpOnly + CSRF (double-submit de Django)** | Estándar del Contrato Técnico; revocación inmediata en el servidor (THREAT-002/025); nada de tokens en JS; encaja con el backend `sesion_panel` y con el XSRF de Angular | Exige CSRF en toda operación de cambio y mismo origen |
| JWT de acceso + refresh en cookie | Stateless | Revocación compleja (lista negra), rotación de refresh, más superficie; no hay terceros ni móvil que lo justifiquen (§12.2) |
| JWT en `localStorage` | Sencillo en el cliente | Robable por XSS (THREAT-005); lo prohíbe la práctica ASVS L2 |

## Decisión
1. **Mecanismo:** sesión Django en el servidor (backend `sesion_panel`, ADR-DB-005). No se usa JWT. Autorización en el servidor por acción, deny-by-default. El rol se lee de la cuenta, nunca de la petición (THREAT-004).
2. **Cookies (DEC-AUTO-101):**
   - `sessionid`: `HttpOnly; Secure; SameSite=Lax; Path=/api/v1/panel/`. La cookie que actúa como credencial solo viaja a la API del panel: ni el sitio público ni los estáticos la reciben.
   - `csrftoken`: `Secure; SameSite=Lax; Path=/`, **sin HttpOnly**, porque Angular tiene que leerla desde las páginas `/panel/**` (Skill_Frontend). No es una credencial.
   - Solo las emiten operaciones del panel (`GET /api/v1/panel/auth/csrf`, login y rotaciones). Ninguna ruta pública responde con `Set-Cookie` (RULE-029, AC-119). Un visitante que nunca entra al panel no tiene ninguna cookie (AC-060).
   - `CSRF_FAILURE_VIEW` devuelve 403 `csrf_invalido` en `application/problem+json`. `CSRF_TRUSTED_ORIGINS` y CORS se configuran con listas explícitas; CORS queda vacío porque todo es mismo origen.
3. **Flujo de login por pasos (DEC-AUTO-102):** `POST /auth/login` crea una sesión y devuelve `paso_pendiente` ∈ {MFA, CAMBIO_CREDENCIAL, CONFIGURAR_MFA, AUTORIZACION, NINGUNO}, en el orden de SCR-030 → 031 → 032 → 033. Mientras haya un paso pendiente, el resto del panel responde 401 `mfa_requerido` o 403 `cambio_credencial_requerido` / `configuracion_mfa_requerida` / `autorizacion_requerida` (STATE-004). El identificador de sesión rota al autenticarse, al verificar el MFA, al cambiar la contraseña y ante cualquier cambio de privilegio.
4. **Anti fuerza bruta y anti enumeración (THREAT-001/018):** el contador de fallos se lleva por **usuario normalizado, exista o no la cuenta**: 5 fallos → bloqueo de 15 min progresivo, con 429 `acceso_bloqueado_temporalmente` + `Retry-After`. Además hay un límite por IP (10/min, perfil `panel-login`). Credenciales inválidas → 401 `credenciales_invalidas`, con el mismo mensaje y un tiempo equivalente (se ejecuta siempre el hash, incluso si el usuario no existe). No hay recuperación pública de contraseña (DEC-AUTO-036).
5. **Expiración (DEC-AUTO-049):** 30 min de inactividad y 12 h absolutas. `GET /auth/sesion` no renueva la inactividad; `POST /auth/sesion/renovar` sí ("Seguir conectado") y nunca supera las 12 h. Logout, desactivar, restablecer, cambiar el rol y anonimizar invalidan en el servidor todas las sesiones de la cuenta.
6. **Redirección segura:** `siguiente` solo se acepta como ruta relativa bajo `/panel/`; si no cumple, `redireccion` = `/panel` (THREAT-017, AC-115).
7. **MFA TOTP (SHOULD, DEC-AUTO-037 / DEC-AUTO-119):** secreto cifrado en reposo; el QR se genera en el cliente a partir de `otpauth_uri`, sin servicios de terceros; 10 códigos de recuperación que se muestran una sola vez (se guarda solo su hash). Para el Administrador, cuando se implemente, el MFA es obligatorio: paso `CONFIGURAR_MFA`, y desactivarlo devuelve 409 `mfa_obligatorio`. **CHG-API-002 (DEC-AUTO-215/218):** iniciar la activación (`panelIniciarActivacionMfa`) exige reautenticación con `contrasena`. Si es incorrecta, devuelve 401 `credenciales_invalidas` sin cerrar la sesión y cuenta para el bloqueo de RULE-017. El detalle está en ADR-API-002 §17.
8. **Respuestas del panel:** `Cache-Control: no-store` y `X-Robots-Tag: noindex, nofollow` en todas (AC-119). La contraseña temporal solo aparece en la respuesta de alta o restablecimiento. Ningún cuerpo de login ni secreto se registra en logs (THREAT-020).

## Consecuencias
- El Developer implementa un backend de sesión sobre `sesion_panel`, un middleware de "paso pendiente", un throttle por usuario normalizado (clave HMAC, ADR-DB-005 §3) y una vista CSRF en problem+json.
- QA verifica: CSRF en cada operación de cambio (THREAT-003), ausencia de `Set-Cookie` en las rutas públicas, rotación del identificador de sesión, expiración a los 30 min y a las 12 h, acceso horizontal y vertical (Editor → 403 en cuentas, auditoría, configuración, licencias, escalas y páginas legales: AC-105) y los tiempos equivalentes del login.
- El SSR de Angular no necesita la sesión: el panel se renderiza en el cliente y es noindex.

## Riesgos
- RULE-029 dice "cookies limitadas al panel". `csrftoken` usa `Path=/`, así que el navegador de un miembro del staff la envía también a las rutas públicas. No es una credencial y solo existe tras entrar al panel; las rutas públicas nunca la fijan. Si QA o el Orquestador exigen el alcance estricto, la alternativa es `CSRF_USE_SESSIONS=True` + un token entregado en el cuerpo por `GET /auth/csrf` (requiere un CHG en Skill_Frontend, que hoy usa `withXsrfConfiguration`).
- Si en el futuro hay clientes de terceros o una app móvil, se reabre este ADR (JWT u OAuth2 con un ADR nuevo).

## Condiciones de invalidez
- Aparecen clientes que no son navegadores o un despliegue en origen cruzado (API en otro dominio).
- El equipo supera la escala de ASM-003 y se necesita SSO corporativo.
