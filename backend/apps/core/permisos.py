"""Permisos base de DRF (Blueprint §12: autorización deny-by-default en el servidor)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class DenegarPorDefecto(BasePermission):
    """Permiso por defecto: niega todo. Cada vista declara explícitamente sus permisos."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return False
