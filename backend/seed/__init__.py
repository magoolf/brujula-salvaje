"""Dataset de contenido semilla (TKT-007).

Este paquete contiene únicamente DATOS (dataclasses/diccionarios en Python): ninguna función de
aquí toca el ORM ni las reglas de negocio. La orquestación (llamar a los servicios reales del
panel: `apps.contenido.services`, `apps.medios.services`, `apps.catalogos.services`,
`apps.inicio.services`) vive en
`apps.contenido.management.commands.cargar_semilla`.

Fuente de la lista de destinos/tipos/categorías: `docs/01_requerimientos/requirements.yaml`
(`contenido_semilla`, DEC-AUTO-006/007/010) — no se inventan ni se cambian esas listas.
"""
