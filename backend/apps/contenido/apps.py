from django.apps import AppConfig


class ContenidoConfig(AppConfig):
    """Supertipo contenido, subtipos 1:1 y relaciones polimórficas (ADR-DB-002)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contenido"
    label = "contenido"

    def ready(self) -> None:
        # TKT-006 (CHG-API-005): CATALOGO es el catálogo cerrado de `code` de Problem
        # (Skill_Backend §12.1). Los 3 códigos multi-entidad del ciclo editorial del panel
        # (contracts/openapi.yaml, components.schemas.Problem) pertenecen por diseño a ese
        # catálogo compartido (backend/apps/core/**), fuera de los archivos_permitidos de este
        # ticket. Se registran aquí de forma aditiva (nunca se sobrescribe una entrada existente)
        # para no tocar un archivo fuera de alcance; un ticket de infraestructura debería
        # moverlos al catálogo físico.
        from apps.core.problemas import CATALOGO

        nuevos = {
            "cascada_bloqueada": (
                409,
                "No se puede retirar",
                "La retirada en cascada la bloquea contenido publicado que aún depende de ella.",
            ),
            "cascada_sin_confirmar": (
                409,
                "Confirma la cascada",
                "La operación afecta a más contenido. Revisa el impacto y confírmalo.",
            ),
            "impacto_modificado": (
                409,
                "El impacto cambió",
                "El estado cambió desde que revisaste el impacto. Vuelve a revisarlo.",
            ),
        }
        for codigo, valor in nuevos.items():
            CATALOGO.setdefault(codigo, valor)
