"""Fixtures de las pruebas HTTP de taxonomías (TKT-012): sesión real de panel (login + CSRF vía
`apps.cuentas.tests.conftest`, mismo patrón que `apps/medios/tests/conftest.py`)."""

from apps.cuentas.tests.conftest import (  # noqa: F401 (fixtures de pytest)
    admin,
    cliente_admin,
    cliente_editora,
    editora,
)
