"""Países de los 24 destinos semilla, con su región del catálogo (7 regiones ya sembradas por
`apps.catalogos.migrations.0002_semilla`: DB_HANDOFF "los países llegan con la carga semilla de
F7 (comando cargar_semilla)").

Cada entrada: (nombre, slug, codigo_iso2, region_slug). Los códigos ISO 3166-1 alpha-2 y la
región son hechos verificables (geografía), no cifras volátiles (DEC-AUTO-033).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaisSemilla:
    nombre: str
    slug: str
    codigo_iso2: str
    region_slug: str


PAISES: list[PaisSemilla] = [
    PaisSemilla("Colombia", "colombia", "CO", "america-del-sur"),
    PaisSemilla("Chile", "chile", "CL", "america-del-sur"),
    PaisSemilla("Argentina", "argentina", "AR", "america-del-sur"),
    PaisSemilla("Perú", "peru", "PE", "america-del-sur"),
    PaisSemilla("Bolivia", "bolivia", "BO", "america-del-sur"),
    PaisSemilla("Ecuador", "ecuador", "EC", "america-del-sur"),
    PaisSemilla("Costa Rica", "costa-rica", "CR", "america-central-y-caribe"),
    PaisSemilla("México", "mexico", "MX", "america-central-y-caribe"),
    PaisSemilla("Estados Unidos", "estados-unidos", "US", "america-del-norte"),
    PaisSemilla("Canadá", "canada", "CA", "america-del-norte"),
    PaisSemilla("Islandia", "islandia", "IS", "europa"),
    PaisSemilla("Italia", "italia", "IT", "europa"),
    PaisSemilla("Francia", "francia", "FR", "europa"),
    PaisSemilla("Noruega", "noruega", "NO", "europa"),
    PaisSemilla("Tanzania", "tanzania", "TZ", "africa"),
    PaisSemilla("Botsuana", "botsuana", "BW", "africa"),
    PaisSemilla("Nepal", "nepal", "NP", "asia"),
    PaisSemilla("Vietnam", "vietnam", "VN", "asia"),
    PaisSemilla("Jordania", "jordania", "JO", "asia"),
    PaisSemilla("Nueva Zelanda", "nueva-zelanda", "NZ", "oceania"),
    PaisSemilla("Australia", "australia", "AU", "oceania"),
]

PAIS_POR_SLUG: dict[str, PaisSemilla] = {p.slug: p for p in PAISES}
