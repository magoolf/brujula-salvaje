"""Negociación de contenido: la API solo produce JSON (nunca responde 406)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.renderers import BaseRenderer
from rest_framework.request import Request


class NegociacionSoloJson(DefaultContentNegotiation):
    def select_renderer(
        self,
        request: Request,
        renderers: Iterable[BaseRenderer],
        format_suffix: str | None = None,
    ) -> tuple[BaseRenderer, Any]:
        renderer = next(iter(renderers))
        return renderer, renderer.media_type
