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
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-001, MOD-002, "Skill_UI_UX#47.2"]
    depende_de: [TKT-008]
    archivos_permitidos: ["frontend/src/app/app.config.ts", "frontend/src/app/core/layout/**", "frontend/src/app/features/inicio/**", "frontend/src/app/features/destinos/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Línea base actualizada por QA (ciclo 2/3 de TKT-008, entorno propio 100% reproducible, sin ruido de rate-limit durante la medición): CLS Inicio = 1.609 (2 corridas idénticas), CLS /destinos = 0.674 (1 corrida) -- notablemente más severo que la primera medición del Developer (0-1.16 intermitente). QA recomienda revisar la prioridad de este ticket al alza dado el nivel de reproducibilidad y severidad."]
    actualizado: 2026-09-29
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
  - id: TKT-OPS-016
    titulo: "HIGH, CONDICIÓN DE F9: recalibrar el limitador de borde nginx (zone=por_ip 20r/s burst=60, clave $binary_remote_addr) -- 2-3 visitantes fríos tras una misma IP compartida (NAT/CGNAT, oficinas, operadores móviles) reciben 429 en chunks JS lazy y la navegación del router nunca completa (QA TKT-018 F-3: N=2 1/10, N=3 7-9/15 navegaciones rotas tras el fix de frontend). Una carga fría ya son ~30 peticiones: no corregible desde frontend. Opción recomendada por QA: excluir o dar zona propia generosa a los assets estáticos inmutables (chunks /*.js y /*.css con hash, /media/publico/**) y mantener por_ip 20r/s burst=60 en /api/** y HTML SSR. Documentar en ADR la decisión frente a agotamiento de recursos (DEC-AUTO-111/190/193/195/214)"
    fase: F7
    estado: READY_FOR_VALIDATION
    owner: devops
    trazabilidad: [TKT-018, "DEC-AUTO-111", "DEC-AUTO-190", "DEC-AUTO-193", "DEC-AUTO-195", "DEC-AUTO-214", REQ-052]
    depende_de: [TKT-018]
    archivos_permitidos: ["infra/proxy/**", "docs/adr/ADR-OPS-*.md", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 1/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT PASS de TKT-018 (F-3 + needs_validation 'Quota-accounting scope'). AC: escenario Inicio->clic a 300 ms con N=2 y N=3 contextos Chromium fríos concurrentes desde la misma IP, 2 series, 0 navegaciones rotas y 0 429 en assets estáticos; /api/** y HTML SSR siguen limitados (verificar 429 con ráfaga sintética a /api/).", "Despachado a devops 2026-09-30 en paralelo con TKT-010 (archivos disjuntos).", "DEC-AUTO-929: alcance ampliado con X-Robots-Tag noindex, nofollow en las respuestas HTML de /panel/** (RULE-029 y sitemap exigen noindex por cabecera; hoy solo security-headers-error.conf la emite). Hallazgo del Developer de TKT-010; mismo archivo y mismo owner, comunicado al agente DevOps en curso.", "Entregado @ PR #38 (rama tkt-ops-016-limitador-estaticos, HEAD aa9324d). ADR-OPS-001 (PROPOSED): zona nueva estaticos (50 r/s, burst 300 nodelay) solo para assets del build en raíz (/*.js|mjs|css), /fonts/*.woff2, /favicon.ico y /media/publico/**; por_ip 20r/s burst=60 intacto para /api/**, SSR y el resto. Anti-evasión: la location de assets reenvía Host estaticos.invalid, de modo que un asset inexistente es rechazado por AngularNodeAppEngine (400 sin render, ~6 ms) y devuelto como 404 Problem Details. X-Robots-Tag noindex,nofollow vía map solo en ^/panel(/|$). Campo ruta_pedida en el log JSON. Mediciones declaradas (Chromium, misma IP, Inicio->clic 300 ms): antes N=2 1/10 y 0/10 rotas, N=3 15/15 y 13/15; después N=2/3/5/8 0 rotas y 0 429. Ráfagas de 200 a /api, / y /destinos siguen limitadas (~61x200/139x429). CI del PR ROJO por causa ajena verificada por el Orquestador: trivy CVE-2026-103111 HIGH en libpcre2-8-0 de las imágenes Debian (la imagen proxy alpine da 0); afecta igual a main en su próxima ejecución con código -> TKT-OPS-017. Smoke CI del proxy SKIPPED en GitHub, reproducido en local. RSK-OPS-040..043 declarados (040: NG_ALLOWED_HOSTS nunca con *, smoke a CI -> TKT-OPS-018). QA despachada; integración condicionada a QA PASS y CI verde tras TKT-OPS-017.", "QA_VERDICT PASS (ciclo 1/3), A/B cambiando solo el contenedor proxy sobre la misma semilla: N=3 main 12/15 y 12/15 navegaciones rotas (80-93 respuestas 429) -> rama 0/15 y 0/15, N=5 0/25, 0 respuestas 429; ráfagas a /api, / y /destinos siguen limitadas (~61x200/139x429), cupos separados comprobados en ambos sentidos; matriz de evasión de 31 variantes x3 (codificaciones, dobles barras, métodos, Host/X-Forwarded-* manipulados, forma absoluta): 0 renders SSR y 0 peticiones al backend; cabeceras idénticas a main salvo X-Robots-Tag en /panel*; schemathesis 3161/3161; trivy proxy 0; gitleaks/semgrep sin hallazgos reales. Hallazgos no bloqueantes -> TKT-OPS-019 (F-1 LOW: la query de un asset inexistente llega al log del SSR; F-2 INFO: X-Forwarded-Host redundante y documentación de 3 vs 8 líneas de log) y TKT-026 (F-3/F-4 preexistentes del SSR). Pendiente de integración: CI verde tras TKT-OPS-017."]
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
    estado: TODO
    owner: devops
    trazabilidad: [TKT-OPS-016, "ADR-OPS-001", RSK-OPS-040]
    depende_de: [TKT-OPS-016, TKT-OPS-017]
    archivos_permitidos: [".github/workflows/**", "scripts/ops/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Recomendado por el DevOps de TKT-OPS-016 (RSK-OPS-040).", "QA de TKT-OPS-016 recomienda que este smoke sea condición de F9: la defensa anti-evasión depende de NG_ALLOWED_HOSTS y de que Angular valide el Host antes de renderizar; sin smoke en CI, una regresión pasaría en silencio. Se eleva a condición de F9 (DEC-AUTO-932)."]
    actualizado: 2026-10-01
  - id: TKT-OPS-019
    titulo: "LOW: en la location de assets de infra/proxy/nginx.conf, enviar al SSR solo la ruta sin query (p. ej. proxy_pass http://frontend$uri, seguro porque la regex limita la ruta a [A-Za-z0-9_./-]) para que la query de un asset inexistente no acabe en el log del SSR (QA TKT-OPS-016 F-1: 'ERROR: Bad Request (http://estaticos.invalid/qaB.js?x=1)', contrario a REQ-057/THREAT-020 'logs sin query strings'); quitar el proxy_set_header X-Forwarded-Host redundante (Angular 22.2 lo ignora sin trustProxyHeaders y genera 2 avisos por petición) y corregir RSK-OPS-041 en ADR-OPS-001/DEVOPS_HANDOFF (8 líneas por asset inexistente, no ~3)"
    fase: F7
    estado: TODO
    owner: devops
    trazabilidad: [TKT-OPS-016, "ADR-OPS-001", REQ-057, THREAT-020, RSK-OPS-041]
    depende_de: [TKT-OPS-016]
    archivos_permitidos: ["infra/proxy/**", "docs/adr/ADR-OPS-001.md", "docs/05_operacion/DEVOPS_HANDOFF.md"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Hallazgos F-1/F-2 de QA_VERDICT PASS de TKT-OPS-016. AC: curl /no-existe.js?secreto=1 -> 0 coincidencias de 'secreto' en el log del frontend; la matriz de evasión de TKT-OPS-016 sigue dando 0 renders; assets existentes con ?v=1 siguen dando 200."]
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
  - id: TKT-020
    titulo: "ImagenResponsiva: (F-2 MEDIUM, preexistente de TKT-002) src/srcset solo AVIF sin formato de respaldo -- en navegadores sin AVIF (WebKit de Playwright en Windows) (error)->alFallar() elimina el <img>: 0 imágenes de tarjeta en WebKit en todos los listados; usar <picture> con <source type=image/avif> + respaldo WebP/JPEG (los derivados ya existen por DEC-AUTO-044). (F-1 LOW, introducido por TKT-018) imágenes no prioritarias con alt informativo (galerías de destino/itinerario, miniaturas de créditos) salen sin src en SSR y nunca cargan sin JS ni para crawlers; emitir src en SSR o <noscript> para las no decorativas y corregir el comentario incorrecto del componente, sin reintroducir la ráfaga de TKT-018"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-018, TKT-002, "DEC-AUTO-044"]
    depende_de: [TKT-018]
    archivos_permitidos: ["frontend/src/app/shared/ui/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT PASS de TKT-018 (F-1, F-2). Si el contrato o el cliente generado no exponen los derivados WebP/JPEG, usar Botón de Pánico (no tocar apps/medios ni contracts/). AC: WebKit renderiza imágenes de tarjeta en /destinos; curl de /creditos sin JS muestra src en imágenes con alt no vacío; el conteo de peticiones frías de /destinos no vuelve a subir (≤ ~30 en Chromium)."]
    actualizado: 2026-09-30
  - id: TKT-021
    titulo: "LCP móvil de las páginas de listado 3.1-3.7 s (Lighthouse móvil, throttling simulado) frente a REQ-052 (≤ 2,5 s): preexistente, medido igual en main antes de TKT-018, sin ticket que lo cubra (TKT-016 solo cubre CLS). Investigar la causa (imagen LCP, bundle, TTFB de SSR, fuentes) y corregir o acotar"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [REQ-052, TKT-018, TKT-016]
    depende_de: [TKT-016, TKT-020]
    archivos_permitidos: ["frontend/src/app/features/destinos/**", "frontend/src/app/features/guias/**", "frontend/src/app/features/itinerarios/**", "frontend/src/app/shared/ui/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir de QA_VERDICT PASS de TKT-018 (riesgo 2). Depende de TKT-016 y TKT-020 por solape de archivos. archivos_permitidos provisionales: ampliar por DEC-AUTO si la causa está en core/ o en la configuración de build."]
    actualizado: 2026-09-30
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
    estado: READY_FOR_VALIDATION
    owner: Skill_Developer
    trazabilidad: [MOD-009, MOD-010, FEAT-029, FEAT-030, FEAT-031, FEAT-032, FEAT-033, FLOW-010, SCR-030, SCR-031, SCR-032, SCR-033, SCR-034, SCR-048, RULE-017, RULE-029, THREAT-001, THREAT-002, "DEC-AUTO-215"]
    depende_de: [TKT-009, TKT-006]
    archivos_permitidos: ["frontend/src/app/app.routes.ts", "frontend/src/app/app.html", "frontend/src/app/app.ts", "frontend/src/app/app.css", "frontend/src/app/app.spec.ts", "frontend/src/app/core/layout/shell-publico/**", "frontend/src/app/features/panel/**", "frontend/src/app/core/auth/**", "frontend/e2e/**", "frontend/package.json", "frontend/package-lock.json"]
    ciclo_qa: 0/3
    ciclo_panico: 1/2
    evidencia: ["DEC-AUTO-927: el TKT-010 original (19 pantallas SCR-030..048, ~70 endpoints) se divide en 4 Micro-Tickets secuenciales: TKT-010 (acceso+armazón+tablero), TKT-022 (medios), TKT-023 (contenidos), TKT-024 (inicio, taxonomías, configuración, cuentas, auditoría). Despachado 2026-09-30 en paralelo con TKT-OPS-016 (archivos disjuntos).", "Botón de Pánico 1/2 (justificado, antes de escribir código): el shell público (app.html: skip-link + cabecera + main + pie sin condición alrededor del único router-outlet) envolvería /panel/**, incumpliendo TPL-PANEL-AUTH/TPL-PANEL-SHELL (HANDOFF_UI_UX l.194-199) y anidando landmarks (AC_TKT010_10). Verificado por el Orquestador. DEC-AUTO-928: ampliación opción A (ShellPublico como ruta de layout padre de las rutas públicas). Estructura del Developer aceptada: features/panel como UNA feature con capas planas (los globs de eslint features/*/{ui,state,data,domain} no cubrirían subcarpetas por área), rutas hijas en features/panel/ui/panel.routes.ts, catálogo de secciones en domain. Reanudado.", "Entregado @ PR #39 (rama tkt-010-panel-acceso, HEAD f349018). Diff verificado por el Orquestador dentro de archivos_permitidos ampliados. 505/505 unit, cobertura global 84 % / panel domain 100 % líneas, eslint/tsc/build OK; E2E contra stack real 168/168 en 3 motores (13 casos del panel x3 + regresión pública completa 129/129 en serie). Dependencia nueva uqr@0.1.3 (MIT, sin transitivas). gitleaks/semgrep/npm audit limpios. CI: todo verde salvo trivy (CVE-2026-103111, TKT-OPS-017, ajeno). Riesgos declarados: (1) con la opción A un 429 en un chunk diferido en la primera carga deja la página en blanco en vez de conservar cabecera/pie -> TKT-025; (2) AC_TKT010_08 E2E parcial hasta que exista una ruta solo-Admin (TKT-024 debe añadir el E2E sobre /panel/usuarios); (3) QR no decodificado con lector (la clave manual sí se probó E2E). El Developer declaró un taskkill por nombre de imagen demasiado amplio, sin efecto constatado. QA despachada."]
    actualizado: 2026-09-30
  - id: TKT-022
    titulo: "Panel 2/4 -- medios: SCR-039 Biblioteca de medios con subida (FLOW-013: JPEG/PNG/WebP ≤10 MB, licencia y créditos obligatorios), SCR-040 Detalle de medio (usos, retirar/reactivar), SCR-041 Selector de medios reutilizable por el editor de TKT-023"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-011, FEAT-041, FEAT-042, FLOW-013, SCR-039, SCR-040, SCR-041, RULE-005, RULE-021, "DEC-AUTO-044"]
    depende_de: [TKT-010]
    archivos_permitidos: ["frontend/src/app/features/panel/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Creado por DEC-AUTO-927 (división de TKT-010)."]
    actualizado: 2026-09-30
  - id: TKT-023
    titulo: "Panel 3/4 -- contenidos: SCR-035 Listado por tipo (filtros estado/texto, orden por última modificación), SCR-036 Editor de los 7 tipos (destino, itinerario con días, guía, tipo con checklist, colección, término, página), SCR-037 Vista previa sin persistir (noindex, marca BORRADOR), SCR-038 Publicar/Actualizar/Retirar/Reactivar con análisis de publicación e impacto de retiro, revisiones y restauración, bloqueo optimista"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-010, FEAT-033, FEAT-034, FEAT-035, FEAT-036, FEAT-037, FEAT-038, FEAT-039, FEAT-040, FEAT-049, FEAT-050, FLOW-011, FLOW-012, SCR-035, SCR-036, SCR-037, SCR-038, "RULE-001..012", "RULE-020..027"]
    depende_de: [TKT-010, TKT-022]
    archivos_permitidos: ["frontend/src/app/features/panel/**", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Creado por DEC-AUTO-927 (división de TKT-010). Depende de TKT-022 porque el editor abre el selector de medios SCR-041. Si resulta demasiado grande, el Developer puede proponer una subdivisión por tipo de contenido (Botón de Pánico no requerido: basta con reportarlo)."]
    actualizado: 2026-09-30
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
    evidencia: ["Creado por DEC-AUTO-927 (división de TKT-010). Secuencial tras TKT-023 porque comparte el archivo de rutas y la navegación del panel (§0.10).", "Heredado de TKT-010: añadir el E2E de AC_TKT010_08 sobre una ruta real solo-Admin (/panel/usuarios): Editor -> SCR-048 conservando la URL; Admin -> accede."]
    actualizado: 2026-09-30
  - id: TKT-025
    titulo: "LOW: manejar errores de navegación por carga de chunk diferido (ChunkLoadError / 'Failed to fetch dynamically imported module') con withNavigationErrorHandler en app.config.ts (p. ej. recarga completa una sola vez hacia la URL destino), para que un fallo transitorio de red/429 no deje la página en blanco sin el shell (riesgo introducido por la opción A de DEC-AUTO-928)"
    fase: F7
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [TKT-010, TKT-018, "DEC-AUTO-928"]
    depende_de: [TKT-010, TKT-016]
    archivos_permitidos: ["frontend/src/app/app.config.ts", "frontend/src/app/app.config.spec.ts", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Recomendado por el Developer de TKT-010. Depende de TKT-016 porque comparte app.config.ts (§0.10)."]
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
    estado: BLOCKED_HUMAN
    owner: devops
    trazabilidad: [RSK-OPS-001, TKT-OPS-005]
    depende_de: []
    archivos_permitidos: [".trivyignore"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Despachado a devops", "REQUIERE INTERVENCIÓN: DevOps rechazó ejecutar la instrucción del ticket tal cual porque su premisa es objetivamente falsa. Verificó en vivo (build real de brujula/db + trivy con DB actualizada a 2026-09-30 + apt-cache policy dentro del propio contenedor) que Debian YA publicó el parche para CVE-2026-84782 (DSA-6531-1, openssl/libssl3t64/openssl-provider-legacy 3.5.7-1~deb13u3, disponible ahora mismo en trixie-security) -- la condición 'sin parche publicado' que exige tanto este ticket como la cabecera de .trivyignore ya no se cumple. Añadir la excepción violaría la política ya documentada y ocultaría con una excepción temporal un CVE que se puede eliminar de raíz hoy. Encontró además un SEGUNDO HIGH no detectado por nadie: CVE-2026-75804 (QUIC DoS), mismos 3 paquetes, mismo DSA, mismo fix -- el enfoque original del ticket no habría dejado el CI en verde ni siquiera bajo su propia premisa. No tocó ningún archivo, no abrió rama/PR. Ticket SUPERSEDIDO por TKT-OPS-014 (actualizar el paquete en el Dockerfile en vez de añadir una excepción). La decisión humana GATE_HUMANO/RSK-OPS-001 del 2026-09-30 sobre este CVE queda revisada/superada: ya no aplica como 'aceptar riesgo sin corregir' porque hay un fix real disponible -- ver audit_log.md"]
    actualizado: 2026-09-30
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
    estado: TODO
    owner: Skill_Developer
    trazabilidad: [MOD-001, "SCR-022", "FEAT-025", "RULE-030", "OBJ-001"]
    depende_de: [TKT-008, TKT-009]
    archivos_permitidos: ["frontend/src/app/features/mapa-del-sitio/**", "frontend/src/app/app.routes.ts", "frontend/e2e/**"]
    ciclo_qa: 0/3
    ciclo_panico: 0/2
    evidencia: ["Abierto a partir del HANDOFF de QA en TKT-009 ciclo 1/3 (agente aa764ec0f042e41cd): confirmado con curl real contra el stack en producción-equivalente que /mapa-del-sitio devuelve 404; enlace ya presente en el pie de página desde TKT-008 (core/layout/pie-sitio). Depende de TKT-009 para poder enlazar itinerarios/guías/tipos/colecciones/glosario/búsqueda ya construidos."]
    actualizado: 2026-09-30
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
