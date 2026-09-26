# Migración n=4 del plan (DB_HANDOFF v1.1): semilla de catálogos. Patrón data migration,
# idempotente por clave natural (get_or_create: no pisa ediciones del Administrador) y
# reversible (borra por clave natural). Los países y el contenido NO van aquí (carga semilla).
#
# Fuentes: regiones BLUEPRINT DATA-001 (DEC-AUTO-051); categorías PRD §6.5 (DEC-AUTO-010);
# licencias DB_HANDOFF licencia.notas [SUPUESTO: lista final en F7]; escalas DATA-020 (RULE-012).
# [SUPUESTO] Las etiquetas y descripciones de las escalas y de las categorías no están fijadas en
# el Blueprint: son textos iniciales editables por el Administrador (FEAT-047).
from django.db import migrations

REGIONES = [
    # (slug, nombre, continente, orden)
    ("america-del-sur", "América del Sur", "AMERICA", 1),
    ("america-central-y-caribe", "América Central y Caribe", "AMERICA", 2),
    ("america-del-norte", "América del Norte", "AMERICA", 3),
    ("europa", "Europa", "EUROPA", 4),
    ("africa", "África", "AFRICA", 5),
    ("asia", "Asia", "ASIA", 6),
    ("oceania", "Oceanía", "OCEANIA", 7),
]

CATEGORIAS = [
    # (slug, nombre, descripcion, orden)
    (
        "preparacion-fisica",
        "Preparación física",
        "Cómo entrenar resistencia, fuerza y aclimatación antes de una aventura.",
        1,
    ),
    (
        "equipo-y-mochila",
        "Equipo y mochila",
        "Qué llevar, cómo elegir el material y cómo organizar la mochila según la actividad.",
        2,
    ),
    (
        "seguridad-y-gestion-de-riesgos",
        "Seguridad y gestión de riesgos",
        "Planificación, evaluación de riesgos y respuesta ante imprevistos en el terreno.",
        3,
    ),
    (
        "salud-en-altitud-y-en-viaje",
        "Salud en altitud y en viaje",
        "Mal de altura, hidratación, botiquín y cuidados de salud durante el viaje.",
        4,
    ),
    (
        "viaje-sostenible-y-no-dejar-rastro",
        'Viaje sostenible y "no dejar rastro"',
        "Principios para minimizar el impacto ambiental y respetar a las comunidades locales.",
        5,
    ),
    (
        "presupuesto-y-planificacion",
        "Presupuesto y planificación",
        "Cómo estimar costes, organizar la logística y preparar el itinerario.",
        6,
    ),
    (
        "fotografia-de-aventura",
        "Fotografía de aventura",
        "Técnicas y equipo para fotografiar paisajes y actividades en entornos exigentes.",
        7,
    ),
    (
        "primera-aventura",
        "Primera aventura (principiantes)",
        "Consejos para quien se inicia: cómo elegir destino, nivel y acompañamiento.",
        8,
    ),
]

LICENCIAS = [
    # (codigo, nombre, url_texto_legal, requiere_atribucion, compatible_publicacion)
    (
        "CC-BY-4.0",
        "Creative Commons Atribución 4.0 Internacional",
        "https://creativecommons.org/licenses/by/4.0/",
        True,
        True,
    ),
    (
        "CC-BY-SA-4.0",
        "Creative Commons Atribución-CompartirIgual 4.0 Internacional",
        "https://creativecommons.org/licenses/by-sa/4.0/",
        True,
        True,
    ),
    (
        "CC0-1.0",
        "Creative Commons Cero 1.0 Universal (dominio público)",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        False,
        True,
    ),
    (
        "PDM-1.0",
        "Marca de Dominio Público 1.0",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        False,
        True,
    ),
    ("PROPIA", "Obra propia del equipo editorial", None, True, True),
]

NIVELES = [
    # (escala, nivel, etiqueta, descripcion)
    ("DIFICULTAD", 1, "Muy fácil", "Recorridos cortos y sin desnivel relevante, aptos para todos."),
    ("DIFICULTAD", 2, "Fácil", "Jornadas moderadas con algo de desnivel; basta una forma física básica."),
    ("DIFICULTAD", 3, "Moderada", "Jornadas largas o con desnivel sostenido; requiere buena forma física."),
    ("DIFICULTAD", 4, "Exigente", "Terreno técnico, altitud o varios días seguidos; requiere experiencia previa."),
    ("DIFICULTAD", 5, "Muy exigente", "Expediciones técnicas o en condiciones extremas; solo para personas expertas."),
    ("PRESUPUESTO", 1, "Económico", "Alojamiento sencillo, transporte público y gastos mínimos."),
    ("PRESUPUESTO", 2, "Moderado", "Alojamiento de gama media y algunas actividades guiadas."),
    ("PRESUPUESTO", 3, "Alto", "Logística organizada, guías y alojamiento cómodo."),
    ("PRESUPUESTO", 4, "Muy alto", "Expediciones o viajes con permisos, vuelos internos y servicios exclusivos."),
]


def sembrar(apps, schema_editor):
    Region = apps.get_model("catalogos", "Region")
    CategoriaGuia = apps.get_model("catalogos", "CategoriaGuia")
    Licencia = apps.get_model("catalogos", "Licencia")
    NivelEscala = apps.get_model("catalogos", "NivelEscala")

    for slug, nombre, continente, orden in REGIONES:
        Region.objects.get_or_create(
            slug=slug, defaults={"nombre": nombre, "continente": continente, "orden": orden}
        )
    for slug, nombre, descripcion, orden in CATEGORIAS:
        CategoriaGuia.objects.get_or_create(
            slug=slug, defaults={"nombre": nombre, "descripcion": descripcion, "orden": orden}
        )
    for codigo, nombre, url, atribucion, compatible in LICENCIAS:
        Licencia.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "url_texto_legal": url,
                "requiere_atribucion": atribucion,
                "compatible_publicacion": compatible,
            },
        )
    for escala, nivel, etiqueta, descripcion in NIVELES:
        NivelEscala.objects.get_or_create(
            escala=escala, nivel=nivel, defaults={"etiqueta": etiqueta, "descripcion": descripcion}
        )


def retirar_semilla(apps, schema_editor):
    Region = apps.get_model("catalogos", "Region")
    CategoriaGuia = apps.get_model("catalogos", "CategoriaGuia")
    Licencia = apps.get_model("catalogos", "Licencia")
    NivelEscala = apps.get_model("catalogos", "NivelEscala")

    Region.objects.filter(slug__in=[r[0] for r in REGIONES]).delete()
    CategoriaGuia.objects.filter(slug__in=[c[0] for c in CATEGORIAS]).delete()
    Licencia.objects.filter(codigo__in=[lic[0] for lic in LICENCIAS]).delete()
    for escala, nivel, _etiqueta, _descripcion in NIVELES:
        NivelEscala.objects.filter(escala=escala, nivel=nivel).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogos", "0001_inicial"),
    ]

    operations = [
        migrations.RunPython(sembrar, reverse_code=retirar_semilla),
    ]
