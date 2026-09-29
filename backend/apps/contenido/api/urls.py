"""Rutas de la API pública /api/v1/publico/** (contracts/openapi.yaml, tags publico-*).

Los slugs siguen el patrón de RULE-008 en la propia ruta (THREAT-023): cualquier otro valor no
resuelve y responde 404 problem+json. `mapa` y `aleatorio` van antes del detalle (DEC-AUTO-117).
"""

from django.urls import path, register_converter

from apps.contenido.api import views


class SlugPublico:
    """RULE-008: [a-z0-9]+(-[a-z0-9]+)*, máximo 120 caracteres."""

    regex = r"[a-z0-9]+(?:-[a-z0-9]+)*"

    def to_python(self, valor: str) -> str:
        return valor

    def to_url(self, valor: str) -> str:
        return valor


class GrupoBusqueda:
    regex = r"[a-z]{1,20}"

    def to_python(self, valor: str) -> str:
        return valor

    def to_url(self, valor: str) -> str:
        return valor


register_converter(SlugPublico, "slugpub")
register_converter(GrupoBusqueda, "grupo")

app_name = "publico"

urlpatterns = [
    path("inicio", views.Inicio.as_view(), name="inicio"),
    path("configuracion", views.Configuracion.as_view(), name="configuracion"),
    path("escalas", views.Escalas.as_view(), name="escalas"),
    path("meses", views.Meses.as_view(), name="meses"),
    path("indice", views.Indice.as_view(), name="indice"),
    path("paginas/<slugpub:slug>", views.PaginaInstitucional.as_view(), name="pagina"),
    path("facetas/destinos", views.FacetasDestinos.as_view(), name="facetas-destinos"),
    path("destinos", views.ListaDestinos.as_view(), name="destinos"),
    path("destinos/mapa", views.MapaDestinos.as_view(), name="destinos-mapa"),
    path("destinos/aleatorio", views.DestinoAleatorio.as_view(), name="destino-aleatorio"),
    path("destinos/<slugpub:slug>", views.DetalleDestino.as_view(), name="destino"),
    path("itinerarios", views.ListaItinerarios.as_view(), name="itinerarios"),
    path("itinerarios/<slugpub:slug>", views.DetalleItinerario.as_view(), name="itinerario"),
    path("tipos-aventura", views.ListaTipos.as_view(), name="tipos"),
    path("tipos-aventura/<slugpub:slug>", views.DetalleTipo.as_view(), name="tipo"),
    path("categorias-guia", views.ListaCategoriasGuia.as_view(), name="categorias-guia"),
    path(
        "categorias-guia/<slugpub:slug>",
        views.DetalleCategoriaGuia.as_view(),
        name="categoria-guia",
    ),
    path("guias", views.ListaGuias.as_view(), name="guias"),
    path("guias/<slugpub:slug>", views.DetalleGuia.as_view(), name="guia"),
    path("colecciones", views.ListaColecciones.as_view(), name="colecciones"),
    path("colecciones/<slugpub:slug>", views.DetalleColeccion.as_view(), name="coleccion"),
    path("busqueda", views.Busqueda.as_view(), name="busqueda"),
    path("busqueda/<grupo:grupo>", views.BusquedaPorGrupo.as_view(), name="busqueda-grupo"),
    path("glosario", views.Glosario.as_view(), name="glosario"),
    path("creditos", views.Creditos.as_view(), name="creditos"),
]
