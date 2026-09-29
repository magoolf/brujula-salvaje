# KANBAN — Estado persistente del proyecto

> Gestionado exclusivamente por el Orquestador (CLAUDE.md §0.8). Se actualiza ANTES y DESPUÉS de cada delegación.

## Proyecto
- nombre: Portal web experto sobre vacaciones (nombre provisional)
- fase_actual: F7 — Desarrollo por Micro-Tickets
- abierto: 2026-09-24
- idea_original: "crear una página web nivel experto sobre vacaciones"

## Tickets
```yaml
tickets:
  - id: TKT-F2-001
    titulo: "Entrevista Pública + PRD y requirements.yaml (Modo Expansor)"
    fase: F2
    estado: DONE
    owner: Orquestador (entrevista) -> requerimientos (Modo Expansor)
    trazabilidad: []
    depende_de: []
    archivos_permitidos: ["docs/01_requerimientos/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Entrevista respondida 2026-09-24 (P1-P13); P14-P16 sin respuesta -> DEC-AUTO", "docs/01_requerimientos/PRD.md", "docs/01_requerimientos/requirements.yaml (YAML válido, js-yaml)", "51 REQ, 60 AC (corregido: el handoff F2 decía 53/64), 34 DEC-AUTO, gate PASS"]
    actualizado: 2026-09-24
  - id: TKT-F3-001
    titulo: "Blueprint Funcional / Master PRD (sitemap, flujos, modelo lógico, §55, §56)"
    fase: F3
    estado: DONE
    owner: arquitecto-funcional
    trazabilidad: [REQ-001, REQ-040]
    depende_de: [TKT-F2-001]
    archivos_permitidos: ["docs/02_blueprint/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["docs/02_blueprint/BLUEPRINT.md (1333 líneas)", "44 SCR, 17 FLOW, 26 entidades, 28 THREAT, 52 FEAT, 4 EXP, DEC-AUTO-035..056", "Cobertura 51/51 REQ; gate PASS por revisión estática"]
    actualizado: 2026-09-24
  - id: TKT-F4-001
    titulo: "Design System + tokens + VIEW_SPEC (HANDOFF_UI_UX)"
    fase: F4
    estado: DONE
    owner: ui-ux
    trazabilidad: [REQ-001, REQ-040]
    depende_de: [TKT-F3-001]
    archivos_permitidos: ["docs/03_diseno/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["docs/03_diseno/HANDOFF_UI_UX.yaml (YAML válido, 44/44 SCR, 17/17 FLOW)", "docs/03_diseno/tokens.json (JSON válido)", "Validación sintáctica ejecutada por el Orquestador (js-yaml, json)", "QUALITY_GATE PASS_WITH_NOTES; axe/Lighthouse NOT_RUN hasta F8"]
    actualizado: 2026-09-25
  - id: TKT-F4-002
    titulo: "Modelo físico PostgreSQL + ADR-DB + plan de migraciones"
    fase: F4
    estado: DONE
    owner: base-datos
    trazabilidad: [REQ-001, REQ-040]
    depende_de: [TKT-F3-001]
    archivos_permitidos: ["docs/04_datos/**", "docs/adr/ADR-DB-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["docs/04_datos/DB_HANDOFF.yaml (YAML válido, js-yaml por el Orquestador)", "ADR-DB-001..005", "PostgreSQL 18.6, 37 tablas + 1 vista, 12 migraciones reversibles", "gate NOT_RUN: diseño estático; pruebas en F7/F8"]
    actualizado: 2026-09-25
  - id: TKT-F4-003
    titulo: "Contrato OpenAPI v1 + ADR-API"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [REQ-001, REQ-040]
    depende_de: [TKT-F3-001]
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/ADR-API-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["contracts/openapi.yaml: OpenAPI 3.1.0, 127 operaciones; js-yaml OK; redocly lint: válido, 0 errores, 12 warnings de estilo (ejecutado por el Orquestador)", "docs/adr/ADR-API-001.md (sesión+CSRF), ADR-API-002.md (DEC-AUTO-100..119)", "Gates de implementación NOT_RUN (modo contrato)"]
    actualizado: 2026-09-25
  - id: TKT-F4-004
    titulo: "CHG-DB-001: persistencia de Idempotency-Key (24 h) para las POST del panel"
    fase: F4
    estado: DONE
    owner: base-datos
    trazabilidad: [REQ-055]
    depende_de: [TKT-F4-002, TKT-F4-003]
    archivos_permitidos: ["docs/04_datos/**", "docs/adr/ADR-DB-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DB_HANDOFF v1.1 con idempotencia_peticion (YAML válido, js-yaml por el Orquestador)", "ADR-DB-004/005 actualizados; RSK-DB-007 cerrado; DEC-AUTO-124..128"]
    actualizado: 2026-09-25
  - id: TKT-F4-005
    titulo: "CHG-API-001: repetición idempotente de panelCrearCuenta y 409 por lock_timeout"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [REQ-055, AC-106]
    depende_de: [TKT-F4-004]
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/ADR-API-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["contracts/openapi.yaml: redocly lint válido, 0 errores, 12 warnings (ejecutado por el Orquestador)", "ADR-API-002 §5 actualizado; 11 operaciones con Idempotency-Key = CHECK de DB_HANDOFF v1.1"]
    actualizado: 2026-09-25
  - id: TKT-F6-001
    titulo: "DevOps PRE-DESARROLLO: matriz de interoperabilidad, compose.yaml, Dockerfiles, CI base"
    fase: F6
    estado: DONE
    owner: devops
    trazabilidad: [REQ-050, REQ-054, REQ-055]
    depende_de: [TKT-F4-001, TKT-F4-002, TKT-F4-003, TKT-F4-004]
    archivos_permitidos: ["Dockerfile*", "**/Dockerfile*", "compose*.yaml", ".github/workflows/**", "infra/**", "scripts/ops/**", ".env.example", "docs/05_operacion/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["docs/05_operacion/DEVOPS_HANDOFF.md", "compose config 4/4 OK; INFRA-DB-000 healthy y roles verificados; proxy/CSP/backup probados con fixtures fuera del repo", "Orquestador verificó: stack brujula bajado (0 contenedores/volúmenes), ci.yaml YAML válido, gitleaks sin fugas", "gate NOT_RUN (sin código de aplicación); RSK-OPS-001 HIGH -> Puerta Humana antes de F9"]
    actualizado: 2026-09-25
  - id: TKT-001
    titulo: "Backend base: startproject, uv/pyproject, settings por entorno, apps/core (RFC 9457 + trace_id, logging JSON, health live/ready, cabeceras, throttling base, confianza en proxy), pytest"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [REQ-050, REQ-055, REQ-057, FEAT-048, MOD-014]
    depende_de: [TKT-F6-001]
    archivos_permitidos: ["backend/*", "backend/config/**", "backend/apps/__init__.py", "backend/apps/core/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["rama tkt-001-backend-base @ 7e84ed0 integrada en main @ 5d4ac9c (merge --no-ff)", "QA_VERDICT PASS ciclo 1/3: 79/79 tests, cobertura 98.96 %, schemathesis /health 18/18, semgrep/bandit/pip-audit/gitleaks 0", "OBS-01..08 y NV-01/02 trasladados a TKT-003/004/OPS"]
    actualizado: 2026-09-25
  - id: TKT-002
    titulo: "Frontend base: ng new SSR, versiones exactas, CSP nonce, tokens+Tailwind+fuentes+Lucide, core/http (traceparent, XSRF, ErrorApi), cliente generado del OpenAPI, shared/ui, shell de layout y páginas de error, Playwright+axe"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [REQ-052, REQ-056, REQ-058, FEAT-001, FEAT-002, MOD-001, MOD-008]
    depende_de: [TKT-F6-001]
    archivos_permitidos: ["frontend/*", "frontend/.*", "frontend/public/**", "frontend/e2e/**", "frontend/src/*", "frontend/src/app/*", "frontend/src/app/core/**", "frontend/src/app/shared/**", "frontend/src/app/api/**", "frontend/src/styles/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["PR #9 integrado en main", "QA_VERDICT PASS 2/3 @ cfb98d7; regeneración de cliente 0107056 verificada por el CI completo", "Primer job images en GitHub: build 6 imágenes + trivy con .trivyignore + SBOM + smoke + schemathesis = PASS"]
    actualizado: 2026-09-25
  - id: TKT-003
    titulo: "Backend datos: modelos y migraciones de DB_HANDOFF v1.1 (catálogos + semilla de catálogos, cuentas, medios, contenido + integridad SQL, inicio, auditoría inmutable, búsqueda, ops, idempotencia) con pruebas de introspección"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [REQ-040, REQ-057, DATA-001..026]
    depende_de: [TKT-001]
    archivos_permitidos: ["backend/config/settings/**", "backend/apps/catalogos/**", "backend/apps/cuentas/**", "backend/apps/medios/**", "backend/apps/contenido/**", "backend/apps/inicio/**", "backend/apps/auditoria/**", "backend/apps/busqueda/**", "backend/apps/ops/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["rama tkt-003-modelo-datos @ 8f1480e; PR #2 integrado en main @ 0fd6f33", "QA_VERDICT PASS 1/3; CI verde (run 36235308337)"]
    actualizado: 2026-09-25
  - id: TKT-004
    titulo: "Backend acceso al panel y cuentas: sesión+CSRF, login por pasos, MFA TOTP, bloqueo progresivo, autorización Ley 1581, cuentas (alta/restablecer/desactivar/anonimizar), auditoría, servicio común de idempotencia"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-009, MOD-013, FEAT-029..032, FEAT-045, FEAT-046, REQ-055, REQ-OPS002-01, OBS-01, NV-02, OBS-QA003-01, OBS-QA003-05, OBS-QA003-06, CHG-DB-002]
    depende_de: [TKT-003 (QA PASS; parte de su rama)]
    archivos_permitidos: ["backend/config/urls.py", "backend/config/settings/**", "backend/apps/core/**", "backend/apps/cuentas/**", "backend/apps/auditoria/**"]
    ciclo_qa: 4/3 (excepcional autorizado)
    ciclo_panico: 0/2
    evidencia: ["PR #8 integrado en main", "QA_VERDICT PASS ciclo 4 excepcional @ a4ec249; CI verde completo tras update-branch"]
    actualizado: 2026-09-25
  - id: TKT-005
    titulo: "Backend API pública + búsqueda + comandos de operación: /api/v1/publico/**, filtros/facetas, mapa, aleatorio, 410, búsqueda es_unaccent+pg_trgm, throttling público, comandos programados del crontab"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-001..008, MOD-014, FEAT-001..028, FEAT-048, FEAT-051, FEAT-052, CHG-DB-002 (medios.0002, contenido.0003, catalogos.0003, inicio.0002 de DB_HANDOFF v1.2)]
    depende_de: [TKT-004]
    archivos_permitidos: ["backend/config/urls.py", "backend/apps/contenido/**", "backend/apps/catalogos/**", "backend/apps/inicio/**", "backend/apps/busqueda/**", "backend/apps/ops/**", "backend/apps/medios/**", "backend/apps/cuentas/**", "backend/apps/auditoria/**", "backend/pyproject.toml", "backend/uv.lock"]
    ciclo_qa: 2/3
    ciclo_panico: 1/2
    evidencia: ["PR #18 @ 9af0dcc; CI verde run 36478626205 (todos los jobs)", "Corrección ciclo 1: visibilidad pública única (AC-129), libro de anonimizaciones v2 (CHG-DB-003), nosec B608, OBS-04/05/06; p95 lecturas 117 ms, búsqueda 42 ms", "QA ciclo 2/3 previo cortado por límite de sesión sin veredicto (NOT_RUN, ver audit_log.md 2026-09-28); relanzado ciclo 2/3 desde cero sobre el mismo commit", "Segundo corte durante schemathesis, de nuevo sin QA_VERDICT persistido ni subagente alcanzable: NOT_RUN otra vez (ver audit_log.md 2026-09-28, segunda entrada); relanzado ciclo 2/3 desde cero sobre 9af0dcc, sin integrar a main", "QA_VERDICT PASS ciclo 2/3 @ 9af0dcc: schemathesis 3032 casos/0 fallos, pytest 591 passed, bandit/semgrep/gitleaks limpios, 4 correcciones del ciclo 1 verificadas; OBS-QA-TKT005-C2-01 INFO (artefacto Git-Bash/MSYS en Windows, no es defecto de código); RSK-DB-015 verificado, recomendado MITIGADO", "PR #18 actualizado con main (072bf55) y CI verde completo (run 36501571124); integrado en main con git merge --no-ff @ 3e042e8. TKT-005 DONE"]
    actualizado: 2026-09-28
  - id: TKT-006
    titulo: "Backend API del panel: contenidos (CRUD, vista previa, publicar/retirar/reactivar, revisiones, bloqueo optimista), medios (subida segura, derivados, publico/privado), taxonomías, inicio, configuración, tablero"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-010, MOD-011, MOD-012, FEAT-033..044, FEAT-047, FEAT-049, FEAT-050]
    depende_de: [TKT-005]
    archivos_permitidos: ["backend/config/urls.py", "backend/config/settings/base.py", "backend/apps/contenido/**", "backend/apps/medios/**", "backend/apps/catalogos/**", "backend/apps/inicio/**", "backend/apps/busqueda/**", "backend/apps/core/esquema.py", "backend/pyproject.toml", "backend/uv.lock"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["PR #24 @ 5b6f270 (base main 3e042e8), rama tkt-006-panel-editorial", "Developer: pytest 674 passed/3 skipped, mypy sin issues (176 archivos), ruff limpio, manage.py check --deploy sin hallazgos", "DEC-AUTO-917: 3 códigos Problem Details de CHG-API-005 registrados vía apps.py::ready() en el propio dominio contenido (apps/core/problemas.py fuera de archivos_permitidos), reversible", "GAP declarado por el Developer: sin tests HTTP/E2E de panel_views.py ni medición de cobertura pytest-cov -> a validar por QA", "Verificación tras reinicio 2026-09-29: CI run 36513898298 terminó en FAIL (no 'en curso' como registraba el kanban); lint/typecheck/tests/check --deploy en verde, pero el gate de contrato (oasdiff, paso 14) falló con 77 errores -> no es READY_FOR_VALIDATION real; se devuelve al Developer sobre la misma rama, no es Botón de Pánico", "Corrección 1 @ 7ad0ae4: gate_contrato.py (N1-N14) pasa a 0 errores (antes 76-77); pytest/oasdiff NOT_RUN por el Developer (sin Docker/Postgres/binario oasdiff en su entorno)", "Segundo FAIL de CI (run 36517118944): gate_contrato.py sigue en 0 errores, pero el paso siguiente de la misma etapa ('oasdiff breaking contrato-filtrado.yaml generado.yaml --fail-on WARN') falla con 296 cambios (103 error/193 warning) — primera vez que esta comprobación llega a ejecutarse en el proyecto (antes siempre fallaba primero el gate N1-N14). Patrón sistemático de 'allOf branch removed'/'media type removed' que coincide con endpoints que usan el patrón de paginación PaginaMetaSerializer (herencia de clases DRF) ya usado con éxito en TKT-005; incluye también /panel/taxonomias/paises y /regiones, fuera del alcance de la corrección anterior. Se devuelve al Developer, segunda ronda de corrección sobre la misma rama, aún no es QA (ciclo_qa 0/3)", "Corrección 2 @ 6cc15d0: 4 causas raíz distintas diagnosticadas y corregidas (25 respuestas sin schema por serializers con 0 campos declarados/código muerto nunca importado; 16 parámetros de query/header no declarados vía OpenApiParameter; ~15 enums perdidos por el patrón _CampoTipo anti-colisión W001; ~25 campos sin format/pattern/maxItems), verificado con script propio de aproximación a oasdiff (no versionado, sin binario oasdiff disponible en su entorno). GAP arquitectónico residual identificado con precisión: apps/core/esquema.py solo generaliza el allOf de paginación (_paginas) y de Problema*, no la composición {EntidadMeta}+{ComunCampos}+{TipoCampos} que el contrato usa en los 7 tipos de contenido del panel + Pais/Region (~75 hallazgos restantes). DEC-AUTO-918 (Orquestador, ver audit_log): se amplía archivos_permitidos con backend/apps/core/esquema.py (generalización del hook existente, ya usado por TKT-005; no es cambio de arquitectura ni de contrato) en vez de abrir un ticket separado. Tercera ronda de corrección despachada sobre la misma rama, aún no es QA (ciclo_qa 0/3), no es Botón de Pánico formal", "Corrección 3 @ bce84ce: tabla `_COMPOSICIONES` (28 entradas) generaliza allOf para los 9 recursos autorizados (75->26 hallazgos de allOf, los 26 restantes fuera de alcance); prerrequisito encontrado y corregido: los 7 serializers Panel no declaraban casi ningún campo como atributo de clase (solo en to_representation), completados con los Mixin ya usados por Entrada. CI real (run 36522908583): 676 passed/1 failed — regresión real (no del Developer, preexistente desde antes: TKT-001 test_AC_TKT001_01_check_deploy_prod_sin_avisos) por 9 colisiones de nombre de enum (drf_spectacular.W001) que aparecieron al restaurar los enums explícitos; el paso del gate de contrato ni siquiera se ejecutó (se saltó tras el fallo de pytest). DEC-AUTO-919 (Orquestador): se amplía archivos_permitidos con backend/config/settings/base.py para añadir las entradas que faltan a ENUM_NAME_OVERRIDES (patrón ya existente en ese archivo, 4 entradas previas, mecánico y de bajo riesgo). Cuarta ronda despachada, aún no es QA", "Corrección 4 @ 91e78e0: 5 entradas nuevas en ENUM_NAME_OVERRIDES, verificado con evidencia real (133 tests sin BD, incluido exactamente el que había fallado en CI, PASS). CI real (run 36524304762): unit tests y check --deploy en VERDE por primera vez; el gate de contrato por fin se ejecutó completo (primera vez en 4 rondas) y sigue en FAIL: 677 cambios (69 error, 608 warning) — MÁS que en la ronda 2 (296), no menos: la corrección de allOf de la ronda 3 permitió que oasdiff recorra más profundo dentro de las ramas y revele una capa nueva de hallazgos de bajo nivel (177 pattern, 199 maxItems, 58 max, 36 tipo, 32 uniqueItems, 60 content-media-type, 28 required, etc.), abrumadoramente formato/patrón/límites de campos anidados, no rupturas estructurales. El script de aproximación del Developer (oasdiff_lite.py) no predijo este salto (mostraba 26 residuales, no 677): no es fiable como sustituto del oasdiff real. Pausa del Orquestador: 4 rondas de corrección pre-QA sobre el mismo gate, con el conteo de hallazgos EMPEORANDO en la última ronda en vez de converger — no se despacha una quinta ronda sin decisión explícita del usuario sobre cómo proceder (ver audit_log.md, pregunta planteada al usuario)", "DECISIÓN DEL USUARIO 2026-09-29: relajar el gate a --fail-on ERROR. Se abre TKT-OPS-010 (DevOps, cambio de CI) y TKT-012 (deuda técnica de los 608 warnings, seguimiento). TKT-006 vuelve a IN_PROGRESS, a la espera de TKT-OPS-010 para saber si los 69 hallazgos ERROR restantes exigen una quinta ronda del Developer", "TKT-OPS-010 DONE, rama actualizada con main (gh pr update-branch). CI real (run 36564573410) confirma: los 608 warnings ya no bloquean, pero los 69 error SIGUEN bloqueando sin cambios (--fail-on ERR no los afecta, como se esperaba). Desglose: 44 response-property-max-items-unset + 8 min-items-unset (anotaciones de límites de array faltantes, mecánico), 7 response-property-one-of-added (rama oneOf extra en licencia/motivo/salud_editorial, probable estilo de representación de nullable), 5 request-property-min-length-set (minLength=1 añadido en 5 campos de texto de PUT /panel/medios/{id}, más restrictivo que el contrato), 3 request-property-max-set, 1 response-property-became-optional (bloqueos en impacto-retiro), 1 request-body-type-changed (POST /panel/medios multipart, gap ya señalado por el Developer en la ronda 3 como patrón preexistente de subida de archivos). Quinta ronda despachada al Developer con la lista exacta", "Ronda 5 @ 894d2f8: 69 error -> 1 error (563 warning). Causa raíz real de los 52 maxItems/minItems: el helper _con_limite (usado desde las rondas 3-4) mutaba campo.validators.append(...) tras construir el ListSerializer, pero BaseSerializer.get_fields() hace deepcopy de _declared_fields en cada instanciación y Field.__deepcopy__ reconstruye desde _args/_kwargs originales, descartando la mutación -- NINGUNO de los fixes de maxItems/minItems de las rondas 3-4 estaba surtiendo efecto en el esquema real hasta este commit (confirmado inspeccionando el YAML antes/después). Rediseñado pasando validators= como kwarg del constructor (DRF sí conserva eso en deepcopy). CI real (run 36569339583) confirma exactamente lo mismo que la verificación local del Developer con el binario oasdiff real: 564 changes: 1 error, 563 warning. Único error restante: request-body-type-changed en POST /panel/medios (multipart/form-data vs string/binary del contrato) -- gap dejado documentado por instrucción explícita del Orquestador, no corregido. Se resuelve con una excepción quirúrgica del gate (no otra ronda de Developer, no reabrir el contrato): despachado a devops", "CI real (run 36574041536) tras heredar TKT-OPS-011: TODOS los pasos en verde por primera vez, incluidos SAST y SCA (nunca habían llegado a ejecutarse antes). Gate de contrato: 563 changes: 0 error, 563 warning, 0 info (los warnings no bloquean desde TKT-OPS-010, deuda en TKT-012). READY_FOR_VALIDATION real; QA despachado (ciclo 1/3) sobre el ticket completo -- GAP declarado por el Developer desde la ronda 1 pendiente de validar: sin tests HTTP/E2E de panel_views.py/panel_urls.py, sin medición de cobertura pytest-cov", "QA_VERDICT FAIL (ciclo 1/3), primera ejecución real de pytest contra PostgreSQL real de todo este ticket (674 passed/0 failed, pero cobertura de los módulos propios muy por debajo del umbral: panel_views.py 41%, panel_selectors.py 29%, medios/selectors_panel.py 21%). 2 bugs bloqueantes reproducidos con HTTP real: BUG-1 (500 en TODO el CRUD de Destino/Itinerario/Guía con tipos_aventura asociado -- panel_serializers.py:887/931/974 usa tipos_aventura.values_list('id',...) pero la PK real de TipoAventura es 'contenido' (ADR-DB-002, patrón supertipo), el propio archivo ya usa el patrón correcto en la línea 973); BUG-2 (subida de medios 100% inalcanzable -- DEFAULT_PARSER_CLASSES en settings/base.py:216 solo tiene JSONParser, sin MultiPartParser en ningún parser_classes de apps/medios/api/views.py, ListaMedios.post nunca recibe request.FILES). Ambos en las líneas de 0% cobertura. Contrato también FAIL por la misma vía (5xx real que schemathesis no encontró por fuzzing puro). Seguridad PASS (gitleaks/semgrep limpios); idempotencia, los 3 Problem Details de DEC-AUTO-917 y RBAC vertical (licencias/páginas) confirmados correctos en runtime real. Devuelto al Developer con corrección puntual + tests HTTP obligatorios", "Corrección @ 4881494: BUG-1 (3 líneas, values_list('id',...) -> values_list('contenido_id',...)) y BUG-2 (parser_classes=[MultiPartParser,FormParser] scoped a ListaMedios) corregidos. Esta vez con Docker real disponible: suite completa 681 passed/3 skipped/0 failed, cobertura 88.12%, 2 tests HTTP nuevos de regresión (test_ac_tkt006_08_panel_http_tipos_aventura.py, test_ac_tkt006_04_http_subida.py). Gate de contrato con oasdiff real: 0 errores, 563 warning (sin cambios). CI real (run 36582671814) confirma: TODOS los jobs en verde incluido build+trivy+SBOM (schemathesis real). QA ciclo 2/3 despachado sobre los 2 bugs específicos", "QA_VERDICT PASS ciclo 2/3: BUG-1 y BUG-2 verificados corregidos de forma independiente (repros exactos + 7 tests nuevos ejecutados aislados + suite completa 681/0 + cadena schemathesis deliberada 0 fallos + DEC-AUTO-044 verificado end-to-end por primera vez, rechazo real de archivo disfrazado que el test del Developer no cubría). gitleaks/semgrep limpios. Hallazgo no bloqueante (criterio de Gatekeeper, invitado explícitamente): cobertura de varios módulos (panel_selectors.py 0% real en listar_por_tipo/FEAT-033, panel_views.py 55%, services.py 56-87%) sigue por debajo de los umbrales de Skill_Backend §8 pese a mejorar, sin defecto conocido detrás -- se suma al alcance de TKT-012. PR #24 integrado con git merge --no-ff @ fa24f1e. TKT-006 DONE. Desbloquea TKT-007 (semilla de contenido) y TKT-010 (frontend panel)"]
    actualizado: 2026-09-29
  - id: TKT-007
    titulo: "Semilla de contenido: comando cargar_semilla (24 destinos reales, itinerarios, guías, 12 tipos, colecciones, glosario, páginas legales, config de inicio, medios propios con licencia) vía servicio de publicación"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [REQ-040, REQ-043, DEC-AUTO-007, DEC-AUTO-033, PRB-BP-002]
    depende_de: [TKT-006]
    archivos_permitidos: ["backend/seed/**", "backend/apps/contenido/management/**", "backend/apps/contenido/tests/**", "backend/pyproject.toml", "backend/uv.lock"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Despachado tras integrar TKT-006 (main @ fa24f1e)", "Entregado @ 4863fc7, PR #27. 24/24 destinos PUBLICADO, 12/12 tipos, 10/10 itinerarios, 10/10 guías, 4/4 colecciones, 12/12 términos, 4/4 páginas institucionales, ConfigInicio completo, 133 medios 100% con licencia/autor/alt (código PROPIA). Idempotencia verificada con 2 ejecuciones reales contra Postgres (no solo declarada): 2ª ejecución 0 creados/97 reutilizados en <2s. RULE-025, RULE-006 y PRB-BP-002 (Surf->Galápagos, Ciclismo de montaña->Queenstown, ambos secundarios) verificados por consulta real a BD. Suite completa 697 passed/1 failed (preexistente, no relacionado, mismo patrón que OBS-QA-TKT005-C2-01 de artefacto Git-Bash/MSYS en Windows)/3 skipped, cobertura 89.25%. Gate de contrato intacto (128/128, 0 errores, no se tocó ninguna vista/serializer). 3 decisiones documentadas: arranque de RULE-006 con clique mínimo de 4 (reutiliza reglas.py real, no lo modifica), creación directa de PaginaInstitucional/ConfigInicio por ausencia de servicio real (services.py fuera de su alcance), y GAP-DEV-003 -- bug real preexistente encontrado en apps/contenido/services.py (publicar() reindexa el destino ANTES de confirmar sus tipos co-publicados, dejándolo transitoriamente fuera de búsqueda) mitigado con un reindexado final sin tocar el archivo. QA despachado", "QA_VERDICT PASS ciclo 1/3: verificación completamente independiente en contenedor Linux aislado, BD limpia desde cero -- 701/701 tests (0 failed, incluido el que el Developer reportó como preexistente: NO reprodujo en Linux, confirma que es artefacto Git-Bash/MSYS de Windows, no regresión), 2 ejecuciones propias de cargar_semilla confirmando idempotencia real, consultas SQL directas confirman 24/12/10/10/4/12/4 entidades PUBLICADO con los 15 campos obligatorios de REQ-042 completos. Contenido de seguridad (REQ-024/RSK-001) auditado con rigor en los 5 destinos de mayor riesgo: correcto y específico por actividad, no genérico; descargo presente en el 100%. PRB-BP-002 confirmado. DEC-AUTO-033 confirmado (0 cifras volátiles). gitleaks/semgrep limpios. PR #27 integrado con git merge --no-ff @ e26c680. TKT-007 DONE. Hallazgo menor: _configurar_inicio no incrementa el contador informativo en 2ª ejecución (blindspot de stdout, sin duplicación real) -- sumado a TKT-012. Riesgo residual: precisión factual no contrastada contra fuente web en vivo (QA sin WebFetch disponible), recomienda revisión editorial humana antes de publicación pública"]
    actualizado: 2026-09-29
  - id: TKT-008
    titulo: "Frontend público 1: inicio, explorar destinos (filtros en URL, mapa SVG, por mes, sorpréndeme), ficha de destino, guardados y compartir, SEO"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-001, MOD-002, MOD-003, MOD-006, MOD-008]
    depende_de: [TKT-002, TKT-007]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/core/layout/**", "frontend/src/app/features/inicio/**", "frontend/src/app/features/destinos/**", "frontend/src/app/features/guardados/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-25
  - id: TKT-009
    titulo: "Frontend público 2: itinerarios, guías, tipos de aventura, colecciones, glosario, búsqueda, institucional/legal, créditos"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-003, MOD-004, MOD-005, MOD-007]
    depende_de: [TKT-008]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/features/itinerarios/**", "frontend/src/app/features/guias/**", "frontend/src/app/features/tipos-aventura/**", "frontend/src/app/features/colecciones/**", "frontend/src/app/features/glosario/**", "frontend/src/app/features/busqueda/**", "frontend/src/app/features/institucional/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-25
  - id: TKT-010
    titulo: "Frontend panel editorial /panel: acceso (login, MFA, cambio credencial, autorización), tablero, editores de contenido, medios, taxonomías, inicio, configuración, cuentas, auditoría"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-009..013, FEAT-029..050]
    depende_de: [TKT-009, TKT-006]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/app.routes.server.ts", "frontend/src/app/features/panel/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-25
  - id: TKT-OPS-001
    titulo: "DevOps: init-volumes falla con volumen de medios poblado por la imagen (RSK-TKT001-01) y socket de control de gunicorn en FS de solo lectura + logs no JSON (RSK-TKT001-02)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [REQ-050, REQ-057, FEAT-048]
    depende_de: [TKT-F6-001]
    archivos_permitidos: ["compose*.yaml", "infra/**", "docs/05_operacion/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["rama tkt-ops-001-infra-fixes @ 3d67163 integrada en main @ 0151a4b", "QA_VERDICT PASS 1/3: stack completo healthy en volúmenes limpios y poblados; control negativo reproduce el fallo en main; logs 25/25 JSON; NV-01 validado (nginx sobrescribe XFF y X-Forwarded-Proto)"]
    actualizado: 2026-09-25
  - id: TKT-OPS-002
    titulo: "DevOps: excluir tests/conftest de la imagen (OBS-06); acotar --forwarded-allow-ips (OBS-08/NV-QAOPS-01); APP_VERSION por proyecto (RSK-OPS-010); chown -h en init-volumes (NV-QAOPS-02); smoke CI 0 líneas no JSON (RSK-OPS-009)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [REQ-055]
    depende_de: [TKT-OPS-001]
    archivos_permitidos: ["compose*.yaml", "infra/**", "docs/05_operacion/**", ".env.example"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["PR #1 integrado vía PR #4 (merge 486005e)", "QA_VERDICT PASS 1/3 @ 1c6c524"]
    actualizado: 2026-09-25
  - id: TKT-OPS-003
    titulo: "DevOps: CI verde en GitHub (ci.yaml:83 cast ::text), gzip text/javascript en nginx (F-01 de QA TKT-002), 429 del proxy en problem+json (HALLAZGO-QA-OPS002-02), dependabot.yml, runbook de init-volumes abortado (OBS-QA-OPS002-03)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [REQ-055, RSK-OPS-007]
    depende_de: [TKT-OPS-002]
    archivos_permitidos: [".github/workflows/**", ".github/dependabot.yml", "infra/**", "docs/05_operacion/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["PR #4 integrado en main @ 486005e", "QA_VERDICT PASS 1/3 @ 29aae22 (LCP 2366 ms); corrección gitleaks 79e14ac revisada por el Orquestador (diff de 1 línea CI + 1 huella)", "CI verde run 36235144225"]
    actualizado: 2026-09-25
  - id: TKT-F4-006
    titulo: "CHG-DB-002: impedir borrado físico de cuenta_staff por app_rw (OBS-QA003-01) y pg_temp al final del search_path de funciones SECURITY DEFINER (OBS-QA003-05)"
    fase: F4
    estado: DONE
    owner: base-datos
    trazabilidad: [REQ-055, RULE-017]
    depende_de: [TKT-003]
    archivos_permitidos: ["docs/04_datos/**", "docs/adr/ADR-DB-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DB_HANDOFF v1.2 (YAML válido, js-yaml por el Orquestador), ADR-DB-001/004 actualizados", "para_tkt_004 inyectado en TKT-004; para_otro_ticket (medios/contenido/catalogos/inicio) inyectado en TKT-005"]
    actualizado: 2026-09-25
  - id: TKT-OPS-004
    titulo: "DevOps: gate de contrato N9/N10/N11; límite de borde para /health (RSK-OPS-016); cabeceras de seguridad en errores del proxy (OBS-QA-OPS003-03/04); Dependabot ignora semver-major (DEC-AUTO-210)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [REQ-055, HALLAZGO-QA-OPS003-01, HALLAZGO-QA-OPS003-02, RSK-OPS-016]
    depende_de: [TKT-OPS-003]
    archivos_permitidos: [".github/workflows/**", ".github/dependabot.yml", "infra/**", "docs/05_operacion/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["PR #11 integrado en main", "QA_VERDICT PASS 1/3 @ 0210727; CI verde"]
    actualizado: 2026-09-25
  - id: TKT-OPS-005
    titulo: "DevOps: RSK-OPS-001 según decisión humana (.trivyignore solo CVE Debian sin parche con exp:2026-10-26); quitar npm del runtime frontend y pip/setuptools del runtime Python; imagen de backup mínima; Cache-Control no-store en HTML SSR (OBS-QA002-C2-04); DJANGO_TRUSTED_PROXIES en compose (OBS-QA004-03)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [RSK-OPS-001, REQ-055]
    depende_de: [TKT-OPS-004 (parte de su rama)]
    archivos_permitidos: ["infra/**", "compose*.yaml", ".env.example", ".github/workflows/**", ".trivyignore", "docs/05_operacion/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["PR #13 integrado en main", "QA_VERDICT PASS 2/3 @ e11745e; CI verde"]
    actualizado: 2026-09-25
  - id: TKT-F4-007
    titulo: "CHG-API-002: 429 LimiteTasa y 404 en saludLive/saludReady (RSK-OPS-020); 409 idempotencia_respuesta_no_reproducible para respuestas > 64 KB en cualquier operación idempotente (OBS-QA004-02); prohibir NUL en campos de texto del panel (OBS-QA004-05)"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [REQ-055, RSK-OPS-020, OBS-QA004-02, OBS-QA004-05]
    depende_de: []
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/ADR-API-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["PR #10 integrado en main", "CI verde; lint Redocly OK"]
    actualizado: 2026-09-25
  - id: TKT-OPS-006
    titulo: "DevOps LOW: gate con memoización y timeout-minutes (OBS-QA-OPS004-01); objeto abierto vs cerrado (OBS-QA-OPS004-02); 405 de medios en Problem Details (OBS-QA-OPS004-03); comentario de dependabot.yml; /infra/db en Dependabot docker (RSK-OPS-025); alerta de tamaño de cache_limites (RSK-QA004-02); política de trivy robusta a líneas de continuación (QA-OPS005-04)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [REQ-055]
    depende_de: [TKT-OPS-005]
    archivos_permitidos: [".github/workflows/**", ".github/dependabot.yml", "infra/**", "docs/05_operacion/**"]
    ciclo_qa: 3/3
    ciclo_panico: 0/2
    evidencia: ["PR #20 integrado en main (decisión humana: riesgo aceptado hasta TKT-OPS-009)", "CI verde"]
    actualizado: 2026-09-25
  - id: TKT-OPS-007
    titulo: "DevOps: restore-local.sh falla sobre BD limpia (schema app/ext, COMMENT pg_stat_statements, REVOKE public) — usar lista TOC filtrada; bloquea AC-054 y F9 (QA-OPS005-02, preexistente)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [REQ-054, AC-054]
    depende_de: [TKT-OPS-005]
    archivos_permitidos: ["scripts/ops/**", "infra/**", "docs/05_operacion/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["PR #16 integrado en main", "QA_VERDICT PASS 1/3 @ 7e5d803; CI verde tras update-branch"]
    actualizado: 2026-09-25
  - id: TKT-F4-008
    titulo: "CHG-API-003: maxLength del contrato alineado con el CHECK de BD (TextoEnriquecido 200000 -> 100000; revisar el resto de campos de texto largo)"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [DEC-AUTO-097]
    depende_de: []
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/ADR-API-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["PR #15 integrado en main", "lint Redocly OK; cliente regenerado dc2f907; CI verde"]
    actualizado: 2026-09-25
  - id: TKT-OPS-008
    titulo: "DevOps: reinstalación de medios (RSK-OPS-027); backup/restore sin tmpfs de 512 MiB (RSK-OPS-029); job CI del simulacro AC-054; post-restore no arranca la app si faltan pasos (DEC-AUTO-908); runbook: perfil ops, LIBRO_AUSENTE/avisos del libro v2 (CHG-DB-003); precondición de tipos/dominios (OBS-QAOPS007-03)"
    fase: F7
    estado: TODO
    owner: devops
    trazabilidad: [REQ-054, AC-054]
    depende_de: [TKT-OPS-007, TKT-005]
    archivos_permitidos: ["scripts/ops/**", "infra/**", "compose*.yaml", ".github/workflows/**", "docs/05_operacion/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-27
  - id: TKT-F4-009
    titulo: "CHG-API-004: parámetros de ruta de las 8 rutas públicas declarados a nivel de ruta (coherencia con el panel y el hook de esquema) + regeneración del cliente del frontend"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [DEC-AUTO-910]
    depende_de: []
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/ADR-API-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["PR #17 integrado en main", "lint Redocly OK; CI verde; sin regeneración de cliente necesaria"]
    actualizado: 2026-09-25
  - id: TKT-011
    titulo: "Backend: comando de gestión vigilar_cache_limites (alerta de tamaño de cache_limites, DEVOPS_HANDOFF §19.3.6) + línea en el crontab vía DevOps"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [RSK-QA004-02, RSK-OPS-032]
    depende_de: [TKT-005, TKT-OPS-006]
    archivos_permitidos: ["backend/apps/ops/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-28
  - id: TKT-F3-002
    titulo: "CHG-BP-001: enmienda de RULE-025/RULE-002 (co-publicación de tipos y destinos, invariante: destino publicado solo con tipos publicados) en el Blueprint (DEC-AUTO-912)"
    fase: F3
    estado: DONE
    owner: arquitecto-funcional
    trazabilidad: [RULE-002, RULE-025, THREAT-011]
    depende_de: []
    archivos_permitidos: ["docs/02_blueprint/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["PR #19 integrado en main", "Blueprint v1.1"]
    actualizado: 2026-09-25
  - id: TKT-F4-010
    titulo: "CHG-DB-003: evento REACTIVADA en el libro de anonimizaciones, 'último evento gana' y respeto de RULE-015 en desactivación por sistema (ADR-DB-004 §4, DEC-AUTO-913)"
    fase: F4
    estado: DONE
    owner: base-datos
    trazabilidad: [REQ-057, RULE-015]
    depende_de: []
    archivos_permitidos: ["docs/04_datos/**", "docs/adr/ADR-DB-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["PR #19 integrado en main", "DB_HANDOFF v1.3"]
    actualizado: 2026-09-25
  - id: TKT-F4-011
    titulo: "CHG-API-005: operaciones multi-entidad del panel (co-publicación destino+tipos, previsualización de impacto de retiro con cascada/bloqueo, errores agrupados por entidad) según CHG-BP-001; antes de TKT-006"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [AC-124, AC-125, AC-126, AC-127, AC-128, AC-130, DEC-AUTO-912]
    depende_de: [TKT-F3-002]
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/ADR-API-*.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["PR #23 integrado en main", "lint OK; cliente regenerado bc57a97; CI verde"]
    actualizado: 2026-09-25
  - id: TKT-OPS-009
    titulo: "DevOps: política de trivy también sobre canales implícitos: prohibir TRIVY_* en env/run/*.sh y trivy.yaml|.trivyignore.yaml generados (QA-OPS006-04); excepción del control negativo analizada como shell y sin otras escrituras al fichero (QA-OPS006-05); sin escrituras a .trivyignore en ejecución (OBS-C3-1); gate sin '|| true', '&' ni continue-on-error (OBS-C3-2); sha256sum -c junto a la instalación (OBS-C3-3)"
    fase: F7
    estado: TODO
    owner: devops
    trazabilidad: [RSK-OPS-001, QA-OPS006-04, QA-OPS006-05]
    depende_de: [TKT-OPS-006]
    archivos_permitidos: [".github/workflows/**", "infra/ci/**", "docs/05_operacion/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-28
  - id: TKT-OPS-010
    titulo: "DevOps: relajar el gate de contrato oasdiff a --fail-on ERR (decisión humana 2026-09-29, ver audit_log.md); los 608 hallazgos WARNING de fidelidad de formato/patrón/límites dejan de bloquear el CI, los 69 ERROR (posibles rupturas de compatibilidad: max/min-items, one-of-added, min-length/max añadidos, propiedad opcional, tipo de body cambiado) siguen bloqueando. Desbloquea TKT-006"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [DEC-AUTO-196, TKT-OPS-004]
    depende_de: []
    archivos_permitidos: [".github/workflows/**", "docs/05_operacion/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["PR #25 (rama tkt-ops-010-gate-error, worktree nuevo ops010); único cambio funcional: --fail-on WARN -> --fail-on ERROR en el paso de oasdiff de ci.yaml; docstring de gate_contrato.py y DEVOPS_HANDOFF.md §20 actualizados; RSK-OPS-035 (608 warnings sin bloquear, deuda en TKT-012) y RSK-OPS-036 (actionlint no disponible localmente, solo sintaxis YAML validada) registrados", "READY_FOR_VALIDATION; despachado a QA aunque el propio DevOps sugería que no hacía falta (consistencia con TKT-OPS-001..009, todos pasaron por QA antes de integrarse)", "CI real del PR #25 (run 36561133019) FALLÓ: --fail-on ERROR no es un valor válido del binario oasdiff (solo acepta ERR o WARN), error de uso del comando, no un hallazgo de contrato. Se devuelve a devops en la misma rama para corregir a --fail-on ERR", "Corregido y verificado en CI real: run 36562546754, TODOS los jobs en verde (backend, frontend, infraestructura, detectar código, build+trivy+SBOM). QA despachado (ciclo 1/3)", "QA_VERDICT PASS ciclo 1/3: único cambio funcional confirmado en el diff, checksum del binario oasdiff sin alterar, gitleaks/semgrep limpios, gate_contrato.py idéntico salvo comentarios, riesgo RSK-OPS-035 documentado honestamente. PR #25 integrado con git merge --no-ff @ ccaf127. TKT-OPS-010 DONE"]
    actualizado: 2026-09-29
  - id: TKT-OPS-011
    titulo: "DevOps: excepción quirúrgica y nombrada en el gate oasdiff (--err-ignore o mecanismo equivalente) para el único error restante de TKT-006: request-body-type-changed en POST /api/v1/panel/medios (multipart/form-data vs string/binary del contrato, DEC-AUTO-920). No relajar nada más; documentar motivo, alcance exacto (una sola operación) y referencia a TKT-012 para revisarlo si el contrato de subida de medios cambia"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [DEC-AUTO-196, DEC-AUTO-920, TKT-006]
    depende_de: [TKT-OPS-010]
    archivos_permitidos: [".github/workflows/**", "infra/ci/**", "docs/05_operacion/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Despachado a devops, worktree/rama nueva tkt-ops-011-err-ignore", "PR #26 entregado: infra/ci/oasdiff_err_ignore.txt + flag --err-ignore en ci.yaml; formato del mecanismo investigado contra el código fuente real de oasdiff v1.32.1 (discrepancia encontrada: el ejemplo oficial dice 'regex' pero la implementación real exige coincidencia exacta de ruta+método+texto). CI del PR verde, pero solo prueba que no rompe nada sobre las 50 operaciones ya en main (TKT-006 aún no fusionado, el caso real de multipart no se ejerce en este PR). QA despachado (ciclo 1/3) para verificación independiente del mecanismo", "QA_VERDICT PASS ciclo 1/3: QA reconstruyó el algoritmo y el mensaje exacto desde el código fuente de oasdiff v1.32.1 de forma independiente (sin reutilizar el trabajo de DevOps), coincide carácter a carácter con el hallazgo real de CI. gitleaks/semgrep limpios. PR #26 integrado con git merge --no-ff @ dfe6ee0. TKT-OPS-011 DONE. Rama tkt-006-panel-editorial actualizada con main (gh pr update-branch); pendiente confirmar en su CI real que el error de multipart por fin deja de bloquear"]
    actualizado: 2026-09-29
  - id: TKT-012
    titulo: "Backend: deuda técnica — cerrar los ~563 hallazgos WARNING de oasdiff (pattern/maxItems/minItems/content-media-type/tipo) entre el contrato y la API del panel, dejados sin bloquear por TKT-OPS-010 (decisión humana 2026-09-29); anotar format/pattern/maxItems en los serializers de los 9 recursos del panel + los que aparezcan en /publico y /panel/taxonomias. Ampliado por QA (ciclo 2/3 de TKT-006, no bloqueante): cobertura de panel_selectors.py (0% real en listar_por_tipo/FEAT-033), panel_views.py (55%) y services.py de contenido/medios (56-87%) por debajo de los umbrales tiered de Skill_Backend §8 pese a no tener defecto funcional conocido detrás; añadir tests HTTP de listar/filtrar, retirar/reactivar/revisiones/restaurar, y las ramas de rechazo de medios (formato_no_permitido/tamano_excedido/duplicado), incluido el caso 'archivo disfrazado' que el test de subida original no cubría. Ampliado por QA de TKT-007 (no bloqueante): backend/apps/contenido/management/commands/cargar_semilla.py::_configurar_inicio no incrementa el contador informativo de creados/reutilizados en su 2ª+ ejecución (blindspot de stdout, sin duplicación real en BD)"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-006, TKT-OPS-010]
    depende_de: [TKT-006, TKT-OPS-010]
    archivos_permitidos: ["backend/apps/contenido/**", "backend/apps/catalogos/**", "backend/apps/medios/**", "backend/apps/inicio/**", "backend/apps/busqueda/**", "backend/apps/core/esquema.py"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: []
    actualizado: 2026-09-29
  - id: TKT-013
    titulo: "BUG: apps/contenido/services.py publicar() reindexa el Destino en el índice de búsqueda ANTES de confirmar la publicación de sus Tipos co-publicados en la misma operación; si tipo_principal se co-publica junto al destino, este queda transitoriamente (y sin un reindexado posterior, permanentemente) fuera del índice de búsqueda pese a estar PUBLICADO y cumplir AC-129 (visibilidad exige tipo_principal ya PUBLICADO). Encontrado y verificado por el Developer de TKT-007 (4/24 destinos afectados sin el workaround aplicado solo al comando de semilla); services.py estaba fuera de su archivos_permitidos, así que el bug de fondo sigue sin corregir y afecta también al uso real del panel (co-publicación vía API), no solo a la semilla"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-007, AC-129, CHG-API-005]
    depende_de: [TKT-006]
    archivos_permitidos: ["backend/apps/contenido/services.py", "backend/apps/contenido/tests/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Despachado con análisis del Orquestador: mismo patrón de bug en publicar() (1212+1214-1216) y _actualizar_publicacion() (939+941-943); _reindexar() vive dentro de _confirmar_publicacion_entidad (línea 1074), se ejecuta por entidad en vez de una vez al final de la operación completa", "Entregado @ d4a0487, PR #28. _reindexar() sacado de _confirmar_publicacion_entidad, invocado explícitamente al final de publicar() y _actualizar_publicacion() para destino+tipos co-publicados. 2 tests de regresión nuevos confirmados por el Developer con git stash (fallan sin el fix, pasan con él). Suite completa 699 passed/1 failed (preexistente THREAT-019)/3 skipped. TKT-005/006/007 sin regresiones (227 tests). retirar()/reactivar() no tocados (análisis: sin ventana de incoherencia en esa dirección). CI real (run 36611073364) en verde completo. QA despachado", "QA_VERDICT PASS ciclo 1/3: verificación completamente independiente (worktree propio, Postgres real efímero) -- reprodujo el bug ANTES del fix con datos reales (no solo tests), revirtió el fix con git checkout HEAD~1 y confirmó que los 2 tests nuevos fallan sin él y pasan con él, confirmó por grep que los 3 sitios de producción y cargar_semilla.py conservan su reindexado. Suite completa propia: 700 passed/3 skipped/0 failed (ni siquiera reprodujo el flake THREAT-019). gate_contrato.py 128/128 propio; CI real (oasdiff) confirmado SUCCESS vía gh. gitleaks/semgrep limpios. PR #28 integrado con git merge --no-ff @ 5fb4eae. TKT-013 DONE. QA encontró un bug DISTINTO y real durante la verificación (no introducido por este diff, confirmado): retirar(T.TIPO,...) no reindexa los Destinos que lo tienen como tipo_principal -- quedan visibles en búsqueda con 404 al abrirlos. Se abre TKT-014"]
    actualizado: 2026-09-29
  - id: TKT-014
    titulo: "BUG: apps/contenido/services.py retirar(T.TIPO, ...) no reindexa los Destinos que tienen ese Tipo como tipo_principal; el propio Destino sigue PUBLICADO en BD pero deja de cumplir AC-129 (tipo_principal ya no PUBLICADO) sin que su fila en BusquedaDocumento se borre o actualice -- queda visible en resultados de búsqueda pública y devuelve 404 al abrirlo. Encontrado y reproducido con datos reales por QA durante la verificación de TKT-013 (no introducido por ese diff, confirmado preexistente); _confirmar_retiro_entidad solo reindexa la entidad que se retira, nunca las que dependen de ella"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-013, AC-129]
    depende_de: [TKT-006]
    archivos_permitidos: ["backend/apps/contenido/services.py", "backend/apps/contenido/tests/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Despachado con análisis del Orquestador: confirmado que DEC-AUTO-912(a) ya acepta el estado 'destino PUBLICADO con tipo_principal no PUBLICADO' como posible y lo trata como invisible en la API; el único bug real es que el índice de búsqueda no se actualiza para reflejarlo, no falta ninguna regla de negocio nueva -- fix acotado a reindexar dependientes, no a bloquear/cascada el retiro de T.TIPO", "Entregado @ e76c24b, PR #29. _reindexar_dependientes_de_tipo() añadida, reindexa Destinos (vía tipo_principal) e Itinerarios (vía tipos_aventura) PUBLICADOS tras retirar un Tipo directamente. 3 tests nuevos verificados con git stash. Suite completa 703 passed/0 failed/3 skipped, TKT-005/006/007/013 sin regresiones. Verificó por qué tipos_cascada (retiro de Destino) NO necesita el mismo fix: ya garantiza 0 usos publicados antes de llegar ahí. reactivar() revisado, sin el mismo bug (BORRADOR nunca es visible). HALLAZGO IMPORTANTE fuera de alcance: RULE-007/FLOW-012 del Blueprint exigen que retirar un Tipo en uso por contenido publicado esté BLOQUEADO (no solo invisible) -- confirmado también en contracts/openapi.yaml (409 dependencia_bloqueante ya documentado para este caso exacto) y en el propio código (clase DependenciaBloqueante ya definida en services.py línea 125, nunca usada). Se abre TKT-015", "CI real (run 36617834786) en verde completo. QA despachado (ciclo 1/3), con instrucción explícita de NO evaluar el gap de RULE-007 (eso es TKT-015, separado)", "QA_VERDICT PASS ciclo 1/3: verificación completamente independiente (worktree y Postgres propios), incluida verificación por SHA256 de que el binario oasdiff descargado es el release legítimo fijado en CI. Revirtió el fix con git checkout HEAD~1 (no solo stash) y confirmó que 2/3 tests fallan sin él. Derivó matemáticamente (constraint SQL fk_destino_tipo_principal_en_tipos) que tipos_cascada garantiza 0 usos publicados, sin dar por sentado el análisis del Developer. Aplicó DATA-ISOLATION-AND-LIFECYCLE.md (clase de ataque 'search/index ACL drift') y confirmó que BusquedaDocumento es el único consumidor derivado que puede desincronizarse. PR #29 integrado con git merge --no-ff @ 689511e. TKT-014 DONE"]
    actualizado: 2026-09-29
  - id: TKT-015
    titulo: "GAP: retirar(T.TIPO, ...) en apps/contenido/services.py no bloquea el retiro directo de un Tipo de aventura en uso por Destinos o Itinerarios PUBLICADOS, pese a que RULE-007/FLOW-012 del Blueprint lo exigen explícitamente ('No se puede retirar un Tipo... en uso por contenido publicado'; 'el uso por destinos publicados se resuelve retirando el último destino -cascada-; nunca de forma directa'), y el contrato ya documenta 409 dependencia_bloqueante para este caso exacto (contracts/openapi.yaml líneas 2439-2441: 'dependencia_bloqueante queda solo para los usos de RULE-007... un tipo en uso por destinos publicados nunca se retira de forma directa'). La excepción DependenciaBloqueante ya existe en services.py (línea 125) pero nunca se usa -- implementar el bloqueo con la lista de usos, siguiendo el mismo patrón ya implementado en apps/catalogos/services.py para País/Región/Categoría/Licencia (DependenciaBloqueante con extra usos/total_usos) y en apps/medios/services.py (MedioEnUso). No toca el contrato (el código de error y su semántica ya están documentados). Encontrado por el Developer de TKT-014 durante su investigación, no introducido por ningún diff reciente"
    fase: F7
    estado: IN_PROGRESS
    owner: Skill_Developer
    trazabilidad: [TKT-014, RULE-007, FLOW-012, FEAT-037]
    depende_de: [TKT-014]
    archivos_permitidos: ["backend/apps/contenido/services.py", "backend/apps/contenido/tests/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Despachado: TKT-014 integrado, ya no hay solapamiento de archivo. Reutilizar _destinos_publicados_de_tipo() y el patrón de _bloqueos_de_cascada() ya existentes para construir la lista de usos", "Entregado @ 3c9b8cb, PR #30. _usos_publicados_de_tipo() añadida; retirar() con tipo==T.TIPO ahora levanta DependenciaBloqueante(usos/total_usos) antes de confirmar, si el tipo es tipo_principal de un destino publicado o lo usa un itinerario publicado. Rama T.DESTINO/cascada sin tocar. 5 tests nuevos (706 passed total, 0 failed). Alcance documentado explícitamente: NO bloquea si el tipo es solo secundario (no principal) de un destino publicado -- riesgo residual bajo, mitigado por RULE-001 v1.1, con test propio que lo deja trazado en vez de oculto. CI real (run 36623872475) en verde completo. QA despachado (ciclo 1/3), con instrucción explícita de re-evaluar por su cuenta la decisión de alcance (tipo secundario no bloqueado)"]
    actualizado: 2026-09-29
```

## F5 — Reglas de stack inyectadas (Orquestador, leídas de los Contratos Técnicos el 2026-09-25)
```yaml
stack_fijado:
  frontend:   # Skill_Frontend §2, §4, §7, §13, §27
    framework: "Angular 22, zoneless, Signals, httpResource, standalone"
    estructura: "src/app/{core/{http,auth,forms}, shared/ui, features/<MOD>/{ui,state,data,domain}}; nombres de features desde MOD-XXX del Blueprint"
    cliente_api: "DTO y cliente GENERADOS desde contracts/openapi.yaml (openapi-typescript o ng-openapi-gen); prohibido DTO a mano; CI falla si difiere"
    errores: "ErrorApi mapea RFC 9457: type->tipo, title/detail->mensaje, errors->campos, trace_id->traceId"
    seguridad: "sin bypassSecurityTrust*, sin innerHTML no saneado, sin eval; CSP estricta sin unsafe-inline en scripts (RSK-UX-001: nonce o desactivar inlining de CSS crítico del SSR); XSRF cookie csrftoken/cabecera X-CSRFToken; mismo origen vía proxy; nada de tokens en localStorage; npm audit --audit-level=high limpio"
    observabilidad: "interceptor traceparent W3C; ErrorHandler global sin PII"
    cobertura: "domain >=90 %, state >=80 %, global >=70 %"
    e2e: "@playwright/test con data-testid por FLOW crítico; @axe-core/playwright 0 serious/critical por ruta"
    diseno: "docs/03_diseno/tokens.json + HANDOFF_UI_UX.yaml; Angular CDK + Tailwind; fuentes WOFF2 y Lucide autoalojados; sin CDN"
  backend:    # Skill_Backend §2, §4, §7, §12
    framework: "Django 5.2 + DRF + drf-spectacular; monolito modular"
    capas: "apps/<dominio>/{api/(views,serializers,urls), services.py, selectors.py, models.py}; services sin Request/Response/serializers"
    errores: "RFC 9457 application/problem+json con code y trace_id obligatorio (X-Trace-Id)"
    auth: "sesión Django + CSRF (ADR-API-001); sin JWT"
    seguridad: "ASVS L2; permisos por objeto + test de acceso horizontal; throttling; CORS explícito; cabeceras check --deploy; subida de medios validada por contenido (DEC-AUTO-044); cada THREAT-XXX con test; bandit, pip-audit, semgrep p/django, gitleaks"
    observabilidad: "logging JSON (structlog) con trace_id, sin PII; OpenTelemetry HTTP+ORM; /health/live y /health/ready"
    asincronia: "SIN Celery ni broker (CONFLICT-001 / DEC-AUTO-122): comandos de gestión con advisory lock"
    contrato: "implementar contra contracts/openapi.yaml; diff semántico con oasdiff; schemathesis sin 5xx"
    versiones: "dependencias Python con == y lockfile (Skill_Developer §16.2)"
  datos:      # Skill_Base_datos §4, §7
    motor: "PostgreSQL 18.6 (DEC-AUTO-080)"
    fuente: "docs/04_datos/DB_HANDOFF.yaml + ADR-DB-001..005"
    migraciones: "Django migrations, expand/contract, reversibles; RunSQL solo donde lo indica DB_HANDOFF con pruebas de introspección"
    roles: "app_rw sin DDL; app_migrator con DDL; readonly; app_backup"
  proceso:    # Skill_Developer §16
    cli_first: "ng new / ng generate; django-admin startproject / manage.py startapp"
    versiones_exactas: ".npmrc save-exact=true; sin ^ ni ~"
    pruebas_ac: "cada AC-XXX con test nombrado test_AC_XXX_*"
    ramas: "tkt-XXX-descripcion; commits convencionales; nunca a main"
  entorno: "Docker Compose local (F6); sin despliegue ni costes (DEC-AUTO-002)"
```

## Conflictos
```yaml
conflictos:   # CONFLICT-XXX (CLAUDE.md §0.1)
  - id: CONFLICT-001
    partes: ["Skill_Backend §2/§12.3/§12.4 (Celery + broker como referencia)", "Skill_Base_datos §4.E + ADR-DB-005 / DEC-AUTO-090 (sin broker)"]
    rango: "igual (nivel 4, Contratos Técnicos)"
    resolucion: "DEC-AUTO-122: sin Celery ni broker en el MVP. No hay tareas asíncronas ni efectos externos; los trabajos periódicos son comandos de gestión con advisory lock. §12.4 condiciona el broker a que exista Celery. Gate OBSERVABILITY: trazas Celery = NOT_APPLICABLE. Reversible: se introduce Celery+broker con ADR si aparece trabajo asíncrono"
    estado: RESUELTO
```

## Bloqueados que requieren intervención humana
```yaml
blocked_human: []   # CLAUDE.md §0.5 y §0.7
```
