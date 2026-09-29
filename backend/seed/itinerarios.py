"""10 itinerarios día a día (REQ-041, Must >=10), uno por cada uno de 10 destinos distintos
(Should, DEC-AUTO-009), con contenido real y verosímil, sin cifras volátiles (DEC-AUTO-033):
duraciones y desniveles son aproximaciones cualitativas de referencia, no datos operativos
exactos de un operador concreto.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiaSemilla:
    numero_dia: int
    titulo: str
    actividades: str
    distancia_km: float | None = None
    desnivel_positivo_m: int | None = None
    desnivel_negativo_m: int | None = None
    alojamiento_orientativo: str | None = None
    consejos: str | None = None


@dataclass(frozen=True)
class ItinerarioSemilla:
    titulo: str
    slug: str
    destino_slug: str
    resumen: str
    duracion_dias: int
    dificultad: int
    distancia_total_km: float | None
    desnivel_acumulado_m: int | None
    riesgos_seguridad: str
    tipos_slugs: list[str]
    dias: list[DiaSemilla]
    seo_titulo: str
    seo_descripcion: str
    relacionados_slugs: list[str] = field(default_factory=list)


_DESCARGO_ITIN = (
    "<p>Este itinerario es orientativo y no sustituye la valoración de guías certificados ni "
    "las condiciones reales del terreno el día de la actividad.</p>"
)

ITINERARIOS: list[ItinerarioSemilla] = [
    ItinerarioSemilla(
        titulo="Ciudad Perdida en 4 días",
        slug="ciudad-perdida-en-4-dias",
        destino_slug="ciudad-perdida-teyuna",
        resumen=(
            "La ruta clásica de ida y vuelta a Teyuna, con tres noches en campamentos junto al "
            "río Buritaca y el ascenso final por las escalinatas originales taironas."
        ),
        duracion_dias=4,
        dificultad=4,
        distancia_total_km=44.0,
        desnivel_acumulado_m=1800,
        riesgos_seguridad=(
            "<p>Calor húmedo, cruces de río con corriente variable y terreno irregular; la ruta "
            "se recorre siempre con guías certificados de agencias autorizadas, que deciden el "
            "ritmo diario y el punto de cruce de cada río.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dias=[
            DiaSemilla(
                1,
                "Del valle al primer campamento",
                "Salida en vehículo desde Santa Marta hasta el inicio del sendero y primera "
                "jornada de caminata entre fincas y selva húmeda hasta el primer campamento "
                "junto al río Buritaca.",
                distancia_km=8.0,
                desnivel_positivo_m=600,
                alojamiento_orientativo="Campamento con literas y mosquitera junto al río",
            ),
            DiaSemilla(
                2,
                "Cruces de río y selva densa",
                "Jornada más larga, con varios cruces del río Buritaca a pie y ascenso "
                "progresivo hacia el segundo campamento, ya en territorio de comunidades "
                "indígenas de la Sierra.",
                distancia_km=14.0,
                desnivel_positivo_m=500,
                alojamiento_orientativo="Campamento cercano a un poblado indígena",
            ),
            DiaSemilla(
                3,
                "Ascenso a Ciudad Perdida y regreso parcial",
                "Ascenso por las más de mil escalinatas de piedra original hasta las terrazas "
                "de la ciudadela, tiempo de recorrido guiado por el sitio arqueológico y "
                "descenso hasta un campamento intermedio en el camino de vuelta.",
                distancia_km=15.0,
                desnivel_positivo_m=400,
                desnivel_negativo_m=700,
                consejos="Llevar calzado con buen agarre para las escalinatas húmedas.",
            ),
            DiaSemilla(
                4,
                "Regreso a Santa Marta",
                "Última jornada de caminata de descenso hasta el punto de partida y traslado en "
                "vehículo de vuelta a Santa Marta.",
                distancia_km=7.0,
                desnivel_negativo_m=600,
            ),
        ],
        seo_titulo="Itinerario de 4 días a Ciudad Perdida",
        seo_descripcion=(
            "Itinerario día a día de la caminata de 4 días a Ciudad Perdida (Teyuna), Sierra "
            "Nevada de Santa Marta, Colombia."
        ),
        relacionados_slugs=["camino-inca-en-4-dias"],
    ),
    ItinerarioSemilla(
        titulo="Camino Inca clásico en 4 días",
        slug="camino-inca-en-4-dias",
        destino_slug="camino-inca-machu-picchu",
        resumen=(
            "Los cuatro días estándar del Camino Inca, con el paso de Warmiwañusca y la "
            "llegada a Machu Picchu por la Puerta del Sol al amanecer del último día."
        ),
        duracion_dias=4,
        dificultad=4,
        distancia_total_km=42.0,
        desnivel_acumulado_m=2600,
        riesgos_seguridad=(
            "<p>Mal de altura en el paso de Warmiwañusca (por encima de 4.000 m), escalinatas "
            "de piedra irregular y lluvia fría fuera de temporada seca; la ruta solo se recorre "
            "con agencias autorizadas y guías certificados.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dias=[
            DiaSemilla(
                1,
                "Valle sagrado y primeros sitios incas",
                "Salida desde el kilómetro 82 de la vía férrea, caminata suave junto al río "
                "Urubamba con vistas a los primeros sitios arqueológicos incas del recorrido.",
                distancia_km=11.0,
                desnivel_positivo_m=400,
                alojamiento_orientativo="Campamento en el valle",
            ),
            DiaSemilla(
                2,
                "El paso de Warmiwañusca",
                "Jornada más exigente del recorrido, con ascenso sostenido hasta el punto más "
                "alto de la ruta y descenso posterior hasta el siguiente valle de campamento.",
                distancia_km=12.0,
                desnivel_positivo_m=1200,
                desnivel_negativo_m=600,
                consejos="Ritmo lento y constante; la aclimatación previa en Cusco ayuda mucho.",
            ),
            DiaSemilla(
                3,
                "Sitios arqueológicos de altura",
                "Recorrido por varios sitios arqueológicos incas intermedios, entre ellos "
                "Wiñay Wayna, con tramos de escalinatas de piedra y vistas a la selva de "
                "montaña.",
                distancia_km=16.0,
                desnivel_positivo_m=400,
                desnivel_negativo_m=1000,
                alojamiento_orientativo="Campamento cercano a Wiñay Wayna",
            ),
            DiaSemilla(
                4,
                "Llegada a Machu Picchu",
                "Caminata de madrugada hasta la Puerta del Sol (Inti Punku) para la llegada a "
                "Machu Picchu al amanecer, seguida de un recorrido guiado por la ciudadela y "
                "regreso en tren desde Aguas Calientes.",
                distancia_km=3.0,
                desnivel_negativo_m=300,
            ),
        ],
        seo_titulo="Itinerario de 4 días del Camino Inca a Machu Picchu",
        seo_descripcion=(
            "Itinerario día a día del Camino Inca clásico de 4 días hasta Machu Picchu, con el "
            "paso de Warmiwañusca y la llegada por la Puerta del Sol."
        ),
        relacionados_slugs=["ciudad-perdida-en-4-dias"],
    ),
    ItinerarioSemilla(
        titulo="Torres del Paine: circuito W en 5 días",
        slug="torres-del-paine-circuito-w-en-5-dias",
        destino_slug="torres-del-paine",
        resumen=(
            "El circuito W completo, de valle Francés al glaciar Grey y la base de las Torres, "
            "con pernocta en refugios y campings del parque."
        ),
        duracion_dias=5,
        dificultad=4,
        distancia_total_km=71.0,
        desnivel_acumulado_m=3400,
        riesgos_seguridad=(
            "<p>Viento patagónico fuerte y constante, cambios meteorológicos rápidos y "
            "pasos expuestos; reservar refugios y campings con antelación y llevar equipo "
            "impermeable de calidad son medidas indispensables.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dias=[
            DiaSemilla(
                1,
                "Llegada y valle Ascencio",
                "Traslado hasta el sector Torres y primera caminata de aproximación hacia el "
                "valle Ascencio, base para la subida a las Torres al día siguiente.",
                distancia_km=10.0,
                desnivel_positivo_m=500,
                alojamiento_orientativo="Refugio o camping del sector Torres",
            ),
            DiaSemilla(
                2,
                "Mirador base de las Torres",
                "Ascenso exigente hasta el mirador de la base de las tres torres de granito y "
                "regreso al refugio, con el tramo final entre bloques de roca.",
                distancia_km=18.0,
                desnivel_positivo_m=800,
                desnivel_negativo_m=800,
                consejos="Salir temprano: las torres suelen despejarse mejor por la mañana.",
            ),
            DiaSemilla(
                3,
                "Traslado y valle Francés",
                "Traslado en catamarán por el lago Pehoé y caminata hacia el interior del valle "
                "Francés, con vistas al glaciar colgante del Paine Grande.",
                distancia_km=15.0,
                desnivel_positivo_m=600,
                alojamiento_orientativo="Camping del valle Francés",
            ),
            DiaSemilla(
                4,
                "Hacia el glaciar Grey",
                "Caminata hasta el sector del glaciar Grey, con vistas a los icebergs "
                "desprendidos flotando en el lago del mismo nombre.",
                distancia_km=18.0,
                desnivel_positivo_m=700,
                alojamiento_orientativo="Refugio Grey",
            ),
            DiaSemilla(
                5,
                "Salida del parque",
                "Última jornada de regreso desde el sector Grey hasta el punto de salida del "
                "parque y traslado hacia Puerto Natales.",
                distancia_km=10.0,
                desnivel_negativo_m=400,
            ),
        ],
        seo_titulo="Itinerario del circuito W en Torres del Paine (5 días)",
        seo_descripcion=(
            "Itinerario día a día del circuito W de 5 días en Torres del Paine: valle Francés, "
            "glaciar Grey y base de las Torres."
        ),
        relacionados_slugs=["el-chalten-en-4-dias"],
    ),
    ItinerarioSemilla(
        titulo="El Chaltén: Fitz Roy y Cerro Torre en 4 días",
        slug="el-chalten-en-4-dias",
        destino_slug="el-chalten-fitz-roy",
        resumen=(
            "Los dos grandes miradores de El Chaltén, laguna de los Tres y laguna Torre, con un "
            "día de descanso o excursión corta entre ambos."
        ),
        duracion_dias=4,
        dificultad=3,
        distancia_total_km=52.0,
        desnivel_acumulado_m=2200,
        riesgos_seguridad=(
            "<p>Viento fuerte en tramos expuestos y cambios meteorológicos rápidos propios de "
            "la Patagonia; registrar la salida en el centro de informes de Parques Nacionales "
            "antes de cada excursión es una práctica recomendada.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["senderismo-y-trekking", "escalada-y-via-ferrata"],
        dias=[
            DiaSemilla(
                1,
                "Llegada a El Chaltén",
                "Llegada al pueblo y caminata corta de aclimatación por senderos cercanos con "
                "vistas preliminares al macizo del Fitz Roy.",
                distancia_km=8.0,
                desnivel_positivo_m=200,
                alojamiento_orientativo="Alojamiento en El Chaltén",
            ),
            DiaSemilla(
                2,
                "Laguna de los Tres",
                "Caminata de día completo hasta el mirador de la laguna de los Tres, a los pies "
                "del Fitz Roy, con el tramo final de mayor desnivel de la excursión.",
                distancia_km=20.0,
                desnivel_positivo_m=1000,
                desnivel_negativo_m=1000,
                consejos="Llevar ropa de abrigo adicional para el mirador, muy expuesto al viento.",
            ),
            DiaSemilla(
                3,
                "Laguna Torre",
                "Caminata hasta el mirador Maestri, frente al Cerro Torre y su laguna, con "
                "posibilidad de acercarse hasta la propia orilla si el sendero está en buenas "
                "condiciones.",
                distancia_km=18.0,
                desnivel_positivo_m=600,
                desnivel_negativo_m=600,
            ),
            DiaSemilla(
                4,
                "Día libre o excursión corta",
                "Jornada de margen para repetir alguno de los miradores con mejor clima o "
                "recorrer senderos cortos cercanos al pueblo antes del traslado de salida.",
                distancia_km=6.0,
                desnivel_positivo_m=150,
            ),
        ],
        seo_titulo="Itinerario de 4 días en El Chaltén: Fitz Roy y Cerro Torre",
        seo_descripcion=(
            "Itinerario día a día de 4 días en El Chaltén: laguna de los Tres, laguna Torre y "
            "los miradores del Fitz Roy y el Cerro Torre."
        ),
        relacionados_slugs=["torres-del-paine-circuito-w-en-5-dias"],
    ),
    ItinerarioSemilla(
        titulo="San Gil: rafting y parapente en 3 días",
        slug="san-gil-en-3-dias",
        destino_slug="san-gil-canon-del-chicamocha",
        resumen=(
            "Tres días combinando rafting en el río Fonce, parapente sobre el cañón del "
            "Chicamocha y una visita al pueblo colonial de Barichara."
        ),
        duracion_dias=3,
        dificultad=2,
        distancia_total_km=None,
        desnivel_acumulado_m=None,
        riesgos_seguridad=(
            "<p>Caída al agua en los rápidos del Fonce y dependencia de las condiciones de "
            "viento para el parapente; ambas actividades se realizan con operadores locales "
            "certificados que deciden si las condiciones del día son seguras.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["rafting-y-deportes-de-rio", "parapente-y-deportes-aereos"],
        dias=[
            DiaSemilla(
                1,
                "Llegada y rafting en el río Fonce",
                "Llegada a San Gil y salida de rafting de medio día por los rápidos del río "
                "Fonce con operador local certificado.",
                alojamiento_orientativo="Alojamiento en San Gil",
            ),
            DiaSemilla(
                2,
                "Parapente sobre el Chicamocha",
                "Traslado al mirador del cañón del Chicamocha para un vuelo en parapente en "
                "tándem, condicionado a la ventana de viento del día.",
                consejos="Confirmar el vuelo la misma mañana según el parte de viento.",
            ),
            DiaSemilla(
                3,
                "Barichara y regreso",
                "Visita al pueblo colonial de Barichara, con tiempo libre para recorrer sus "
                "calles empedradas, antes del traslado de salida.",
            ),
        ],
        seo_titulo="Itinerario de 3 días de aventura en San Gil",
        seo_descripcion=(
            "Itinerario de 3 días en San Gil: rafting en el río Fonce, parapente sobre el "
            "cañón del Chicamocha y Barichara."
        ),
        relacionados_slugs=["ciudad-perdida-en-4-dias"],
    ),
    ItinerarioSemilla(
        titulo="Salar de Uyuni: circuito clásico en 3 días",
        slug="salar-de-uyuni-en-3-dias",
        destino_slug="salar-de-uyuni",
        resumen=(
            "El circuito clásico en 4x4 por el salar, las lagunas de colores del altiplano y "
            "los geysers de altura, con dos noches en alojamientos de la región."
        ),
        duracion_dias=3,
        dificultad=3,
        distancia_total_km=900.0,
        desnivel_acumulado_m=None,
        riesgos_seguridad=(
            "<p>Mal de altura por la elevada cota del altiplano, reverberación solar intensa "
            "sobre la sal y temperaturas nocturnas muy bajas; viajar con operadores locales de "
            "trayectoria conocida y vehículos revisados es la medida de seguridad más "
            "relevante.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["travesias-por-desierto-y-expediciones"],
        dias=[
            DiaSemilla(
                1,
                "Salar de Uyuni",
                "Salida desde Uyuni hacia el salar: cementerio de trenes, pueblo de Colchani y "
                "travesía por la superficie del salar hasta la isla Incahuasi, cubierta de "
                "cactus gigantes.",
                distancia_km=250.0,
                alojamiento_orientativo="Hotel de sal en el borde del salar",
            ),
            DiaSemilla(
                2,
                "Lagunas de colores del altiplano",
                "Ruta por el altiplano suroeste hasta las lagunas coloreadas por minerales y "
                "algas, con avistamiento de flamencos andinos, y desierto de Siloli.",
                distancia_km=350.0,
                alojamiento_orientativo="Refugio de altiplano cerca de la laguna Colorada",
            ),
            DiaSemilla(
                3,
                "Geysers y regreso",
                "Salida de madrugada a los geysers de Sol de Mañana, paso por aguas termales "
                "naturales y regreso a Uyuni o continuación hacia la frontera con Chile.",
                distancia_km=300.0,
            ),
        ],
        seo_titulo="Itinerario de 3 días por el Salar de Uyuni",
        seo_descripcion=(
            "Itinerario de 3 días del circuito clásico en 4x4 por el Salar de Uyuni y el "
            "altiplano suroeste de Bolivia."
        ),
        relacionados_slugs=["wadi-rum-en-3-dias"],
    ),
    ItinerarioSemilla(
        titulo="Wadi Rum: expedición beduina en 3 días",
        slug="wadi-rum-en-3-dias",
        destino_slug="wadi-rum",
        resumen=(
            "Dos noches en campamento beduino con travesía en 4x4, caminata por cañones del "
            "desierto y una jornada de escalada opcional en roca de arenisca."
        ),
        duracion_dias=3,
        dificultad=2,
        distancia_total_km=None,
        desnivel_acumulado_m=None,
        riesgos_seguridad=(
            "<p>Orientación compleja sin guía en el desierto, calor intenso de día y frío "
            "nocturno; la travesía se realiza siempre con guías beduinos locales que conocen el "
            "terreno.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["travesias-por-desierto-y-expediciones"],
        dias=[
            DiaSemilla(
                1,
                "Llegada y primer atardecer en el desierto",
                "Llegada al valle, recorrido corto en 4x4 por las primeras formaciones de "
                "arenisca y atardecer en un mirador de dunas.",
                alojamiento_orientativo="Campamento beduino",
            ),
            DiaSemilla(
                2,
                "Cañones y grabados rupestres",
                "Jornada completa en 4x4 y a pie por cañones estrechos, puentes de roca "
                "naturales y grabados rupestres milenarios del valle.",
                distancia_km=15.0,
                consejos="Llevar suficiente agua: no hay fuentes naturales en el trayecto.",
            ),
            DiaSemilla(
                3,
                "Salida del valle",
                "Última mañana con tiempo libre en el campamento antes del traslado de salida "
                "hacia Aqaba o Amán.",
            ),
        ],
        seo_titulo="Itinerario de 3 días de expedición en Wadi Rum",
        seo_descripcion=(
            "Itinerario de 3 días de expedición beduina en Wadi Rum: campamento, 4x4 y cañones "
            "del desierto jordano."
        ),
        relacionados_slugs=["salar-de-uyuni-en-3-dias"],
    ),
    ItinerarioSemilla(
        titulo="Queenstown: cuatro días de aventura",
        slug="queenstown-en-4-dias",
        destino_slug="queenstown",
        resumen=(
            "Parapente, ciclismo de montaña en el Queenstown Bike Park y rafting en el río "
            "Shotover, con un día de margen para el clima."
        ),
        duracion_dias=4,
        dificultad=3,
        distancia_total_km=None,
        desnivel_acumulado_m=None,
        riesgos_seguridad=(
            "<p>Cada actividad tiene su propio riesgo específico (caídas en ciclismo de "
            "descenso, vuelco en rafting, dependencia del viento en parapente); elegir siempre "
            "operadores certificados por la regulación neozelandesa de turismo de aventura es "
            "la medida común a todas ellas.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=[
            "parapente-y-deportes-aereos",
            "ciclismo-de-montana",
            "rafting-y-deportes-de-rio",
        ],
        dias=[
            DiaSemilla(
                1,
                "Llegada y parapente sobre el lago Wakatipu",
                "Llegada a Queenstown y vuelo en parapente en tándem desde Bob's Peak, con "
                "vistas al lago Wakatipu, condicionado a la ventana de viento del día.",
                alojamiento_orientativo="Alojamiento en Queenstown",
            ),
            DiaSemilla(
                2,
                "Queenstown Bike Park",
                "Jornada de ciclismo de montaña en el bike park, con telecabina de acceso y "
                "circuitos señalizados por dificultad para distintos niveles.",
                consejos="Empezar por los circuitos verdes o azules antes de subir de nivel.",
            ),
            DiaSemilla(
                3,
                "Rafting en el río Shotover",
                "Salida de rafting por el cañón del río Shotover, con guía certificado y "
                "briefing de seguridad previo obligatorio.",
            ),
            DiaSemilla(
                4,
                "Día libre o actividad adicional",
                "Jornada de margen para repetir una actividad según las condiciones "
                "meteorológicas o recorrer senderos cortos junto al lago antes de la salida.",
            ),
        ],
        seo_titulo="Itinerario de 4 días de aventura en Queenstown",
        seo_descripcion=(
            "Itinerario de 4 días en Queenstown, Nueva Zelanda: parapente, ciclismo de montaña "
            "y rafting en el río Shotover."
        ),
        relacionados_slugs=["dolomitas-via-ferrata-en-5-dias"],
    ),
    ItinerarioSemilla(
        titulo="Dolomitas: vía ferrata de refugio en refugio en 5 días",
        slug="dolomitas-via-ferrata-en-5-dias",
        destino_slug="dolomitas",
        resumen=(
            "Cinco días de vía ferrata y senderismo alpino entre refugios de montaña de las "
            "Dolomitas, con dificultad progresiva a lo largo de la semana."
        ),
        duracion_dias=5,
        dificultad=4,
        distancia_total_km=48.0,
        desnivel_acumulado_m=4200,
        riesgos_seguridad=(
            "<p>Caídas por mal uso del sistema de doble mosquetón, exposición a tormentas de "
            "tarde y caída de piedras en tramos concurridos; revisar el material antes de cada "
            "salida y comenzar temprano cada jornada son medidas de seguridad básicas.</p>"
            + _DESCARGO_ITIN
        ),
        tipos_slugs=["escalada-y-via-ferrata"],
        dias=[
            DiaSemilla(
                1,
                "Vía ferrata introductoria",
                "Primera vía ferrata de dificultad moderada para tomar contacto con el sistema "
                "de doble mosquetón y el cable de seguridad, con noche en refugio de montaña.",
                distancia_km=8.0,
                desnivel_positivo_m=700,
                alojamiento_orientativo="Refugio de montaña",
            ),
            DiaSemilla(
                2,
                "Cresta expuesta",
                "Vía ferrata de mayor exposición sobre una cresta rocosa, con tramos de cable "
                "vertical y vistas panorámicas al conjunto del macizo.",
                distancia_km=9.0,
                desnivel_positivo_m=900,
                desnivel_negativo_m=400,
            ),
            DiaSemilla(
                3,
                "Historia de la Primera Guerra Mundial",
                "Recorrido por una vía ferrata construida sobre instalaciones militares "
                "restauradas de la Primera Guerra Mundial, con paneles interpretativos en "
                "varios puntos de la ruta.",
                distancia_km=10.0,
                desnivel_positivo_m=850,
                desnivel_negativo_m=500,
            ),
            DiaSemilla(
                4,
                "Traslado y vía ferrata técnica",
                "Traslado a otro sector del macizo dolomítico para una vía ferrata de nivel más "
                "avanzado, con tramos verticales y techos en desplome.",
                distancia_km=7.0,
                desnivel_positivo_m=750,
                desnivel_negativo_m=600,
                consejos="Reservar esta etapa para cuando el equipo ya domine el sistema.",
            ),
            DiaSemilla(
                5,
                "Descenso final",
                "Última vía ferrata corta de cierre y descenso por sendero alpino hasta el "
                "punto de partida del valle.",
                distancia_km=6.0,
                desnivel_negativo_m=1500,
            ),
        ],
        seo_titulo="Itinerario de vía ferrata de 5 días en las Dolomitas",
        seo_descripcion=(
            "Itinerario de 5 días de vía ferrata de refugio en refugio en las Dolomitas, Alpes "
            "italianos, con dificultad progresiva."
        ),
        relacionados_slugs=["queenstown-en-4-dias"],
    ),
    ItinerarioSemilla(
        titulo="Campo base del Everest en 12 días",
        slug="everest-campo-base-en-12-dias",
        destino_slug="everest-campo-base",
        resumen=(
            "El itinerario estándar del valle del Khumbu, con días de aclimatación en Namche "
            "Bazaar y Dingboche y la subida a Kala Patthar para ver la cumbre del Everest."
        ),
        duracion_dias=12,
        dificultad=4,
        distancia_total_km=130.0,
        desnivel_acumulado_m=5800,
        riesgos_seguridad=(
            "<p>Mal de altura sostenido por encima de los 4.000 y 5.000 metros durante buena "
            "parte de la travesía; respetar los días de aclimatación del itinerario y estar "
            "atento a los síntomas es la medida de seguridad más importante.</p>" + _DESCARGO_ITIN
        ),
        tipos_slugs=["alta-montana-y-alpinismo"],
        dias=[
            DiaSemilla(
                1,
                "Vuelo a Lukla y Phakding",
                "Vuelo de montaña hasta Lukla y primera caminata corta hasta Phakding.",
                distancia_km=8.0,
                desnivel_negativo_m=250,
            ),
            DiaSemilla(
                2,
                "Ascenso a Namche Bazaar",
                "Ascenso hasta el principal centro comercial del valle, con el primer cruce de "
                "puentes colgantes sobre el río Dudh Koshi.",
                distancia_km=11.0,
                desnivel_positivo_m=800,
            ),
            DiaSemilla(
                3,
                "Día de aclimatación en Namche",
                "Caminata corta de aclimatación a una cota superior con regreso a dormir en "
                "Namche Bazaar.",
                distancia_km=6.0,
                desnivel_positivo_m=400,
                desnivel_negativo_m=400,
            ),
            DiaSemilla(
                4,
                "Hacia Tengboche",
                "Caminata hasta el monasterio de Tengboche, con las primeras vistas cercanas "
                "del Ama Dablam.",
                distancia_km=10.0,
                desnivel_positivo_m=600,
                desnivel_negativo_m=300,
            ),
            DiaSemilla(
                5,
                "Ascenso a Dingboche",
                "Continuación por el valle hasta Dingboche, ya en paisaje de alta montaña casi "
                "sin árboles.",
                distancia_km=12.0,
                desnivel_positivo_m=500,
            ),
            DiaSemilla(
                6,
                "Día de aclimatación en Dingboche",
                "Segunda jornada de aclimatación con caminata corta a una cota superior y "
                "regreso a Dingboche.",
                distancia_km=7.0,
                desnivel_positivo_m=400,
                desnivel_negativo_m=400,
            ),
            DiaSemilla(
                7,
                "Ascenso a Lobuche",
                "Caminata junto a las morrenas del glaciar Khumbu hasta el poblado de Lobuche.",
                distancia_km=13.0,
                desnivel_positivo_m=500,
            ),
            DiaSemilla(
                8,
                "Campo base del Everest",
                "Caminata hasta Gorak Shep y desde allí hasta el propio campo base del Everest, "
                "sobre la morrena del glaciar Khumbu.",
                distancia_km=15.0,
                desnivel_positivo_m=550,
                desnivel_negativo_m=150,
            ),
            DiaSemilla(
                9,
                "Kala Patthar y descenso",
                "Ascenso de madrugada a Kala Patthar para ver la cumbre del Everest y descenso "
                "hasta Pheriche.",
                distancia_km=16.0,
                desnivel_positivo_m=400,
                desnivel_negativo_m=1000,
            ),
            DiaSemilla(
                10,
                "Descenso a Namche Bazaar",
                "Descenso largo por el mismo valle hasta Namche Bazaar.",
                distancia_km=18.0,
                desnivel_negativo_m=1200,
            ),
            DiaSemilla(
                11,
                "Descenso a Lukla",
                "Última jornada de descenso hasta Lukla, cerrando el circuito del valle del "
                "Khumbu.",
                distancia_km=19.0,
                desnivel_negativo_m=800,
            ),
            DiaSemilla(
                12,
                "Vuelo de regreso a Katmandú",
                "Vuelo de montaña de regreso desde Lukla a Katmandú, sujeto a las condiciones "
                "meteorológicas del día.",
            ),
        ],
        seo_titulo="Itinerario de 12 días al campo base del Everest",
        seo_descripcion=(
            "Itinerario día a día de 12 días al campo base del Everest por el valle del Khumbu, "
            "con aclimatación y Kala Patthar."
        ),
        relacionados_slugs=["dolomitas-via-ferrata-en-5-dias"],
    ),
]
