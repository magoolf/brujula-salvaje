"""Rutas de la API pública /api/v1/publico/** (contracts/openapi.yaml, tags publico-*).

Los slugs siguen el patrón de RULE-008 en la propia ruta (THREAT-023): cualquier otro valor no
resuelve y responde 404 problem+json. `mapa` y `aleatorio` van antes del detalle (DEC-AUTO-117).
"""

from django.urls import path, re_path

from apps.contenido.api import views

app_name = "publico"

SLUG = r"(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)"

urlpatterns = [
    path("inicio", views.Inicio.as_view(), name="inicio"),
    path("configuracion", views.Configuracion.as_view(), name="configuracion"),
    path("escalas", views.Escalas.as_view(), name="escalas"),
    path("meses", views.Meses.as_view(), name="meses"),
    path("indice", views.Indice.as_view(), name="indice"),
    re_path(rf"^paginas/{SLUG}$", views.PaginaInstitucional.as_view(), name="pagina"),
    path("facetas/destinos", views.FacetasDestinos.as_view(), name="facetas-destinos"),
    path("destinos", views.ListaDestinos.as_view(), name="destinos"),
    path("destinos/mapa", views.MapaDestinos.as_view(), name="destinos-mapa"),
    path("destinos/aleatorio", views.DestinoAleatorio.as_view(), name="destino-aleatorio"),
    re_path(rf"^destinos/{SLUG}$", views.DetalleDestino.as_view(), name="destino"),
    path("itinerarios", views.ListaItinerarios.as_view(), name="itinerarios"),
    re_path(rf"^itinerarios/{SLUG}$", views.DetalleItinerario.as_view(), name="itinerario"),
    path("tipos-aventura", views.ListaTipos.as_view(), name="tipos"),
    re_path(rf"^tipos-aventura/{SLUG}$", views.DetalleTipo.as_view(), name="tipo"),
    path("categorias-guia", views.ListaCategoriasGuia.as_view(), name="categorias-guia"),
    re_path(
        rf"^categorias-guia/{SLUG}$", views.DetalleCategoriaGuia.as_view(), name="categoria-guia"
    ),
    path("guias", views.ListaGuias.as_view(), name="guias"),
    re_path(rf"^guias/{SLUG}$", views.DetalleGuia.as_view(), name="guia"),
    path("colecciones", views.ListaColecciones.as_view(), name="colecciones"),
    re_path(rf"^colecciones/{SLUG}$", views.DetalleColeccion.as_view(), name="coleccion"),
    path("busqueda", views.Busqueda.as_view(), name="busqueda"),
    re_path(
        r"^busqueda/(?P<grupo>[a-z]+)$", views.BusquedaPorGrupo.as_view(), name="busqueda-grupo"
    ),
    path("glosario", views.Glosario.as_view(), name="glosario"),
    path("creditos", views.Creditos.as_view(), name="creditos"),
]
