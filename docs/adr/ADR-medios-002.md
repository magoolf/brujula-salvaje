# ADR-medios-002 — Subida de fotos de cámara grandes (≤ 40 MP) dentro del timeout de gunicorn

| Campo | Valor |
|---|---|
| Estado | PROPOSED (pendiente de QA y de la integración por el Orquestador) |
| Fecha | 2026-10-12 |
| Ticket | TKT-072 (MEDIUM, OBS-QA071-01) |
| Autor | Skill_Developer |
| Trazabilidad | DEC-AUTO-044 (JPEG/PNG/WebP ≤ 10 MB y ≤ 40 MP, recodificar, sin EXIF, derivados), THREAT-006/007, ADR-API-002 §8 (subida síncrona, gunicorn 120 s), ADR-DB-005 (sin broker), ADR-medios-001 (DEC-AUTO-1315), HANDOFF_UI_UX ASM-UX-001 (anchos 320-1920); DEC-AUTO-1320..1323 |
| Archivos | `backend/apps/medios/services.py`, `backend/apps/medios/tests/test_tkt072_subida_fotos_grandes.py` |

## Contexto
<!-- MEDICIONES -->

## Decisión
<!-- DECISION -->

## Alternativas
<!-- ALTERNATIVAS -->

## Consecuencias
<!-- CONSECUENCIAS -->
