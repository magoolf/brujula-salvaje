"""components.schemas.MedioMiniatura para las respuestas del panel (TKT-057, TKT-062).

Criterio único de la miniatura (DEC-AUTO-1080/1081): `url_miniatura` apunta al canal autenticado
del panel (`panelObtenerArchivoMedio`, que sirve también medios no DISPONIBLES) con el derivado
más estrecho; a igual ancho, WebP antes que JPEG y AVIF. Un medio sin derivados no tiene miniatura
que enlazar y se omite (`referencias.medios` no tiene `minItems`). Infraestructura (Regla 10): el
medio llega ya cargado (licencia por JOIN y derivados por prefetch) y se trata por sus atributos.
"""

from __future__ import annotations

from typing import Any

_PREFERENCIA_FORMATO = {"WEBP": 0, "JPEG": 1, "AVIF": 2}


def medio_miniatura(medio: Any) -> dict[str, Any] | None:
    """MedioMiniatura de un medio con `licencia` y `derivados` precargados (sin consultas)."""
    derivados = sorted(
        medio.derivados.all(),
        key=lambda d: (d.ancho_px, _PREFERENCIA_FORMATO.get(d.formato, 99), d.pk),
    )
    if not derivados:
        return None
    menor = derivados[0]
    return {
        "id": medio.pk,
        "estado": medio.estado,
        "texto_alternativo": medio.texto_alternativo,
        "licencia_codigo": medio.licencia.codigo if medio.licencia_id else None,
        "url_miniatura": (
            f"/api/v1/panel/medios/{medio.pk}/archivo?ancho={menor.ancho_px}&formato={menor.formato}"
        ),
    }
