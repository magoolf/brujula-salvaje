"""Fixtures de las pruebas HTTP del panel de medios (TKT-006).

`cliente_editora`/`editora`: sesión real de panel (login + CSRF vía `apps.cuentas.tests.conftest`,
mismo patrón que `apps/auditoria/tests/conftest.py` y `apps/contenido/tests/conftest.py`) para
pruebas HTTP end-to-end del panel de medios (QA ciclo 1/3, BUG-2: la subida de medios solo se
detectó rota con una petición `multipart/form-data` real contra el servidor, nunca con una
llamada directa a `services.subir_medios`)."""

from apps.cuentas.tests.conftest import cliente_editora, editora  # noqa: F401 (fixtures de pytest)
