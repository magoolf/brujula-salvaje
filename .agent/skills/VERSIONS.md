# Versiones fijadas de herramientas de terceros

Registradas el 2026-09-24. Cualquier actualización requiere cambiar el SHA aquí y registrar el cambio en `audit_log.md`.

| Herramienta | Origen | Commit SHA fijado | Notas |
|---|---|---|---|
| playwright-cli | https://github.com/microsoft/playwright-cli.git | `74354ecc7a43da16d91a9bc54fa8db8283a3fcf5` | `CLAUDE.md` → `CLAUDE.md.disabled` y `.claude/` → `_claude.disabled` (neutralizados, CLAUDE.md §0.11) |
| security-audit-skill | https://github.com/cloudflare/security-audit-skill.git | `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` | Sin archivos de gobierno internos |

Verificación: `git -C .agent/skills/<herramienta> rev-parse HEAD` debe coincidir con el SHA de esta tabla (o `git submodule status` desde la raíz).

## Gestión como submódulos git

Ambas herramientas son submódulos del repositorio raíz (`.gitmodules`), fijados a los SHA de la tabla.

**Tras clonar el repositorio** (obligatorio, CLAUDE.md §0.11):
```bash
git submodule update --init
cd .agent/skills/playwright-cli && mv CLAUDE.md CLAUDE.md.disabled && mv .claude _claude.disabled
```
La neutralización de playwright-cli es un cambio local dentro del submódulo: no viaja con el clon. Por eso `.gitmodules` declara `ignore = dirty` solo para playwright-cli.
security-audit-skill NO tiene `ignore = dirty`: cualquier modificación local debe aparecer en `git status` y revisarse.

## Incidencias

- 2026-09-24: `security-audit-skill/skills/security-audit/SKILL.md` tenía una modificación local ajena al upstream (fechada 2026-09-23 12:40): renombraba el skill a `code-compliance-review`, reformulaba la auditoría de seguridad como "compliance" y eliminaba la salvaguarda "Do not automatically run all six phases, create an output directory, or write audit artifacts". Restaurado al SHA fijado por decisión del usuario.
