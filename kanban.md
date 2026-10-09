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
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-001, MOD-002, MOD-003, MOD-006, MOD-008]
    depende_de: [TKT-002, TKT-007]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/app.spec.ts", "frontend/src/app/core/layout/**", "frontend/src/app/features/inicio/**", "frontend/src/app/features/destinos/**", "frontend/src/app/features/guardados/**", "frontend/e2e/**"]
    ciclo_qa: 3/3
    ciclo_panico: 0/2
    evidencia: ["Despachado. Primer ticket de frontend de esta sesión; TKT-002 (base) ya construyó cliente API generado, shared/ui (tarjeta-contenido, medidor-dificultad/presupuesto, paginacion, migas-de-pan, etc.), core/layout (cabecera/pie/menu-movil/banner-sin-conexion, páginas de error 404/410/500), core/seo -- se instruyó inventariar antes de construir, por Skill_Frontend.md ETAPA 1", "Entregado @ PR #33. 3 features nuevas (inicio, destinos, guardados) + interacciones globales Compartir/Guardar en core/layout. BUG CRÍTICO encontrado y corregido probando contra backend real + semilla real (no un mock): DestinoDetalleStore/DestinosListadoStore/DestinosDelMesStore con providedIn:'root' resolvían ActivatedRoute de la ruta RAÍZ, nunca la ruta activa -> 404 permanente en toda ficha de destino y cada mes; corregido proveyendo cada store en el componente de su ruta. Accesibilidad: target-size de los marcadores del mapa corregido (axe 0 serious/critical). 255/255 tests unitarios, cobertura domain ≥90%/state ≥80%/global ≥70% cumplidos. E2E contra stack real con Docker+semilla TKT-007, 26 pruebas nuevas. 3 simplificaciones de alcance documentadas (mapa decorativo no geográfico real, filtros sin hoja modal en móvil, listas sin 'ver más'). CI real: falló exactamente el gap que el propio Developer ya había señalado -- app.spec.ts (fuera de su alcance original) prueba la página placeholder que este ticket sustituye a propósito. Se amplía archivos_permitidos con ese único archivo (DEC-AUTO, mismo patrón que TKT-006/esquema.py) y se devuelve para el ajuste de una línea", "Corrección @ 45fc12e: cuestionó mi sugerencia de testid antes de aplicarla (verificó con debug que en un test unitario sin backend real la página cae en su rama de error, no de éxito) y usó un criterio más robusto (host del componente + ausencia de 404), mismo patrón que shell.spec.ts/ssr-csp.spec.ts. 258/258 tests sin exclusiones. CI real (run 36652541319) en verde completo, todos los jobs. QA despachado (ciclo 1/3)", "QA_VERDICT FAIL (ciclo 1/3), auditoría propia e independiente (worktree propio, Docker+semilla real, axe-scan y Lighthouse propios): tests/arquitectura/seguridad/contrato PASS (2 notas no bloqueantes), bug de enrutamiento de PR#33 reconfirmado correcto en destinos reales. 4 hallazgos CONFIRMADOS: (1) CRÍTICO a11y -- aria-pressed en <a [routerLink]> del panel de filtros de pagina-destinos.html (~30 nodos, rol 'link' no admite aria-pressed); (2) MEDIO regresión -- e2e/shell.spec.ts:46 aserto de orden de nav no incluye los 2 links nuevos (Cuándo ir/Guardados), falla solo en proyecto WebKit; (3) MEDIO gap de autoría E2E -- guardados.spec.ts:66 (AC_TKT008_09) usa context.grantPermissions(clipboard-*), no soportado por Playwright fuera de Chromium, falla en Firefox/WebKit; (4) ALTO performance -- CLS=1.001 en Inicio vs ≤0.1 (Skill_UI_UX §47.2), Lighthouse señala app-pie-sitio desplazándose en ~2 eventos acumulados. Se devuelve a Developer para corrección (ciclo 2/3 pendiente).", "Corrección @ 13069b8 (PR #33): 3 de 4 hallazgos corregidos y verificados en verde de forma reproducible -- (1) a11y: aria-pressed -> aria-current en los 6 grupos de filtros de pagina-destinos.html (los <a> navegan por queryParams, es un conjunto de enlaces con selección vigente, no un grupo de botones toggle), axe 0 violaciones serious/critical en /destinos en los 3 motores; (2) shell.spec.ts:46 corregido, y de paso encontró y corrigió una carrera real en WebKit (Enter sobre un enlace enfocado por .focus() podía perderse por completo, no solo lentitud) sustituyendo por locator.press/click según el motor -- verde x4+ en chromium/firefox/webkit; (3) guardados.spec.ts AC_TKT008_09 reescrito para mockear navigator.clipboard vía addInitScript en vez de context.grantPermissions (solo Chromium) -- verde en firefox/webkit; en chromium el propio Developer no logró una corrida limpia en su máquina y documentó la causa con evidencia (rate-limiter real de publico-lectura con caché en Postgres TTL≤1h agotado por su propia sesión de depuración del CLS, más un fallo aislado de carga de chunk bajo ~80% de RAM en uso) -- se pide a QA reconfirmar en su propio entorno. 261/261 tests unitarios, eslint y tsc limpios. (4) CLS de Inicio: implementó y verificó unitariamente un fix real (InicioRepositorio usa TransferState para no repetir /publico/inicio tras hidratación) pero midió con PerformanceObserver propio que el CLS real SIGUE por encima de 0.1 de forma intermitente (0 a 1.16) tras el fix -- investigó y descartó 4 hipótesis (doble fetch, imágenes rotas, remount real del footer vía MutationObserver, esqueleto SSR) sin aislar la causa raíz, y encontró que el MISMO fenómeno ocurre también en /destinos (página que no tocó para esto), lo que apunta a un problema compartido de shell/hidratación y no a algo específico de Inicio. Reportó con total transparencia en vez de forzar un PASS (checks_marcados_not_pass_honestamente). Hallazgo colateral no corregido (fuera de su archivos_permitidos): las imágenes de portada de los destinos devuelven 404 en el stack Docker real (URL bien construida por la API, archivo físico ausente).", "QA_VERDICT FAIL (ciclo 2/3), verificación independiente completa (worktree y stack Docker propios desde cero, semilla real, 3 navegadores, múltiples repeticiones aisladas con trace inspeccionado): a11y CONFIRMADO PASS (0 violaciones en los 3 motores, aria-current correcto). 2 fallos e2e reales: (A) el propio fix de shell.spec.ts del ciclo 2 INTRODUJO una regresión nueva en Chromium (~35-40% de fallos reproducidos en 3 tandas independientes, sistema ocioso): locator.press('Enter') reenfoca el elemento por script en vez de reutilizar el foco real de Tab, reintroduciendo la misma clase de carrera que motivó el fix de WebKit; contraprueba confirma que el código PRE-ciclo-2 (page.keyboard.press('Enter') global) era 100% fiable en los 3 motores. Firefox y WebKit siguen verdes. QA marca esto como posible bug real de UX de teclado en Chromium, no solo un artefacto de test -- pide investigarlo, no solo 'arreglar el test'. (B) AC_TKT008_09 falla 100% en Chromium en el entorno de QA, pero el CÓDIGO DEL FIX DE CICLO 2 SE VERIFICÓ CORRECTO de forma aislada (9/9 PASS en los 3 motores bloqueando peticiones de imagen): la causa real es que una sola carga de /destinos dispara ~69 peticiones casi simultáneas que exceden el límite de borde nginx (burst=60, infra/proxy/nginx.conf, fuera de archivos_permitidos de TKT-008) -- hallazgo de PRODUCCIÓN real (rompería la navegación a fichas para cualquier visitante con caché fría), no un defecto de este ticket; amplificado por los 404 de medios ya rastreados en TKT-017. Se abre TKT-018 para ese hallazgo (DEC-AUTO). CLS medido de nuevo, mucho más severo y 100% reproducible que lo reportado antes (Inicio 1.609, /destinos 0.674) -- línea base actualizada en TKT-016, sigue sin ser criterio de TKT-008. Se devuelve a Developer para ciclo 3/3 (ÚLTIMO ciclo disponible antes de BLOCKED_HUMAN por §0.7): (1) corregir la regresión real de Chromium en shell.spec.ts investigando si es un bug de aplicación o solo semántica de locator.press() vs Tab real; (2) ajustar guardados.spec.ts AC_TKT008_09 para no depender de disparar el burst completo de imágenes de /destinos (p. ej. bloquear peticiones de imagen no relevantes para el aserto de portapapeles, como hizo QA en su repro aislada), sin tocar infra/**.", "Corrección @ 4c76977 (PR #33), ciclo 3/3: (1) shell.spec.ts revertido en la rama chromium/firefox a page.keyboard.press('Enter') global sin reenfoque -- exactamente el código que QA validó como fiable; antes de aplicarlo, el Developer investigó si el problema podía ser de la app real (revisó cabecera-sitio.ts, sin ningún handler de teclado que intercepte Enter) y concluyó que es una diferencia de semántica interna de Playwright, no un bug de producto. HALLAZGO ADICIONAL propio: hizo un experimento A/B reconstruyendo shell.spec.ts tal como estaba en 22153c9 (antes de cualquier cambio de este ticket) y lo corrió 8 veces en Chromium en su máquina: 4/8 fallaron con el MISMO síntoma que QA reportó como 'regresión del ciclo 2' -- evidencia de que la intermitencia en Chromium ya existía en el código ORIGINAL de TKT-008 y no fue introducida por ningún cambio de este Developer; sugiere que puede ser una condición de máquina/carga, no del código. Esto contradice parcialmente la lectura de QA en el ciclo 2 (que su propia repro aislada del código pre-ciclo-2 fue 100% fiable) -- evidencia en conflicto entre dos entornos distintos, requiere que QA reconfirme en su propio entorno como árbitro. (2) guardados.spec.ts AC_TKT008_09 aislado en su propio test.describe con page.route bloqueando /media/** antes de navegar, replicando la técnica exacta de QA; el resto de AC_TKT008_06/07/08 no se tocó. HALLAZGO NUEVO propio, reportado con total transparencia: en repeticiones locales tras el fix, WebKit mostró ~1/3 de fallos con un síntoma DISTINTO (toast de portapapeles no aparece a tiempo) -- investigó y descartó 3 hipótesis (bloqueo de medios como causa, abort vs fulfill(404), timeout en el servicio de compartir) sin aislar la causa raíz; recomienda que la validación de QA en su entorno sea la confirmación autoritativa, igual que para el punto 1. 261/261 tests unitarios, eslint/tsc limpios. Ningún archivo fuera de frontend/e2e/** tocado; infra/proxy/nginx.conf no tocado (correcto, es de TKT-018). QA despachado (ciclo 3/3, el último antes de BLOCKED_HUMAN).", "QA_VERDICT PASS (ciclo 3/3), árbitro final independiente en entorno propio (worktree y stack Docker nuevos): shell.spec.ts 160/160 PASS (Chromium 10/10 repeticiones x8, Firefox+WebKit 5/5 x8, 0 fallos) con el código revertido a page.keyboard.press('Enter'); guardados.spec.ts AC_TKT008_09 39/39 PASS en los 3 motores, incluidas 23/23 repeticiones extra en WebKit específicamente para descartar la fragilidad de toast que reportó el Developer (con 33% de tasa de fallo real, la probabilidad de 23/23 éxitos sería ~0.006% -- confirma con alta confianza que el fix es fiable). git diff 13069b8..4c76977 verificado: solo los 2 archivos e2e tocados, gitleaks/semgrep limpios, a11y/contrato/seguridad PASS heredado del ciclo 2 (código de aplicación sin cambios). TKT-008 CIERRA SUS 3 CICLOS DE QA CON PASS. Hallazgo adicional no bloqueante: reprodujo el mismo patrón de 429 de TKT-018 corriendo el archivo guardados.spec.ts completo (no solo el AC aislado), reforzando la prioridad de ese ticket -- no bloquea este PASS. Integración pausada: CI real de PR #33 (run 36668871573) está en rojo por CVE-2026-84782 (HIGH, openssl, imagen brujula/db), sin relación con el código de este ticket (drift de la base de trivy detectado entre dos runs del mismo branch en <3h) -- Puerta Humana Obligatoria (§0.5), usuario decidió 'aceptar con lista y caducidad' (GATE_HUMANO en audit_log.md). Se abre TKT-OPS-013 para que DevOps añada la excepción; TKT-008 queda BLOCKED (no BLOCKED_HUMAN -- no es un fallo de este ticket) hasta que ese PR esté verde y se pueda reintentar el merge.", "Bloqueo resuelto: TKT-OPS-014/TKT-OPS-015 corrigieron el CVE de raíz (no por excepción) en las 6 imágenes, PR #34 integrado en main (f2699ba). Se sincronizó la rama de este ticket con gh api -X PUT pulls/33/update-branch para que su propio build de imágenes recoja los Dockerfiles corregidos; esperando el nuevo CI real antes de reintentar el merge.", "CI real (run 36713037433) tras la sincronización: 6/6 jobs no opcionales en pass, incluido 'build + trivy + SBOM'. Verificado por el Orquestador que el único diff entre el commit ya validado por QA (4c76977) y el nuevo HEAD (0ea08f7) son los archivos de infra/docs traídos de main (sin tocar ningún archivo de código de este ticket) -- el veredicto PASS de QA sigue vigente sin necesidad de un nuevo ciclo. PR #33 integrado con gh pr merge --merge @ 8b72a64. Main local reconciliado con git merge (sin conflictos). TKT-008 DONE -- primer ticket de frontend completo de esta sesión: 3 features (inicio, destinos, guardados), 1 bug crítico de enrutamiento encontrado y corregido, 3 ciclos de QA con 1 CRÍTICO de a11y y 3 hallazgos MEDIO/ALTO corregidos, 4 tickets colaterales abiertos (TKT-016 CLS compartido, TKT-017 imágenes 404, TKT-018 riesgo de rate-limit, más la cadena TKT-OPS-013/014/015 del CVE de openssl)."]
    actualizado: 2026-09-30
  - id: TKT-016
    titulo: "Investigar y corregir la causa raíz de un layout-shift compartido del shell/hidratación (no específico de una página): CLS medido de forma intermitente entre 0 y 1.16 tanto en Inicio como en /destinos (Skill_UI_UX §47.2 exige ≤0.1), con app-pie-sitio desplazándose 300-420ms después de la hidratación. Documentado por el Developer de TKT-008 tras descartar 4 hipótesis específicas de Inicio (doble fetch ya corregido con TransferState, imágenes rotas, remount real del footer, esqueleto SSR) sin aislar la causa; puede requerir tocar frontend/src/app/app.config.ts (fuera del alcance de un solo Developer-ticket previo, con una restricción de CSP ya documentada ahí por TKT-002 sobre event replay que hay que respetar)"
    fase: F7
    estado: READY_FOR_VALIDATION
    owner: Skill_Developer
    trazabilidad: [MOD-001, MOD-002, "Skill_UI_UX#47.2"]
    depende_de: [TKT-008]
    archivos_permitidos: ["frontend/src/app/app.config.ts", "frontend/src/app/core/layout/**", "frontend/src/app/features/inicio/**", "frontend/src/app/features/destinos/**", "frontend/e2e/**", "frontend/src/app/features/*/state/*.store.ts", "frontend/src/app/features/*/state/*.store.spec.ts"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Línea base actualizada por QA (ciclo 2/3 de TKT-008, entorno propio 100% reproducible, sin ruido de rate-limit durante la medición): CLS Inicio = 1.609 (2 corridas idénticas), CLS /destinos = 0.674 (1 corrida) -- notablemente más severo que la primera medición del Developer (0-1.16 intermitente). QA recomienda revisar la prioridad de este ticket al alza dado el nivel de reproducibilidad y severidad.", "Dato de TKT-020 (A/B igual en main): /creditos con CLS 0.398 y /acerca-de con 1.12 en Chromium, en ambos casos por el desplazamiento de app-pie-sitio. Es probablemente la misma causa raíz de este ticket: incluir esas rutas en la verificación.", "QA TKT-010 c3: CLS de /destinos bimodal (0.25/0.67/0.95), /acerca-de 1.181 e Inicio (AC_TKT008_14 falla 6/10 en main y en la rama), todo preexistente.", "2026-10-09 PR #75 @ 2d35b12: causa raíz = resource() sin id no transfiere el valor del SSR y la hidratación pasa por el esqueleto; corregido en inicio y destinos (CLS ≤0,0002 en 3 motores x3, 135 E2E PASS). BLOCKED por 8 rutas cuyos stores estaban fuera de alcance -> DEC-AUTO-980 amplía a features/*/state/*.store(.spec).ts. CI rojo solo por CVE-2026-78667 (TKT-OPS-031).", "2026-10-09 PR #75 @ 1731b61: id en resource() de todos los stores públicos (clave con los parámetros de la URL); 24 rutas públicas CLS ≤0,0014 salvo guía 0,009 y /guardados 0,0507, 0 nodos SSR retirados; cls-hidratacion 243/243 en 3 motores x3; unit 661. QA ciclo 1/3 despachada."]
    actualizado: 2026-10-08
  - id: TKT-017
    titulo: "GAP de datos/medios: las imágenes de portada de los destinos devuelven 404 en el stack Docker real (la API construye bien la URL del derivado, p. ej. /media/publico/medios/derivados/<hash>-800.avif, pero el archivo físico no se sirve). Hallazgo colateral del Developer de TKT-008 durante la investigación de CLS; probablemente relacionado con la generación de derivados del comando de semilla de TKT-007 o con el montaje de volúmenes de medios. Investigar causa raíz; si resulta ser configuración de infraestructura/volúmenes (no código de aplicación), usar Botón de Pánico hacia DevOps en vez de tocar infra/** directamente"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-007, MOD-001]
    depende_de: [TKT-007]
    archivos_permitidos: ["backend/apps/medios/**", "backend/seed/**", "backend/apps/contenido/management/commands/cargar_semilla.py"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Despachado con prioridad elevada: QA confirmó en TKT-009 ciclo 2/3 que estos 404 son el mayor contribuyente a la ráfaga de peticiones que agota el limitador de nginx (TKT-018, ahora confirmado 100% reproducible en Chromium, riesgo crítico de navegación rota). Se prioriza este ticket antes que TKT-010 (panel) porque reducir la ráfaga aquí puede resolver o acotar TKT-018 sin tocar infra/proxy/nginx.conf.", "Entregado @ PR #36 (rama tkt-017-fix-medios-publico-privado). CAUSA RAÍZ REAL encontrada por investigación directa (NO era volumen/montaje Docker como se sospechaba -- era código de aplicación): apps/medios/services.py guardaba TODOS los archivos (originales y derivados) bajo MEDIA_ROOT/medios/**, una ruta que nginx nunca expone (solo sirve MEDIA_ROOT/publico/**) -- el layout publico/privado con permisos 0644/0640 ya estaba documentado en DEVOPS_HANDOFF.md §6 y DEC-AUTO-147, pero TKT-006 nunca lo implementó. La URL pública que construye la API siempre fue correcta; el archivo físico nunca estuvo donde nginx lo busca. Fix: derivados se generan en privado/, catalogar() los mueve a publico/ al pasar a DISPONIBLE, retirar() los devuelve a privado/, el original saneado vive siempre en privado/ (nunca se sirve, THREAT-023). Verificado en stack Docker real (rebuild limpio + cargar_semilla x2 para idempotencia): 732/732 derivados públicos reales devuelven 200 (antes 100% 404); privado/** y el prefijo legado siguen en 404 (nada expuesto de más); permisos físicos verificados dentro del contenedor. 718 passed/4 skipped, cobertura total 89.95% (umbral real 80%, cumplido; services.py queda en 87% pero las líneas no cubiertas son ramas preexistentes fuera de este ticket, detalladas y justificadas). 7 tests nuevos cubren la causa raíz. IMPORTANTE para TKT-018: el Developer midió que este fix elimina el 404 en sí y habilita cache-control (max-age=31536000) para visitas repetidas, pero NO reduce el número de peticiones que el frontend dispara en una carga en frío -- el burst de ~69/~40 peticiones simultáneas sigue intacto y TKT-018 sigue reproduciéndose igual en frío; TKT-018 necesita su propio fix (lado frontend y/o nginx), no se resuelve como efecto colateral de este ticket. Divergencia detectada y corregida por el Orquestador: origin/main estaba 1 commit detrás del main local usado como base (contenido verificado idéntico, byte a byte, no era ajeno) -- main empujado a origin antes de verificar CI. CI real del PR #36 verificado en verde completo por el Orquestador (run 36739030708, todos los jobs requeridos PASS). QA despachado.", "QA_VERDICT PASS (ciclo 1/3), verificación completamente independiente (worktree y stack Docker propios desde cero, semilla real cargada por QA, editor real creado por QA, sin reutilizar ninguna evidencia del Developer): 60/60 portadas reales (todos los tipos de contenido + hero de inicio) devuelven 200 vía curl real, Content-Type y Cache-Control correctos; negativos confirmados (privado/**, prefijo legado medios/** -> 404); permisos físicos verificados dentro del contenedor (0644/0640, sin directorio legado). Ciclo de estado completo probado contra la API real del panel (login con CSRF real, no solo tests unitarios): subida->privado, catalogar->publico (FS+nginx confirmados), retirar->privado (FS+nginx confirmados). Idempotencia de cargar_semilla reconfirmada. Regresión completa: 718 passed/4 skipped, cobertura 89.99%, ruff/mypy limpios. Verificó la cobertura de services.py (89% en su corrida) comparando contra el commit BASE (antes de TKT-017) con el mismo subconjunto de pruebas -- confirmó que el gap ya existía antes del ticket (87%->89%, TKT-017 en realidad la mejora) y ninguna línea sin cubrir pertenece al código nuevo. gitleaks/semgrep limpios, contrato NOT_APPLICABLE, THREAT-023 confirmado (original saneado nunca servible, en ningún estado, por prueba física+HTTP). PASS SIN HALLAZGOS BLOQUEANTES. Nota de cobertura añadida a TKT-012 (no bloqueante, preexistente). Confirmó de forma independiente (96 URLs de imagen distintas por página, todas 200) que el fix no reduce el volumen de peticiones -- refuerza lo ya sabido sobre TKT-018, sigue pendiente. PR #36 sincronizado con main (estaba BEHIND tras los commits de documentación del Orquestador) y reverificado. CI real re-verificado en verde completo tras la sincronización (run 36749972530). PR #36 integrado con gh pr merge --merge @ 234e4c6. Main local reconciliado (fast-forward limpio). TKT-017 DONE -- causa raíz real del gap de medios de TKT-008/009 corregida en origen."]
    actualizado: 2026-09-30
  - id: TKT-018
    titulo: "RIESGO DE PRODUCCIÓN: una sola carga en frío (caché vacía) de /destinos dispara ~69 peticiones casi simultáneas (medido: mayoritariamente derivados de imagen), superando el burst=60 del límite de borde nginx por IP (infra/proxy/nginx.conf, limit_req_zone zone=por_ip, defensa en profundidad documentada en DEC-AUTO-111/190/193/195/214). Produce 429 reales que rompen la navegación a fichas de destino para cualquier visitante real con caché fría -- no es un artefacto de test (encontrado y aislado por QA en TKT-008 ciclo 2/3 investigando el fallo de guardados.spec.ts AC_TKT008_09; el código de ese test se verificó correcto de forma aislada). Amplificado por TKT-017 (cada 404 de imagen sigue consumiendo cupo del limitador). Investigar ambos lados antes de decidir: (a) si /destinos puede reducir el número de peticiones casi simultáneas (lazy-loading más agresivo, priorización, batching); y/o (b) si el burst de nginx necesita recalibrarse para tolerar una carga legítima de página completa. Si la conclusión es (b) o mixta, el ajuste de infra/proxy/nginx.conf es de DevOps -- el Developer no debe tocar ese archivo directamente (usar Botón de Pánico o reportar al Orquestador para repartir el ticket)"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-008, TKT-017, "DEC-AUTO-111", "DEC-AUTO-190", "DEC-AUTO-193", "DEC-AUTO-195", "DEC-AUTO-214"]
    depende_de: [TKT-008, TKT-017]
    archivos_permitidos: ["frontend/src/app/features/destinos/**", "frontend/src/app/shared/ui/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir del hallazgo de QA en TKT-008 ciclo 2/3 (HANDOFF agente a4ecfe6891e3f069b): reproducido con logs JSON del proxy, 429 en la misma marca de segundo que ráfagas de 404 de TKT-017; reproducible incluso tras 30s de reposo total del cupo del limitador porque la propia carga de /destinos ya excede el burst por sí sola.", "REFORZADO Y AGRAVADO por QA en TKT-009 ciclo 1/3 (HANDOFF agente aa764ec0f042e41cd): confirmado que el 429 del limitador de borde puede tumbar también los CHUNKS JS de lazy-loading de rutas de Angular ('Failed to fetch dynamically imported module'), no solo peticiones de imagen -- el router nunca completa la navegación y la URL se queda en la anterior. Esto significa que el riesgo no es solo 'imágenes rotas para visitantes con caché fría', sino potencialmente 'navegación completa rota' en cualquier página con suficientes peticiones de imagen previas (confirmado en /guias tras pasar por /destinos). Eleva la prioridad de este ticket.", "SEVERIDAD ELEVADA A CRÍTICA por QA en TKT-009 ciclo 2/3 (HANDOFF agente ae69535e774643b37): reproducido 10/10 en Chromium (el motor más usado) en un stack recién levantado con semilla real, sin ninguna otra prueba corriendo antes -- ya no es 'puede romper bajo ciertas condiciones', es 100% reproducible en el flujo normal Inicio→cualquier página. QA recomienda evaluarlo como bloqueante de F9/release. Decisión de secuenciación del Orquestador: dado que TKT-017 (404 reales de imágenes) es la causa que MÁS peticiones añade a la ráfaga (mayoría de las ~40+ peticiones que agotan el burst son 404 que no deberían existir), se prioriza TKT-017 primero -- puede reducir la ráfaga lo suficiente para que TKT-018 deje de reproducirse sin tocar nginx, o al menos acotar cuánto ajuste de frontend/infra hace falta después. TKT-017 se despacha antes que TKT-010 (panel).", "CORRECCIÓN a la hipótesis anterior: el Developer de TKT-017 midió directamente el efecto de su fix sobre este problema. El fix elimina el 404 en sí (cada petición de imagen ahora es un acierto cacheable, Cache-Control: immutable/max-age=31536000) pero NO reduce el número de peticiones que el frontend dispara en una carga en frío -- eso depende de cómo Angular renderiza picture/srcset, fuera del alcance de TKT-017 (backend/apps/medios). El burst de ~69/~40 peticiones simultáneas sigue intacto y este ticket sigue reproduciéndose igual en frío tras TKT-017. Beneficio real de TKT-017 para este ticket: mejora las cargas repetidas del mismo visitante (cache-control ahora alcanzable), pero NO resuelve la carga en frío -- este ticket sigue necesitando su propio fix (reducir fan-out de peticiones en el frontend y/o recalibrar el burst de nginx).", "Despachado a Developer tras cerrar TKT-017. archivos_permitidos sin cambios (destinos/** + shared/ui/**) porque tarjeta-contenido e imagen-responsiva (shared/ui) son los componentes centralizados que renderizan imágenes en TODAS las páginas de listado (destinos, itinerarios, guías, tipos, colecciones) -- un fix ahí se propaga automáticamente sin tocar cada feature. Instrucción explícita: si la investigación concluye que hace falta recalibrar infra/proxy/nginx.conf, usar Botón de Pánico o reportar al Orquestador para repartir el ticket, no tocarlo directamente.", "Entregado @ PR #37 (rama tkt-018-diferir-imagenes-fuera-de-viewport). Causa raíz de la investigación: loading='lazy' nativo YA estaba declarado pero es INEFECTIVO en la práctica -- Chromium en conexión sin limitar trata una rejilla completa de 24 tarjetas como 'cerca del viewport' y dispara las 24 peticiones casi en el mismo milisegundo (confirmado: 594-595ms). El srcset YA deduplicaba correctamente por ancho (no era el problema). Fix: IntersectionObserver propio (margen 300px) en ImagenResponsiva (shared/ui, componente centralizado -> se propaga a TODOS los listados sin tocar cada feature, confirmado en /guias sin haberlo tocado), retiene src/srcset hasta que la imagen está realmente próxima al viewport, igual en SSR y primer render de cliente (sin mismatch de hidratación, diseñado explícitamente para evitarlo), loading='lazy' nativo conservado como respaldo de degradación progresiva. Imágenes prioritarias (LCP) sin cambios. MEDICIÓN REAL antes/después (mismo método que QA, Docker+semilla real): escenario exacto de TKT-008/009 (Inicio -> clic a enlace a los 300ms) 0/3 reproducciones de 429 (antes: sin margen, reproducible); /destinos carga directa: peticiones de imagen 24->6, totales 48->30; /guias (no tocada) confirma propagación, 0 429. Estrés adicional (más allá del escenario del ticket): suite e2e completa en serie sin reiniciar el limitador entre páginas, 429 reales en logs del proxy 295->23 (-92%), e2e fallidas 6/22->3/22. 415/415 tests unitarios (3 nuevos), eslint/tsc limpios, build íntegro. CI real del PR en verde completo. RIESGO RESIDUAL declarado con evidencia (no Botón de Pánico, porque el escenario específico del ticket SÍ queda resuelto): bajo navegación rápida y sostenida por muchas páginas seguidas, persisten 429 reales (92% menos, no cero) -- 2 de las 3 e2e que aún fallan muestran el patrón de TKT-009; la 3ª es el CLS preexistente de TKT-016, no relacionada. Hallazgo colateral no corregido (fuera de alcance): construirSrcset puede terminar sirviendo siempre el candidato AVIF sin declarar tipo MIME por candidato (código preexistente de TKT-002, no su deduplicación). QA despachado, con instrucción de validar el escenario exacto y evaluar independientemente si el riesgo residual amerita ticket de recalibración de nginx.", "QA ciclo 1/3 INTERRUMPIDO (primer intento): el subagente QA cayó por un microcorte de red (ENOTFOUND) sin emitir QA_VERDICT -- veredicto NOT_RUN, no cuenta como ciclo consumido. Reanudación (DEC-AUTO-901) 2026-09-30: verificado PR #37 y rama @ 0c8a31c sin cambios, worktree del Developer limpio; desmontado el stack Docker huérfano brujulaqa018 (down -v) y su worktree temporal de QA (solo scripts de exploración sin veredicto). QA relanzada desde cero sobre 0c8a31c.", "QA_VERDICT PASS (ciclo 1/3, auditoría desde cero, A/B main vs 0c8a31c con misma semilla, 3 motores): archivos_permitidos PASS (solo imagen-responsiva.ts/.spec.ts), 415/415 tests, cobertura OK, a11y 0 violaciones, hidratación SSR sin errores, CLS/LCP sin regresión (LCP ligeramente mejor, bytes 456->289 KB), gitleaks/semgrep limpios, contrato NOT_APPLICABLE. Cifras del Developer reproducidas (24->6 imágenes, 48->30 peticiones) y mejoradas en la medición independiente: e2e serie 696->0 respuestas 429, fallos 3->1 (el restante es CLS de Inicio preexistente, TKT-016). Riesgo residual REAL distinto al declarado: con 1 visitante 0 429 en todo escenario; con 2-3 visitantes fríos tras la misma IP (NAT/CGNAT) persisten 429 en chunks JS que rompen navegación (N=2: 1/10, N=3: 7-9/15) -- no corregible desde frontend, requiere nginx (F-3 HIGH, ticket DevOps). Hallazgos no bloqueantes: F-1 LOW (imágenes con alt informativo sin src en SSR/sin JS; comentario del componente incorrecto), F-2 MEDIUM preexistente (solo AVIF sin fallback: 0 imágenes renderizadas en WebKit). LCP móvil 3.1-3.7 s preexistente sin ticket (REQ-052). Sincronizando PR #37 con main (BEHIND solo por commits de docs del Orquestador).", "Integrado: PR #37 sincronizado con main (gh pr update-branch, diff de sincronización solo audit_log.md/kanban.md), CI real verde 5/5 jobs requeridos sobre 92c2eaa, merge @ 764fa54. DONE. Hallazgos derivados a TKT-OPS-016 (F-3 nginx, HIGH, condición de F9), TKT-020 (F-1+F-2 imagen-responsiva) y TKT-021 (LCP móvil REQ-052) -- DEC-AUTO-926."]
    actualizado: 2026-09-30
  - id: TKT-031
    titulo: "LOW (seguimiento de QA TKT-027): en backend/apps/cuentas, (OBS-01) rechazar /panel/acceso y /panel/acceso/** (también sus formas codificadas canonizadas) como destino de redirección para igualar al cliente; (OBS-02) fijar con tests el rechazo de %2f/%5c ('/panel/medios%2f123', '/panel/a%5cb' -> /panel); (OBS-04) un siguiente inválido o demasiado largo se ignora y devuelve /panel en vez de 400 que impide el login (igualar el límite a 2048 del cliente o ignorarlo); (OBS-05) revalidar la redirección guardada en sesión al leerla"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-027, AC-115, THREAT-017]
    depende_de: [TKT-027]
    archivos_permitidos: ["backend/apps/cuentas/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Hallazgos no bloqueantes de la QA de TKT-027 (DEC-AUTO-942). Si cambia el comportamiento de OBS-04, comprobar si requiere CHG en contracts/openapi.yaml (400 documentado para siguiente).", "Entregado @ PR #46 (f47279a), CI verde (run 36868836634). Diff verificado: services.py, autenticacion.py y un test nuevo. OBS-01, OBS-02 (mutación vía monkeypatch: la edición temporal del código fuente fue denegada por el clasificador de permisos) y OBS-05 corregidos; OBS-04 dentro del contrato (maxLength 2000 -> 400), franja 2001-2048 resuelta en el cliente por TKT-028 (DEC-AUTO-944). QA ciclo 1/3 despachada.", "QA_VERDICT PASS (ciclo 1/3): AC_TKT031_01..05 PASS; mutación REAL del código fuente (M1 10 fallos, M2 27, M3 9); 186 comprobaciones HTTP con 0 fallos, 0 /panel/acceso y 0 5xx; sesión alterada en sesion_panel con 17 valores -> /panel; matriz de evasión de TKT-027 sin regresión; schemathesis 3153/3153; seguridad 0. Hallazgos INFO de coherencia cliente/servidor a TKT-028.", "PR #46 integrado en main (gh pr merge --merge), CI verde. DONE."]
    actualizado: 2026-10-01
  - id: TKT-032
    titulo: "MEDIUM (QA TKT-012, preexistente): (F1) traducir a 400/404/422 Problem Details los 7 caminos del panel que dan 500 por errores de BD no traducidos: POST/PUT /panel/taxonomias/paises con region_id inexistente; POST /panel/contenidos/itinerarios con destino_id inexistente (Destino.DoesNotExist); colecciones y guias con relaciones a id inexistente; destinos con latitud sin longitud (ck_destino_coordenadas); PUT /panel/medios/{id DISPONIBLE} con autor_credito null (ck_medio_disponible); (F2) aplicar uniqueItems con lista_unica en copublicar_tipos, cascada_confirmada y analisis-publicacion.tipos_ids, y documentar sus maxItems/uniqueItems en el esquema generado; (F3) dar valor a actualizado_por en las fixtures para que los tests de N+1 de contenido detecten la falta de select_related; (F4) tests HTTP de regiones y países (catalogos/api/views.py >= 95 %) e inicio/api/views.py líneas 35-37; (INFO) fuente_url de catalogación de medios no debe aceptar cadena vacía si el contrato la prohíbe"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-012, TKT-006, "Skill_Backend §8"]
    depende_de: [TKT-012]
    archivos_permitidos: ["backend/apps/contenido/**", "backend/apps/catalogos/**", "backend/apps/medios/**", "backend/apps/inicio/**", "backend/apps/core/esquema.py"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Hallazgos F1-F4 e INFO de la QA de TKT-012 (DEC-AUTO-943); reproducciones en el scratchpad qa-tkt012/evidencia.md de la sesión 4af54f6f.", "Entregado @ PR #47 (b84c8cc), CI verde (run 36879781212); diff dentro de alcance. Sonda transaccional con COMMIT: 50 caminos 5xx en main (los 7 de la QA + 43) -> 0. pytest 1087, 97 %; schemathesis panel Editor 9035/9035 sin 5xx; oasdiff 0. Cambios de comportamiento: referencias inexistentes y CHECK -> 400 validacion por campo; vaciar alt/crédito/licencia de medio DISPONIBLE -> 422 regla_negocio; título duplicado al actualizar -> 409. Hallazgo preexistente (retirar con cascada_confirmada distinta y cascada calculada vacía da 200 en vez de 409) a TKT-033 (DEC-AUTO-945). QA ciclo 1/3 despachada.", "Al integrar: retirar de infra/ci/cobertura_umbrales.toml las excepciones EXC-01/EXC-02 de TKT-OPS-021 (DevOps) si TKT-OPS-021 ya está integrado (caducan 2026-10-31).", "QA_VERDICT PASS (ciclo 1/3): sonda HTTP con COMMIT de 55 casos: main 41 respuestas 500, rama 0; 55/55 con código documentado en su operación y errors por campo; cambios de comportamiento verificados y coherentes con RULE-005/STATE-002; 13/13 mutaciones detectadas; pytest 1088, 97,09 %, catalogos e inicio views 100 %; oasdiff 0; schemathesis CI 3052/3052 y panel Editor 11482 / Admin 11659 sin 5xx del ticket. Hallazgos a TKT-033 (DEC-AUTO-947).", "PR #47 integrado en main (gh pr merge --merge), CI verde. DONE."]
    actualizado: 2026-10-01
  - id: TKT-033
    titulo: "MEDIUM (hallazgos de TKT-032 y su QA): (F-032-02, MEDIUM, preexistente) DELETE /panel/contenidos/destinos/{id} de un borrador referenciado por un itinerario (PROTECT) da 500 ProtectedError: debe dar el 409 documentado; (F-032-01, LOW) carrera alta/DELETE concurrente: traducir IntegrityError 23503 y ProtectedError residuales a 409 o bloquear referencias con SELECT ... FOR SHARE, y DoesNotExist en _datos_regla_itinerario; (F-032-03, LOW, preexistente) POST /panel/medios/{id}/retirar con 409 medio_en_uso devuelve usos[] con campos distintos del ReferenciaUso del contrato {tipo_entidad, id, titulo}: alinear al contrato; (cascada) retirar con cascada_confirmada distinta y cascada calculada vacía da 200 en lugar de 409 impacto_modificado; (INFO) AnalisisPublicacion.copublicar_tipos[].id documenta maximum en la respuesta; (INFO F-032-04) mensaje del 400 en tipo_principal_id cuando el PUT omite tipos_ids"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-032, TKT-006]
    depende_de: [TKT-032]
    archivos_permitidos: ["backend/apps/contenido/**", "backend/apps/medios/**", "backend/apps/core/esquema.py"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-945.", "Entregado @ PR #51 (b273b62); diff en contenido y medios. CI verde salvo image scan (CVE del proxy, TKT-OPS-024). Bloqueo FOR KEY SHARE de referencias ordenado por id, DELETE con FOR UPDATE y ediciones con FOR NO KEY UPDATE; 55P03/40P01 -> 409 conflicto_version; 409 dependencia_bloqueante con ReferenciaUso al borrar borradores referenciados; 409 medio_en_uso con ReferenciaUso; impacto_modificado también con cascada vacía (retirar y PUT destino). Carrera A/B: main 500 en la ronda 0, rama 0 5xx en 2560 peticiones. Traducción global de 55P03/40P01 propuesta a TKT-035 (DEC-AUTO-951). QA ciclo 1/3 despachada.", "2026-10-01 (reanudación tras corte): la QA ciclo 1 no emitió QA_VERDICT; stacks brujulaqa033* y worktrees qa033r1* de esa QA quedaron huérfanos (su baja fue denegada por el clasificador: pendiente del usuario); se relanza desde cero sobre PR #51 @ b273b62 con proyectos nuevos.", "2026-10-08 (reanudación): la QA relanzada el 2026-10-01 tampoco emitió QA_VERDICT (NOT_RUN); se relanza sobre PR #51 @ b273b62 con checkpoint de progreso.", "2026-10-08 QA_VERDICT PASS ciclo 1/3 (validado b273b62; backend y contrato idénticos en 7fdb397/dbe99b1): 1185 passed, cobertura 97,11 %, gate por módulo 15/15; F-032-02/01/03, cascada e INFO reproducidos en main (500/forma errónea) y corregidos en la rama (409 documentados); carrera 380 peticiones 0 5xx; schemathesis Editor+Admin ~10000 casos, 13486 respuestas 0 5xx; oasdiff 0 breaking; semgrep/bandit/gitleaks 0. Pendiente de CI verde y merge.", "CI verde completo en dbe99b1 (image scan incluido). Integrado en main con gh pr merge 51 --merge el 2026-10-08. DONE."]
    actualizado: 2026-10-08
  - id: TKT-034
    titulo: "LOW: tests de backend/apps/cuentas/sesiones.py (76 %) y permisos.py (94,12 %) hasta > 95 % (críticos desde TKT-OPS-022), y añadir backend/coverage.json y backend/vistas_urlconf.json a .gitignore. Al integrar, DevOps retira TKT-OPS-022-EXC-01/EXC-02 (caducan 2026-11-15)"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-OPS-022, "Skill_Backend §8"]
    depende_de: [TKT-OPS-022]
    archivos_permitidos: ["backend/apps/cuentas/tests/**", ".gitignore"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Propuesto por el DevOps de TKT-OPS-022 (DEC-AUTO-950).", "2026-10-08: TKT-OPS-022 DONE; despachado al Developer. Al integrarse, TKT-OPS-027 retira EXC-01/02 y corrige su campo ticket (F-QA022-03).", "Entregado @ PR #61 (4bc3a9c, base 409d9c0): 50 pruebas test_TKT034_*, sesiones.py y permisos.py al 100 %, gate PASS sin excepciones, .gitignore actualizado; CI run 37789841168 verde (1239 passed). INFO: docstring de sesiones.py dice cifrado (solo firmado); bucle teórico CreateError con FK inexistente (inalcanzable). QA ciclo 1/3 despachada.", "2026-10-08 QA_VERDICT PASS ciclo 1/3 @ 4bc3a9c (ticket idéntico en e4bb112): 1235 passed, sesiones/permisos 100 %, gate sin excepciones PASS, 38/42 mutantes (supervivientes equivalentes salvo S11, cubierto por la suite existente), sin flakiness, 0 confirmed. Merge pendiente de CI verde: image scan rojo solo por CVE-2026-4775 del proxy (TKT-OPS-028). Deuda -> TKT-039.", "2026-10-08: update-branch tras #64/#66, CI verde completo; integrado (gh pr merge 61 --merge @ ece6cb5). DONE. Desbloquea F-QA022-03 de TKT-OPS-027 (retirar EXC-01/02)."]
    actualizado: 2026-10-08
  - id: TKT-041
    titulo: "HIGH (decisión del usuario 2026-10-08): sustituir las ilustraciones geométricas de la semilla (backend/seed/imagenes.py) por fotografías reales y pertinentes con licencia libre verificada (Wikimedia Commons u otra fuente sin claves de API; solo CC0, PDM, CC BY y CC BY-SA, añadiendo al catálogo de licencias las versiones 2.0/3.0 si hacen falta), con autor, fuente y licencia registrados (REQ-043/071, créditos) y texto alternativo en español; cada foto debe mostrar de verdad el lugar/actividad (verificación visual). Cubrir portadas y galerías de los 24 destinos, itinerarios, guías, tipos de aventura, colecciones, páginas e imagen principal de inicio; procesar por el pipeline de medios existente (recodificación, sin EXIF, derivados); idempotente; tamaño acotado en el repo"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-007, REQ-043, REQ-071, RSK-002, GAP-008]
    depende_de: []
    archivos_permitidos: ["backend/seed/**", "backend/apps/contenido/management/**", "backend/apps/contenido/tests/test_ac_tkt007*", "backend/apps/catalogos/migrations/**", "backend/apps/catalogos/tests/**", "backend/apps/medios/tests/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["DECISION_HUMANA 2026-10-08: el usuario pide que el Orquestador busque y coloque fotografías reales. DEC-AUTO-967: fuente Wikimedia Commons (sin API key, licencia por archivo verificable); sustituye a DEC-AUTO-014 (solo ilustraciones propias).", "2026-10-08 entregado PR #70 @ ae545ad (CI 37870911477 verde): 129 fotos de Commons con MANIFIESTO (sha256, autor, licencia, alt), 24 MB, migración 0004 (CC BY/BY-SA 2.0/2.5/3.0), pipeline de medios real, idempotente; pytest 1340 PASS. cargar_semilla usa date.today() (corrige el fallo de zona horaria, parte de TKT-045). Riesgo: contraste del rótulo pequeño del hero sobre la foto. QA ciclo 1/3 despachada.", "2026-10-08 QA_VERDICT FAIL ciclo 1/3: F-01 HIGH contraste del hero de inicio sobre la foto nueva (rótulo 1,08-1,33:1; H1 mín. 1,41; subtítulo mín. 2,60; regresión frente a main, axe lo deja incomplete). F-02 MEDIUM LCP +0,2-0,6 s (inicio 3,06 s; fichas 3,45 s; main ya >2,5 s) por codificación por defecto de Pillow -> TKT-048 (DEC-AUTO-976). Licencias 129/129 verificadas en Commons, EXIF 0, créditos 129/129, idempotente, schemathesis 0 fallos. OBS-01..05 en alcance. Ciclo de corrección 2/3 al Developer (F-01 + OBS).", "2026-10-08 ciclo 2 entregado @ e014094 (CI 37880059334 verde): portada Fitz Roy El Chalten sunrise-17 (CC BY-SA 3.0, recorte 16:9) con contraste mín. ≥8,06 rótulo y ≥12,35 H1/subtítulo en 1280/1366/390; OBS-01..05 resueltos (2 fotos sustituidas, campo modificaciones, nota en Acerca de). QA ciclo 2/3 despachada.", "2026-10-09 QA_VERDICT PASS ciclo 2/3 @ e014094: F-01 contraste mín. 8,06 (Chromium) / 7,76 (Firefox), WebKit no medible por AVIF sin respaldo (TKT-029); OBS-01..05 resueltas; 3 licencias nuevas verificadas en Commons; pytest 1341 PASS, E2E públicas 3 motores, axe 0, schemathesis 0 5xx, gitleaks/semgrep 0; LCP inicio mediana < 2,5 s. Integración en espera de TKT-OPS-031 (CI rojo por CVE ajena).", "Integrado tras TKT-OPS-031: PR #70 @ bc54a50 con CI verde. DONE."]
    actualizado: 2026-10-09
  - id: TKT-042
    titulo: "MEDIUM, preexistentes (QA TKT-019 OBS-01/OBS-02): (a) enlaces internos de ancla con href='#x' se resuelven contra <base href=/> y llevan a /#x (Inicio): índice de letras de pagina-glosario.html:23 y probablemente destinos/ui/pagina-mapa-destinos.html:27; buscar y corregir todos los href='#...' de las features (routerLink + fragment), salvo el skip link global que funciona; (b) la navegación en cliente a /glosario#termino no desplaza al término (anchorScrolling actúa antes de que lleguen los datos): desplazar tras cargar, afecta a los enlaces [fragment] desde guías, tipos, itinerarios y el mapa del sitio; E2E que verifiquen pathname y desplazamiento en 3 motores"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-019, TKT-009, "RULE-030"]
    depende_de: []
    archivos_permitidos: ["frontend/src/app/features/glosario/**", "frontend/src/app/features/destinos/ui/**", "frontend/src/app/features/**/ui/*.html", "frontend/src/app/app.config.ts", "frontend/src/app/core/layout/foco-ruta.ts", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-968. QA TKT-019: via-ferrata desde el mapa queda en scrollY 0 (término en top=2019px); carga directa sí desplaza.", "Causa probable aportada por el Developer de TKT-019: core/layout/foco-ruta.ts (FocoRuta) pone el foco en el h1 y sube el scroll en cada NavigationEnd, anulando el desplazamiento a fragmentos; solución de referencia: irASeccion() de features/mapa-del-sitio. Añadir core/layout/foco-ruta.ts a archivos permitidos."]
    actualizado: 2026-10-08
  - id: TKT-043
    titulo: "MEDIUM (needs_validation, QA TKT-022 OBS-C2-04): LimitePorAmbito sobre DatabaseCache parece contar de forma no atómica bajo concurrencia: 912 GET/min a /api/v1/panel/medios/{id} con la misma cuenta en lotes de 12 concurrentes no producen ningún 429 de panel-lectura (600/min), en secuencia sí. Verificar con prueba de concurrencia y, si se confirma, hacer el conteo atómico (UPDATE ... RETURNING / incr atómico) para todos los ámbitos; comprobar que panel-login sigue exacto"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-022, "THREAT limitación de tasa"]
    depende_de: []
    archivos_permitidos: ["backend/apps/core/**", "backend/config/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-969. Sonda de QA en scratchpad/qa022c2/res/."]
    actualizado: 2026-10-08
  - id: TKT-044
    titulo: "MEDIUM (QA TKT-040 F-01, preexistente, THREAT-002): si falla la rotación de sesión tras cambio de contraseña o MFA, la clave anterior sigue válida y renovable hasta el máximo absoluto de 12 h. Si falla la INSERT de la clave nueva, borrar la fila anterior (no está bloqueada); si el borrado de la anterior choca con un bloqueo, invalidarla de forma fiable (UPDATE expire_date en el pasado con reintento/SKIP LOCKED o limpieza diferida). (F-02 LOW) rotar_sesion detecta mal el fallo de la INSERT (SessionBase.create asigna la clave antes de save: rama 'sesion_no_rotada' inalcanzable, logs engañosos) y el test AC_TKT040_04 lo oculta con un mock de create: probar con la INSERT real fallando. (F-03/F-04 LOW, CWE-204) diferencia de tiempo existente/inexistente (~10 ms sin contención; 5 s vs 0,23 s con la fila de cuenta bloqueada): igualar caminos en lo razonable"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-040, "THREAT-002", "CWE-204"]
    depende_de: [TKT-040]
    archivos_permitidos: ["backend/apps/cuentas/**", "backend/apps/core/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-970. Reproducción: scratchpad/qa040/qa_tests/test_qa040_carreras.py (QA4, QA5, QA6, QA6b, QA7, QA9).", "2026-10-08 entregado PR #72 @ 7b114f7 (CI 37870716674 verde, 1351 tests, 97,56 %): marca de revocación en sesion_panel si el DELETE choca con bloqueo, INSERT verificada antes de cambiar la clave, 401 sesion_expirada si no se puede rotar, login con NOWAIT y caminos igualados; AC_TKT044 16 PASS en rama / 14 FAIL en main. Ampliaciones aceptadas en DEC-AUTO-974. QA ciclo 1/3 despachada.", "2026-10-08 QA_VERDICT FAIL ciclo 1/3: F-01 y F-03/F-04 verificados con PostgreSQL real (QA4-QA9 corregidos; marcas no falsificables; EXPLAIN 0,029 ms; 0 hallazgos de seguridad). F-A MEDIUM: con FK violada en el alta/rotación, __cause__ cíclico (raise causa from exc) hace que fallo_por_contencion no termine (bucle de CPU) y la clave anterior no se invalida; hoy solo provocable con operación directa en BD; en main también se cuelga. Ciclo de corrección 2/3 al Developer.", "2026-10-08 ciclo 2 entregado @ f524fbb (CI 37878104068 verde, 1354 tests): raise sin encadenar, recorrido de __cause__ con visitados, invalidación antes del log, AC_TKT044_07 HTTP con plazo. QA ciclo 2/3 despachada.", "2026-10-09 QA_VERDICT PASS ciclo 2/3 @ f524fbb. CI rojo por CVE ajena (TKT-OPS-031); tras su integración, update-branch y CI verde: PR #72 integrado @ 145ec1a. DONE."]
    actualizado: 2026-10-09
  - id: TKT-045
    titulo: "HIGH (QA TKT-023 F-01 + Developer TKT-023 RULE-009): (1) F-01 HIGH: restaurar revisión pierde datos: services._instantanea (l.236-259) recorre solo subtipo._meta.fields (sin M2M ni hijos) y usa campo.name sin _id; restaurar_revision (l.2198) devuelve esa instantánea, incumpliendo el contrato ('Cuerpo compatible con {Tipo}Actualizacion'): faltan relaciones, terminos_ids, fuentes (todos), tipos_ids/galeria_ids (destino), dias (itinerario), checklist (tipo), elementos (colección), destinos_ids/tipos_ids (guía) y las FK salen sin _id. Instantánea completa y respuesta conforme a {Tipo}Actualizacion para los 7 tipos; compatibilidad con revisiones antiguas incompletas (no inventar: devolver lo que haya y marcar/advertir según contrato, sin borrar datos actuales por omisión); tests por tipo ida y vuelta. (2) RULE-009 en servidor con el criterio de DEC-AUTO-977: fecha_revision válida si <= fecha actual en UTC+14; Problem Details coherente con el contrato. (3) OBS-02: analisis-publicacion debe devolver confirmable:false si un tipo del destino está RETIRADO (hoy publicar da 422 tipo_retirado tras confirmar). (4) OBS-03 hardening: saneado.py debe descartar href relativos al protocolo ('//host') y eliminar el contenido de <script>/<style>, no dejarlo como texto"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-023, "RULE-009", "SCR-038", "FEAT-039", MOD-010, "THREAT XSS"]
    depende_de: []
    archivos_permitidos: ["backend/apps/contenido/services.py", "backend/apps/contenido/reglas.py", "backend/apps/contenido/saneado.py", "backend/apps/contenido/selectors.py", "backend/apps/contenido/api/**", "backend/apps/contenido/tests/test_tkt045*", "backend/apps/contenido/tests/test_ac_tkt006_01_reglas.py"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-973, DEC-AUTO-977. La parte de la semilla (fecha UTC) ya la corrige TKT-041. Reproducción F-01: scratchpad 56bc59a0…/qa023/specs/qa-restaurar2.spec.ts y qa-restaurar3.spec.ts. Disjunto de TKT-041 (management/ y test_ac_tkt007*).", "2026-10-09 PR #76 @ cf24228: 51 tests TKT-045 (42 fallan en main), pytest completo 1380 PASS TZ=UTC (1 intermitente de concurrencia TKT-033, 3/3 al repetir) y 1381 PASS TZ=UTC-5, cobertura 97,57 %, gate de contrato 128/128. CI: backend/frontend/infra PASS; build+trivy FAIL solo por supercronic (TKT-OPS-031). QA ciclo 1/3 despachada en paralelo.", "2026-10-09 QA_VERDICT PASS ciclo 1/3 @ cf24228: suite 1385 PASS en UTC, UTC-12 y UTC+14; restaurar ida y vuelta 110/110 en 7 tipos, revisiones antiguas 64/64, reproducciones F-01 6/6 en 3 motores, E2E TKT-023 con E2E_TKT045=1 30/30; RULE-009/OBS-02/OBS-03 verificados; schemathesis Editor+Admin 0 5xx; 60 payloads XSS sin marcado ejecutable; semgrep/bandit/gitleaks 0. F-QA045-01 LOW preexistente -> TKT-050; OBS-QA045-03 -> CHG-API-007. PR #76 integrado @ 1030e4b. DONE."]
    actualizado: 2026-10-09
  - id: TKT-046
    titulo: "LOW (Developer TKT-023): E2E intermitente AC_TKT022_02 en firefox ('route.fulfill: Fetch response has been disposed' en panel-soporte.ts:313): el soporte de TKT-022 no desmonta la ruta del borde 429 al cerrar la página; aplicar afterEach con page.unrouteAll({behavior:'ignoreErrors'}) en panel-medios*/panel-selector* como ya hace panel-contenidos.spec.ts"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-022, TKT-023]
    depende_de: [TKT-023]
    archivos_permitidos: ["frontend/e2e/panel-soporte.ts", "frontend/e2e/panel-medios*.spec.ts", "frontend/e2e/panel-selector*.spec.ts"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-975."]
    actualizado: 2026-10-08
  - id: TKT-047
    titulo: "MEDIUM (QA TKT-041 F-01, corrección duradera): el contraste del texto del hero de inicio depende de la foto (editable desde el panel). Scrim más fuerte o localizado detrás del bloque de texto, color del rótulo .overline-marca y text-shadow, de modo que rótulo y subtítulo ≥4,5:1 y H1 ≥3:1 con cualquier imagen (probar con una imagen blanca y otra con nieve); E2E de contraste real por píxel que no dependa del 'incomplete' de axe"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-041, "Skill_UI_UX#47.2", "WCAG 1.4.3"]
    depende_de: []
    archivos_permitidos: ["frontend/src/app/features/inicio/**", "frontend/e2e/inicio*.spec.ts", "frontend/e2e/contraste*.ts"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-976. Método de medición: scratchpad 56bc59a0…/qa041/contraste.cjs + ratio.py."]
    actualizado: 2026-10-08
  - id: TKT-048
    titulo: "HIGH antes de F9 (QA TKT-041 F-02): LCP de inicio 3,06 s y fichas de destino ~3,45 s (presupuesto 2,5 s; main ya >2,5 s). Derivados codificados con valores por defecto de Pillow (apps/medios/services.py:197, sin quality/speed): AVIF de 800 px 94-174 KB, a veces mayor que WebP/JPEG. Fijar parámetros (AVIF quality≈50-60 + speed, WebP≈75-80, JPEG≈80 progresivo), comando para regenerar derivados existentes, tests de tamaño; y en el frontend de la ficha preload/fetchpriority y sizes de la portada (ampliación de TKT-021 a fichas). Verificar LCP ≤2,5 s con Lighthouse móvil x5"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-041, TKT-021, "Skill_UI_UX#47.2", DEC-AUTO-044]
    depende_de: [TKT-041]
    archivos_permitidos: ["backend/apps/medios/**", "frontend/src/app/features/destinos/**", "frontend/src/app/features/inicio/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-976. A/B Lighthouse de la QA: scratchpad 56bc59a0…/qa041/lh_m, lh_b."]
    actualizado: 2026-10-08
  - id: TKT-049
    titulo: "LOW (QA TKT-041 OBS-C2-04, preexistente): en Chromium a 1280 px los rótulos de la navegación principal parten palabras ('Destino/s', 'Guía/s'); ajustar el layout de la cabecera para que los rótulos no se corten (sin reducir tamaño táctil ni contraste), verificar 1024-1440 px en 3 motores"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-041, MOD-001, "Skill_UI_UX"]
    depende_de: []
    archivos_permitidos: ["frontend/src/app/core/layout/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-981. Captura: scratchpad 56bc59a0…/qa041/c_d1280_hero.png."]
    actualizado: 2026-10-09
  - id: TKT-050
    titulo: "LOW (QA TKT-045 F-QA045-01, preexistente, control de acceso): un Editor obtiene 200 en GET de la lista y del detalle de revisiones y en POST .../revisiones/{n}/restaurar de las páginas legales (AVISO_LEGAL, POLITICA_COOKIES, POLITICA_DATOS), solo editables por Administrador (el PUT ya da 403). Aplicar _autorizar_pagina en RestaurarRevision, DetalleRevision y la lista de revisiones cuando el tipo sea PAGINA; 403 permiso_denegado según contrato; tests por rol y página"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-045, MOD-010, "THREAT control de acceso por objeto"]
    depende_de: []
    archivos_permitidos: ["backend/apps/contenido/api/**", "backend/apps/contenido/tests/test_tkt050*"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-983. Reproducción: scratchpad 7e63c98e…/qa/acceso.log."]
    actualizado: 2026-10-09
  - id: CHG-API-007
    titulo: "LOW (tras TKT-040): ajustar ADR-API-002 §22 a la implementación de TKT-040: fila de panelRenovarSesion (la renovación la guarda AutenticacionSesionPanel.authenticate, OBS-02 QA CHG-API-006 c2) y viñeta de deuda (resuelta): contención antes del efecto -> 409 sin efectos; tras el efecto -> éxito sin renovar o 401 sesion_expirada, nunca 409; GET y vistas previas -> 401; login con contención -> 401 credenciales_invalidas (NV-01), 409 solo por sesión previa bloqueada"
    fase: F4
    estado: TODO
    owner: backend-contrato
    trazabilidad: [CHG-API-006, TKT-040]
    depende_de: [TKT-040]
    archivos_permitidos: ["docs/adr/**", "contracts/openapi.yaml"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["OBS-01/OBS-02 QA CHG-API-006 ciclo 2; riesgos del handoff de TKT-040.", "F-05 QA TKT-040: un GET con contención responde 401 sesion_expirada sin borrar la cookie y la sesión sigue válida (el frontend enviará al login sin necesidad): documentarlo; riesgo residual de la rotación fallida es de hasta 12 h (máximo absoluto), no 30 min, hasta TKT-044.", "2026-10-09 (DEC-AUTO-984) incluye OBS-QA045-03: ColeccionActualizacion/creación admite terminos_ids por ContenidoComunCampos pero el servidor responde 400 desde TKT-045; excluirlo del esquema de colección. Si cambia el esquema, regenerar el cliente del frontend (npm run api:generate) en ticket de Developer."]
    actualizado: 2026-10-09
  - id: TKT-040
    titulo: "MEDIUM (QA CHG-API-006 F-01, NV-01, INFO): (a) SessionMiddleware.process_response guarda la sesión fuera del EXCEPTION_HANDLER de DRF: ante 55P03/40P01/40001 o fila de sesion_panel borrada por una invalidación concurrente, SessionStore.save lanza UpdateError -> SessionInterrupted -> 400 validacion. Traducirlo a 409 conflicto_version (Problem Details, reintentable) o a 401 sesion_expirada si la fila ya no existe, en todas las escrituras del panel que renuevan la inactividad (incluida panelRenovarSesion), con pruebas de carrera; (b) NV-01 (CWE-204): en panelIniciarSesion un 409 por contención del FOR UPDATE de la cuenta delata que el usuario existe: respuesta uniforme con la de credenciales inválidas (o NOWAIT/SKIP con respuesta uniforme), con prueba; (c) declarar 409 en @extend_schema de las 8 vistas de CHG-API-006 para que el esquema generado coincida con el contrato"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [CHG-API-006, TKT-035, "THREAT enumeración de cuentas"]
    depende_de: []
    archivos_permitidos: ["backend/apps/core/**", "backend/apps/cuentas/**", "backend/apps/inicio/**", "backend/apps/catalogos/**", "backend/config/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-966. Reproducción de la QA: scratchpad/qachg006/renovar_middleware.py (SessionInterrupted -> 400 application/problem+json validacion).", "Riesgo de backend-contrato: en escrituras del panel el efecto ya está confirmado (ATOMIC_REQUESTS=False) cuando falla el guardado de la sesión: un 409 reintentable podría duplicar efectos en operaciones sin Idempotency-Key; elegir la respuesta en consecuencia. En GET que renuevan inactividad, solo códigos ya declarados (401 sesion_expirada) o abrir CHG-API.", "OBS-01/02 QA CHG-API-006 c2: en escrituras con efecto confirmado no responder 409 (éxito sin renovar o 401 si la fila no existe); tras integrar, backend-contrato ajusta la viñeta de deuda y la fila de panelRenovarSesion del ADR-API-002 §22.", "Entregado @ PR #68 (2dfb309): sesión guardada en authenticate dentro de DRF (contención en método no seguro -> 409 sin efecto; GET/vista previa -> 401; fila inexistente -> 401), tras el efecto nunca 409 (éxito sin renovar o 401), SesionPanelMiddleware como red de seguridad, logout borra la fila antes de auditar, login serializado con pg_advisory_xact_lock por HMAC del usuario (exista o no) y contención -> 401 credenciales_invalidas, 409 en extend_schema de las 8 vistas. 1330 passed, 97,36 %; carreras 4/6 FAIL en main, 6/6 PASS en rama. DEV-040-01..06 aceptadas. Depende de PR #62 para el gate de contrato del CI.", "2026-10-08 QA_VERDICT PASS ciclo 1/3 @ 10129fd: 1330 passed 97,40 %, gate 39/39, contrato 0 errores, schemathesis auth 1347 casos 0 5xx, SAST 0; carreras reales vs main confirman la corrección (400 con efecto -> 409 sin efecto; 400 -> 401; logout; oráculo 409 de NV-01 eliminado). F-01 MEDIUM preexistente, F-02/F-03/F-04 LOW -> TKT-044; F-05 INFO -> CHG-API-007. update-branch del PR #68 y merge tras CI.", "Integrado (gh pr merge 68 --merge) con CI verde tras update-branch. DONE. Desbloquea CHG-API-007 y TKT-044."]
    actualizado: 2026-10-08
  - id: CHG-API-006
    titulo: "LOW (TKT-035): documentar 409 conflicto_version (Problem Details, reintentable) en las operaciones de escritura que toman bloqueos de fila y hoy no lo declaran: panelIniciarSesion, panelVerificarMfa, panelCambiarContrasena, panelActualizarConfigInicio, panelActualizarConfiguracionSitio, panelActualizarNivelEscala, panelCerrarSesion, panelRenovarSesion; versionar según política del contrato; lint Redocly 0 errores; regenerar cliente del frontend si cambia"
    fase: F4
    estado: DONE
    owner: backend-contrato
    trazabilidad: [TKT-035, "Skill_Backend §12.1"]
    depende_de: [TKT-035]
    archivos_permitidos: ["contracts/openapi.yaml", "docs/adr/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-958.", "Entregado @ PR #62: 409 Conflicto en 8 operaciones del panel, sin esquemas nuevos, info.version 1.0.0, x-cambios y ADR-API-002 §22. El agente backend-contrato no tenía shell: su parche manual no aplicaba; editó en el worktree y el Orquestador hizo commit/push/PR sin cambiar contenido (DEC-AUTO-961). YAML válido. oasdiff/gate/cliente generado: los verifica el CI.", "2026-10-08 QA_VERDICT FAIL ciclo 1/3 @ 081875e: lint 0 errores, oasdiff sin breaking, cliente sin cambios, gate de contrato PASS, cuerpo 409 valida contra ProblemaConUsos, seguridad 0 confirmed. F-01 MEDIUM: en panelRenovarSesion el UPDATE de sesion_panel ocurre en SessionMiddleware.process_response (fuera de DRF): 55P03/40P01 o fila borrada -> UpdateError -> SessionInterrupted -> 400 validacion, no 409; ADR §22 incorrecto. schemathesis NOT_RUN (CI cortado por la CVE de tiff, ya corregida). DEC-AUTO-966: remedio (b) -> TKT-040 (backend) y ciclo 2 corrige la fila del §22 enlazando TKT-040; NV-01 -> TKT-040.", "Ciclo 2 @ 398290f (commit 2a89b58 del ADR sin editar por el Orquestador + merge de origin/main): §22 describe el guardado de la sesión en el middleware y la deuda ligada a TKT-040; contrato sin cambios (401 sesion_expirada ya declarado). QA ciclo 2/3 tras el CI con schemathesis.", "2026-10-08 QA_VERDICT PASS ciclo 2/3 @ 398290f: F-01 resuelto según DEC-AUTO-966 (§22 veraz, deuda -> TKT-040); contrato idéntico al ciclo 1; CI run 37843936514 verde con schemathesis 3169/3169 casos, 0 5xx, smoke OK, trivy 0. OBS-01 LOW (viñeta del §22 promete 409 en escrituras con efecto confirmado) -> aclaración enviada al Developer de TKT-040 y ajuste del ADR tras TKT-040; OBS-02 INFO (marcar_actividad la llama authenticate, no la vista) -> mismo ajuste. Pendiente: update-branch y merge.", "Integrado (gh pr merge 62 --merge) con CI verde tras update-branch. DONE. Ajuste posterior del ADR en CHG-API-007."]
    actualizado: 2026-10-08
  - id: TKT-037
    titulo: "MEDIUM (hallazgo del Developer de TKT-035): RULE-007 eludible sin concurrencia: contenido no exige que el país/categoría referenciados estén activos ni al guardar la referencia ni al publicar (retirar el país con el destino en borrador y luego publicar el destino). Exigir activo al asignar la referencia y regla de publicación, bloqueando la fila del catálogo FOR KEY SHARE; además (deuda) simplificar contenido/services._transaccion eliminando la traducción 55P03/40P01 ya global en core, y (OBS-1 QA TKT-033) orden global de bloqueo por id ascendente en ediciones de contenidos relacionados para evitar 40P01"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [RULE-007, TKT-035, TKT-033]
    depende_de: [TKT-035]
    archivos_permitidos: ["backend/apps/contenido/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-958.", "2026-10-08 OBS-02 QA TKT-035: el retiro con FOR NO KEY UPDATE no choca con el FOR KEY SHARE de la FK al crear: creación y retiro concurrentes ambos tienen éxito (6 destinos con país retirado tras la carrera). Exigir activo bajo FOR KEY SHARE (o FOR SHARE) de la fila del catálogo y prueba de carrera retiro vs altas.", "Entregado @ PR #67 (da2e1ee): RULE-007 exige catálogo activo (FOR SHARE) al asignar y al publicar; _transaccion eliminado; 1232 passed, cobertura 97,18 %, gate 39/39; carreras 6/6 FAIL en main, PASS en rama. DEV-037-01..04 aceptadas. QA ciclo 1/3 despachada.", "2026-10-08 QA_VERDICT PASS ciclo 1/3 @ da2e1ee: pytest 1232 passed, gate 21 módulos OK; RULE-007 por API: publicar con país/región/categoría retirados -> 422, asignar -> 400; carreras 35 rondas rama 0 5xx/0 inconsistencias/0 deadlocks (main: 23 publicados con catálogo retirado, 40 deadlocks); schemathesis sin 5xx; 0 confirmed. OBS-01 INFO (datos previos inconsistentes) -> consulta de diagnóstico en F9; OBS-02 INFO (vista previa no comprueba existencia de pais_id/categoria_id) -> TKT-038. update-branch y merge tras CI verde.", "Integrado (gh pr merge 67 --merge @ d777aad) con CI verde tras update-branch. DONE."]
    actualizado: 2026-10-08
  - id: TKT-038
    titulo: "LOW (OBS-01 QA TKT-035): el manejador global traduce cualquier 23503 a 409 conflicto_version y lo registra como WARNING sin traza, incluidas violaciones de FK por defectos de validación (no carreras). Registrar 23503 a nivel ERROR con exc_info y/o limitar la traducción a la comprobación diferida en COMMIT; (OBS-04 INFO) usar nombres de dominio en usos.tipo_entidad en lugar de db_table en mayúsculas; (OBS-02 QA TKT-037, INFO) la vista previa de contenidos acepta pais_id/categoria_id inexistentes sin marcarlos"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-035]
    depende_de: [TKT-035]
    archivos_permitidos: ["backend/apps/core/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-959."]
    actualizado: 2026-10-08
  - id: TKT-039
    titulo: "LOW (QA TKT-034): (S11) prueba propia de que la actualización de sesión persiste expire_date (caducidad deslizante); (INFO-1) corregir el docstring de apps/cuentas/sesiones.py ('cifrado y firmado' -> solo firmado); (INFO-2, defensa en profundidad) traducir a CreateError solo la violación de la PK de sesion_panel para evitar un bucle teórico de SessionStore.create() ante FK inexistente"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-034, THREAT-002]
    depende_de: [TKT-034]
    archivos_permitidos: ["backend/apps/cuentas/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-963."]
    actualizado: 2026-10-08
  - id: TKT-036
    titulo: "LOW (OBS-01 de la QA de TKT-022): .bs-boton (src/styles/componentes.css) anima background-color pero no color: al habilitar un botón primary aria-disabled, durante ~100 ms se ve texto blanco sobre crema (contraste ~1.2:1). Animar ambos de forma coherente (o no animar color de fondo al cambiar de estado) y respetar prefers-reduced-motion; prueba que verifique contraste estable tras habilitar"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-022, "Skill_UI_UX §47", "WCAG 1.4.3"]
    depende_de: []
    archivos_permitidos: ["frontend/src/styles/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-954."]
    actualizado: 2026-10-08
  - id: TKT-035
    titulo: "LOW (propuesta del Developer de TKT-033): traducir de forma global en backend/apps/core (manejador de excepciones de DRF) los OperationalError 55P03 lock_timeout y 40P01 deadlock_detected a 409 conflicto_version reintentable en todas las apps (hoy solo lo hace contenido), y revisar la carrera de DELETE de catálogos (pais_id, categoria_id) frente a altas de contenido"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-033, TKT-032]
    depende_de: [TKT-033]
    archivos_permitidos: ["backend/apps/core/**", "backend/apps/catalogos/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-951.", "2026-10-08 OBS-1 de la QA de TKT-033: dos PUT concurrentes de contenidos relacionados entre sí (A<->B) producen 40P01, ya traducido a 409 conflicto_version reintentable (15/40 en 20 rondas); considerar un orden de bloqueo global para reducirlo.", "2026-10-08: TKT-033 DONE; despachado al Developer (rama tkt-035-errores-bloqueo-global).", "Entregado @ PR #60 (39dc940, base ee8dfda; update-branch tras #52): core/exceptions traduce 55P03/40P01/40001/23503 -> 409 conflicto_version y ProtectedError/RestrictedError -> 409 dependencia_bloqueante; catalogos con select_for_update(no_key) (defecto hallado: un PUT de retiro reinsertaba un país borrado). 1205 passed, gate 15/15, 6 tests de carrera FAIL en main / PASS en rama. CI run 37787766442 verde. QA ciclo 1/3 despachada. Propuestas -> CHG-API-006 y TKT-037.", "2026-10-08 QA_VERDICT PASS ciclo 1/3 @ 6ff55aa: main 56 x 500 y 2 filas resucitadas en 30 rondas; rama 0 5xx y 0 inconsistencias en 40 rondas; errores reales no relacionados siguen 500; schemathesis 7669 casos 0 5xx; contrato sin cambios; 0 confirmed. CI run 37790112167 verde. Integrado (gh pr merge 60 --merge @ 167f2b0). DONE. OBS-01 -> TKT-038; OBS-02 -> TKT-037; OBS-03 -> CHG-API-006 (antes de F9)."]
    actualizado: 2026-10-08
  - id: TKT-OPS-029
    titulo: "CRITICAL, PRIORIDAD MÁXIMA (bloquea el job frontend del CI de main y de todos los PR): handlebars 4.0.0-4.7.9 (GHSA-xw65-4hp5-5hc7, GHSA-8r5x-fm3f-whwj, GHSA-p8wg-vrv2-v86f, inyección de JavaScript), dependencia transitiva del frontend detectada por npm audit (run 37836571528, PR #65). Subir handlebars a la versión corregida solo en frontend/package-lock.json (package.json sin cambios salvo overrides si no hay otra vía, justificado); verificar npm ci, npm audit --audit-level=high, lint, build y tests del frontend; rama propia desde origin/main y PR"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-025, "Skill_devops §4.2"]
    depende_de: []
    archivos_permitidos: ["frontend/package-lock.json", "frontend/package.json", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-965.", "PR #66 @ 684ebb8: handlebars 4.7.9 -> 4.7.10 solo en el lockfile (vía ng-openapi-gen, dev; no entra en el bundle), package.json sin cambios; npm audit 0, 546/546 tests, build OK; CI verde completo (run 37840174099). Validación por CI (DEC-AUTO-964). Integrado (gh pr merge 66 --merge @ 85dd738). DONE."]
    actualizado: 2026-10-08
  - id: TKT-OPS-028
    titulo: "HIGH, PRIORIDAD MÁXIMA (bloquea el CI de main y de todos los PR): CVE-2026-4775 (HIGH, libtiff 4.7.1-r0, ejecución de código/DoS, corregido en 4.7.2-r0) en brujula/proxy (alpine 3.24.2). Corregir sin .trivyignore, con el mismo patrón que TKT-OPS-024 (paquete fijado en infra/proxy/Dockerfile o base nueva); valorar si tiff es necesario en el proxy y quitarlo si no lo es; validar nginx -t, smoke anti-evasión y cabeceras"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-024, "RSK-OPS-046"]
    depende_de: []
    archivos_permitidos: ["infra/proxy/**", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-962. Detectado en el run 37830313288 (PR #62 CHG-API-006, ajeno al diff): brujula/proxy Total 1 (HIGH 1) tiff CVE-2026-4775 fixed 4.7.2-r0; el resto de imágenes 0.", "PR #64 @ ae0cfd9: apk del nginx-module-image-filter (módulo nunca cargado; 41 paquetes en lugar de 70, sin tiff/libgd/libexpat), control en el build; CI verde completo (run 37836015217: build+trivy+SBOM+smoke+schemathesis). DEC-AUTO-964: validación por CI como en TKT-OPS-024. Integrado (gh pr merge 64 --merge @ ea33268). DONE."]
    actualizado: 2026-10-08
  - id: TKT-OPS-030
    titulo: "LOW (QA TKT-OPS-027): (OBS-01) ruta_normalizada() de infra/ci/gate_cobertura.py solo quita '^' y '//': rutas escritas como regex ('/^api/v1/panel$', '(?P<s>panel)', barras escapadas) eluden prefijos_criticos en vistas no críticas; quitar también '$' y '\' y fallar si un archivo no crítico sirve una ruta regex que contenga 'panel', con controles negativos M4/M7. (OBS-02 INFO) comparar también [vistas_externas] con prefijos_criticos. (OBS-03 INFO) eliminar el comentario obsoleto '33 sintéticos + 6 reales' de ci.yaml"
    fase: F7
    estado: TODO
    owner: devops
    trazabilidad: [TKT-OPS-027, "Skill_Backend §8"]
    depende_de: [TKT-OPS-027]
    archivos_permitidos: ["infra/ci/**", ".github/workflows/**", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-971. Mutaciones de la QA: scratchpad 56bc59a0…/q027/mut.py."]
    actualizado: 2026-10-08
  - id: TKT-OPS-031
    titulo: "HIGH (CI rojo en todos los PR desde 2026-10-09): CVE-2026-78667 (Go stdlib net/http, DoS; corregida en Go 1.26.9/1.27.2) en /usr/local/bin/supercronic v0.2.49 (compilado con Go 1.26.6) de las imágenes scheduler y backup; no hay release corregida de supercronic. Compilar supercronic v0.2.49 desde el código fuente (tag verificado por commit SHA) en una etapa builder con Go >= 1.26.9 fijado por digest, binario estático, reproducible, sin cambiar el comportamiento; o actualizar a una release corregida si aparece. Sin entradas nuevas en .trivyignore"
    fase: F6
    estado: DONE
    owner: Skill_devops
    trazabilidad: [RSK-OPS-001, "THREAT supply chain"]
    depende_de: []
    archivos_permitidos: ["infra/**", ".github/workflows/**", ".github/dependabot.yml", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-979. Run 37954467230 (PR #72): trivy HIGH x2 CVE-2026-78667 en supercronic (gobinary) de scheduler y backup.", "2026-10-09 PR #77 @ 57cad6b (CI 37958056463 verde): supercronic v0.2.49 (commit 8e0a4a4) compilado con golang:1.26.9-trixie por digest, receta idéntica en ambos Dockerfile con control en CI, grupo golang en Dependabot, DEVOPS_HANDOFF §33; trivy 0 HIGH/CRITICAL en las 6 imágenes sin tocar .trivyignore. NOT_RUN: arm64. QA ciclo 1/3 despachada.", "2026-10-09 QA_VERDICT PASS ciclo 1/3: CVE-2026-78667 y CVE-2026-97031 ausentes (control positivo con el binario upstream), build reproducible, tag=commit, cadena verificada, regresión real de scheduler/backup con BD, SIGTERM limpio. OBS-01/02/03 -> TKT-OPS-032. Integrado PR #77 @ d91e152 con CI verde. DONE."]
    actualizado: 2026-10-09
  - id: TKT-OPS-032
    titulo: "LOW (QA TKT-OPS-031 OBS-01..03): (1) supercronic_receta.sh debe exigir invariantes dentro del bloque (GOFLAGS=-mod=readonly, GOTOOLCHAIN=local, sin GOSUMDB/GONOSUMDB/GOINSECURE/GOPRIVATE/GOPROXY=direct, presencia de go mod verify y de la comprobación commit==tag) con casos negativos; (2) /usr/local/bin/supercronic como destino una sola vez y solo con --from=supercronic; (3) el JSON de evidencia de trivy 'sin .trivyignore' sale filtrado por la autocarga de ./.trivyignore: generarlo sin filtrar, compatible con politica_trivy.py"
    fase: F6
    estado: TODO
    owner: Skill_devops
    trazabilidad: [TKT-OPS-031, "THREAT supply chain"]
    depende_de: [TKT-OPS-031]
    archivos_permitidos: ["infra/ci/**", ".github/workflows/**", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-982. Mutaciones M3-M7 de la QA (rc=0)."]
    actualizado: 2026-10-09
  - id: TKT-OPS-027
    titulo: "LOW (QA de TKT-OPS-022): (F-QA022-01) gate_cobertura_controles.py da TypeError en Windows sin PYTHONUTF8=1 (UnicodeDecodeError del hijo cp1252): pasar env PYTHONUTF8=1/PYTHONIOENCODING=utf-8 y errors='replace' en subprocess.run, también en gate_contrato_controles si aplica; (F-QA022-02) el gate debe fallar si un archivo de [vistas_no_criticas] o [api_soporte] sirve rutas /api/v1/panel/** (prefijo crítico configurable en el TOML), con control negativo; (F-QA022-04) enmascarar todos los valores que init-env.sh genera desde CHANGE_ME o declarar las 8 obligatorias; (F-QA022-03, tras integrar TKT-034) retirar TKT-OPS-022-EXC-01/02 y, mientras existan, corregir su campo ticket a TKT-034"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-022, TKT-034, "Skill_Backend §8"]
    depende_de: []
    archivos_permitidos: ["infra/ci/**", ".github/workflows/**", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-957.", "2026-10-08 PR #65 @ e2e5975 (sincronizado con main; §30 renumerada a §31; EXC-01/02 retiradas con sesiones.py y permisos.py al 100 %), CI 37868923649 verde. QA_VERDICT PASS ciclo 1/3 (mutaciones M0-M9, Windows sin PYTHONUTF8, enmascarado 8/8). OBS-01/02/03 -> TKT-OPS-030. Resincronizado tras #63, CI verde, integrado (gh pr merge 65 --merge @ 612d29e). DONE."]
    actualizado: 2026-10-08
  - id: TKT-OPS-026
    titulo: "Dependabot del 2026-10-05: (a) #54 ruff 0.16.10, #55 cryptography 50.0.2, #57 @types/node 24.19.1 y #56 grupo angular (12 paquetes): sincronizadas con main y sujetas a QA de regresión (una QA_VERDICT por PR) antes de integrar; (b) #58 vitest 5.0.3 falla en npm ci (ERESOLVE: @vitest/coverage-v8 5.0.2 exige vitest 5.0.2): añadir en .github/dependabot.yml un grupo vitest (vitest, @vitest/*) para que se actualicen juntos, cerrar #58 y dejar que Dependabot lo regenere agrupado"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: ["Skill_devops §5", "Skill_devops §4.2"]
    depende_de: []
    archivos_permitidos: [".github/dependabot.yml", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-956. 2026-10-08: update-branch de #54-#57 ejecutado por el Orquestador; #58 run 37780415306 FAIL ERESOLVE.", "2026-10-08 PR #63 sincronizado (f829cf5, CI 37866726692 verde); QA_VERDICT PASS ciclo 1/3. update-branch tras #69, CI verde, integrado (gh pr merge 63 --merge @ f080842); #58 cerrado para que Dependabot lo regenere agrupado. DONE."]
    actualizado: 2026-10-08
  - id: TKT-OPS-025
    titulo: "HIGH, PRIORIDAD MÁXIMA (bloquea el CI de main y de todos los PR): GHSA-68fv-2mgg-jv7q (HIGH, DoS del bucle de eventos) en source-map-js 1.2.1, dependencia transitiva del frontend (postcss, @tailwindcss/node, css-tree, magicast, sass). Subir source-map-js a la versión corregida solo en frontend/package-lock.json (package.json sin cambios); verificar npm ci, npm audit --audit-level=high, build y tests del frontend; rama propia desde origin/main y PR"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-022, "CLAUDE.md §0.3 (lockfiles)", "Skill_devops §5"]
    depende_de: []
    archivos_permitidos: ["frontend/package-lock.json", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-953. Detectado por el DevOps de TKT-OPS-022 en el run 37772199219 (PR #52 @ 815a5e7): job frontend FAIL solo en npm audit; frontend/** idéntico a main, aviso publicado tras el último CI verde de main (36947600250).", "Entregado @ PR #59 (8dcf633): lockfile 1.2.1 -> 1.2.2, diff verificado; CI run 37774069616 verde completo, trivy 0 HIGH/CRITICAL en 6 imágenes. Integrado en main por el usuario (gh pr merge 59 --merge @ 8b2ea8c). DONE."]
    actualizado: 2026-10-08
  - id: TKT-OPS-024
    titulo: "HIGH, PRIORIDAD MÁXIMA (bloquea el CI de main y de todos los PR): CVE-2026-103111 (HIGH, pcre2 10.48-r0, corregido en 10.49-r0) en brujula/proxy (alpine 3.24.2, nginxinc/nginx-unprivileged:1.30.5-alpine). Corregir sin .trivyignore (hay parche): apk upgrade de pcre2 fijado o nuevo digest de la base; revisar si el PR #22 de Dependabot (1.31.5-alpine) lo resuelve y es compatible; validar el proxy (nginx -t, smoke anti-evasión 6/6, cabeceras idénticas)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-017, "RSK-OPS-044", "RSK-OPS-045"]
    depende_de: []
    archivos_permitidos: ["infra/proxy/Dockerfile", "infra/proxy/**", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Detectado por el DevOps de TKT-OPS-022 y verificado por el Orquestador en el run 36913373742 de main (d453dae): brujula/proxy Total 1 (HIGH 1), pcre2 CVE-2026-103111 fixed 10.49-r0. DEC-AUTO-950.", "Entregado @ PR #53 (577b9e4; pcre2 y libexpat fijados en infra/proxy/Dockerfile, RSK-OPS-046 MEDIUM). Trivy del CI: 6 imágenes 0 HIGH/CRITICAL (run 36922497210). Sincronizado con main (c5853fe) y CI verde completo; integrado en main 2026-10-01 (gh pr merge --merge @ 4c1d362). DONE. PR #22 de Dependabot no integra la corrección: no se integra."]
    actualizado: 2026-10-01
  - id: TKT-OPS-023
    titulo: "LOW (CHG de TKT-022): las miniaturas del panel salen de /api/v1/panel/medios/{id}/archivo y consumen el limitador por_ip del borde (20 r/s, burst 60): con navegación rápida por la biblioteca aparecen 429 y 'Vista previa no disponible'. Dar a /api/v1/panel/medios/*/archivo (GET, autenticado) una zona limit_req propia y adecuada, sin debilitar /api ni la anti-evasión (ADR-OPS-001), con prueba de carga de una página de 48 miniaturas x 3 navegaciones rápidas sin 429"
    fase: F7
    estado: TODO
    owner: devops
    trazabilidad: [TKT-022, TKT-OPS-016, "ADR-OPS-001", SCR-039]
    depende_de: [TKT-022]
    archivos_permitidos: ["infra/proxy/**", "docs/adr/ADR-OPS-001.md", "docs/05_operacion/DEVOPS_HANDOFF.md", "scripts/ops/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-949.", "OBS-C2-01 QA TKT-022 c2: absorberLimiteBorde (frontend/e2e/panel-soporte.ts) identifica el 429 del borde solo por Retry-After=1 (el backend también lo emite); al corregir el limitador, que el proxy marque sus 429 (cabecera propia) y el helper se restrinja a ella o a /medios/*/archivo."]
    actualizado: 2026-10-01
  - id: TKT-OPS-022
    titulo: "LOW (QA de TKT-OPS-021, más retirada de excepciones): (0) retirar EXC-01 y EXC-02 de infra/ci/cobertura_umbrales.toml (TKT-032 ya integrado: catalogos/api/views.py e inicio/api/views.py al 100 %); (F-QA021-01) clasificar vistas y services sin depender del nombre de archivo (apps/*/api/*.py salvo serializers/urls/filtros, paquetes apps/*/services/*.py, o a partir del URLconf) para que vistas_*.py o endpoints.py no pasen en silencio; (F-QA021-02) validar 'registrada' frente a hoy (ventana real <= 45 días); (F-QA021-03) límite inferior para umbral_minimo de excepciones; (F-QA021-04) incluir como críticos los módulos de soporte de auth (cuentas/sesiones.py 76 %, permisos.py, autenticacion.py) y, si quedan por debajo, abrir ticket de Developer; (F-QA021-06) no recorrer .venv; (F-PRE-01) ::add-mask:: para DJANGO_SECRET_KEY, THROTTLE_HMAC_KEY, MFA_FERNET_KEY y DB_PASSWORD efímeros del CI; añadir coverage.json a .gitignore si el contrato de DevOps lo permite (si no, anotarlo)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-021, TKT-032, "Skill_Backend §8", TKT-OPS-003]
    depende_de: [TKT-OPS-021]
    archivos_permitidos: ["infra/ci/**", ".github/workflows/**", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["DEC-AUTO-948.", "Entregado @ PR #52 (c9d1e79). Gate por estructura + URLconf real (vistas_urlconf.py; hallazgo: contenido/api/panel_urls.py sirve 18 rutas del panel con vistas de fábrica y no se clasificaba), reglas de fecha y suelo, críticos de auth, sin recorrer .venv, 8 secretos efímeros enmascarados (*** verificado en el log real). EXC-01/02 de TKT-OPS-021 retiradas; nuevas EXC sesiones.py (76 %) y permisos.py (94,12 %) hasta 2026-11-15 -> TKT-034. Controles 39/39. CI: todo verde salvo image scan por CVE-2026-103111 en el proxy (ajeno, también en main) -> TKT-OPS-024. QA tras CI verde (DEC-AUTO-950).", "2026-10-01: TKT-OPS-024 integrado (CVE del proxy corregida en main); QA ciclo 1/3 despachada sobre PR #52 @ c9d1e79 (CI rojo solo por image scan previo a #53).", "2026-10-08 (reanudación): la QA del 2026-10-01 no emitió QA_VERDICT (NOT_RUN). PR #52 en conflicto con main (DEVOPS_HANDOFF.md, tras #53): DevOps sincroniza la rama con origin/main (merge normal) y luego se relanza la QA.", "2026-10-08: rama sincronizada con main por merge normal (815a5e7; solo DEVOPS_HANDOFF.md en conflicto, fila de CVE-2026-103111 marcada CERRADA). CI run 37772199219: backend PASS (1163 tests, 97,26 %, controles 39/39), frontend FAIL por GHSA-68fv-2mgg-jv7q ajena -> TKT-OPS-025; image scan NOT_RUN (omitido). La QA espera a TKT-OPS-025.", "2026-10-08: re-sincronizado tras #59 (bc5c5ee, merge limpio), CI run 37780187419 verde completo con trivy 0 HIGH/CRITICAL en 6 imágenes. Tras integrar #51, update-branch de #52. QA ciclo 1/3 relanzada.", "2026-10-08 QA_VERDICT PASS ciclo 1/3 @ 3ecc4f4 (39/39 controles, 31/31 mutantes, E2E de URLconf, enmascarado verificado en el log real, 0 confirmed). CI run 37782526694 verde. Integrado en main (gh pr merge 52 --merge @ 409d9c0). DONE. Hallazgos LOW/INFO F-QA022-01..04 -> TKT-OPS-027."]
    actualizado: 2026-10-08
  - id: TKT-OPS-016
    titulo: "HIGH, CONDICIÓN DE F9: recalibrar el limitador de borde nginx (zone=por_ip 20r/s burst=60, clave $binary_remote_addr) -- 2-3 visitantes fríos tras una misma IP compartida (NAT/CGNAT, oficinas, operadores móviles) reciben 429 en chunks JS lazy y la navegación del router nunca completa (QA TKT-018 F-3: N=2 1/10, N=3 7-9/15 navegaciones rotas tras el fix de frontend). Una carga fría ya son ~30 peticiones: no corregible desde frontend. Opción recomendada por QA: excluir o dar zona propia generosa a los assets estáticos inmutables (chunks /*.js y /*.css con hash, /media/publico/**) y mantener por_ip 20r/s burst=60 en /api/** y HTML SSR. Documentar en ADR la decisión frente a agotamiento de recursos (DEC-AUTO-111/190/193/195/214)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-018, "DEC-AUTO-111", "DEC-AUTO-190", "DEC-AUTO-193", "DEC-AUTO-195", "DEC-AUTO-214", REQ-052]
    depende_de: [TKT-018]
    archivos_permitidos: ["infra/proxy/**", "docs/adr/ADR-OPS-*.md", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT PASS de TKT-018 (F-3 + needs_validation 'Quota-accounting scope'). AC: escenario Inicio->clic a 300 ms con N=2 y N=3 contextos Chromium fríos concurrentes desde la misma IP, 2 series, 0 navegaciones rotas y 0 429 en assets estáticos; /api/** y HTML SSR siguen limitados (verificar 429 con ráfaga sintética a /api/).", "Despachado a devops 2026-09-30 en paralelo con TKT-010 (archivos disjuntos).", "DEC-AUTO-929: alcance ampliado con X-Robots-Tag noindex, nofollow en las respuestas HTML de /panel/** (RULE-029 y sitemap exigen noindex por cabecera; hoy solo security-headers-error.conf la emite). Hallazgo del Developer de TKT-010; mismo archivo y mismo owner, comunicado al agente DevOps en curso.", "Entregado @ PR #38 (rama tkt-ops-016-limitador-estaticos, HEAD aa9324d). ADR-OPS-001 (PROPOSED): zona nueva estaticos (50 r/s, burst 300 nodelay) solo para assets del build en raíz (/*.js|mjs|css), /fonts/*.woff2, /favicon.ico y /media/publico/**; por_ip 20r/s burst=60 intacto para /api/**, SSR y el resto. Anti-evasión: la location de assets reenvía Host estaticos.invalid, de modo que un asset inexistente es rechazado por AngularNodeAppEngine (400 sin render, ~6 ms) y devuelto como 404 Problem Details. X-Robots-Tag noindex,nofollow vía map solo en ^/panel(/|$). Campo ruta_pedida en el log JSON. Mediciones declaradas (Chromium, misma IP, Inicio->clic 300 ms): antes N=2 1/10 y 0/10 rotas, N=3 15/15 y 13/15; después N=2/3/5/8 0 rotas y 0 429. Ráfagas de 200 a /api, / y /destinos siguen limitadas (~61x200/139x429). CI del PR ROJO por causa ajena verificada por el Orquestador: trivy CVE-2026-103111 HIGH en libpcre2-8-0 de las imágenes Debian (la imagen proxy alpine da 0); afecta igual a main en su próxima ejecución con código -> TKT-OPS-017. Smoke CI del proxy SKIPPED en GitHub, reproducido en local. RSK-OPS-040..043 declarados (040: NG_ALLOWED_HOSTS nunca con *, smoke a CI -> TKT-OPS-018). QA despachada; integración condicionada a QA PASS y CI verde tras TKT-OPS-017.", "QA_VERDICT PASS (ciclo 1/3), A/B cambiando solo el contenedor proxy sobre la misma semilla: N=3 main 12/15 y 12/15 navegaciones rotas (80-93 respuestas 429) -> rama 0/15 y 0/15, N=5 0/25, 0 respuestas 429; ráfagas a /api, / y /destinos siguen limitadas (~61x200/139x429), cupos separados comprobados en ambos sentidos; matriz de evasión de 31 variantes x3 (codificaciones, dobles barras, métodos, Host/X-Forwarded-* manipulados, forma absoluta): 0 renders SSR y 0 peticiones al backend; cabeceras idénticas a main salvo X-Robots-Tag en /panel*; schemathesis 3161/3161; trivy proxy 0; gitleaks/semgrep sin hallazgos reales. Hallazgos no bloqueantes -> TKT-OPS-019 (F-1 LOW: la query de un asset inexistente llega al log del SSR; F-2 INFO: X-Forwarded-Host redundante y documentación de 3 vs 8 líneas de log) y TKT-026 (F-3/F-4 preexistentes del SSR). Pendiente de integración: CI verde tras TKT-OPS-017.", "DONE: PR #38 sincronizado con main por DevOps (merge de origin/main, único conflicto en DEVOPS_HANDOFF.md resuelto conservando §23 y §24); verificado por el Orquestador que infra/proxy y docs/adr son idénticos a aa9324d (commit aprobado por QA) y que el diff frente a main son solo los 3 archivos del ticket. CI real 6/6 verde @ e4bd35f (run 36811099288), incluido por primera vez el smoke del proxy en GitHub. Merge @ e75ee7a. Riesgo HIGH de TKT-018 (F-3) cerrado."]
    actualizado: 2026-09-30
  - id: TKT-OPS-017
    titulo: "URGENTE, bloquea todo el CI: CVE-2026-103111 HIGH en libpcre2-8-0 10.46-1~deb13u2 (corregida en 10.46-1~deb13u3) presente en TODAS las imágenes Debian (backend, frontend, scheduler, backup, db); trivy CRITICAL/HIGH = fail. Corregir con el cambio mínimo reproducible (subir digest de la imagen base a uno que incluya la corrección, o actualizar el paquete en el Dockerfile con versión fijada), sin tocar .trivyignore (aceptar el CVE sería Puerta Humana §0.5)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [RSK-OPS-001, TKT-OPS-005, TKT-OPS-016]
    depende_de: []
    archivos_permitidos: ["infra/docker/**", "infra/db/**", "infra/backup/**", "infra/scheduler/**", "Dockerfile*", "compose*.yaml", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Detectado por el DevOps de TKT-OPS-016 y verificado por el Orquestador en los logs de la ejecución 36806399271 (trivy: Total 1, HIGH 1, libpcre2-8-0 CVE-2026-103111, fixed). infra/proxy/** excluido de archivos_permitidos: lo tiene TKT-OPS-016 en el PR #38 (§0.10). Despachado 2026-10-01 en paralelo con la QA de TKT-OPS-016 y el Developer de TKT-010.", "DONE @ PR #40, merge 2a95f8f. libpcre2-8-0=10.46-1~deb13u3 fijada en backend/frontend/db/backup (scheduler hereda de backend), con verificación dpkg-query en cada build (mismo patrón que openssl en TKT-OPS-014/015). Subir digest base no corregía el CVE (verificado por DevOps); rama Dependabot python-3.14.7 descartada (también trae deb13u2 y cambia el runtime). Validado por el Orquestador con el gate trivy del CI real (criterio DEVOPS_DONE de TKT-OPS-014/015): 5 imágenes Debian Total 0 HIGH/CRITICAL; CI 6/6 verde tras sincronizar con main (diff de sincronización solo docs). Riesgos nuevos: RSK-OPS-044 MEDIUM (versiones Debian fijadas a mano: revisar en cada PR de Dependabot de imagen base), RSK-OPS-045 LOW (caché local de la BD de trivy desactualizada dio falso negativo: los escaneos locales de evidencia deben usar BD fresca y registrar su UpdatedAt)."]
    actualizado: 2026-10-01
  - id: TKT-OPS-018
    titulo: "CONDICIÓN DE F9: añadir al CI un smoke del proxy para RSK-OPS-040 (ADR-OPS-001): /no-existe-N.js -> 404 problem+json sin render SSR, y una ráfaga de 120 assets estáticos sin 429; y verificar que NG_ALLOWED_HOSTS nunca contiene '*'"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-016, "ADR-OPS-001", RSK-OPS-040]
    depende_de: [TKT-OPS-016, TKT-OPS-017]
    archivos_permitidos: [".github/workflows/**", "scripts/ops/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["Recomendado por el DevOps de TKT-OPS-016 (RSK-OPS-040).", "QA de TKT-OPS-016 recomienda que este smoke sea condición de F9: la defensa anti-evasión depende de NG_ALLOWED_HOSTS y de que Angular valide el Host antes de renderizar; sin smoke en CI, una regresión pasaría en silencio. Se eleva a condición de F9 (DEC-AUTO-932).", "Despachado 2026-10-01 a devops tras TKT-OPS-019 (secuencial, PR separado); el smoke debe cubrir también el comportamiento corregido en TKT-OPS-019.", "Entregado @ PR #43 (2eb4ea4), CI real verde (run 36815190546), paso nuevo de 12 s. La rama sale de la de TKT-OPS-019: integrar antes el #41 y sincronizar. Diff propio: ci.yaml + scripts/ops/smoke-anti-evasion.sh (C1-C5). Control negativo documentado en 6 escenarios (NG_ALLOWED_HOSTS=*, *.invalid, proxy anterior a TKT-OPS-019, proxy anterior a TKT-OPS-016, /api en la zona estaticos): todos fallan con la comprobación esperada y la configuración real pasa. Pendiente fuera de su alcance: anotar el smoke en DEVOPS_HANDOFF (se hará en F9). QA despachada.", "QA_VERDICT FAIL (ciclo 1/3). F-018-01 MEDIUM: C3 no es determinista. Con por_ip intacto, en 9 ejecuciones locales los 429 del borde fueron 0, 12, 136, 0, 136, 11, 0, 5 y 18: 3 de 9 son falsos FAIL. En CI solo pasa porque el paso anterior (smoke: errores del proxy) deja DRF limitado; es una dependencia oculta de la ventana de 60 s. F-018-02 LOW: el smoke no detecta volver a $ en lugar de \z (falta C6 con /no-existe-N.js%0A). INFO: un curl -f en C2 aborta sin el resumen. Controles negativos (NG=*, proxy de main, /api en estaticos) correctos, shellcheck 0. Devuelto a devops (DEC-AUTO-936).", "Corrección del ciclo 1 @ 16b4f67 (PR #43, ya sincronizado con main; diff: solo los 2 archivos permitidos). CI real verde (run 36824127533), paso de 11 s. C3 rehecho: satura por_ip con POST / (403 por limit_except, sin upstream) y luego lanza 20 sondas GET /api; exige ≥10 respuestas 429 del borde. Resultados: 30/30 PASS en 3 series (en frío, seguidas y con el paso previo del CI delante), mínimo 16/20. Con /api en la zona estaticos falla en 5/5. C6 nuevo: con $ falla en 3/3. C2 ya no aborta. Re-QA ciclo 2/3 despachada.", "2026-10-01 corte de sesión: la re-QA ciclo 2/3 se interrumpió sin QA_VERDICT (NOT_RUN, no consume ciclo). Rama @ 16b4f67 intacta. Re-QA relanzada desde cero.", "QA_VERDICT PASS (ciclo 2/3): C3 32/32 PASS (en frío, seguidas, tras el paso previo del CI y con CPU limitada; los 429 del borde se distinguen de los de DRF por upstream_s); 6 mutantes de proxy y 4 de NG_ALLOWED_HOSTS fallan con exit 1 en la comprobación esperada; falla cerrado sin logs; shellcheck/gitleaks/semgrep 0. Hallazgos LOW/INFO a TKT-OPS-020 (DEC-AUTO-939). PR #43 sincronizado con main (10cf7fa), integración pendiente de CI verde.", "PR #43 integrado en main (gh pr merge --merge @ fdd89cf), CI verde run 36858336364. DONE."]
    actualizado: 2026-10-01
  - id: TKT-OPS-020
    titulo: "LOW: robustez del smoke anti-evasión (QA TKT-OPS-018 c2): C3 no debe depender del orden de campos del log_format (parsear JSON del log en lugar de buscar una cadena literal, con mensaje de fallo correcto); sustituir la expansión ${linea:-<sin línea>} de la línea 109 para que semgrep pueda analizar el script completo; documentar que tras C3 por_ip queda saturada ~3 s (espera si se añade un paso HTTP posterior)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-018, "ADR-OPS-001", RSK-OPS-040]
    depende_de: [TKT-OPS-018]
    archivos_permitidos: ["scripts/ops/**", ".github/workflows/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["F-QA018c2-01 LOW, F-QA018c2-04 INFO y riesgo de saturación posterior de la QA de TKT-OPS-018 ciclo 2 (DEC-AUTO-939).", "Entregado @ PR #49 (7fc3a64), CI verde (run 36900650511, smoke 6/6). C3 por campos JSON del log (control nuevo con log_format reordenado 3/3 PASS), C6 sin la expansión que rompía semgrep, espera de 4 s tras C3. Controles negativos correctos; shellcheck 0. Pendiente documentar en DEVOPS_HANDOFF en F9 junto a TKT-OPS-018. QA despachada.", "QA_VERDICT PASS (ciclo 1/3): 12/12 smoke sin falsos FAIL (C3 17-20/20), parser C3 probado con entradas preparadas, controles negativos (estaticos, $, log_format reordenado, ruta_pedida renombrada, proxy pre-TKT-OPS-016, NG_ALLOWED_HOSTS) correctos; shellcheck 0; semgrep sin error de parseo; #48 y #49 se integran sin conflicto en ambos órdenes.", "PR #49 integrado en main (gh pr merge --merge), CI verde. DONE."]
    actualizado: 2026-10-01
  - id: TKT-OPS-021
    titulo: "LOW: (a) retirar de infra/ci/oasdiff_err_ignore.txt la excepción de DEC-AUTO-920 (request-body-type-changed en POST /api/v1/panel/medios), que tras TKT-012 ya no casa con ningún hallazgo; (b) gate de cobertura por módulo en CI según Skill_Backend §8 (services >= 90 %, vistas de endpoints críticos >= 95 %) leyendo coverage.json, con umbrales versionados en infra/ci/ y excepciones con caducidad"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-012, TKT-OPS-010, "DEC-AUTO-920"]
    depende_de: [TKT-012]
    archivos_permitidos: ["infra/ci/**", ".github/workflows/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["CHG-OPS propuestos por el Developer de TKT-012 (DEC-AUTO-940).", "QA TKT-012 confirma que la excepción de err-ignore de DEC-AUTO-920 sobra (rama: 0 cambios con --fail-on WARN sin err-ignore). Al gate por módulo: catalogos/api/views.py 71,8 % e inicio/api/views.py 93,8 % (TKT-032 los sube).", "Entregado @ PR #48 (4794311), CI verde (run 36898054477). Diff: infra/ci/** + ci.yaml + DEVOPS_HANDOFF.md §26 (artefacto de DevOps según §0.12). Excepción de oasdiff retirada (mecanismo conservado vacío); gate de cobertura por módulo (gate_cobertura.py, umbrales en cobertura_umbrales.toml, excepciones con caducidad ≤45 días, falla cerrado; 20 controles). Excepciones EXC-01 (catalogos/api/views.py, suelo 71) y EXC-02 (inicio/api/views.py, suelo 93), caducidad 2026-10-31, se retiran tras integrar TKT-032 (DEC-AUTO-946). QA despachada.", "QA_VERDICT PASS (ciclo 1/3): oasdiff 0 sin la excepción y mecanismo de err-ignore verificado con mutantes; gate leído entero, 20/20 controles propios del DevOps + 26 de QA (estricto '>', caducidad, suelos, vistas sin clasificar, json vacío/ausente/NaN) con el exit esperado; pytest Linux 1073, 96,51 %; clasificación de críticos completa frente a /api/v1/panel/**. Hallazgos LOW/INFO a TKT-OPS-022 (DEC-AUTO-948).", "PR #48 integrado en main (gh pr merge --merge), CI verde. DONE."]
    actualizado: 2026-10-01
  - id: TKT-OPS-019
    titulo: "LOW: en la location de assets de infra/proxy/nginx.conf, enviar al SSR solo la ruta sin query (p. ej. proxy_pass http://frontend$uri, seguro porque la regex limita la ruta a [A-Za-z0-9_./-]) para que la query de un asset inexistente no acabe en el log del SSR (QA TKT-OPS-016 F-1: 'ERROR: Bad Request (http://estaticos.invalid/qaB.js?x=1)', contrario a REQ-057/THREAT-020 'logs sin query strings'); quitar el proxy_set_header X-Forwarded-Host redundante (Angular 22.2 lo ignora sin trustProxyHeaders y genera 2 avisos por petición) y corregir RSK-OPS-041 en ADR-OPS-001/DEVOPS_HANDOFF (8 líneas por asset inexistente, no ~3)"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-OPS-016, "ADR-OPS-001", REQ-057, THREAT-020, RSK-OPS-041]
    depende_de: [TKT-OPS-016]
    archivos_permitidos: ["infra/proxy/**", "docs/adr/ADR-OPS-001.md", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Hallazgos F-1/F-2 de QA_VERDICT PASS de TKT-OPS-016. AC: curl /no-existe.js?secreto=1 -> 0 coincidencias de 'secreto' en el log del frontend; la matriz de evasión de TKT-OPS-016 sigue dando 0 renders; assets existentes con ?v=1 siguen dando 200.", "Despachado 2026-10-01 a devops (mismo agente que TKT-OPS-018, secuencial, PR separado).", "Entregado @ PR #41 (e7ea451), CI real verde (run 36813942642). Diff verificado: los 3 archivos permitidos. proxy_pass http://frontend$uri (sin query hacia el SSR); en el log del SSR, 3 -> 0 apariciones del token de la query. DEC-AUTO-935: (a) ancla \z en lugar de $ en la regex de la location de assets, porque en PCRE $ casa antes de un \n final y con $uri /x.js%0A llegaba al SSR con un salto de línea crudo; con \z esa ruta cae en location / (por_ip), como /x.js%20 en main; (b) también se retira X-Forwarded-Proto (redundante, como X-Forwarded-Host). Matriz de 37 variantes: 0 error_ssr y 0 peticiones al backend. Cabeceras idénticas a main. RSK-OPS-041 medido: 8 -> 4 líneas de log por asset inexistente. QA despachada (junto con TKT-OPS-018).", "QA_VERDICT PASS (ciclo 1/3), con tcpdump en el frontend y el backend para ver la línea de petición exacta. La query ya no llega al SSR (main la mostraba en su log; la rama, 0). Matriz de 85 variantes A/B: 0 error_ssr y 0 peticiones al backend; nada crudo llega aguas arriba. DEC-AUTO-935 verificada: con $ se cuela un LF crudo, con \z no. Los 58 assets reales del build siguen en la zona estaticos. 3 visitantes en frío: 0/30 navegaciones rotas. Keepalive intacto (1 SYN por cada 400 peticiones) y latencia igual. Cabeceras idénticas a main. Hallazgos INFO, todos preexistentes (F-019-01..03). Pendiente: integrar tras sincronizar y con CI verde.", "DONE: PR #41 sincronizado con main (diff de sincronización solo docs), CI real 6/6 verde @ 28f7cc2, merge @ 42546be."]
    actualizado: 2026-10-01
  - id: TKT-026
    titulo: "INFO, preexistentes en el SSR (QA TKT-OPS-016 F-3/F-4): (a) Range no satisfacible sobre un asset existente -> express.static lanza RangeNotSatisfiableError y frontend/src/server.ts responde 500 (error_ssr) en lugar de 416; (b) cuando DRF limita (429) la llamada del SSR a /api/v1/publico/destinos/<slug>, la ficha de un slug inexistente se sirve como 200 con página de error suave en vez de un código real (debería ser 503 con Retry-After, o el error que corresponda, nunca 200)"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-OPS-016, TKT-008]
    depende_de: [TKT-OPS-016]
    archivos_permitidos: ["frontend/src/server.ts", "frontend/src/server.spec.ts", "frontend/src/app/features/destinos/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Hallazgos F-3/F-4 de QA_VERDICT PASS de TKT-OPS-016. Revisar si (b) afecta también a las demás fichas SSR (itinerarios, guías, tipos, colecciones); si es así, ampliar archivos_permitidos por DEC-AUTO antes de tocar otras features."]
    actualizado: 2026-10-01
  - id: TKT-027
    titulo: "LOW (QA TKT-010 FALLO-03, parte backend): la validación de 'siguiente' en el login del panel acepta segmentos de punto codificados (/panel/%2e%2e/destinos, /panel/%2E%2E/%2E%2E/destinos, /panel/.%2e/destinos) y devuelve redireccion fuera de /panel. Es mismo origen, sin redirección externa, pero incumple AC-115 y THREAT-017. Decodificar antes de validar, o rechazar %2e/%2f/%5c, y añadir pruebas con esas variantes"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [AC-115, THREAT-017, TKT-004, TKT-010]
    depende_de: []
    archivos_permitidos: ["backend/apps/cuentas/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT FAIL de TKT-010 (FALLO-03). La parte frontend (core/auth/destino-seguro.ts) se corrige dentro de TKT-010. Candidatos: backend/apps/cuentas/api/serializers.py, api/views.py, autenticacion.py.", "Despachado 2026-10-01 en paralelo con TKT-012 (backend, archivos disjuntos) y con TKT-010 / TKT-OPS-018 en curso.", "Entregado @ PR #44 (66a7245), CI real verde, solo backend/apps/cuentas/**. Validador puro services.redireccion_segura: decodifica de forma iterativa (máx. 5 niveles), rechaza %2f/%5c en cualquier nivel y valida por segmentos la forma canónica, que es la que devuelve. 852 passed; services.py 97 % (validador 100 %). Endurecimiento: %zz y UTF-8 no ASCII ahora dan /panel. Incoherencia preexistente: el frontend acepta query en siguiente y el backend no (la redireccion del servidor será /panel). QA despachada.", "2026-10-01 corte de sesión: la QA ciclo 1/3 se interrumpió sin QA_VERDICT (NOT_RUN, no consume ciclo). Rama @ 66a7245 intacta. QA en cola, se relanza cuando haya capacidad (máx. 3 agentes).", "QA_VERDICT PASS (ciclo 1/3, relanzada tras el corte): AC_TKT027_01..04 PASS; 111 casos de evasión por HTTP real (overlong, fullwidth, ancho cero, %25 hasta 11 niveles, CR/LF, ';', '#', longitudes ~2000) con 0 salidas de /panel y 0 5xx; 198 009 caracteres en 38 ms; mutantes M1/M2/M4/M5/M6 detectados (M3 sobrevive: OBS-02); pytest 856, services 97 % (validador 100 %); schemathesis 3142/3142; bandit/semgrep/gitleaks 0. Hallazgos LOW (OBS-01 /panel/acceso aceptado como destino, preexistente y neutralizado en el cliente; OBS-02; OBS-04; OBS-05) a TKT-031; OBS-03 (regla única cliente/servidor para query) a TKT-028 (DEC-AUTO-942). PR #44 sincronizado con main, integración pendiente de CI verde.", "PR #44 integrado en main (gh pr merge --merge @ 56fca30), CI verde. DONE."]
    actualizado: 2026-10-01
  - id: TKT-028
    titulo: "LOW (QA TKT-010 OBS-08 y OBS-07): (a) /robots.txt responde con la página HTML 404 del SSR; servir un robots.txt real (permitir el sitio público, bloquear /panel/ y /api/, y enlazar el sitemap si existe) con tipo text/plain; (b) conservar Retry-After en core/http (normalizarError -> ErrorApi) para todas las features, de modo que features/panel/data/espera.ts deje de reconocer HttpErrorResponse por su forma"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-010, RULE-029, "Skill_Frontend#Regla09"]
    depende_de: [TKT-010]
    archivos_permitidos: ["frontend/public/robots.txt", "frontend/src/server.ts", "frontend/src/app/core/http/**", "frontend/src/app/features/panel/data/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT FAIL de TKT-010 (observaciones no bloqueantes). Coordinar con TKT-019 (mapa del sitio) para enlazar el sitemap si TKT-019 genera uno.", "OBS-03 de la QA de TKT-027: el frontend (destino-seguro.ts) acepta query/fragmento y segmentos no ASCII en siguiente y el backend los descarta (cae en /panel, se pierde el deep link con filtros). Decidir una sola regla (DEC-AUTO-942).", "DEC-AUTO-944: bajar a 2000 el límite de siguiente en frontend/src/app/core/auth/destino-seguro.ts para igualar LoginEntrada.siguiente.maxLength del contrato (OBS-04 de TKT-027/031): hoy un enlace con siguiente de 2001-2048 caracteres impide el login.", "QA TKT-031 (INFO, servidor más estricto, sin impacto): /panel/ACCESO aceptado en ambos lados (rutas sensibles a mayúsculas, sin bucle); diferencias en %2e (cliente rechaza, servidor decodifica), niveles de decodificación (1 frente a 5: /panel/%2561cceso), segmentos vacíos (/panel//x) y no ASCII. Incluir en la regla única."]
    actualizado: 2026-10-01
  - id: TKT-029
    titulo: "LOW (seguimiento de TKT-020): (a) features/institucional/ui/pagina-creditos.html no pasa [derivados] a <app-imagen-responsiva>, así que en navegadores sin AVIF /creditos sigue mostrando 24 textos alternativos; (b) los 8 mappers de las features descartan el campo formato (FormatoDerivado del contrato) de los derivados: pasarlo para que ImagenResponsiva deje de deducirlo por la extensión (DEC-AUTO-934); (c) versionar en frontend/e2e las E2E de los AC de TKT-020 (WebKit con imágenes de respaldo, Chromium descargando solo AVIF, HTML sin JS con src en imágenes informativas)"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-020, "DEC-AUTO-934"]
    depende_de: [TKT-020, TKT-010, TKT-016]
    archivos_permitidos: ["frontend/src/app/shared/ui/imagen-responsiva/**", "frontend/src/app/features/inicio/ui/pagina-inicio.html", "frontend/src/app/features/inicio/ui/pagina-inicio.ts", "frontend/src/app/features/*/data/**", "frontend/src/app/features/institucional/ui/pagina-creditos.html", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Propuesto por el Developer de TKT-020. Depende de TKT-010 porque comparte frontend/e2e/** (§0.10).", "Ampliado por la QA de TKT-020 (DEC-AUTO-937): (d) F-QA020-01: formatoDeUrl debe quitar ?/# antes de aplicar la regex (shared/ui/imagen-responsiva); (e) F-QA020-05: la hero de Inicio (features/inicio/ui/pagina-inicio.html:21) es un <img> con un único AVIF de 400 px -> invisible en WebKit; usar <app-imagen-responsiva> con derivados. Depende también de TKT-016 por solaparse en features/inicio."]
    actualizado: 2026-10-01
  - id: TKT-030
    titulo: "MEDIUM, preexistente (QA TKT-020 F-QA020-04): tras la hidratación, el cliente elimina y recrea los subárboles renderizados por SSR que contienen imágenes (medido con MutationObserver: /destinos 24 IMG en DIV.resultados, ficha 13, itinerario 7, Inicio 24+1; igual en main, 3 motores, sin NG0500). Investigar la causa (p. ej. stores que vuelven a pedir los datos en cliente sin TransferState / withHttpTransferCache, o un @if/@for cuya identidad cambia) y hacer que la hidratación reutilice el DOM. Probable contribución a LCP (TKT-021) y CLS (TKT-016)"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-020, TKT-016, TKT-021]
    depende_de: [TKT-010]
    archivos_permitidos: ["frontend/src/app/features/*/state/**", "frontend/src/app/features/*/ui/**", "frontend/src/app/core/http/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de la QA de TKT-020. archivos_permitidos provisionales: primero diagnosticar; si la causa está en app.config.ts (proveedores de hidratación o caché de transferencia) coordinar con TKT-016/TKT-025, que comparten ese archivo. Ordenar con TKT-016 y TKT-021: diagnosticar este antes de optimizar LCP/CLS."]
    actualizado: 2026-10-01
  - id: TKT-020
    titulo: "ImagenResponsiva: (F-2 MEDIUM, preexistente de TKT-002) src/srcset solo AVIF sin formato de respaldo -- en navegadores sin AVIF (WebKit de Playwright en Windows) (error)->alFallar() elimina el <img>: 0 imágenes de tarjeta en WebKit en todos los listados; usar <picture> con <source type=image/avif> + respaldo WebP/JPEG (los derivados ya existen por DEC-AUTO-044). (F-1 LOW, introducido por TKT-018) imágenes no prioritarias con alt informativo (galerías de destino/itinerario, miniaturas de créditos) salen sin src en SSR y nunca cargan sin JS ni para crawlers; emitir src en SSR o <noscript> para las no decorativas y corregir el comentario incorrecto del componente, sin reintroducir la ráfaga de TKT-018"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-018, TKT-002, "DEC-AUTO-044"]
    depende_de: [TKT-018]
    archivos_permitidos: ["frontend/src/app/shared/ui/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT PASS de TKT-018 (F-1, F-2). Si el contrato o el cliente generado no exponen los derivados WebP/JPEG, usar Botón de Pánico (no tocar apps/medios ni contracts/). AC: WebKit renderiza imágenes de tarjeta en /destinos; curl de /creditos sin JS muestra src en imágenes con alt no vacío; el conteo de peticiones frías de /destinos no vuelve a subir (≤ ~30 en Chromium).", "Despachado 2026-10-01 en paralelo con la QA de TKT-010 y con TKT-OPS-018/019 (archivos disjuntos: shared/ui frente a features/panel, core/layout/shell-publico e infra).", "Entregado @ PR #42 (rama tkt-020-imagenes-formato-respaldo, c3bd314). Diff verificado: solo imagen-responsiva.ts/.spec.ts. <picture> con <source> por formato (AVIF/WebP) + JPEG de respaldo; alFallar descarta solo el formato que falló (img.currentSrc); src en SSR para imágenes con alt informativo (sin <noscript>, para no romper la hidratación), decorativas siguen diferidas. A/B declarado: WebKit /destinos 0/24 -> 24/24 imágenes; ficha 3/12 -> 13/13; Chromium solo descarga AVIF; HTML sin JS de /creditos 24/24 sin src -> 0/24; ráfaga de /destinos igual (6 imágenes, 30 peticiones). 430/430 unit, CI 5/5 verde. DEC-AUTO-934: se acepta deducir el formato por la extensión de la URL mientras los mappers de las features no pasen formato (el backend nombra <huella>-<ancho>.<avif|webp|jpeg> y nginx fija el Content-Type por extensión; si la extensión no se reconoce, se usa el <img> como antes). Lo pendiente fuera de alcance va a TKT-029. QA despachada.", "QA_VERDICT PASS (ciclo 1/3), A/B con la misma semilla en 3 motores. WebKit: /destinos 0/24 -> 24/24, ficha 3/13 -> 13/13, itinerario 0/7 -> 7/7. Chromium y Firefox solo AVIF. Sin JS: /creditos 0/24 -> 24/24 con src; decorativas siguen diferidas. Ráfaga de /destinos igual (30 peticiones, 6 imágenes); N=5 sin 429. alFallar verificado bloqueando formatos (AVIF -> WebP -> JPEG, sin bucles). SSR = cliente, 0 avisos de hidratación, axe 0. Lighthouse sin regresión. gitleaks/semgrep limpios. Hallazgos: F-QA020-01 LOW (formatoDeUrl toma la extensión de la query si la ruta no tiene) y F-QA020-05 MEDIUM preexistente (hero de Inicio solo AVIF) -> TKT-029; F-QA020-02 LOW aceptado (/creditos 24 imágenes en frío, consecuencia esperada del AC03, 0 x 429 con N=5); F-QA020-03 LOW (WebKit descarga JPEG + WebP del LCP) -> TKT-021; F-QA020-04 MEDIUM preexistente (la hidratación destruye y recrea los subárboles SSR) -> TKT-030. Pendiente: integrar tras sincronizar y con CI verde.", "DONE: PR #42 sincronizado con main (el diff propio sigue siendo los 2 archivos de shared/ui), CI real 6/6 verde @ 75f521e, merge @ a2a06e7."]
    actualizado: 2026-09-30
  - id: TKT-021
    titulo: "LCP móvil de las páginas de listado 3.1-3.7 s (Lighthouse móvil, throttling simulado) frente a REQ-052 (≤ 2,5 s): preexistente, medido igual en main antes de TKT-018, sin ticket que lo cubra (TKT-016 solo cubre CLS). Investigar la causa (imagen LCP, bundle, TTFB de SSR, fuentes) y corregir o acotar"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [REQ-052, TKT-018, TKT-016]
    depende_de: [TKT-016, TKT-020]
    archivos_permitidos: ["frontend/angular.json", "frontend/src/app/features/destinos/**", "frontend/src/app/features/guias/**", "frontend/src/app/features/itinerarios/**", "frontend/src/app/shared/ui/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT PASS de TKT-018 (riesgo 2). Depende de TKT-016 y TKT-020 por solape de archivos. archivos_permitidos provisionales: ampliar por DEC-AUTO si la causa está en core/ o en la configuración de build.", "QA de TKT-010 (OBS-08): LCP de laboratorio > 2.5 s también en Inicio en main (2.65-2.80 s móvil), CLS de /destinos en Lighthouse móvil de 0.67 a 0.95 y /acerca-de con CLS 1.12 en Chromium (pie desplazado), todo preexistente. Incluir Inicio y /acerca-de en la investigación; coordinar con TKT-016 (CLS).", "QA de TKT-020: F-QA020-03, en WebKit la ficha y el itinerario descargan el JPEG del src SSR del LCP además del WebP del <source> (1 petición extra). Y F-QA020-04 (TKT-030, recreación del DOM en la hidratación) probablemente influye en LCP y CLS.", "DEC-AUTO-938: incluye el residual de LCP simulado de Inicio de TKT-010 (~150 ms, solo en Lighthouse con throttling simulado; tiempos observados iguales a main). Causa medida por el Developer de TKT-010: con ≥3 chunks diferidos, @angular/build 22.2 (rolldown con main como única entrada) separa el framework (~90 kB gzip) en un chunk aparte junto a un main pequeño. Investigar en la configuración del build (angular.json, budgets/optimization, variables de build del Dockerfile o la versión de @angular/build); NG_BUILD_OPTIMIZE_CHUNKS=false empeora (5 ficheros).", "QA TKT-010 c2: en /destinos el LCP simulado empeora ~150 ms con paridad en el observado (misma causa que DEC-AUTO-938).", "QA TKT-010 c3: LCP simulado de /destinos y /acerca-de ~150-300 ms peor que main con paridad observada (mismo mecanismo de DEC-AUTO-938)."]
    actualizado: 2026-10-01
  - id: TKT-009
    titulo: "Frontend público 2: itinerarios, guías, tipos de aventura, colecciones, glosario, búsqueda, institucional/legal, créditos"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-003, MOD-004, MOD-005, MOD-007]
    depende_de: [TKT-008]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/features/itinerarios/**", "frontend/src/app/features/guias/**", "frontend/src/app/features/tipos-aventura/**", "frontend/src/app/features/colecciones/**", "frontend/src/app/features/glosario/**", "frontend/src/app/features/busqueda/**", "frontend/src/app/features/institucional/**", "frontend/e2e/**", "frontend/src/app/core/layout/navegacion.ts", "frontend/src/app/features/inicio/ui/pagina-inicio.html", "frontend/src/app/features/inicio/ui/pagina-inicio.ts", "frontend/src/app/core/layout/cabecera-sitio/cabecera-sitio.spec.ts"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["Despachado. Segundo ticket de frontend de esta sesión, tras TKT-008 (inicio/destinos/guardados) DONE. Se instruyó inventariar lo ya construido en TKT-002/008 antes de programar (shared/ui, core/layout, api client, y el patrón de features inicio/destinos como referencia de arquitectura), y se dieron punteros de fuente primaria a BLUEPRINT.md (SCR-005..014/017/018/020/021, FEAT-006..024/052, RULE-005/014/018/024/026) y HANDOFF_UI_UX.yaml (líneas 780-1085) en vez de parafrasear. Se señaló explícitamente que ElementoGuardado (core/layout/guardados) ya soporta tipo 'ITINERARIO' además de 'DESTINO' -- reutilizar boton-guardar/boton-compartir ahí, no reinventar. Se pidió aplicar los aprendizajes de QA de TKT-008 de forma proactiva: no aria-pressed en <a>, cuidado con layout shift de contenido async sin reservar espacio, cuidado con ráfagas de peticiones de imagen en listados (rate-limit real de nginx, TKT-018).", "Entregado @ PR #35 (rama tkt-009-frontend-publico-2, sobre main @ 8b72a64). Las 7 features restantes del frontend público: itinerarios, tipos de aventura, guías, colecciones, glosario, búsqueda, institucional (4 páginas legales/informativas + créditos). 11 pantallas nuevas. 412/412 tests unitarios (89 archivos), cobertura domain≥90%/state≥80%/global≥70% en verde, tsc/eslint limpios, build cliente+SSR íntegro. CI real del PR (todos los jobs requeridos) en verde, incluido build+trivy+SBOM. 4 decisiones de alcance documentadas: (1) medidor de 'exigencia' de Tipos de aventura reutiliza <app-medidor-dificultad> en vez de una variante propia (fuera de archivos_permitidos tocar shared/ui); (2) Colecciones y Glosario NO añadidos a la navegación principal (core/layout/navegacion.ts fuera de alcance) -- quedan alcanzables solo por enlaces contextuales (términos de glosario, bloques 'Sigue explorando' tipo COLECCION, buscador), Developer señala riesgo de posible violación de 'Cero Elementos Huérfanos' (CLAUDE.md §5.3) y sugiere ticket de seguimiento para navegacion.ts -- QUEDA PARA QUE QA EVALÚE SI ES BLOQUEANTE; (3) SCR-021 Créditos: el contrato es medio-céntrico, se invirtió el pivote a agrupado-por-contenido en el dominio (agruparCreditosPorContenido, con test), sin tocar el contrato; (4) FEAT-022 (versión imprimible, COULD) no implementado, galería de itinerario sin visor modal (VisorGaleria es de la feature destinos, no importable entre features por Regla 05 de Skill_Frontend) -- documentado como mejora opcional, no regresión de alcance MUST. E2E nuevos (contenido-aventura.spec.ts, busqueda-e-institucional.spec.ts) escritos pero NO ejecutados por el Developer (requieren stack real con semilla, corresponde a QA). QA despachado.", "QA_VERDICT FAIL (ciclo 1/3), auditoría independiente completa (worktree y stack Docker propios, semilla real, 3 navegadores): tests(412/412)/arquitectura(13 reglas)/a11y(0 violaciones, confirmó por grep 0 usos de aria-pressed)/contrato(NOT_APPLICABLE)/seguridad(gitleaks+semgrep limpios)/performance(CLS=0 en las 4 páginas de listado nuevas) PASS. Confirmó con grep que la justificación de Regla 05 (VisorGaleria no importable entre features) es correcta, y que la reutilización de medidor-dificultad y la inversión de pivote de créditos son válidas. 2 hallazgos CONFIRMADOS: (1) MEDIO regresión de test -- frontend/e2e/shell.spec.ts líneas 102-107 (heredado de TKT-002/008) afirma que /guias muestra 404; TKT-009 implementó /guias como página real, dejando la aserción obsoleta. Reproducido 3/3 en aislamiento; descartado que fuera solo ruido de red (429 de TKT-017/018) bloqueando **/media/** y confirmando que la navegación real SÍ llega a /guias -- dentro del propio archivos_permitidos de TKT-009 (frontend/e2e/**). (2) ALTO -- violación CONFIRMADA con datos reales de RULE-030 (Cero huérfanos, CLAUDE.md §5.3): verificó con consultas reales a los 4 índices públicos que 0 contenidos tienen relacionado tipo COLECCION, que /api/v1/publico/busqueda nunca agrupa por colecciones, y que /colecciones no aparece en NAVEGACION_PRINCIPAL ni en pagina-inicio.html -- un visitante real no puede llegar a /colecciones sin escribir la URL. navegacion.ts trae un comentario literal ya previendo esto ('Colecciones* ... se añadirán cuando esa feature exista') y el Blueprint (SCR-001 línea 244, GI-01 línea 198) especifica exactamente el enlace a añadir (el asterisco de RULE-030 se resuelve ahora que la feature existe). Glosario, en cambio, SÍ tiene reachability contextual real (3 guías con términos vinculados) coincidente con su diseño previsto (FEAT-019, solo contextual) -- no es hallazgo. Se amplía archivos_permitidos con core/layout/navegacion.ts + features/inicio/ui/pagina-inicio.{html,ts} (DEC-AUTO, mismo patrón que TKT-006/esquema.py y TKT-008/app.spec.ts) para el enlace mínimo ya especificado por el Blueprint. Hallazgo colateral no bloqueante: QA descubrió que /mapa-del-sitio (SCR-022, MUST, FEAT-025) NUNCA fue ticketado por ningún Micro-Ticket -- 404 real en producción hoy pese a que el pie de página ya lo enlaza desde TKT-008; se abre TKT-019. También reforzó la severidad de TKT-018 (el 429 puede tumbar chunks JS de navegación, no solo imágenes). Se devuelve a Developer para ciclo 2/3.", "Corrección en curso: ambos fixes aplicados y verificados (shell.spec.ts con el h1 real de Guías + orden de nav en WebKit corregido; enlace a Colecciones añadido a NAVEGACION_PRINCIPAL -- reutilizado por cabecera Y pie de página al mismo tiempo -- y al mosaico de Inicio sin tocar el dominio). El propio fix de navegación rompió, como consecuencia directa y esperada, una aserción 'todavía no implementado' en cabecera-sitio.spec.ts (misma clase de problema que shell.spec.ts, mismo patrón). Developer preguntó en vez de tocar un archivo fuera de su alcance autorizado -- se amplía archivos_permitidos con ese único spec (DEC-AUTO, mismo patrón, tercera vez en este ticket) y se autoriza a corregirlo.", "Corrección @ ccc7cc5 (PR #35) completa: los 2 hallazgos de QA corregidos (h1 real de Guías + orden de nav WebKit; enlace a Colecciones en NAVEGACION_PRINCIPAL -- resuelve cabecera y pie en un solo cambio por reutilizar la misma constante -- + mosaico de Inicio sin tocar el dominio), más el efecto colateral autorizado (cabecera-sitio.spec.ts: la aserción negativa sobre Colecciones se reemplazó por una equivalente sobre Glosario, que sigue intencionalmente fuera de la nav). 412/412 tests, tsc/eslint limpios, build íntegro. CI real del PR en verde completo. QA despachado (ciclo 2/3).", "QA_VERDICT PASS (ciclo 2/3), verificación independiente completa (worktree y stack Docker propios desde cero, semilla real): RULE-030 CONFIRMADO CORREGIDO con datos reales -- curl a /api/v1/publico/colecciones confirma 4 colecciones reales; /colecciones responde HTTP 200 con las 4 fichas enlazadas; 'Colecciones' aparece 3 veces en el HTML real (cabecera, mosaico de Inicio, pie), orden de cabecera coincide EXACTO con HANDOFF_UI_UX GI-01 línea 66; Glosario confirmado ausente de la nav principal (0 apariciones), coherente con su diseño. shell.spec.ts y cabecera-sitio.spec.ts verificados correctos. 412/412 tests (sin regresión de cobertura), tsc/eslint limpios, a11y 0 violaciones en /, /colecciones, /guias, gitleaks/semgrep limpios, contrato NOT_APPLICABLE, CLS de Inicio 0.746 (mismo problema preexistente de TKT-016, confirmado que el mosaico de Colecciones -texto estático sin imágenes- no lo causa). PASS SIN HALLAZGOS BLOQUEANTES para TKT-009. Hallazgo colateral de severidad ALTA (no de este ticket, refuerza TKT-018): reprodujo 10/10 en Chromium aislado que el test heredado shell.spec.ts:46 (navegación por teclado, código NO tocado por TKT-009) falla por el mismo fenómeno ya conocido -- el limitador de nginx (429) tumba los chunks JS de rutas lazy-loaded tras el storm de peticiones 404 de imágenes (TKT-017) que la propia carga de Inicio dispara; contraprueba con playwright-core directo (sin las peticiones de imagen) confirma que el código de navegación en sí es 100% correcto. QA eleva la severidad de TKT-018 de 'puede romper' a '100% reproducible en Chromium, el motor más usado, incluso en un stack recién levantado' y recomienda evaluar si debe convertirse en bloqueante de F9/release. PR #35 verificado independientemente por el Orquestador (gh pr checks 35, mergeable=MERGEABLE) e integrado con gh pr merge --merge @ c4b94be. Main local reconciliado sin conflictos. TKT-009 DONE -- segundo ticket de frontend completo de la sesión: 7 features, 11 pantallas nuevas, 1 violación real de RULE-030 encontrada y corregida con datos reales (no solo argumentación), 1 gap de planificación descubierto (SCR-022 nunca ticketado, TKT-019 abierto), severidad de TKT-018 reforzada dos veces (en TKT-008 y ahora en TKT-009)."]
    actualizado: 2026-09-30
  - id: TKT-010
    titulo: "Panel 1/4 -- acceso, armazón y tablero: SCR-030 Acceso (?siguiente= con retorno seguro interno), SCR-031 Verificación MFA, SCR-032 Mi cuenta (cambio de contraseña obligatorio/voluntario, activar/desactivar MFA con reautenticación DEC-AUTO-215, códigos de recuperación), SCR-033 Autorización de tratamiento (bloqueante), SCR-034 Tablero, SCR-048 Acceso denegado (403); armazón del panel (layout de escritorio con navegación lateral, saltos de accesibilidad, cierre de sesión, guard de sesión/rol) y estructura de carpetas que reutilizarán TKT-022/023/024"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-009, MOD-010, FEAT-029, FEAT-030, FEAT-031, FEAT-032, FEAT-033, FLOW-010, SCR-030, SCR-031, SCR-032, SCR-033, SCR-034, SCR-048, RULE-017, RULE-029, THREAT-001, THREAT-002, "DEC-AUTO-215"]
    depende_de: [TKT-009, TKT-006]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/app.html", "frontend/src/app/app.ts", "frontend/src/app/app.css", "frontend/src/app/app.spec.ts", "frontend/src/app/core/layout/shell-publico/**", "frontend/src/app/features/panel/**", "frontend/src/app/core/auth/**", "frontend/e2e/**", "frontend/package.json", "frontend/package-lock.json"]
    ciclo_qa: 3/3
    ciclo_panico: 1/2
    evidencia: ["DEC-AUTO-927: el TKT-010 original (19 pantallas SCR-030..048, ~70 endpoints) se divide en 4 Micro-Tickets secuenciales: TKT-010 (acceso+armazón+tablero), TKT-022 (medios), TKT-023 (contenidos), TKT-024 (inicio, taxonomías, configuración, cuentas, auditoría). Despachado 2026-09-30 en paralelo con TKT-OPS-016 (archivos disjuntos).", "Botón de Pánico 1/2 (justificado, antes de escribir código): el shell público (app.html: skip-link + cabecera + main + pie sin condición alrededor del único router-outlet) envolvería /panel/**, incumpliendo TPL-PANEL-AUTH/TPL-PANEL-SHELL (HANDOFF_UI_UX l.194-199) y anidando landmarks (AC_TKT010_10). Verificado por el Orquestador. DEC-AUTO-928: ampliación opción A (ShellPublico como ruta de layout padre de las rutas públicas). Estructura del Developer aceptada: features/panel como UNA feature con capas planas (los globs de eslint features/*/{ui,state,data,domain} no cubrirían subcarpetas por área), rutas hijas en features/panel/ui/panel.routes.ts, catálogo de secciones en domain. Reanudado.", "Entregado @ PR #39 (rama tkt-010-panel-acceso, HEAD f349018). Diff verificado por el Orquestador dentro de archivos_permitidos ampliados. 505/505 unit, cobertura global 84 % / panel domain 100 % líneas, eslint/tsc/build OK; E2E contra stack real 168/168 en 3 motores (13 casos del panel x3 + regresión pública completa 129/129 en serie). Dependencia nueva uqr@0.1.3 (MIT, sin transitivas). gitleaks/semgrep/npm audit limpios. CI: todo verde salvo trivy (CVE-2026-103111, TKT-OPS-017, ajeno). Riesgos declarados: (1) con la opción A un 429 en un chunk diferido en la primera carga deja la página en blanco en vez de conservar cabecera/pie -> TKT-025; (2) AC_TKT010_08 E2E parcial hasta que exista una ruta solo-Admin (TKT-024 debe añadir el E2E sobre /panel/usuarios); (3) QR no decodificado con lector (la clave manual sí se probó E2E). El Developer declaró un taskkill por nombre de imagen demasiado amplio, sin efecto constatado. QA despachada.", "QA_VERDICT FAIL (ciclo 1/3) sobre f349018. PASS: archivos_permitidos, 505/505 tests y cobertura, lint/tipos/build, 13 reglas de arquitectura, regresión del shell público (A/B del SSR en 10 rutas: códigos, landmarks, skip-link, nonce CSP iguales; CLS de Inicio 0.671 -> 0.0002), a11y (axe 0 en todas las pantallas y pasos del asistente MFA, Lighthouse a11y 100), contrato, seguridad (login genérico, 14 variantes de siguiente externo rechazadas, cookies HttpOnly, storage vacío, QR decodificado con jsQR = clave manual = otpauth del servidor, solo red de mismo origen). FALLOS: FALLO-01 MEDIUM carrera CSRF en el primer login en WebKit (el POST de login sale sin X-CSRFToken porque document.cookie aún no refleja el Set-Cookie del GET csrf; 1/17 en WebKit); FALLO-02 MEDIUM regresión de LCP en Inicio (+350 ms, de 2.65-2.80 a 3.00-3.11 s móvil): con ShellPublico como padre, el SSR de / baja de 9 a 1 modulepreload; FALLO-03 LOW siguiente con segmentos de punto codificados (/panel/%2e%2e/destinos) se acepta en el cliente (esDestinoSeguro) y en el backend. Observaciones que se corrigen en este ciclo por estar en alcance: OBS-04 (<title> de Inicio distinto entre SSR y cliente) y OBS-06 (navegación del panel < lg es desplegable en línea, el HANDOFF pide cajón modal). Devuelto al Developer (DEC-AUTO-933).", "Corrección del ciclo 1 entregada @ 11c0efa (PR #39), CI real 6/6 verde (run 36822865240), alcance verificado por el Orquestador. Cambios: (a) FALLO-01: espera acotada (≤1 s) a la cookie CSRF y un único reintento solo ante csrf_invalido; WebKit AC_TKT010_01 80/80 y 0 respuestas 403 en el proxy. (b) FALLO-03: esDestinoSeguro rechaza %2e/%2f/%5c también tras decodificar, incluida la doble codificación. (c) OBS-04 + modulepreload de FALLO-02: DEC-SHELL, rutas planas como en main, con App eligiendo entre ShellPublico y un outlet sin chrome según la zona; / pasa de 1 a 10 modulepreload (main 9); títulos SSR iguales a main en 14 rutas. (d) OBS-06: cajón modal <dialog>. (e) El JS compartido del panel se reduce (sin DatePipe, NgTemplateOutlet ni @angular/forms): inicial 122.96 kB gzip (main 120.55). Riesgo: TKT-022/023/024 heredan el patrón de formularios sin @angular/forms (directiva EnlaceValor). Residual de FALLO-02: LCP simulado de Inicio ~150 ms peor que main (2.93-3.05 s frente a 2.77-2.81 s), con paridad en los tiempos observados; la causa es la disposición de chunks de @angular/build/rolldown al existir una ruta diferida; no hay palanca dentro de archivos_permitidos. DEC-AUTO-938: se acepta en este ticket y se traslada a TKT-021. QA ciclo 2/3 despachada.", "2026-10-01 corte de sesión: la re-QA ciclo 2/3 se interrumpió sin QA_VERDICT (NOT_RUN, no consume ciclo). Stacks y worktrees de QA desmontados; rama @ 11c0efa intacta. Re-QA ciclo 2/3 relanzada desde cero.", "QA_VERDICT FAIL (ciclo 2/3, relanzada tras el corte): FALLO-01, FALLO-03, OBS-04 y OBS-06 CORREGIDOS con evidencia en 3 motores; FALLO-02 dentro del residual de DEC-AUTO-938 (+33 ms simulado, paridad observada); 524 unit, 183/183 E2E, SSR A/B 22 rutas, a11y y seguridad PASS. FAIL por regresion_shell (HALLAZGO-ZONA, LOW latente / MEDIUM cuando exista un enlace SPA entre zonas): App cambia enPanel en NavigationStart y el outlet nuevo reactiva la ruta saliente: la página pública se remonta sin chrome (80-119 ms local, 1,5 s con latencia, ~2000 nodos y peticiones duplicadas) y el layout del panel aparece dentro del shell público con 2 <main>. Más OBS-A11Y-01 LOW (foco tras login fallido sobre div.resumen vacío). Devuelto al Developer, ciclo 3/3 (DEC-AUTO-941). PR #39 sincronizado con main.", "Corrección del ciclo 2 @ 24e22db (PR #39, CI verde run 36869848637; diff completo frente a main dentro de archivos_permitidos). HALLAZGO-ZONA: ZonaOutlet (extiende RouterOutlet) cambia la zona al activar una ruta de la otra zona, definida por data en app.routes.ts, y conserva la página saliente hasta el swap; e2e/zonas.spec.ts falla 9/9 sin el fix y pasa 18/18 con él; E2E completa 189/189 en 3 motores; SSR 22 rutas sin diferencias. OBS-A11Y-01 con afterNextRender. Contrato para TKT-022/023/024: armazones con <router-outlet appZona=panel> y rutas bajo la ruta panel. Re-QA ciclo 3/3 (última) despachada.", "QA_VERDICT PASS (ciclo 3/3): HALLAZGO-ZONA corregido (0 cuadros sin chrome, con 2 <main> o armazones mezclados en 3 motores, también con 300 ms de latencia, cruces cancelados, alternancia rápida y doble clic; sin fugas tras 44 cruces; la E2E nueva falla 6/6 en 11c0efa y pasa 6/6 en 24e22db); OBS-A11Y-01 corregido; sin regresión del ciclo 2 (CSRF WebKit 32/32, títulos, cajón, SSR A/B 22 rutas, LCP simulado +152 ms dentro de DEC-AUTO-938); 546 unit; E2E 188/189 (el fallo es AC_TKT008_14, preexistente, igual en main); seguridad 0. No bloqueantes: OBS-C3-01 LOW preexistente (carga completa de /panel/** sin armazón hasta resolver el guard) a TKT-022; OBS-C3-02 INFO (/panel;x=1); PRE-CLS a TKT-016; PRE-LCP a TKT-021.", "PR #39 integrado en main (gh pr merge --merge), CI verde. DONE."]
    actualizado: 2026-10-01
  - id: TKT-022
    titulo: "Panel 2/4 -- medios: SCR-039 Biblioteca de medios con subida (FLOW-013: JPEG/PNG/WebP ≤10 MB, licencia y créditos obligatorios), SCR-040 Detalle de medio (usos, retirar/reactivar), SCR-041 Selector de medios reutilizable por el editor de TKT-023"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-011, FEAT-041, FEAT-042, FLOW-013, SCR-039, SCR-040, SCR-041, RULE-005, RULE-021, "DEC-AUTO-044"]
    depende_de: [TKT-010]
    archivos_permitidos: ["frontend/e2e/medios-soporte.ts", "frontend/e2e/panel-acceso.spec.ts", "frontend/e2e/panel-medios.spec.ts", "frontend/e2e/panel-selector-medios.spec.ts", "frontend/e2e/panel-soporte.ts", "frontend/e2e/zonas*.spec.ts", "frontend/e2e/proxy-selector.conf.mjs"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["Creado por DEC-AUTO-927 (división de TKT-010).", "Límites del patrón EnlaceValor (QA TKT-010 c2): (1) un autofill que solo emite change no actualiza la señal; (2) inputs sin name; (3) errores por campo persisten hasta el siguiente envío; (4) solo cubre input de texto (no checkbox/radio/select). Tenerlos en cuenta o ampliarlo.", "Contrato de zonas de TKT-010 (DEC-DEV-ZONA-01/02): armazones nuevos del panel con <router-outlet appZona=\"panel\" />, rutas bajo la ruta panel (data DATOS_ZONA_PANEL) y specs que monten RUTAS_PANEL con esa data.", "OBS-C3-01 (QA TKT-010 c3, LOW preexistente): al cargar por completo una URL /panel/** hay un cuadro sin armazón y sin <main> hasta que resuelve el guard de sesión (350-650 ms con latencia); añadir un estado de carga mínimo del armazón del panel. INFO OBS-C3-02: zonaDeUrl no reconoce parámetros matriz (/panel;x=1).", "Entregado @ PR #50 (05f5a62), CI verde (run 36909515276), diff solo en features/panel y e2e. SCR-039/040/041 + CargaPanel (OBS-C3-01); E2E 234/234 en 3 motores; unit 601; chunks públicos iguales a main. DEC-DEV-022-01..05 (banco del selector solo en dev, miniaturas diferidas con reintentos por el limitador del borde, sin APIs de señales que engorden el chunk inicial, licencia/crédito al catalogar, ruta de carga). EnlaceValor ampliado (change, textarea, select, name). CHG de miniaturas a TKT-OPS-023 (DEC-AUTO-949). QA ciclo 1/3 despachada.", "2026-10-01 (reanudación tras corte): la QA ciclo 1 no emitió QA_VERDICT; se relanza desde cero (NOT_RUN del ciclo anterior) sobre PR #50 @ 05f5a62.", "2026-10-08 (reanudación): la QA relanzada el 2026-10-01 tampoco emitió QA_VERDICT (sesión cortada, NOT_RUN); se relanza de nuevo sobre PR #50 @ 05f5a62 con checkpoint de progreso en scratchpad.", "2026-10-08 QA ciclo 1/3 FAIL (validado 05f5a62; código del ticket idéntico en b11bd25): tests/a11y/contrato/seguridad/performance PASS; e2e FAIL por robustez: F-01 LOW (axe de SCR-041 en WebKit captura el fotograma de la transición de 100 ms de .bs-boton, 3/4 fallos) y F-02 LOW (con 4 workers, login por API recibe 429 del limitador de auth en /panel/auth/csrf y agota timeouts; en serie 18/18). OBS-03: documentar requisitos de entorno de las E2E (semilla, cookies no Secure por http). OBS-01 -> TKT-036. Devuelto al Developer, ciclo 2/3.", "2026-10-08 DEC-AUTO-960: ciclo 2/3 restringido a las pruebas E2E existentes del ticket (el código de producción ya pasó todos los checks no-E2E) para permitir TKT-023 en paralelo.", "2026-10-08 ciclo 2/3 entregado @ e218489 (PR #50, CI run 37848865836 verde): solo frontend/e2e; F-01 esperarTransiciones antes de axe; F-02 sesión compartida por worker + reintentos + absorberLimiteBorde (429 del proxy por_ip, mismo origen que TKT-OPS-023; escrituras/auth/429 del backend intactos); 4 workers 30/30 y 2 workers x3 90/90 en chromium/firefox/webkit @48da9fa. Sin cambios de producción. QA ciclo 2/3 despachada.", "2026-10-08 QA_VERDICT PASS ciclo 2/3 @ e218489: F-01/F-02/OBS-03 resueltos; 4 workers 24/24 en 3 motores; axe 0; contrato/performance reutilizados (producción idéntica); sonda de absorberLimiteBorde: escrituras, auth y 429 del backend intactos. OBS-C2-01 -> TKT-OPS-023; OBS-C2-04 -> TKT-043; OBS-C2-05: medios-soporte.ts añadido a archivos_permitidos. update-branch del PR #50.", "Integrado (gh pr merge 50 --merge @ b8d4694) con CI verde tras update-branch. DONE."]
    actualizado: 2026-10-08
  - id: TKT-023
    titulo: "Panel 3/4 -- contenidos: SCR-035 Listado por tipo (filtros estado/texto, orden por última modificación), SCR-036 Editor de los 7 tipos (destino, itinerario con días, guía, tipo con checklist, colección, término, página), SCR-037 Vista previa sin persistir (noindex, marca BORRADOR), SCR-038 Publicar/Actualizar/Retirar/Reactivar con análisis de publicación e impacto de retiro, revisiones y restauración, bloqueo optimista"
    fase: F7
    estado: IN_PROGRESS
    owner: Skill_Developer
    trazabilidad: [MOD-010, FEAT-033, FEAT-034, FEAT-035, FEAT-036, FEAT-037, FEAT-038, FEAT-039, FEAT-040, FEAT-049, FEAT-050, FLOW-011, FLOW-012, SCR-035, SCR-036, SCR-037, SCR-038, "RULE-001..012", "RULE-020..027"]
    depende_de: [TKT-010, TKT-022, TKT-045]
    archivos_permitidos: ["frontend/src/app/features/panel/**", "frontend/src/app/api/**", "frontend/e2e/panel-contenidos*.spec.ts", "frontend/e2e/panel-contenidos-soporte.ts", "frontend/e2e/panel-acceso.spec.ts"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Creado por DEC-AUTO-927 (división de TKT-010). Depende de TKT-022 porque el editor abre el selector de medios SCR-041. Si resulta demasiado grande, el Developer puede proponer una subdivisión por tipo de contenido (Botón de Pánico no requerido: basta con reportarlo).", "Límites del patrón EnlaceValor (QA TKT-010 c2): (1) un autofill que solo emite change no actualiza la señal; (2) inputs sin name; (3) errores por campo persisten hasta el siguiente envío; (4) solo cubre input de texto (no checkbox/radio/select). Tenerlos en cuenta o ampliarlo.", "Contrato de zonas de TKT-010 (DEC-DEV-ZONA-01/02): armazones nuevos del panel con <router-outlet appZona=\"panel\" />, rutas bajo la ruta panel (data DATOS_ZONA_PANEL) y specs que monten RUTAS_PANEL con esa data.", "2026-10-08 DEC-AUTO-960: arranca en paralelo al ciclo 2 de TKT-022, en rama apilada sobre tkt-022-panel-medios (necesita el selector SCR-041); no edita las E2E de TKT-022 ni panel-soporte.ts. Al integrarse TKT-022, la rama incorpora main por merge normal.", "2026-10-08 PR #71 @ 28af6cc, CI 37869963051 verde; unit 681/681; build inicial +0,02 kB; panel-contenidos 8/8 x3 motores (fix de fecha UTC en el soporte E2E). BLOCKED por 2 asserts obsoletos de panel-acceso.spec.ts (TKT-010) que TKT-023 cambia intencionadamente -> DEC-AUTO-972 amplía archivos_permitidos a ese spec. Riesgo RULE-009 solo en cliente -> TKT-045.", "2026-10-08 desbloqueado: PR #71 @ 864895b (CI 37872050812 verde), panel-acceso AC_TKT010_08/09 actualizados (9dcd527), panel E2E 3 motores PASS salvo intermitente preexistente AC_TKT022_02 en firefox (-> TKT-046). QA ciclo 1/3 despachada.", "2026-10-08 QA_VERDICT FAIL ciclo 1/3 @ 864895b: F-01 HIGH restaurar revisión vacía colecciones y FK (causa en backend _instantanea, fuera de alcance -> TKT-045); F-02 MEDIUM foco perdido al cerrar Retirar/Eliminar abiertos desde Más acciones (WCAG 2.4.3). Resto PASS (unit 719, E2E panel 3 motores, flujos Editor/Admin, 409, vista previa noindex, XSS rejected, axe 0, +0,02 kB). OBS-01 RULE-009 en cliente con fecha local -> DEC-AUTO-977 (<= hoy en UTC+14). Ciclo 2/3 al Developer: F-02 + OBS-01 + assert de campos restaurados en AC_TKT023_12 (verde solo tras TKT-045); re-QA tras integrar TKT-045.", "2026-10-08 ciclo 2 entregado @ c75ad27 (CI 37880093460 verde): foco a Más acciones vía retornoFoco, RULE-009 con fechaMaximaRevision (UTC+14), unit 722/722, panel E2E 31 PASS x3 motores; E2E de F-01 condicionada (E2E_TKT045=1, hoy falla y detecta el bug). En espera de TKT-045 para el re-QA ciclo 2/3 (merge de main + E2E_TKT045=1 sin condición).", "2026-10-09 TKT-045 DONE (1030e4b): desbloqueado. Developer: merge de main y E2E AC_TKT023_12 sin condición E2E_TKT045; luego re-QA ciclo 2/3."]
    actualizado: 2026-10-09
  - id: TKT-024
    titulo: "Panel 4/4 -- configuración editorial y administración: SCR-042 Destacados de inicio (FLOW-014), SCR-043 Taxonomías y catálogos (regiones, países, categorías de guía, licencias, escalas), SCR-047 Configuración del sitio [Admin], SCR-044 Cuentas del equipo y SCR-045 Formulario de cuenta [Admin] (alta, restablecer contraseña/MFA, desactivar, reactivar, anonimizar), SCR-046 Registro de auditoría [Admin]"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-012, MOD-013, FEAT-043, FEAT-044, FEAT-045, FEAT-046, FEAT-047, FLOW-014, SCR-042, SCR-043, SCR-044, SCR-045, SCR-046, SCR-047, RULE-014, RULE-015, RULE-016, RULE-017]
    depende_de: [TKT-010, TKT-023]
    archivos_permitidos: ["frontend/src/app/features/panel/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Creado por DEC-AUTO-927 (división de TKT-010). Secuencial tras TKT-023 porque comparte el archivo de rutas y la navegación del panel (§0.10).", "Heredado de TKT-010: añadir el E2E de AC_TKT010_08 sobre una ruta real solo-Admin (/panel/usuarios): Editor -> SCR-048 conservando la URL; Admin -> accede.", "Límites del patrón EnlaceValor (QA TKT-010 c2): (1) un autofill que solo emite change no actualiza la señal; (2) inputs sin name; (3) errores por campo persisten hasta el siguiente envío; (4) solo cubre input de texto (no checkbox/radio/select). Tenerlos en cuenta o ampliarlo.", "Contrato de zonas de TKT-010 (DEC-DEV-ZONA-01/02): armazones nuevos del panel con <router-outlet appZona=\"panel\" />, rutas bajo la ruta panel (data DATOS_ZONA_PANEL) y specs que monten RUTAS_PANEL con esa data."]
    actualizado: 2026-10-01
  - id: TKT-025
    titulo: "MEDIUM, CONDICIÓN DE F9: manejar errores de navegación por carga de chunk diferido (ChunkLoadError / 'Failed to fetch dynamically imported module') con withNavigationErrorHandler en app.config.ts (p. ej. recarga completa una sola vez hacia la URL destino), para que un fallo transitorio de red/429 no deje la página en blanco sin el shell (riesgo introducido por la opción A de DEC-AUTO-928)"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-010, TKT-018, "DEC-AUTO-928"]
    depende_de: [TKT-010, TKT-016]
    archivos_permitidos: ["frontend/src/app/app.config.ts", "frontend/src/app/app.config.spec.ts", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Recomendado por el Developer de TKT-010. Depende de TKT-016 porque comparte app.config.ts (§0.10).", "Severidad elevada a MEDIUM por la QA de TKT-010 (DEC-AUTO-933): ocurre en la práctica, en 4 de 129 casos de la regresión pública en serie en Chromium. Con la rama de TKT-010 la página queda en blanco (solo el banner de conexión); en main se conservaban cabecera y pie. Condición de F9. TKT-OPS-016 (ya en main) reduce los 429 que lo provocan, pero un fallo transitorio de red sigue pudiendo causarlo."]
    actualizado: 2026-10-01
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
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [RSK-QA004-02, RSK-OPS-032]
    depende_de: [TKT-005, TKT-OPS-006]
    archivos_permitidos: ["backend/apps/ops/**"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Despachado con especificación exacta de DEVOPS_HANDOFF.md §19.3.6 (umbrales, patrón de infra/ops/cache_limites_tamano.sql) y plantilla de código (apps/ops/services.py::verificar_busqueda, mismo patrón Resultado(exito=bool))", "Entregado @ b9cd19a, PR #31. vigilar_cache_limites() añadida a TRABAJOS, mismo patrón que verificar_busqueda(); recuento exacto por COUNT(*) (verificado que app_rw tiene acceso directo, no necesita el fallback de estimación del script SQL de DevOps). Migración 0002 (expand, reversible) amplía el CHECK del campo tarea. 6 tests nuevos, suite completa 712 passed/0 failed/3 skipped, cobertura 89.79%. CI real (run 36634144163) en verde completo. QA despachado (ciclo 1/3). Pendiente: DevOps debe añadir la línea al crontab después de integrar", "QA_VERDICT PASS ciclo 1/3: reprodujo con datos reales bajo el rol app_rw real (confirmó has_table_privilege en BD real, no solo documentación), confirmó que el comando delega íntegramente en ComandoTarea/ejecutar() sin reimplementar lock/registro, revisión de seguridad del SQL crudo sin interpolación insegura, migración reversible verificada (con una advertencia menor sobre reversibilidad tras uso real, no bloqueante). PR #31 integrado con git merge --no-ff @ 8babd75. TKT-011 DONE. Pendiente: TKT-OPS-012 para que DevOps añada la línea al crontab"]
    actualizado: 2026-09-29
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
    titulo: "Backend: deuda técnica — cerrar los ~563 hallazgos WARNING de oasdiff (pattern/maxItems/minItems/content-media-type/tipo) entre el contrato y la API del panel, dejados sin bloquear por TKT-OPS-010 (decisión humana 2026-09-29); anotar format/pattern/maxItems en los serializers de los 9 recursos del panel + los que aparezcan en /publico y /panel/taxonomias. Ampliado por QA (ciclo 2/3 de TKT-006, no bloqueante): cobertura de panel_selectors.py (0% real en listar_por_tipo/FEAT-033), panel_views.py (55%) y services.py de contenido/medios (56-87%) por debajo de los umbrales tiered de Skill_Backend §8 pese a no tener defecto funcional conocido detrás; añadir tests HTTP de listar/filtrar, retirar/reactivar/revisiones/restaurar, y las ramas de rechazo de medios (formato_no_permitido/tamano_excedido/duplicado), incluido el caso 'archivo disfrazado' que el test de subida original no cubría. Ampliado por QA de TKT-007 (no bloqueante): backend/apps/contenido/management/commands/cargar_semilla.py::_configurar_inicio no incrementa el contador informativo de creados/reutilizados en su 2ª+ ejecución (blindspot de stdout, sin duplicación real en BD). Ampliado por QA de TKT-017 (no bloqueante, preexistente, no introducido por TKT-017 -- confirmado comparando contra el commit base antes del ticket): apps/medios/services.py en 89% de cobertura (umbral Services >90%, Skill_Backend §8), 14 líneas/rangos sin cubrir (formato rechazado, archivo corrupto, megapíxeles excedidos, carrera de IntegrityError en subida duplicada, NoEncontrado en obtener/catalogar/retirar/reactivar, rama licencia_incompatible en uso, filas GALERIA/HERO de usos()); el pipeline de CI solo aplica el umbral global de 80% (pytest.ini --cov-fail-under=80), no un gate por módulo -- considerar también si el pipeline debería aplicar el gate por módulo de Skill_Backend §8 automáticamente"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-006, TKT-OPS-010]
    depende_de: [TKT-006, TKT-OPS-010]
    archivos_permitidos: ["backend/apps/contenido/**", "backend/apps/catalogos/**", "backend/apps/medios/**", "backend/apps/inicio/**", "backend/apps/busqueda/**", "backend/apps/core/esquema.py"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Despachado 2026-10-01 en paralelo con TKT-027. El gate de cobertura por módulo en el pipeline queda fuera: es infraestructura de CI (.github/workflows), de DevOps; si el Developer lo propone, se abrirá un ticket.", "2026-10-01 corte de sesión: el Developer quedó interrumpido con trabajo sin commit en su worktree (12 archivos modificados, 7 tests nuevos). Se reanuda en el mismo worktree sin descartar nada.", "Entregado @ PR #45 (3a991e0), CI real verde (run 36859155530). Diff verificado dentro de alcance. oasdiff 563 WARNING -> 0 (0 ERROR); cobertura total 89,99 % -> 96,5 %, panel_selectors/panel_views 100 %, contenido/services 96,8 %, medios/services 97,1 %; contador de _configurar_inicio corregido. 4 bugs reales de 500 corregidos (KeyError al actualizar TERMINO publicado, DecompressionBombError, IntegrityError en carrera de subida, re-ejecución de _configurar_inicio). Cambio de comportamiento exigido por el contrato: 400 ante ids duplicados, NUL y URL no http(s). El Developer hizo amend + force-with-lease en su propia rama antes de abrir el PR para retirar un falso positivo de gitleaks (sin PR existente; aceptado). CHG-OPS a TKT-OPS-021 (DEC-AUTO-940). QA ciclo 1/3 despachada.", "QA_VERDICT PASS (ciclo 1/3): AC_TKT012_01..04 PASS verificados con oasdiff fijado (0 cambios incluso sin err-ignore), 26 restricciones aplicadas por HTTP real con 400 Problem Details, cobertura 89,99 -> 96,36 %, semilla x3 comparada por tabla, schemathesis 3166/3166, cliente generado sin diff; los 4 bugs de 500 reproducidos en main y corregidos (y 3 más no declarados); seguridad de subida sin debilitar; 9/10 mutantes detectados. Hallazgos preexistentes a TKT-032 (DEC-AUTO-943). Integración pendiente de CI verde.", "PR #45 integrado en main (gh pr merge --merge), CI verde. DONE."]
    actualizado: 2026-10-01
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
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [TKT-014, RULE-007, FLOW-012, FEAT-037]
    depende_de: [TKT-014]
    archivos_permitidos: ["backend/apps/contenido/services.py", "backend/apps/contenido/tests/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["Despachado: TKT-014 integrado, ya no hay solapamiento de archivo. Reutilizar _destinos_publicados_de_tipo() y el patrón de _bloqueos_de_cascada() ya existentes para construir la lista de usos", "Entregado @ 3c9b8cb, PR #30. _usos_publicados_de_tipo() añadida; retirar() con tipo==T.TIPO ahora levanta DependenciaBloqueante(usos/total_usos) antes de confirmar, si el tipo es tipo_principal de un destino publicado o lo usa un itinerario publicado. Rama T.DESTINO/cascada sin tocar. 5 tests nuevos (706 passed total, 0 failed). Alcance documentado explícitamente: NO bloquea si el tipo es solo secundario (no principal) de un destino publicado -- riesgo residual bajo, mitigado por RULE-001 v1.1, con test propio que lo deja trazado en vez de oculto. CI real (run 36623872475) en verde completo. QA despachado (ciclo 1/3), con instrucción explícita de re-evaluar por su cuenta la decisión de alcance (tipo secundario no bloqueado)", "QA_VERDICT FAIL (ciclo 1/3): confirmó con datos reales que el alcance limitado del Developer SÍ es un bug bloqueante, no un riesgo residual aceptable. RULE-002 v1.1 (BLUEPRINT.md:603) y AC-124 dicen 'ningún Destino PUBLICADO referencia un Tipo no PUBLICADO' sin distinguir principal/secundario; RULE-025 exige '≥1 destino PUBLICADO asociado' (no 'como principal'); FLOW-012 enumera de forma cerrada las únicas relaciones que se toleran sin bloquear (guías/colecciones/destacados/relacionados) y tipos_aventura secundarios NO está en esa lista; AC-129 describe ese estado como 'inconsistencia FORZADA' para probar la defensa en profundidad, no como estado tolerado. Inconsistencia interna: _destinos_publicados_de_tipo() y _tipos_en_cascada() (ya usadas en la rama T.DESTINO) SÍ tratan el M2M completo (tipos_aventura) como 'uso', pero la nueva _usos_publicados_de_tipo() de TKT-015 solo mira tipo_principal_id. Reproducido con datos reales: retirar un tipo SOLO secundario de un destino publicado tiene éxito sin bloqueo, el Destino sigue PUBLICADO con un enlace M2M roto a un Tipo RETIRADO en BD, y ni siquiera se reindexa (mismo filtro estrecho en _reindexar_dependientes_de_tipo de TKT-014). Fix sugerido por QA: reutilizar el mismo filtro M2M (Destino.tipos_aventura) que ya usa _destinos_publicados_de_tipo. Devuelto al Developer", "Corrección @ b13c4d3: verificó por su cuenta los 5 puntos de QA antes de aplicar el fix (reprodujo el gap con un test contra el código anterior primero). _usos_publicados_de_tipo() y _reindexar_dependientes_de_tipo() (TKT-014) ahora usan el mismo filtro M2M Destino.tipos_aventura que _destinos_publicados_de_tipo()/_tipos_en_cascada() -- las 4 funciones del archivo responden igual a 'destino ⇒ tipo en uso'. Test invertido (ahora confirma que SÍ bloquea). Suite 706 passed/0 failed/3 skipped, mismo conteo que ciclo 1 (test invertido 1:1, sin regresión en T.DESTINO/cascada RULE-025). CI real (run 36629133685) en verde completo. QA despachado (ciclo 2/3), con foco específico en el caso 'tipo secundario' que motivó el FAIL", "QA_VERDICT PASS ciclo 2/3: verificación completamente independiente (worktrees y Postgres propios, distintos de rondas anteriores) -- reprodujo el bug ANTES del fix (revirtiendo a 3c9b8cb) y confirmó que b13c4d3 lo corrige; revisó que la ampliación de _reindexar_dependientes_de_tipo (TKT-014) es idempotente (indexar() es upsert/delete puro); verificó técnicamente el razonamiento de ventana de carrera del Developer (select_for_update solo bloquea la fila del propio Tipo, no sus dependientes). Suite completa 706/0/3 sin regresión, contrato 128/128 sin cambios, gitleaks/semgrep limpios sobre el PR completo. PR #30 integrado con git merge --no-ff @ f46a18b. TKT-015 DONE"]
    actualizado: 2026-09-29
  - id: TKT-OPS-012
    titulo: "DevOps: añadir la línea al crontab del planificador para el comando vigilar_cache_limites de TKT-011 (DEVOPS_HANDOFF.md §19.3.6 ya propone '*/15 * * * * python manage.py vigilar_cache_limites'); cierra RSK-OPS-032"
    fase: F7
    estado: DONE
    owner: devops
    trazabilidad: [TKT-011, RSK-OPS-032]
    depende_de: [TKT-011]
    archivos_permitidos: ["infra/scheduler/**", "docs/05_operacion/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Despachado a devops", "Entregado @ b339a0a, PR #32. Línea de crontab exacta según DEVOPS_HANDOFF.md §19.3.6, validada con el binario real de supercronic reconstruyendo la imagen real del servicio scheduler ('crontab is valid', exit 0). CI real (run 36639252501) en verde completo. Verificación final hecha directamente por el Orquestador (diff mínimo de 2 archivos, sin QA formal por proporcionalidad -- DEC-AUTO, ver audit_log.md). PR #32 integrado con git merge (fast-forward) @ c127e8d. TKT-OPS-012 DONE. RSK-OPS-032 CERRADO"]
    actualizado: 2026-09-29
  - id: TKT-OPS-013
    titulo: "DevOps: añadir CVE-2026-84782 (HIGH, openssl/libssl3t64/openssl-provider-legacy, fallo de lógica de retransmisión DTLS, sin parche en Debian 13.7) a .trivyignore con exp:2026-10-30, bajo la misma política de TKT-OPS-005 (solo CVE de paquetes Debian sin parche publicado, con caducidad y justificación). Decisión humana registrada en audit_log.md (2026-09-30, GATE_HUMANO, RSK-OPS-001): 'Aceptar con lista y caducidad'. Detectado por trivy en brujula/db durante la verificación de CI de TKT-008 (run 36668871573); confirmado NO relacionado con ningún cambio de Dockerfile de ese ticket -- drift de la base de datos de vulnerabilidades de trivy entre dos runs del mismo branch en menos de 3h"
    fase: F9
    estado: DONE
    owner: devops
    trazabilidad: [RSK-OPS-001, TKT-OPS-005]
    depende_de: []
    archivos_permitidos: [".trivyignore"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Despachado a devops", "REQUIERE INTERVENCIÓN: DevOps rechazó ejecutar la instrucción del ticket tal cual porque su premisa es objetivamente falsa. Verificó en vivo (build real de brujula/db + trivy con DB actualizada a 2026-09-30 + apt-cache policy dentro del propio contenedor) que Debian YA publicó el parche para CVE-2026-84782 (DSA-6531-1, openssl/libssl3t64/openssl-provider-legacy 3.5.7-1~deb13u3, disponible ahora mismo en trixie-security) -- la condición 'sin parche publicado' que exige tanto este ticket como la cabecera de .trivyignore ya no se cumple. Añadir la excepción violaría la política ya documentada y ocultaría con una excepción temporal un CVE que se puede eliminar de raíz hoy. Encontró además un SEGUNDO HIGH no detectado por nadie: CVE-2026-75804 (QUIC DoS), mismos 3 paquetes, mismo DSA, mismo fix -- el enfoque original del ticket no habría dejado el CI en verde ni siquiera bajo su propia premisa. No tocó ningún archivo, no abrió rama/PR. Ticket SUPERSEDIDO por TKT-OPS-014 (actualizar el paquete en el Dockerfile en vez de añadir una excepción). La decisión humana GATE_HUMANO/RSK-OPS-001 del 2026-09-30 sobre este CVE queda revisada/superada: ya no aplica como 'aceptar riesgo sin corregir' porque hay un fix real disponible -- ver audit_log.md", "2026-10-08: cierre administrativo (DEC-AUTO-955): SUPERSEDIDO por TKT-OPS-014/015 (DONE 2026-09-30), que eliminaron la CVE actualizando openssl a 3.5.7-1~deb13u3; no se añadió excepción. No queda decisión humana pendiente sobre esta CVE."]
    actualizado: 2026-10-08
  - id: TKT-OPS-014
    titulo: "DevOps: infra/db/Dockerfile -- actualizar openssl, libssl3t64 y openssl-provider-legacy a 3.5.7-1~deb13u3 (DSA-6531-1, ya disponible en trixie-security), corrigiendo de raíz CVE-2026-84782 (DTLS info disclosure) y CVE-2026-75804 (QUIC DoS) sin necesitar ninguna excepción en .trivyignore. Reemplaza a TKT-OPS-013 (que proponía aceptar el riesgo con .trivyignore; DevOps verificó que la premisa 'sin parche' era falsa y rechazó esa ruta). Tras el fix, confirmar con build + trivy real que brujula/db queda con 0 hallazgos CRITICAL/HIGH nuevos y que el resto de .trivyignore (util-linux, acl, systemd, ncurses, perl-base, libxml2, exp:2026-10-26) no cambia"
    fase: F9
    estado: DONE
    owner: devops
    trazabilidad: [RSK-OPS-001, TKT-OPS-013]
    depende_de: []
    archivos_permitidos: ["infra/db/Dockerfile"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir del diagnóstico de DevOps en TKT-OPS-013 (HANDOFF agente aa66cbe495cbba7b5): parche real ya disponible, verificado en vivo dentro de un contenedor construido desde el Dockerfile actual sin modificar nada.", "Entregado @ 958579a, PR #34. infra/db/Dockerfile: openssl/libssl3t64/openssl-provider-legacy fijados a 3.5.7-1~deb13u3 vía apt-get download + dpkg --force-depends -i (apt-get install --only-upgrade no resuelve por el purge de perl ya existente con --force-depends; mismo patrón que el Dockerfile ya usaba). Verificado local: build limpio, trivy con gate exacto de CI (brujula/db baseline 6 HIGH sin suprimir -> 0 sin suprimir + 52 suprimidos idénticos byte a byte al resto de .trivyignore), smoke test real (psql CRUD + CREATE EXTENSION pgcrypto/digest() ejercitando libssl/libcrypto, dpkg-query y ldd confirmando la versión y el enlazado). CI real (run 36708348909) confirma brujula/db con 0 hallazgos -- el fix de ESTE ticket es correcto y completo. PERO el job 'build + trivy + SBOM' del PR sigue en rojo porque el MISMO CVE (mismo DSA-6531-1, mismos 3 paquetes) también afecta a brujula/backend (6 sin suprimir), brujula/scheduler (6, comparte Dockerfile con backend por target), brujula/frontend (4) y brujula/backup (4) -- fuera de archivos_permitidos de TKT-OPS-014. DevOps no los tocó (correcto, REGLA 10 Skill_devops) y recomendó ticket de seguimiento. Se abre TKT-OPS-015 con el mismo patrón ya validado.", "TKT-OPS-015 entregado (@ 5f29e85, misma rama/PR #34): backend/scheduler/frontend/backup corregidos también, CI real completo del PR (run 36711222383) en verde en los 6 jobs no opcionales, incluido 'build + trivy + SBOM' (3m26s). PR #34 verificado independientemente por el Orquestador (gh pr checks 34) e integrado en main con gh pr merge --merge @ f2699ba. TKT-OPS-014 DONE."]
    actualizado: 2026-09-30
  - id: TKT-OPS-015
    titulo: "DevOps: aplicar el mismo fix ya validado en TKT-OPS-014 (openssl/libssl3t64/openssl-provider-legacy -> 3.5.7-1~deb13u3, DSA-6531-1, vía apt-get download + dpkg --force-depends -i con versión fijada) a los Dockerfiles restantes que comparten el mismo drift de versión: infra/docker/backend.Dockerfile (cubre brujula/backend Y brujula/scheduler, mismo archivo con target distinto por etapa multi-stage) y infra/backup/Dockerfile (brujula/backup). infra/docker/frontend.Dockerfile también afectado (libssl3t64/openssl-provider-legacy, sin el paquete openssl). Revisar cada Dockerfile individualmente antes de aplicar el mismo comando a ciegas -- cada uno puede tener sus propias particularidades de purges/force-depends previos (igual que db tuvo el purge de perl). Verificar con build + trivy real (gate exacto de CI) que las 4 imágenes quedan con 0 hallazgos CRITICAL/HIGH nuevos y que .trivyignore no cambia. Objetivo final: PR #34 (o esta rama fusionada en ella) con el job 'build + trivy + SBOM' completo en verde"
    fase: F9
    estado: DONE
    owner: devops
    trazabilidad: [RSK-OPS-001, TKT-OPS-014]
    depende_de: [TKT-OPS-014]
    archivos_permitidos: ["infra/docker/backend.Dockerfile", "infra/docker/frontend.Dockerfile", "infra/backup/Dockerfile"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir del HANDOFF de TKT-OPS-014 (agente ab08ae70a201a9e18): mismo CVE/DSA confirmado en backend(6)/scheduler(6, mismo Dockerfile)/frontend(4)/backup(4) mediante el log real del job de CI del PR #34 (run 36708348909).", "Entregado @ 5f29e85 (misma rama tkt-ops-014-openssl-fix, PR #34). Trabajó en worktree aislado por primera vez en un ticket DevOps de esta sesión (instrucción de proceso nueva tras el hallazgo de TKT-OPS-014). A diferencia de db, ninguna de las 3 etapas tenía un purge --force-depends previo que bloqueara al solver de apt -- verificado explícitamente antes de escribir el Dockerfile, usó apt-get install --only-upgrade/con versión fijada en vez del patrón más complejo de dpkg --force-depends -i. backup/Dockerfile usa un nuevo ARG OPENSSL_DEB_VERSION siguiendo el patrón ya existente de otros ARG *_DEB_VERSION del archivo. Verificado local: build+trivy con el gate exacto de CI (0 hallazgos sin suprimir en las 4 imágenes, CVE-2026-84782/-75804 ni siquiera en la lista de suprimidos), smoke test funcional real (stack completo con --profile ops, 6/6 servicios estables, pg_dump real desde backup ejercitando libpq/libssl3t64 end-to-end, openssl version/ssl.OPENSSL_VERSION confirmando 3.5.7-1~deb13u3 dentro de los contenedores). CI real tras push: run 36711222383, gh run watch confirma success; gh pr checks 34 con los 6 jobs no opcionales en pass, incluido 'build + trivy + SBOM' (3m26s). Worktree eliminado y confirmado (git worktree list, ls del directorio padre); directorio compartido nunca cambió de rama en este ticket. Verificado independientemente por el Orquestador (gh pr checks 34, gh pr view 34: mergeable=MERGEABLE). PR #34 integrado en main con gh pr merge --merge @ f2699ba (reconciliado en local con git merge, conflicto trivial de solo-anexado en audit_log.md resuelto conservando ambos lados, commit 71ba236). TKT-OPS-015 DONE."]
    actualizado: 2026-09-30
  - id: TKT-019
    titulo: "GAP DE PLANIFICACIÓN: SCR-022 (Mapa del sitio HTML, `/mapa-del-sitio`, MOD-001, FEAT-025) tiene prioridad MUST y es la segunda vía obligatoria exigida por RULE-030/OBJ-001 (junto con Inicio) para que 'toda página publicada sea alcanzable' -- pero NUNCA fue asignado a ningún Micro-Ticket (ni TKT-008 ni TKT-009 lo incluyen en su alcance). Resultado: /mapa-del-sitio devuelve HTTP 404 real en producción HOY, pese a que el pie de página (GI-02, construido en TKT-008) ya lo enlaza -- es un enlace roto en vivo para cualquier visitante que lo pulse. Encontrado por QA durante la verificación de RULE-030 en TKT-009 ciclo 1/3 (no es un defecto de TKT-008 ni TKT-009: es un hueco en la descomposición original de tickets de esta sesión). Implementar: página HTML que agrupa todas las páginas publicadas por sección (destinos, itinerarios, tipos de aventura, guías, colecciones, glosario, institucional), MUST, REQ-021/020"
    fase: F7
    estado: DONE
    owner: Skill_Developer
    trazabilidad: [MOD-001, "SCR-022", "FEAT-025", "RULE-030", "OBJ-001"]
    depende_de: [TKT-008, TKT-009]
    archivos_permitidos: ["frontend/src/app/features/mapa-del-sitio/**", "frontend/src/app/app.routes.ts", "frontend/e2e/**"]
    ciclo_qa: 2/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir del HANDOFF de QA en TKT-009 ciclo 1/3 (agente aa764ec0f042e41cd): confirmado con curl real contra el stack en producción-equivalente que /mapa-del-sitio devuelve 404; enlace ya presente en el pie de página desde TKT-008 (core/layout/pie-sitio). Depende de TKT-009 para poder enlazar itinerarios/guías/tipos/colecciones/glosario/búsqueda ya construidos.", "2026-10-08: despachado (ruta crítica, MUST).", "2026-10-08 entregado @ PR #69 (805b2e7, CI run 37850307483 verde): feature mapa-del-sitio con datos de /publico/indice, /meses y /glosario (sin cambio de contrato), TransferState (CLS 0,42 -> corregido), enlaces de /cuando-ir por número; 582 unit PASS, build +0,12 kB inicial, E2E 6/6 en 3 motores, axe 0 serious/critical. QA ciclo 1/3 despachada.", "2026-10-08 QA_VERDICT FAIL ciclo 1/3 @ 805b2e7: tests/a11y/contrato/seguridad/performance PASS (95 rutas 200 reales, SSR con los 72+24 enlaces, axe 0, CLS 0). F-01 MEDIUM: el índice de secciones usa href='#seccion-x' y con <base href=/> lleva a /#seccion-x (Inicio) en 3 motores; AC_TKT019_02 no lo detecta. F-02 MEDIUM: AC_TKT019_04 agota el cupo publico-lectura compartido (385 llamadas, 53 x 429) y hace fallar specs de otros tickets. F-03 LOW: reintentos ante estado-error sin comprobar 429 y crawl que solo mira el status. OBS-01/02 preexistentes -> TKT-042. Ciclo 2/3 al Developer.", "Ciclo 2/3 entregado @ d3f7627 (CI run 37858291250 verde): índice con href /mapa-del-sitio#seccion-x + irASeccion (foco en h2, replaceState; sin routerLink porque FocoRuta devuelve el foco al h1); E2E con una ruta por patrón, reintento solo ante 429 real y rechazo de estado-error/404; suite pública 56/56 en 3 motores con 0 x 429. QA ciclo 2/3 despachada.", "2026-10-08 QA_VERDICT PASS ciclo 2/3 @ d3f7627 (F-01..F-03 verificados; suite pública 56/56 x3 motores, 0 x 429; axe 0; CLS mapa <=0,1 8/8). OBS-01 (scroll al volver atrás tras replaceState) no bloqueante. PR #69 integrado @ 1fce826 con CI verde."]
    actualizado: 2026-10-08
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
