"""4 colecciones curadas (REQ-027, Should en alcance por la API ya construida en TKT-006; Must
>=3 según el ticket). `elementos` referencia destinos ya definidos en `destinos.py` (>=4 cada
una, RULE-024): la publicación exige que esos destinos ya estén publicados.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementoColeccionSemilla:
    tipo: str  # "DESTINO" | "ITINERARIO"
    slug: str
    nota_editorial: str | None = None


@dataclass(frozen=True)
class ColeccionSemilla:
    titulo: str
    slug: str
    resumen: str
    descripcion: str
    elementos: list[ElementoColeccionSemilla]
    seo_titulo: str
    seo_descripcion: str


COLECCIONES: list[ColeccionSemilla] = [
    ColeccionSemilla(
        titulo="Grandes travesías de trekking",
        slug="grandes-travesias-de-trekking",
        resumen=(
            "Cinco rutas de varios días a pie que resumen lo mejor del trekking de montaña en "
            "distintos continentes."
        ),
        descripcion=(
            "<p>Desde las escalinatas de piedra original hasta Ciudad Perdida hasta los "
            "senderos patagónicos de Torres del Paine y El Chaltén, esta colección reúne "
            "travesías de trekking de varios días que no exigen técnica de escalada, solo buena "
            "condición física y preparación logística. Cada una tiene su propio carácter: "
            "selva, alta montaña andina, estepa patagónica o paisaje volcánico islandés.</p>"
        ),
        elementos=[
            ElementoColeccionSemilla(
                "DESTINO", "ciudad-perdida-teyuna", "Selva y patrimonio arqueológico tairona"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "camino-inca-machu-picchu", "La ruta clásica hasta Machu Picchu"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "torres-del-paine", "El circuito W entre torres de granito"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "el-chalten-fitz-roy", "Miradores gratuitos a los pies del Fitz Roy"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "ruta-laugavegur", "Montañas de riolita en las tierras altas islandesas"
            ),
        ],
        seo_titulo="Colección: grandes travesías de trekking",
        seo_descripcion=(
            "Cinco travesías de trekking de varios días en distintos continentes: Ciudad "
            "Perdida, Camino Inca, Torres del Paine, El Chaltén y Laugavegur."
        ),
    ),
    ColeccionSemilla(
        titulo="Techos y volcanes de alta montaña",
        slug="techos-y-volcanes-de-alta-montana",
        resumen=(
            "Cuatro ascensos de alta montaña, entre volcanes andinos y africanos y el macizo "
            "más alto de los Alpes."
        ),
        descripcion=(
            "<p>La alta montaña combina siempre altitud y aclimatación, aunque cada destino de "
            "esta colección la vive de forma distinta: los volcanes nevados del eje cafetero "
            "colombiano, el techo de África en el Kilimanjaro, el campo base del Everest en el "
            "Himalaya nepalí y el macizo del Mont Blanc, cuna histórica del alpinismo europeo.</p>"
        ),
        elementos=[
            ElementoColeccionSemilla(
                "DESTINO", "pnn-los-nevados", "Páramos y volcanes nevados del eje cafetero"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "kilimanjaro", "El techo de África sin escalada técnica"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "everest-campo-base", "El trekking de altitud más célebre del mundo"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "chamonix-mont-blanc", "La cuna histórica del alpinismo alpino"
            ),
        ],
        seo_titulo="Colección: techos y volcanes de alta montaña",
        seo_descripcion=(
            "Cuatro ascensos de alta montaña: Los Nevados, Kilimanjaro, campo base del Everest "
            "y Chamonix-Mont-Blanc."
        ),
    ),
    ColeccionSemilla(
        titulo="Mundos de agua: buceo, cenotes y fiordos",
        slug="mundos-de-agua-buceo-cenotes-y-fiordos",
        resumen=(
            "Cuatro formas distintas de explorar el agua: arrecife de coral, cuevas inundadas y "
            "fiordos glaciares."
        ),
        descripcion=(
            "<p>Esta colección reúne destinos donde el agua es la protagonista, desde el buceo "
            "en arrecife de coral hasta la espeleología acuática en cenotes mayas, pasando por "
            "el kayak entre paredes de fiordo noruego. Cada uno exige un nivel de formación "
            "técnica distinto, del esnórquel sin experiencia previa al buceo certificado en "
            "cuevas.</p>"
        ),
        elementos=[
            ElementoColeccionSemilla(
                "DESTINO", "islas-galapagos", "Fauna endémica y buceo con corrientes"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "gran-barrera-de-coral", "El mayor sistema de arrecifes del mundo"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "cenotes-de-yucatan", "Buceo en cuevas de agua dulce mayas"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "fiordos-de-noruega", "Kayak entre paredes de fiordo glaciar"
            ),
        ],
        seo_titulo="Colección: mundos de agua, buceo, cenotes y fiordos",
        seo_descripcion=(
            "Cuatro destinos de aventura acuática: Galápagos, Gran Barrera de Coral, cenotes de "
            "Yucatán y fiordos de Noruega."
        ),
    ),
    ColeccionSemilla(
        titulo="Deportes de adrenalina y expediciones",
        slug="deportes-de-adrenalina-y-expediciones",
        resumen=(
            "Cuatro destinos para quienes buscan la mayor dosis de adrenalina: rafting, "
            "parapente, desierto y salares de altura."
        ),
        descripcion=(
            "<p>De la capital colombiana de los deportes extremos a la capital neozelandesa de "
            "la aventura, pasando por travesías en 4x4 por desiertos de sal y de arena, esta "
            "colección reúne los destinos de mayor concentración de actividades de adrenalina "
            "de todo el sitio.</p>"
        ),
        elementos=[
            ElementoColeccionSemilla(
                "DESTINO", "san-gil-canon-del-chicamocha", "Rafting y parapente en Santander"
            ),
            ElementoColeccionSemilla("DESTINO", "queenstown", "La capital mundial de la aventura"),
            ElementoColeccionSemilla(
                "DESTINO", "wadi-rum", "Expediciones 4x4 por el desierto rojo"
            ),
            ElementoColeccionSemilla(
                "DESTINO", "salar-de-uyuni", "Travesías por el desierto de sal más grande del mundo"
            ),
        ],
        seo_titulo="Colección: deportes de adrenalina y expediciones",
        seo_descripcion=(
            "Cuatro destinos de adrenalina: San Gil, Queenstown, Wadi Rum y el Salar de Uyuni."
        ),
    ),
]
