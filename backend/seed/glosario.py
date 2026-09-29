"""Términos del glosario (RULE-026), elegidos porque aparecen en las descripciones de destinos y
guías de esta misma semilla, para que el glosario tenga utilidad real de navegación cruzada
(instrucción del ticket TKT-007). `vincular_a` indica a qué contenido de la semilla (tipo, slug)
se enlaza el término vía `terminos_ids` (RULE-026: un término solo se publica si queda vinculado a
al menos un contenido publicado).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TerminoSemilla:
    titulo: str
    slug: str
    definicion: str
    vincular_a: list[tuple[str, str]]  # [(tipo_contenido, slug), ...]


TERMINOS: list[TerminoSemilla] = [
    TerminoSemilla(
        titulo="Aclimatación",
        slug="aclimatacion",
        definicion=(
            "Proceso de adaptación progresiva del cuerpo a la menor disponibilidad de oxígeno "
            "en altitud, ganando altura de forma gradual y con días de descanso, para reducir "
            "el riesgo de mal de altura."
        ),
        vincular_a=[("GUIA", "mal-de-altura-como-prevenirlo-y-reconocerlo")],
    ),
    TerminoSemilla(
        titulo="Mal de altura",
        slug="mal-de-altura",
        definicion=(
            "Conjunto de síntomas (dolor de cabeza, náuseas, fatiga) que puede aparecer por "
            "encima de los 2.500-3.000 metros cuando el cuerpo no ha tenido tiempo suficiente "
            "para aclimatarse a la altitud."
        ),
        vincular_a=[("DESTINO", "kilimanjaro"), ("DESTINO", "everest-campo-base")],
    ),
    TerminoSemilla(
        titulo="Vía ferrata",
        slug="via-ferrata",
        definicion=(
            "Ruta de montaña equipada de forma permanente con cable de acero, grapas y "
            "escalones metálicos, recorrida con un kit de autoaseguramiento de doble "
            "mosquetón enganchado siempre al cable."
        ),
        vincular_a=[("DESTINO", "dolomitas")],
    ),
    TerminoSemilla(
        titulo="Cenote",
        slug="cenote",
        definicion=(
            "Pozo natural de agua dulce formado por el colapso del techo de una cueva en "
            "terreno kárstico, típico de la península de Yucatán, que puede estar abierto, "
            "semicubierto o ser una cueva casi por completo."
        ),
        vincular_a=[("DESTINO", "cenotes-de-yucatan")],
    ),
    TerminoSemilla(
        titulo="Karst",
        slug="karst",
        definicion=(
            "Relieve formado por la disolución de roca caliza en presencia de agua, que da "
            "lugar a cuevas, cenotes, dolinas y paisajes de islotes rocosos como los de la "
            "bahía de Ha Long."
        ),
        vincular_a=[("DESTINO", "cenotes-de-yucatan"), ("DESTINO", "bahia-de-ha-long")],
    ),
    TerminoSemilla(
        titulo="Corriente de resaca",
        slug="corriente-de-resaca",
        definicion=(
            "Canal de agua que fluye mar adentro desde la orilla, capaz de arrastrar a quien no "
            "la reconoce; se sale de ella nadando en paralelo a la costa, nunca contra la "
            "corriente."
        ),
        vincular_a=[("GUIA", "que-preguntar-antes-de-reservar-con-un-operador-local")],
    ),
    TerminoSemilla(
        titulo="Mokoro",
        slug="mokoro",
        definicion=(
            "Canoa tradicional de fondo plano, impulsada con una pértiga por un guía local, "
            "usada para navegar los canales de aguas poco profundas del Delta del Okavango."
        ),
        vincular_a=[("DESTINO", "delta-del-okavango")],
    ),
    TerminoSemilla(
        titulo="Piolet",
        slug="piolet",
        definicion=(
            "Herramienta de mango corto con una pica y una hoja en la cabeza, usada en alta "
            "montaña y alpinismo para progresar y asegurarse sobre nieve o hielo."
        ),
        vincular_a=[("DESTINO", "pnn-los-nevados")],
    ),
    TerminoSemilla(
        titulo="Crampones",
        slug="crampones",
        definicion=(
            "Estructuras metálicas con puntas que se fijan a la bota para dar agarre sobre "
            "nieve dura o hielo, imprescindibles en la progresión de alta montaña y "
            "alpinismo."
        ),
        vincular_a=[("DESTINO", "pnn-los-nevados")],
    ),
    TerminoSemilla(
        titulo="Allemannsretten",
        slug="allemannsretten",
        definicion=(
            "Derecho de acceso libre a la naturaleza reconocido en la ley noruega, que permite "
            "caminar y acampar por la mayor parte del territorio no cultivado del país "
            "respetando unas normas básicas de distancia y cuidado del entorno."
        ),
        vincular_a=[("DESTINO", "fiordos-de-noruega")],
    ),
    TerminoSemilla(
        titulo="No dejar rastro",
        slug="no-dejar-rastro",
        definicion=(
            "Conjunto de principios para minimizar el impacto humano en la naturaleza: "
            "mantenerse en senderos marcados, gestionar correctamente los residuos y respetar "
            "la fauna y a otros visitantes."
        ),
        vincular_a=[("GUIA", "principios-de-no-dejar-rastro-en-la-naturaleza")],
    ),
    TerminoSemilla(
        titulo="Blanqueamiento de coral",
        slug="blanqueamiento-de-coral",
        definicion=(
            "Fenómeno de estrés térmico en el que el coral expulsa las algas que le dan color "
            "y buena parte de su energía cuando la temperatura del agua sube por encima de sus "
            "límites de tolerancia."
        ),
        vincular_a=[("DESTINO", "gran-barrera-de-coral")],
    ),
]
