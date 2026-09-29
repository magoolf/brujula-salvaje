"""Los 24 destinos semilla (requirements.yaml `contenido_semilla.destinos_propuestos`,
DEC-AUTO-007; lista literal, no se inventan ni cambian).

Cada entrada cubre `campos_obligatorios_destino` (requirements.yaml línea 1039, REQ-042):
nombre/slug, país, resumen (<=300c), descripción experta (>=600 palabras), tipos de aventura
(el primero de `tipos_slugs` es el principal), dificultad 1-5, mejor época (meses 1-12), duración
recomendada, presupuesto 1-4, clima/altitud, cómo llegar, seguridad y riesgos (con descargo,
REQ-024/RSK-001), sostenibilidad y coordenadas aproximadas.

DEC-AUTO-033: sin precios, horarios ni cifras volátiles; lenguaje cualitativo ("temporada seca",
"con antelación"). Los hechos geográficos/históricos citados son de conocimiento general y
verificable (nombres de lugares, altitudes aproximadas, coordenadas, actividades típicas); donde
hay incertidumbre razonable se usa lenguaje cualitativo en vez de una cifra exacta.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DestinoSemilla:
    n: int
    titulo: str
    slug: str
    pais_slug: str
    resumen: str
    descripcion_experta: str
    tipos_slugs: list[str]
    dificultad: int
    meses_mejor_epoca: list[int]
    duracion_min_dias: int
    duracion_max_dias: int
    nivel_presupuesto: int
    clima: str
    altitud_max_m: int | None
    como_llegar: str
    seguridad_riesgos: str
    sostenibilidad: str
    latitud: float
    longitud: float
    seo_titulo: str
    seo_descripcion: str
    relacionados_slugs: list[str] = field(default_factory=list)


_DESCARGO = (
    "<p>Esta información es orientativa, procede de fuentes públicas y del criterio editorial "
    "del equipo, y no sustituye la valoración de guías certificados, autoridades locales del "
    "parque o reserva, ni los partes meteorológicos oficiales del día del viaje.</p>"
)

DESTINOS: list[DestinoSemilla] = [
    DestinoSemilla(
        n=1,
        titulo="Ciudad Perdida (Teyuna), Sierra Nevada de Santa Marta",
        slug="ciudad-perdida-teyuna",
        pais_slug="colombia",
        resumen=(
            "Una ciudad prehispánica escondida en la selva de la Sierra Nevada, a la que solo "
            "se llega caminando varios días junto a guías indígenas y locales."
        ),
        descripcion_experta=(
            "<p>Ciudad Perdida, llamada Teyuna por los pueblos indígenas que aún habitan la "
            "Sierra Nevada de Santa Marta, es un conjunto de terrazas de piedra, escalinatas y "
            "plazas construido por la cultura tairona varios siglos antes de la llegada "
            "europea al continente. A diferencia de Machu Picchu, permaneció oculto bajo la "
            "vegetación durante siglos hasta su redescubrimiento en el siglo XX, y hoy sigue "
            "siendo un lugar sagrado activo para los pueblos kogui, wiwa, arhuaco y kankuamo, "
            "descendientes directos de los taironas, que consideran la Sierra Nevada el "
            "corazón del mundo.</p> "
            "<p>El acceso es, en sí mismo, la experiencia central del destino: no existe "
            "carretera ni acceso motorizado, y la única forma de llegar es una caminata de "
            "varios días por senderos de selva húmeda tropical, cruzando el río Buritaca en "
            "múltiples ocasiones y ganando altitud de forma progresiva desde el calor del valle "
            "hasta el clima más fresco de la ciudadela, a más de mil metros sobre el nivel del "
            "mar. La ruta discurre siempre acompañada de guías certificados de la región —una "
            "exigencia operativa y también una forma de reconocer el territorio indígena que se "
            "atraviesa— y combina jornadas de varias horas de caminata con pernoctación en "
            "campamentos con literas y mosquitera junto al río.</p> "
            "<p>El tramo final, unos cientos de escalones de piedra original tallados por los "
            "taironas, desemboca en las terrazas circulares de la ciudadela, envueltas casi "
            "siempre en niebla o luz filtrada por el dosel de la selva. La sensación de "
            "aislamiento —sin señal de telefonía, sin electricidad de red y con muy pocos "
            "visitantes compartiendo el lugar en cada turno de entrada— es parte esencial de lo "
            "que distingue esta caminata de otras rutas patrimoniales más masificadas del "
            "continente.</p> "
            "<p>El calor húmedo, la humedad casi constante y el terreno irregular hacen de esta "
            "una caminata exigente más por las condiciones ambientales que por la técnica: no "
            "requiere experiencia previa de montaña, pero sí una condición física razonable para "
            "sostener varias horas diarias de esfuerzo bajo temperaturas altas. El cruce de ríos "
            "a pie, con el nivel del agua variable según las lluvias recientes, es el punto "
            "técnico que más respeto exige, y los guías son quienes deciden el punto y el modo "
            "de vadeo más seguro cada día.</p> "
            "<p>La relación con las comunidades indígenas de la Sierra es un eje central de "
            "cualquier visita responsable: se recorren territorios ancestrales, se cruzan "
            "poblados indígenas activos y se comparte camino con miembros de estas comunidades, "
            "lo que exige un comportamiento respetuoso —pedir permiso antes de fotografiar "
            "personas, seguir las indicaciones de los guías sobre qué lugares son de acceso "
            "restringido y no dejar ningún resto de basura en el camino ni en los "
            "campamentos—.</p> <p>La Sierra Nevada de Santa Marta es, además, el macizo costero "
            "más alto del mundo: sus picos nevados están a poco más de cuarenta kilómetros del mar "
            "Caribe, lo que genera una diversidad de pisos climáticos extraordinaria en un espacio "
            "relativamente pequeño. La ruta a Ciudad Perdida transcurre en la parte baja y media "
            "de ese gradiente, entre selva húmeda tropical y bosque de montaña, con una "
            "biodiversidad de aves e insectos que forma parte del atractivo del recorrido más "
            "allá de la propia ciudadela arqueológica.</p> "
            "<p>El redescubrimiento moderno de Ciudad Perdida, a mediados de la década de 1970, "
            "estuvo ligado a buscadores de tesoros locales antes de que arqueólogos colombianos "
            "documentaran de forma sistemática el sitio; ese origen convive hoy con un manejo "
            "arqueológico y turístico coordinado entre el Estado colombiano y las autoridades "
            "indígenas de la Sierra, un modelo de gobernanza compartida poco frecuente en "
            "yacimientos arqueológicos de esta magnitud en el continente. Cada cierto número de "
            "años, las comunidades indígenas de la Sierra Nevada han llegado a solicitar el "
            "cierre temporal del sitio para realizar pagamentos y rituales propios, un "
            "recordatorio de que Teyuna sigue siendo, ante todo, un lugar vivo para quienes lo "
            "consideran sagrado, no solo una atracción arqueológica para visitantes externos.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dificultad=4,
        meses_mejor_epoca=[12, 1, 2, 3, 7, 8],
        duracion_min_dias=4,
        duracion_max_dias=5,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima cálido y húmedo de selva tropical durante todo el año, con temperaturas "
            "diurnas altas y humedad constante; las lluvias son más frecuentes fuera de las "
            "temporadas secas de diciembre-marzo y julio-agosto, cuando los senderos y los "
            "cruces de río suelen estar en mejores condiciones.</p>"
        ),
        altitud_max_m=1300,
        como_llegar=(
            "<p>El punto de partida de la caminata se organiza desde Santa Marta, en la costa "
            "Caribe colombiana, a la que se llega por vuelo doméstico o por carretera desde "
            "otras ciudades del país. Desde Santa Marta, las agencias autorizadas trasladan a "
            "los grupos por carretera hasta el punto de inicio del sendero; el resto del "
            "recorrido es exclusivamente a pie. No existe forma de contratar la ruta de manera "
            "totalmente independiente: opera bajo un sistema de agencias autorizadas con guías "
            "locales, y conviene reservar con antelación en temporada alta.</p>"
        ),
        seguridad_riesgos=(
            "<p>Los riesgos principales son el golpe de calor y la deshidratación por el clima "
            "húmedo y las horas de caminata continuada, las torceduras en terreno irregular o "
            "mojado, y la fuerza de la corriente en los cruces de río tras lluvias intensas. La "
            "ruta se realiza siempre con guías certificados de agencias autorizadas, que llevan "
            "botiquín y conocen los protocolos de evacuación de la zona; seguir sus indicaciones "
            "sobre el ritmo, la hidratación y el momento de cruzar cada río es la medida de "
            "seguridad más importante.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>La caminata transcurre por territorio ancestral indígena y por una reserva "
            "natural: llevarse toda la basura generada, evitar el plástico de un solo uso, no "
            "usar jabón ni champú en los ríos y respetar las zonas de acceso restringido "
            "marcadas por los guías son las normas mínimas de un visitante responsable. El "
            "sistema de cupos diarios de acceso, gestionado junto con las autoridades indígenas "
            "y el parque, busca limitar la presión sobre un ecosistema y un patrimonio "
            "culturalmente muy sensibles.</p>"
        ),
        latitud=11.0361,
        longitud=-73.9264,
        seo_titulo="Ciudad Perdida (Teyuna): guía experta de la caminata",
        seo_descripcion=(
            "Guía experta para caminar a Ciudad Perdida (Teyuna): ruta, dificultad, seguridad y "
            "respeto por el territorio indígena de la Sierra Nevada."
        ),
        relacionados_slugs=["cano-cristales", "san-gil-canon-del-chicamocha", "pnn-los-nevados"],
    ),
    DestinoSemilla(
        n=2,
        titulo="Caño Cristales, Serranía de La Macarena",
        slug="cano-cristales",
        pais_slug="colombia",
        resumen=(
            "El «río de los cinco colores»: un lecho de algas endémicas que tiñe sus aguas de "
            "rojo, amarillo y verde durante unos meses del año."
        ),
        descripcion_experta=(
            "<p>Caño Cristales es un río de aguas cristalinas que discurre sobre roca "
            "precámbrica, una de las formaciones geológicas más antiguas del planeta, dentro de "
            "la Serranía de La Macarena, un macizo aislado en el sur de los Llanos colombianos "
            "que actúa como puente biológico entre los Andes, la Amazonía y la Orinoquía. Su fama "
            "se debe a la Macarenia clavigera, una planta acuática endémica que tapiza el fondo "
            "del río y que, durante una ventana concreta del año, adquiere tonos rojos, rosados, "
            "amarillos y verdes que conviven con el azul del agua y el negro de la roca, un "
            "fenómeno que ha valido al lugar el sobrenombre de «el río de los cinco colores» o "
            "«el río que se escapó del paraíso».</p> "
            "<p>La coloración depende de un equilibrio muy preciso entre el nivel del agua y la "
            "luz solar: la planta necesita suficiente corriente y sol directo sobre el lecho "
            "para desarrollar el pigmento, por lo que solo se aprecia con intensidad en una "
            "franja del año entre el final de la temporada de lluvias y el inicio de la seca, "
            "cuando el caudal ya ha bajado de su máximo pero todavía no está tan escaso como para "
            "dejar la planta expuesta y seca. Fuera de esa ventana, el río conserva un atractivo "
            "notable —piscinas naturales de aguas transparentes sobre roca esculpida— pero sin "
            "el color que le da su fama.</p> "
            "<p>El acceso a la zona está regulado desde hace años por un sistema de rutas fijas "
            "y guías locales obligatorios, en parte por la fragilidad del ecosistema y en parte "
            "porque la Serranía de La Macarena fue, durante décadas, una región de difícil "
            "acceso por el conflicto armado colombiano; hoy el turismo regulado es también una "
            "vía de desarrollo económico para las comunidades de La Macarena, el municipio base "
            "de las visitas. Recorrer el caño combina caminatas cortas y moderadas entre "
            "distintos tramos del río —cada uno con formaciones y piscinas propias, con nombres "
            "como Los Ochos o El Tapete— y baños puntuales en zonas habilitadas.</p> "
            "<p>La exigencia física es moderada: los senderos son cortos pero pueden ser "
            "resbaladizos sobre roca húmeda, y el calor de los Llanos, sin apenas sombra en "
            "algunos tramos, obliga a llevar buena hidratación y protección solar. No es una "
            "ruta técnica ni de altitud, lo que la hace accesible a un rango amplio de "
            "condición física, aunque conviene calzado de buen agarre por el terreno rocoso y "
            "mojado.</p> "
            "<p>La conservación del ecosistema es el eje que condiciona toda la experiencia: "
            "está prohibido el uso de protector solar, repelente o cualquier producto químico "
            "antes de entrar en contacto con el agua, porque afecta directamente a la Macarenia "
            "clavigera, así como bañarse fuera de las zonas específicamente habilitadas para "
            "ello. Los guías locales, formados en el manejo de estas normas, acompañan cada "
            "grupo y son quienes indican qué tramos están abiertos según el estado del río en "
            "cada visita.</p> "
            "<p>Más allá del propio caño, la Serranía de La Macarena alberga una biodiversidad "
            "notable de aves, primates y flora propia de su condición de zona de transición "
            "entre varias grandes regiones biogeográficas de Colombia, lo que añade interés "
            "naturalista al recorrido para quien viaja con tiempo suficiente para explorar más "
            "de un tramo del río o combinar la visita con otras caminatas cortas de la zona.</p> "
            "<p>La Macarenia clavigera, la planta que produce el fenómeno de color, solo "
            "prospera en aguas muy limpias, con un lecho rocoso estable y una corriente moderada "
            "constante, condiciones que en la mayoría de ríos tropicales son difíciles de "
            "sostener por la erosión y la carga de sedimentos. La conjunción de roca precámbrica "
            "dura, apenas erosionable, y un caudal relativamente estable a lo largo del año "
            "explica por qué este fenómeno es tan poco común en otros ríos de la región "
            "amazónica y orinocense, y por qué Caño Cristales se describe a menudo como un caso "
            "prácticamente único en el mundo dentro de este tipo de ecosistemas fluviales.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dificultad=2,
        meses_mejor_epoca=[6, 7, 8, 9, 10, 11],
        duracion_min_dias=3,
        duracion_max_dias=4,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima cálido tropical de los Llanos, con una temporada de lluvias marcada "
            "(aproximadamente abril-noviembre) y una seca más corta; el color característico "
            "del río solo se aprecia con intensidad en una ventana entre el final de las lluvias "
            "y el inicio de la seca, por lo que conviene confirmar la temporada vigente con "
            "operadores locales antes de viajar.</p>"
        ),
        altitud_max_m=350,
        como_llegar=(
            "<p>El acceso habitual es en vuelo doméstico desde Bogotá hasta el municipio de La "
            "Macarena, ya que la zona no cuenta con carretera de acceso directo desde los "
            "principales centros urbanos del país. Desde el pueblo, los operadores autorizados "
            "organizan el traslado en lancha y a pie hasta los distintos tramos del río, siempre "
            "con guía local. La regulación del número de visitantes y la disponibilidad de "
            "vuelos hacen recomendable reservar con bastante antelación en la temporada de "
            "color.</p>"
        ),
        seguridad_riesgos=(
            "<p>Los riesgos principales son las resbalones sobre roca húmeda en los senderos y "
            "orillas del caño, la insolación y la deshidratación por el calor de los Llanos sin "
            "apenas sombra en algunos tramos, y las corrientes localmente fuertes tras lluvias "
            "recientes. La visita siempre va acompañada de guía local autorizado, que conoce el "
            "estado del caño cada día y decide qué tramos y piscinas son seguros para el baño en "
            "cada visita.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El ecosistema del caño es extremadamente sensible a químicos: está prohibido "
            "todo protector solar, repelente, maquillaje o crema antes del contacto con el agua, "
            "y el baño solo se permite en las zonas específicamente habilitadas. El acceso "
            "regulado por cupos y guías locales busca limitar la presión humana sobre la "
            "Macarenia clavigera y sostener, a la vez, una fuente de ingresos para las "
            "comunidades de la región.</p>"
        ),
        latitud=2.1811,
        longitud=-73.7936,
        seo_titulo="Caño Cristales: guía del río de los cinco colores",
        seo_descripcion=(
            "Cuándo ir, cómo llegar y qué normas de conservación respetar en Caño Cristales, el "
            "río de los cinco colores en La Macarena, Colombia."
        ),
        relacionados_slugs=[
            "ciudad-perdida-teyuna",
            "pnn-los-nevados",
            "san-gil-canon-del-chicamocha",
        ],
    ),
    DestinoSemilla(
        n=3,
        titulo="San Gil y Cañón del Chicamocha",
        slug="san-gil-canon-del-chicamocha",
        pais_slug="colombia",
        resumen=(
            "La capital colombiana de los deportes extremos: rafting en el río Fonce y "
            "parapente sobre uno de los cañones más profundos del continente."
        ),
        descripcion_experta=(
            "<p>San Gil, en el departamento de Santander, se ha ganado en las últimas décadas el "
            "título informal de capital colombiana de los deportes de aventura, gracias a la "
            "combinación de un río de aguas bravas accesible a las puertas del pueblo —el río "
            "Fonce— y la cercanía del cañón del Chicamocha, una de las gargantas más profundas y "
            "extensas de Suramérica, tallada por el río del mismo nombre entre las cordilleras "
            "andinas de Santander. Esa doble geografía, río de rápidos y cañón de paredes "
            "verticales, ha convertido a la región en un punto de referencia para quienes buscan "
            "concentrar varias actividades de aventura en pocos días sin necesidad de grandes "
            "desplazamientos.</p> "
            "<p>El rafting en el río Fonce se practica en tramos de dificultad moderada, "
            "accesibles a personas sin experiencia previa gracias a operadores locales con años "
            "de trayectoria y guías certificados, lo que ha hecho de esta actividad la puerta de "
            "entrada más habitual al turismo de aventura en Colombia para muchos visitantes "
            "nacionales y extranjeros. El cañón del Chicamocha, por su parte, con paredes que "
            "caen varios cientos de metros hasta el lecho del río, ofrece condiciones de viento "
            "térmico especialmente favorables para el parapente, con despegues desde miradores "
            "en el borde del cañón y vuelos que permiten apreciar la escala del paisaje desde el "
            "aire.</p> "
            "<p>Más allá de estas dos actividades insignia, la región de San Gil concentra un "
            "abanico amplio de opciones: espeleología en cuevas cercanas, rappel en cascadas, "
            "puenting y torrentismo, lo que la convierte en un destino especialmente versátil "
            "para quien quiere combinar distintos niveles de adrenalina en un solo viaje. Los "
            "pueblos coloniales de la región —Barichara, a poca distancia, es uno de los más "
            "reconocidos del país por su arquitectura de calles empedradas y casas blancas— "
            "añaden un contrapunto cultural y tranquilo a la intensidad física de las "
            "actividades de aventura.</p> "
            "<p>El clima cálido de la región santandereana, con temperaturas altas durante buena "
            "parte del año, hace que las actividades de río sean particularmente agradecidas "
            "para refrescarse, mientras que el parapente depende más de las condiciones de "
            "viento del día que de la temporada del año, con vuelos posibles en un rango amplio "
            "de meses siempre que las condiciones lo permitan según el criterio del piloto.</p> "
            "<p>La seguridad de ambas actividades insignia descansa en gran medida en la "
            "trayectoria de los operadores locales, muchos de ellos con varias décadas de "
            "experiencia en la región: revisar que la agencia cuente con guías certificados y "
            "equipo en buen estado es la decisión más importante que toma quien visita San Gil "
            "por primera vez, tanto para el rafting como para el parapente y el resto de "
            "actividades disponibles.</p> "
            "<p>La región es también un buen ejemplo de cómo el turismo de aventura ha "
            "transformado la economía local: gran parte de los operadores de rafting, parapente "
            "y espeleología son negocios familiares o cooperativas de guías santandereanos, lo "
            "que hace que elegir operadores locales establecidos, en lugar de intermediarios "
            "externos, tenga un impacto económico directo y positivo en la comunidad que "
            "sostiene esta oferta de aventura.</p> "
            "<p>El torrentismo y el rappel en cascadas cercanas completan la oferta de la región "
            "para "
            "quien busca actividades de menor duración que el rafting o el parapente: descender "
            "junto "
            "a una caída de agua, asegurado con cuerda y arnés, es una introducción habitual a las "
            "técnicas verticales para quienes luego se interesan por la escalada o la vía ferrata "
            "en "
            "otros destinos. La proximidad de San Gil a Bogotá y a otras ciudades andinas del "
            "interior colombiano, unida a la variedad de actividades concentradas en un radio "
            "reducido, explica buena parte de su popularidad entre viajeros nacionales que "
            "disponen de pocos días mesa.</p>"
        ),
        tipos_slugs=["rafting-y-deportes-de-rio", "parapente-y-deportes-aereos"],
        dificultad=2,
        meses_mejor_epoca=[12, 1, 2, 6, 7, 8],
        duracion_min_dias=2,
        duracion_max_dias=4,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima cálido de valle interandino durante todo el año, con una temporada más "
            "seca hacia diciembre-marzo y otra hacia junio-agosto; las lluvias más intensas "
            "suelen concentrarse en abril-mayo y octubre-noviembre, cuando el caudal del río "
            "Fonce puede variar más de un día a otro.</p>"
        ),
        altitud_max_m=1700,
        como_llegar=(
            "<p>San Gil se encuentra sobre la vía que conecta Bogotá con Bucaramanga, a la que "
            "se llega por carretera desde ambas ciudades; Bucaramanga cuenta con aeropuerto con "
            "vuelos domésticos regulares y es el punto de conexión más habitual para quien viaja "
            "desde otras regiones de Colombia. Una vez en San Gil, la mayoría de las actividades "
            "de aventura se organizan directamente con operadores locales en el propio pueblo.</p>"
        ),
        seguridad_riesgos=(
            "<p>En el rafting, el riesgo principal es la caída al agua en los rápidos y el "
            "atrapamiento si no se sigue la posición correcta indicada en el briefing de "
            "seguridad; en el parapente, el factor determinante es el viento del día, que puede "
            "obligar a posponer o cancelar un vuelo por decisión del piloto. En ambos casos, "
            "contratar operadores locales con guías o pilotos certificados y material revisado "
            "es la medida de seguridad más relevante.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Elegir operadores locales de trayectoria conocida, en lugar de intermediarios "
            "externos, sostiene directamente a las familias y cooperativas de guías de la "
            "región; en el río Fonce, evitar dejar cualquier residuo en las orillas y respetar "
            "los caudales ecológicos mínimos que fijan las autoridades ambientales forma parte "
            "de una visita responsable a esta cuenca compartida por varias comunidades "
            "santandereanas.</p>"
        ),
        latitud=6.5572,
        longitud=-73.1341,
        seo_titulo="San Gil y Chicamocha: guía de aventura en Santander",
        seo_descripcion=(
            "Rafting en el río Fonce y parapente sobre el cañón del Chicamocha: guía práctica "
            "de aventura en San Gil, Santander, Colombia."
        ),
        relacionados_slugs=["ciudad-perdida-teyuna", "cano-cristales", "pnn-los-nevados"],
    ),
    DestinoSemilla(
        n=4,
        titulo="Parque Nacional Natural Los Nevados",
        slug="pnn-los-nevados",
        pais_slug="colombia",
        resumen=(
            "Volcanes nevados, páramos de frailejones y lagunas de alta montaña en el corazón "
            "del eje cafetero colombiano."
        ),
        descripcion_experta=(
            "<p>El Parque Nacional Natural Los Nevados protege un tramo de la cordillera Central "
            "de los Andes colombianos que incluye varios volcanes con casquete glaciar "
            "remanente —el Nevado del Ruiz y el Nevado de Santa Isabel entre los más conocidos— "
            "y una extensión considerable de páramo, el ecosistema de alta montaña tropical "
            "característico de los Andes del norte, dominado por el frailejón, una planta de "
            "crecimiento muy lento y adaptada a la radiación solar intensa y las temperaturas "
            "bajo cero nocturnas propias de esta franja de altitud.</p> "
            "<p>El parque funciona como una torre de agua fundamental para el centro de "
            "Colombia: sus páramos y glaciares alimentan varias de las cuencas hidrográficas más "
            "importantes de la región cafetera, lo que le da una relevancia ecológica que va "
            "mucho más allá de su valor paisajístico. El Nevado del Ruiz, además, es un volcán "
            "activo cuya actividad se monitorea de manera constante por las autoridades "
            "geológicas colombianas, y el acceso a determinadas zonas del parque puede "
            "restringirse temporalmente según el nivel de actividad volcánica vigente.</p> "
            "<p>Las rutas de trekking del parque recorren senderos de páramo entre lagunas "
            "glaciares, formaciones rocosas volcánicas y extensos frailejonales, con vistas "
            "hacia los conos nevados cuando el cielo está despejado. La combinación de altitud "
            "elevada, radiación solar intensa por la delgadez de la atmósfera a esa cota y "
            "temperaturas que pueden caer varios grados bajo cero durante la noche exige una "
            "aclimatación cuidadosa y equipo de abrigo adecuado, incluso en un país de clima "
            "tropical como Colombia.</p> "
            "<p>El mal de altura es un riesgo real en las rutas más altas del parque, que superan "
            "con facilidad los 4.000 metros sobre el nivel del mar: quienes llegan directamente "
            "desde ciudades a baja altitud, como Bogotá o las capitales de la costa, deben "
            "prever un margen de aclimatación progresiva antes de emprender las caminatas más "
            "exigentes, y prestar atención a síntomas como dolor de cabeza persistente, náuseas "
            "o fatiga desproporcionada.</p> "
            "<p>El ecosistema de páramo es, además, uno de los más frágiles y de recuperación "
            "más lenta del planeta: el frailejón puede tardar varias décadas en alcanzar su "
            "altura adulta, y el suelo esponjoso que retiene el agua del páramo se compacta con "
            "facilidad si se camina fuera de los senderos habilitados. Mantenerse siempre sobre "
            "el sendero marcado no es solo una recomendación de seguridad, sino una condición "
            "para no dañar un ecosistema del que depende el abastecimiento de agua de buena "
            "parte de la región.</p> "
            "<p>La cercanía del parque a la llamada zona cafetera colombiana permite combinar la "
            "visita de alta montaña con el paisaje de fincas de café de las tierras medias "
            "circundantes, un contraste de pisos térmicos —del páramo helado a los cafetales "
            "templados— que resume bien la diversidad geográfica de los Andes tropicales en un "
            "espacio relativamente compacto.</p> "
            "<p>El Nevado del Ruiz protagonizó en 1985 una de las erupciones más letales de la "
            "historia reciente de Suramérica, cuando el deshielo súbito de su casquete glaciar "
            "provocó un flujo de lodo volcánico que arrasó la localidad de Armero; ese episodio "
            "sigue "
            "muy presente en la memoria regional y explica el rigor con el que las autoridades "
            "geológicas colombianas vigilan hoy la actividad del volcán y restringen el acceso a "
            "determinadas zonas del parque cuando las señales de actividad lo aconsejan. Los "
            "refugios "
            "de montaña dentro del parque permiten dividir las rutas más largas en varias "
            "jornadas, con paradas para observar de cerca los frailejonales y las lagunas "
            "glaciares que jalonan "
            "buena parte del recorrido.</p> "
            "<p>La ruta hacia el Nevado de Santa Isabel y otros sectores del parque atraviesa "
            "también "
            "bosques de niebla y de Polylepis, un género de árbol andino capaz de crecer a mayor "
            "altitud que casi cualquier otro árbol del planeta, con una corteza laminada "
            "característica que lo protege del frío extremo. Estos bosques de altura, hoy "
            "fragmentados por siglos de actividad ganadera y agrícola en las laderas más bajas de "
            "la "
            "cordillera, son objeto de programas de restauración ecológica que buscan recuperar su "
            "extensión original como parte de la protección integral de la cuenca hídrica del "
            "parque.</p>"
        ),
        tipos_slugs=["alta-montana-y-alpinismo", "senderismo-y-trekking"],
        dificultad=4,
        meses_mejor_epoca=[12, 1, 2, 7, 8],
        duracion_min_dias=1,
        duracion_max_dias=3,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima de páramo de alta montaña tropical: frío durante todo el año, con "
            "temperaturas diurnas suaves cuando hay sol directo y descensos por debajo de cero "
            "durante la noche; la niebla y la lluvia pueden aparecer en cualquier época, con "
            "mejores probabilidades de cielo despejado en las temporadas secas de "
            "diciembre-febrero y julio-agosto.</p>"
        ),
        altitud_max_m=5300,
        como_llegar=(
            "<p>El acceso habitual es por carretera desde Manizales, Pereira o Ibagué, ciudades "
            "del eje cafetero colombiano con conexión aérea nacional, hasta los distintos puntos "
            "de entrada del parque. Conviene confirmar con la autoridad del parque el estado de "
            "acceso vigente, ya que ciertas zonas pueden cerrarse temporalmente por actividad "
            "volcánica del Nevado del Ruiz.</p>"
        ),
        seguridad_riesgos=(
            "<p>El riesgo principal es el mal de altura por la elevada cota de las rutas del "
            "parque, agravado si no hay aclimatación previa; a esto se suman la exposición a "
            "radiación solar intensa, las temperaturas bajo cero nocturnas y, de forma "
            "particular en este parque, la posibilidad de restricciones de acceso por actividad "
            "volcánica del Nevado del Ruiz, que conviene verificar siempre con la autoridad del "
            "parque antes de la visita.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El páramo es un ecosistema de crecimiento extremadamente lento y alta fragilidad: "
            "mantenerse siempre sobre los senderos habilitados, no arrancar frailejones ni otra "
            "vegetación y llevarse toda la basura son normas mínimas para no comprometer un "
            "ecosistema del que depende el agua de buena parte del centro de Colombia.</p>"
        ),
        latitud=4.8880,
        longitud=-75.3230,
        seo_titulo="PNN Los Nevados: guía de trekking en los volcanes andinos",
        seo_descripcion=(
            "Trekking de alta montaña entre páramos y volcanes nevados en el Parque Nacional "
            "Los Nevados, eje cafetero de Colombia."
        ),
        relacionados_slugs=[
            "ciudad-perdida-teyuna",
            "cano-cristales",
            "san-gil-canon-del-chicamocha",
        ],
    ),
    DestinoSemilla(
        n=5,
        titulo="Torres del Paine",
        slug="torres-del-paine",
        pais_slug="chile",
        resumen=(
            "Torres de granito, glaciares y estepa patagónica en uno de los parques nacionales "
            "más espectaculares de Suramérica."
        ),
        descripcion_experta=(
            "<p>El Parque Nacional Torres del Paine, en la Patagonia chilena, debe su nombre a "
            "las tres torres de granito que dominan su perfil, formadas por un antiguo batolito "
            "que el hielo y la erosión han esculpido durante millones de años hasta dejar al "
            "descubierto estas agujas verticales de roca clara. El macizo del Paine se levanta de "
            "forma casi abrupta sobre la estepa patagónica, con glaciares que descienden desde el "
            "campo de hielo Sur, lagos de un turquesa intenso por la harina de roca glaciar en "
            "suspensión y una fauna que incluye guanacos, cóndores y, con algo de suerte, "
            "pumas.</p> "
            "<p>El parque es mundialmente conocido por sus rutas de trekking de varios días, en "
            "particular el circuito «W», que conecta los tres valles principales —el valle "
            "Francés, la base de las Torres y el glaciar Grey— y el circuito completo «O», que "
            "rodea todo el macizo en una travesía más larga y exigente. Ambas rutas combinan "
            "senderos bien señalizados con una infraestructura de refugios y campings que "
            "permite planificar el recorrido por etapas, sin necesidad de cargar todo el equipo "
            "de expedición.</p> "
            "<p>El viento patagónico es, junto con el paisaje, el rasgo que más define la "
            "experiencia de caminar por el Paine: rachas muy fuertes y constantes, especialmente "
            "en los sectores más expuestos, pueden dificultar el avance y obligan a extremar la "
            "precaución en pasos estrechos o con desnivel a un lado del sendero. La climatología "
            "patagónica es además extremadamente cambiante, con la posibilidad de experimentar "
            "sol, viento fuerte y lluvia en una misma jornada, por lo que la ropa de capas y el "
            "equipo impermeable de calidad son imprescindibles independientemente de la época.</p> "
            "<p>La exigencia física del circuito W es moderada-alta por la suma de días y "
            "desnivel acumulado, mientras que el circuito O, al añadir un paso de alta montaña "
            "expuesto al viento, se considera más exigente y recomendado solo con experiencia "
            "previa de trekking de varios días. En ambos casos, reservar con antelación los "
            "refugios o sitios de camping es indispensable, ya que el parque limita el número de "
            "personas que pueden pernoctar en cada sector por noche.</p> "
            "<p>El glaciar Grey, una de las lenguas del campo de hielo patagónico Sur —una de las "
            "mayores extensiones de hielo continental fuera de las zonas polares—, es uno de los "
            "puntos más fotografiados del recorrido, con icebergs de un azul intenso "
            "desprendiéndose hacia el lago del mismo nombre. La conservación de esta reserva de "
            "agua dulce, y del propio equilibrio del parque frente a la creciente afluencia de "
            "visitantes, ha llevado a reforzar en los últimos años las normas de acceso, los "
            "cupos y la exigencia de reservar por adelantado.</p> "
            "<p>La escala de las distancias patagónicas hace que llegar hasta el parque ya sea, "
            "en sí, parte del viaje: la región combina la visita al Paine con otros atractivos "
            "cercanos, como el glaciar Perito Moreno al otro lado de la frontera con Argentina, "
            "lo que convierte a menudo esta zona en el eje de un itinerario patagónico más amplio "
            "en lugar de una visita aislada de pocos días.</p> "
            "<p>El parque debe buena parte de su nombre al color azulado que el aire patagónico da "
            "a "
            "las torres de granito bajo ciertas condiciones de luz («paine» significa azul en "
            "lengua "
            "tehuelche); esa raíz indígena recuerda que la estepa patagónica estuvo habitada "
            "durante "
            "siglos por pueblos cazadores-recolectores antes de la colonización ganadera del "
            "territorio en el siglo XIX. La fauna del parque, con el guanaco como herbívoro "
            "dominante "
            "del paisaje y el cóndor andino sobrevolando los valles, es hoy objeto de programas "
            "activos de conservación que han permitido, entre otros logros, la recuperación de la "
            "población de pumas en la región.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dificultad=4,
        meses_mejor_epoca=[11, 12, 1, 2, 3],
        duracion_min_dias=4,
        duracion_max_dias=9,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima subpolar patagónico, con veranos australes (noviembre-marzo) más "
            "templados y días largos, y vientos fuertes y constantes en cualquier época del año; "
            "fuera de la temporada de verano austral el parque recibe nieve y las condiciones se "
            "vuelven considerablemente más exigentes.</p>"
        ),
        altitud_max_m=2900,
        como_llegar=(
            "<p>El acceso habitual es por vuelo hasta Punta Arenas o Puerto Natales, en la "
            "Patagonia chilena, y desde allí por carretera hasta la entrada del parque. Puerto "
            "Natales, el pueblo más cercano, concentra la mayoría de los servicios de "
            "abastecimiento, alquiler de equipo y transporte hacia los distintos sectores de "
            "inicio de las rutas.</p>"
        ),
        seguridad_riesgos=(
            "<p>El viento patagónico, con rachas capaces de desequilibrar a una persona en "
            "pasos expuestos, es el riesgo más particular del Paine, junto con los cambios "
            "meteorológicos rápidos que pueden traer lluvia o nieve incluso en verano. Reservar "
            "el recorrido por etapas dentro de los refugios y campings autorizados, llevar "
            "equipo de abrigo e impermeable de calidad y respetar los horarios de cierre de "
            "paso en los tramos más expuestos son las medidas de seguridad más relevantes.</p>"
            + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El sistema de cupos y reservas obligatorias en refugios y campings busca limitar "
            "la presión humana sobre un ecosistema de estepa y alta montaña patagónica muy "
            "expuesto a la erosión; llevarse toda la basura, no hacer fuego fuera de las zonas "
            "habilitadas —los incendios forestales han dañado partes del parque en el pasado— y "
            "mantenerse en los senderos marcados son normas centrales de una visita "
            "responsable.</p>"
        ),
        latitud=-50.9423,
        longitud=-73.0511,
        seo_titulo="Torres del Paine: guía de trekking en la Patagonia chilena",
        seo_descripcion=(
            "Circuitos W y O, dificultad, viento patagónico y reservas: guía experta para "
            "hacer trekking en Torres del Paine, Chile."
        ),
        relacionados_slugs=["el-chalten-fitz-roy", "salar-de-uyuni", "camino-inca-machu-picchu"],
    ),
    DestinoSemilla(
        n=6,
        titulo="El Chaltén y Monte Fitz Roy",
        slug="el-chalten-fitz-roy",
        pais_slug="argentina",
        resumen=(
            "La capital argentina del trekking, a los pies de las agujas de granito del Fitz "
            "Roy y el Cerro Torre."
        ),
        descripcion_experta=(
            "<p>El Chaltén es un pueblo relativamente joven —fundado en la década de 1980, en "
            "buena medida por razones de soberanía territorial— situado en la Patagonia "
            "argentina, a los pies del macizo que forman el Monte Fitz Roy y el Cerro Torre, dos "
            "de las agujas de granito más codiciadas del alpinismo mundial por la dificultad "
            "técnica de sus paredes casi verticales y su exposición al viento patagónico. El "
            "pueblo se ha declarado a sí mismo «capital nacional del trekking», y su trama urbana "
            "está pensada casi por completo en función de los senderistas y montañistas que "
            "llegan de todo el mundo.</p> "
            "<p>A diferencia de otros destinos de montaña con acceso restringido o de pago, la "
            "red de senderos de El Chaltén parte directamente desde el propio pueblo y es de "
            "acceso libre y gratuito, lo que la distingue de la mayoría de grandes destinos de "
            "trekking patagónicos. Los dos miradores más conocidos —la laguna de los Tres, a los "
            "pies del Fitz Roy, y la laguna Torre, frente al Cerro Torre— se pueden recorrer como "
            "excursiones de un día completo desde el pueblo, sin necesidad de pernoctar en el "
            "monte, aunque también existen zonas de camping agreste gratuito para quien prefiera "
            "dividir la ruta en varias jornadas.</p> "
            "<p>El clima es, junto con el paisaje, el protagonista silencioso de cualquier visita "
            "a El Chaltén: el Fitz Roy y el Cerro Torre están tan expuestos al viento del campo "
            "de hielo patagónico que suelen permanecer cubiertos de nubes buena parte del año, y "
            "ver sus cumbres completamente despejadas es un motivo de celebración local, casi un "
            "acontecimiento que corre de boca en boca entre los habitantes del pueblo. Por eso "
            "muchos visitantes prevén varios días de estancia, para aumentar las probabilidades "
            "de una jornada de cielo despejado.</p> "
            "<p>Para el alpinismo técnico en las paredes del Fitz Roy y el Cerro Torre, la "
            "dificultad es de nivel mundial: son objetivos de referencia para escaladores de "
            "elite por la combinación de roca de calidad, gran desnivel y condiciones "
            "meteorológicas extremas, y quedan fuera del alcance de quien no tenga formación "
            "avanzada de escalada en roca y montaña. El senderismo hacia los miradores, en "
            "cambio, es exigente pero accesible a cualquier persona con una condición física "
            "razonable, sin necesidad de experiencia técnica.</p> "
            "<p>El viento patagónico condiciona también el senderismo: rachas fuertes son "
            "habituales en los tramos más expuestos, y las temperaturas pueden bajar con rapidez "
            "al perder el sol o ganar altitud, incluso en pleno verano austral. Llevar siempre "
            "ropa de abrigo e impermeable adicional, más allá de lo que parezca necesario al "
            "salir del pueblo con buen tiempo, es una recomendación constante de los guardaparques "
            "locales.</p> "
            "<p>El Chaltén forma parte del Parque Nacional Los Glaciares, que comparte con la "
            "vecina localidad de El Calafate y el glaciar Perito Moreno, lo que permite combinar "
            "en un mismo viaje el trekking de montaña con la observación de uno de los glaciares "
            "más accesibles y estudiados del mundo, a poca distancia por carretera.</p> "
            "<p>El nombre «Chaltén» proviene de una palabra del pueblo tehuelche que significa "
            "aproximadamente «montaña que humea», en referencia a las nubes que casi siempre "
            "envuelven la cumbre del Fitz Roy, y que los primeros pobladores de la región "
            "interpretaban como humo. La primera ascensión documentada al Fitz Roy, en 1952, por "
            "un equipo franco-argentino, se considera uno de los grandes hitos del alpinismo "
            "sudamericano por la dificultad técnica y la exposición al viento de la ruta elegida; "
            "desde entonces, el macizo ha acumulado una historia de ascensiones que sigue "
            "atrayendo cada temporada a algunos de los alpinistas técnicos más reconocidos del "
            "mundo.</p> <p>El Parque Nacional Los Glaciares, del que El Chaltén forma parte, "
            "protege también el "
            "extremo sur del campo de hielo patagónico continental, una de las mayores reservas de "
            "agua dulce en estado sólido fuera de las regiones polares; buena parte de ese hielo "
            "permanece prácticamente inexplorado por su dificultad de acceso, lo que mantiene a la "
            "región como uno de los últimos grandes espacios de exploración de montaña disponibles "
            "en "
            "Suramérica para expediciones de largo aliento.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking", "escalada-y-via-ferrata"],
        dificultad=3,
        meses_mejor_epoca=[11, 12, 1, 2, 3],
        duracion_min_dias=3,
        duracion_max_dias=6,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima patagónico de montaña, con veranos australes (noviembre-marzo) más "
            "estables aunque nunca exentos de viento fuerte; el Fitz Roy y el Cerro Torre pasan "
            "buena parte del año cubiertos de nubes por su exposición al campo de hielo, por lo "
            "que varios días de estancia aumentan la probabilidad de verlos despejados.</p>"
        ),
        altitud_max_m=3405,
        como_llegar=(
            "<p>El acceso habitual es por vuelo hasta El Calafate, en la Patagonia argentina, y "
            "desde allí por carretera hasta El Chaltén. La red de senderos parte directamente "
            "del pueblo, por lo que no se necesita transporte adicional para acceder a las rutas "
            "principales hacia el Fitz Roy y el Cerro Torre.</p>"
        ),
        seguridad_riesgos=(
            "<p>El viento patagónico y los cambios meteorológicos rápidos son el riesgo "
            "principal del senderismo en la zona; en el alpinismo técnico de las paredes del "
            "Fitz Roy y el Cerro Torre, la exigencia es de nivel experto y exclusiva de "
            "montañistas con formación avanzada y, generalmente, guía de alta montaña. Registrar "
            "la salida en el centro de informes de Parques Nacionales antes de cada excursión es "
            "una práctica recomendada por los guardaparques locales.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El acceso libre y gratuito a los senderos convive con un compromiso fuerte de "
            "«no dejar rastro»: llevarse toda la basura, usar exclusivamente las zonas de camping "
            "agreste habilitadas y evitar cualquier fuego fuera de las áreas designadas son "
            "normas centrales en un parque que recibe cada temporada un número creciente de "
            "visitantes.</p>"
        ),
        latitud=-49.3308,
        longitud=-72.8867,
        seo_titulo="El Chaltén y Fitz Roy: guía de trekking en la Patagonia",
        seo_descripcion=(
            "Senderos gratuitos hacia el Fitz Roy y el Cerro Torre: guía de trekking y clima en "
            "El Chaltén, capital argentina del trekking."
        ),
        relacionados_slugs=["torres-del-paine", "salar-de-uyuni", "camino-inca-machu-picchu"],
    ),
    DestinoSemilla(
        n=7,
        titulo="Camino Inca a Machu Picchu",
        slug="camino-inca-machu-picchu",
        pais_slug="peru",
        resumen=(
            "La ruta de piedra original de los incas hasta Machu Picchu, cruzando pasos "
            "andinos y ruinas intermedias hasta llegar por la Puerta del Sol."
        ),
        descripcion_experta=(
            "<p>El Camino Inca clásico es un tramo de cuatro días de la extensa red vial que el "
            "imperio inca construyó por los Andes, y culmina de una forma que ningún otro acceso "
            "a Machu Picchu ofrece: llegando a pie por la Puerta del Sol (Inti Punku), el mismo "
            "punto desde el que, según la tradición, los incas veían amanecer sobre la ciudadela "
            "en fechas rituales concretas. La ruta combina tramos de escalinatas de piedra "
            "original, varios sitios arqueológicos intermedios —Wiñay Wayna es uno de los más "
            "citados— y paisajes que van de la puna andina fría a la selva nubosa subtropical en "
            "un mismo recorrido.</p> "
            "<p>El paso de Warmiwañusca, conocido como «paso de la mujer muerta», es el punto más "
            "alto de la ruta y también su tramo más exigente físicamente, con un ascenso "
            "sostenido hasta una altitud considerable seguido de un descenso igualmente "
            "prolongado. La combinación de altitud, escalinatas de piedra irregular y varios "
            "días consecutivos de esfuerzo hace que la preparación física y una aclimatación "
            "previa en Cusco u otra ciudad andina de altitud similar sean recomendaciones "
            "constantes de los operadores y guías locales.</p> "
            "<p>El acceso al Camino Inca está estrictamente regulado por el gobierno peruano: "
            "existe un número máximo de permisos diarios, que incluyen tanto a los visitantes "
            "como al personal de apoyo (porteadores y cocineros), y la ruta solo puede recorrerse "
            "con una agencia autorizada. Esta regulación, que obliga a reservar con bastante "
            "antelación —los permisos suelen agotarse con meses de anticipación en temporada "
            "alta—, busca proteger tanto el patrimonio arqueológico como el ecosistema andino "
            "que atraviesa la ruta.</p> "
            "<p>Los porteadores, en su mayoría de comunidades quechuas de la región, cargan el "
            "equipo de campamento del grupo y son una parte esencial de la logística y también de "
            "la economía local del trekking; en los últimos años se han reforzado las normas "
            "sobre el peso máximo que puede cargar cada porteador y sus condiciones laborales, y "
            "elegir agencias que cumplen estas normas es una forma directa de viajar de manera "
            "más responsable.</p> "
            "<p>Para quien no consigue permiso para el Camino Inca clásico o prefiere una ruta "
            "alternativa, existen otros senderos andinos hacia la misma zona con menor "
            "regulación, aunque ninguno reproduce la experiencia de entrar a la ciudadela "
            "caminando por la Puerta del Sol al amanecer, que sigue siendo el sello distintivo de "
            "esta ruta frente a llegar en tren o autobús desde el valle.</p> "
            "<p>Machu Picchu en sí —una ciudadela inca del siglo XV construida en una cresta "
            "entre montañas, sobre el valle del río Urubamba— es uno de los sitios arqueológicos "
            "mejor conservados de América y Patrimonio de la Humanidad; completar el Camino Inca "
            "y llegar caminando ofrece una perspectiva del lugar dentro de su contexto geográfico "
            "e histórico que resulta muy distinta de llegar directamente en transporte desde el "
            "pueblo de Aguas Calientes.</p> "
            "<p>Machu Picchu permaneció desconocido para el mundo académico occidental hasta 1911, "
            "cuando el explorador estadounidense Hiram Bingham llegó al sitio guiado por "
            "campesinos locales que ya conocían su existencia; ese origen ha alimentado un debate "
            "histórico sobre la diferencia entre «descubrir» un lugar para la ciencia occidental y "
            "el conocimiento que las comunidades locales habían mantenido durante generaciones. El "
            "propio trazado del Camino Inca forma parte de una red vial incaica mucho más extensa, "
            "el "
            "Qhapaq Ñan, que llegó a conectar buena parte del imperio a lo largo de varios miles "
            "de kilómetros de los Andes.</p> "
            "<p>La red vial incaica que incluye el Camino Inca clásico formaba parte de un sistema "
            "de "
            "comunicaciones y control territorial que permitía a mensajeros especializados, los "
            "chasquis, transportar información a gran velocidad entre distintos puntos del imperio "
            "mediante un sistema de relevos; ese mismo trazado, pensado originalmente para la "
            "administración y la defensa del territorio inca, es el que hoy recorren los "
            "senderistas "
            "de todo el mundo camino a Machu Picchu.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dificultad=4,
        meses_mejor_epoca=[5, 6, 7, 8, 9],
        duracion_min_dias=4,
        duracion_max_dias=4,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima andino de montaña con una temporada seca marcada (aproximadamente "
            "mayo-septiembre), la más recomendada para la ruta, y una temporada de lluvias el "
            "resto del año; el camino cierra por mantenimiento durante febrero, dentro de la "
            "temporada húmeda, según determina cada año la autoridad peruana del parque.</p>"
        ),
        altitud_max_m=4215,
        como_llegar=(
            "<p>El punto de partida se organiza desde Cusco, ciudad con aeropuerto y buena "
            "conexión terrestre con el resto de Perú, desde donde las agencias autorizadas "
            "trasladan a los grupos hasta el kilómetro 82 de la vía férrea, inicio del Camino "
            "Inca. El regreso desde Machu Picchu hacia Cusco se hace habitualmente en tren desde "
            "el pueblo de Aguas Calientes.</p>"
        ),
        seguridad_riesgos=(
            "<p>El mal de altura, agravado por el paso de Warmiwañusca a más de 4.000 metros, es "
            "el riesgo principal de la ruta, junto con las torceduras en las escalinatas de "
            "piedra irregular y la exposición a lluvia fría fuera de temporada seca. La ruta solo "
            "se recorre con agencias autorizadas y guías certificados, que llevan equipo de "
            "primeros auxilios y conocen los protocolos de evacuación de cada tramo.</p>"
            + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El sistema de permisos diarios limita el número de personas en la ruta para "
            "proteger el patrimonio arqueológico y el ecosistema andino; elegir agencias que "
            "cumplen las normas de peso máximo y condiciones laborales de los porteadores "
            "quechuas es una forma directa de que el turismo beneficie a las comunidades locales "
            "de la región del Cusco.</p>"
        ),
        latitud=-13.1547,
        longitud=-72.5250,
        seo_titulo="Camino Inca a Machu Picchu: guía experta de la ruta clásica",
        seo_descripcion=(
            "Permisos, dificultad, altitud y porteadores: guía experta del Camino Inca clásico "
            "de cuatro días hasta Machu Picchu, Perú."
        ),
        relacionados_slugs=["torres-del-paine", "el-chalten-fitz-roy", "salar-de-uyuni"],
    ),
    DestinoSemilla(
        n=8,
        titulo="Salar de Uyuni",
        slug="salar-de-uyuni",
        pais_slug="bolivia",
        resumen=(
            "El desierto de sal más grande del mundo, un espejo blanco que se funde con el "
            "cielo del altiplano boliviano."
        ),
        descripcion_experta=(
            "<p>El Salar de Uyuni, en el altiplano boliviano, es la mayor extensión de sal "
            "continua del planeta, formada por la evaporación sucesiva de antiguos lagos "
            "prehistóricos que cubrían buena parte de esta región andina. Su superficie, "
            "prácticamente plana a lo largo de decenas de kilómetros, se cubre de una fina lámina "
            "de agua durante la temporada de lluvias y produce entonces el efecto espejo por el "
            "que el lugar se ha hecho célebre en la fotografía de viajes: el cielo y las nubes se "
            "reflejan con tal nitidez sobre el agua que resulta difícil distinguir dónde termina "
            "el suelo y empieza el horizonte.</p> "
            "<p>Fuera de la temporada de lluvias, el salar se seca y expone su característico "
            "patrón de polígonos de sal cristalizada, una textura muy distinta pero igualmente "
            "reconocible, que permite el acceso en vehículo a zonas más alejadas del salar, "
            "incluidas islas rocosas cubiertas de cactus gigantes que emergen como formaciones "
            "aisladas en medio de la blancura. La elección de la temporada —espejo de agua o "
            "suelo seco de polígonos— cambia por completo el carácter de la visita, y muchos "
            "operadores recomiendan planificar el viaje en función de qué efecto se busca.</p> "
            "<p>Las travesías por el salar se organizan casi siempre en vehículo 4x4 con "
            "conductor y guía local, y combinan la visita al propio salar con otros paisajes del "
            "altiplano suroeste boliviano: lagunas de colores por la concentración de minerales y "
            "algas, geysers de altura, y poblaciones de flamencos andinos que se alimentan en "
            "estas lagunas hipersalinas pese a la altitud extrema y el frío de la región. Las "
            "rutas de varios días suelen recorrer varios cientos de kilómetros de altiplano casi "
            "deshabitado antes de llegar a la frontera con Chile o regresar a Uyuni.</p> "
            "<p>La altitud —el salar y buena parte del altiplano circundante están por encima de "
            "los 3.600 metros, y algunos puntos de la ruta superan los 4.800— es el factor de "
            "exigencia física principal de esta travesía, más que el esfuerzo muscular en sí: el "
            "mal de altura puede aparecer incluso viajando en vehículo, y la aclimatación previa "
            "en La Paz, Uyuni o Potosí antes de emprender la ruta es una recomendación constante "
            "de los operadores locales.</p> "
            "<p>La reverberación solar sobre la sal blanca es intensísima, y produce una "
            "combinación peligrosa de quemaduras solares y deslumbramiento que exige protección "
            "reforzada: gafas de sol de categoría alta y protector solar de aplicación frecuente "
            "son indispensables incluso en días nublados, porque la superficie reflectante "
            "multiplica la radiación que llega a la piel y los ojos respecto a un terreno "
            "normal.</p> "
            "<p>El salar es también una fuente relevante de litio, un mineral clave para la "
            "fabricación de baterías, lo que ha generado un debate boliviano sobre cómo "
            "compatibilizar "
            "la explotación de ese recurso con la conservación de un paisaje que sostiene a las "
            "comunidades locales de sal y turismo desde hace generaciones; los operadores "
            "turísticos de la región de Uyuni forman parte activa de esa economía local basada en "
            "el propio salar.</p> "
            "<p>Antes de convertirse en un destino turístico, el Salar de Uyuni fue durante siglos "
            "una fuente de sal extraída de forma artesanal por comunidades locales, una actividad "
            "que "
            "sigue realizándose hoy en pequeña escala en los bordes del salar y que puede "
            "observarse "
            "en algunas de las rutas turísticas de la zona. La superficie del salar, prácticamente "
            "sin desniveles a lo largo de decenas de kilómetros, se ha usado incluso para calibrar "
            "instrumentos de satélites de observación terrestre, dada su planicie extrema y su "
            "reflectividad tan constante y predecible.</p> "
            "<p>La cercanía del Salar de Uyuni con la frontera chilena permite a algunos "
            "operadores organizar la travesía como un cruce de varios días entre Bolivia y el "
            "desierto de Atacama, uniendo dos de los paisajes de altiplano más extremos de "
            "Suramérica en un solo "
            "itinerario; esa ruta, aunque más exigente logísticamente, se ha convertido en una "
            "opción "
            "habitual para quien dispone de tiempo suficiente para combinar ambos países en un "
            "mismo "
            "viaje por el altiplano andino.</p>"
        ),
        tipos_slugs=["travesias-por-desierto-y-expediciones"],
        dificultad=3,
        meses_mejor_epoca=[5, 6, 7, 8, 9],
        duracion_min_dias=1,
        duracion_max_dias=4,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima de altiplano árido y frío, con una temporada de lluvias entre diciembre y "
            "marzo (cuando aparece el efecto espejo sobre el agua) y una temporada seca el resto "
            "del año, con noches muy frías por la altitud incluso cuando los días son soleados.</p>"
        ),
        altitud_max_m=4800,
        como_llegar=(
            "<p>El acceso habitual es por vuelo o por carretera hasta la ciudad de Uyuni, punto "
            "de partida de la práctica totalidad de las travesías organizadas en vehículo 4x4 por "
            "el salar y el altiplano suroeste boliviano. También es posible llegar por carretera "
            "desde Potosí o La Paz, con trayectos largos por altiplano.</p>"
        ),
        seguridad_riesgos=(
            "<p>El mal de altura por la elevada cota del altiplano, la reverberación solar "
            "intensa sobre la sal y las bajas temperaturas nocturnas son los riesgos principales "
            "de esta travesía. Viajar siempre con operadores locales de trayectoria conocida, con "
            "vehículos revisados y comunicación de emergencia, es especialmente importante dada "
            "la lejanía y el aislamiento de buena parte de la ruta por el altiplano.</p>"
            + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Elegir operadores locales de la región de Uyuni sostiene directamente la economía "
            "de las comunidades que dependen del salar; llevarse toda la basura generada durante "
            "la travesía y respetar las zonas de extracción artesanal de sal y las poblaciones de "
            "flamencos andinos de las lagunas cercanas son normas básicas de una visita "
            "responsable a este ecosistema de altiplano.</p>"
        ),
        latitud=-20.1338,
        longitud=-67.4891,
        seo_titulo="Salar de Uyuni: guía de la travesía por el desierto de sal",
        seo_descripcion=(
            "Efecto espejo, altitud y travesía en 4x4: guía experta para visitar el Salar de "
            "Uyuni, el desierto de sal más grande del mundo, en Bolivia."
        ),
        relacionados_slugs=["torres-del-paine", "wadi-rum", "camino-inca-machu-picchu"],
    ),
    DestinoSemilla(
        n=9,
        titulo="Islas Galápagos",
        slug="islas-galapagos",
        pais_slug="ecuador",
        resumen=(
            "El archipiélago que inspiró a Darwin: fauna endémica sin temor al ser humano, "
            "buceo con tiburones y tortugas gigantes."
        ),
        descripcion_experta=(
            "<p>Las Islas Galápagos, un archipiélago volcánico a unos mil kilómetros de la costa "
            "de Ecuador, deben su fama científica al viaje que Charles Darwin realizó por ellas "
            "en 1835, cuya observación de la variación entre especies de pinzones e iguanas de "
            "distintas islas influyó de forma decisiva en el desarrollo posterior de la teoría de "
            "la evolución. Hoy el archipiélago sigue siendo uno de los laboratorios naturales "
            "más singulares del planeta: su aislamiento geográfico y la ausencia histórica de "
            "depredadores terrestres han producido una fauna endémica que, en muchos casos, "
            "apenas muestra temor ante la presencia humana.</p> "
            "<p>La confluencia de varias corrientes oceánicas —la fría corriente de Humboldt "
            "entre ellas— frente a un archipiélago situado prácticamente sobre el ecuador "
            "geográfico genera una mezcla inusual de especies de aguas frías y tropicales en un "
            "mismo entorno, lo que explica por qué en Galápagos conviven pingüinos (los únicos "
            "que habitan de forma natural al norte del ecuador) con tiburones martillo, tortugas "
            "marinas, mantarrayas y una biodiversidad marina que ha convertido a las islas en uno "
            "de los destinos de buceo y snorkel más reconocidos del mundo.</p> "
            "<p>El acceso al archipiélago está estrictamente regulado por el Parque Nacional "
            "Galápagos: la práctica totalidad de las visitas se realizan con guías naturalistas "
            "certificados, siguiendo senderos e itinerarios de navegación fijados de antemano, "
            "con el objetivo de minimizar el impacto humano sobre un ecosistema declarado "
            "Patrimonio de la Humanidad. Los visitantes suelen recorrer las islas en cruceros de "
            "varios días o en excursiones diarias desde alguna de las islas pobladas, combinando "
            "caminatas cortas por senderos volcánicos con salidas de esnórquel o buceo.</p> "
            "<p>La isla de San Cristóbal, una de las pobladas del archipiélago, cuenta además con "
            "olas de calidad suficiente para el surf, una faceta menos conocida de Galápagos "
            "frente a su fama como destino de naturaleza y buceo, pero real y practicada tanto "
            "por visitantes como por surfistas locales en determinados puntos de la costa de la "
            "isla.</p> "
            "<p>El buceo en Galápagos, particularmente en los puntos más alejados del "
            "archipiélago, puede implicar corrientes fuertes y aguas relativamente frías por la "
            "influencia de la corriente de Humboldt, lo que lo sitúa en un nivel de exigencia "
            "superior al de un arrecife tropical tranquilo y lo hace más adecuado para "
            "buceadores con cierta experiencia previa en condiciones de corriente y visibilidad "
            "variable.</p> "
            "<p>La conservación es, más que en casi cualquier otro destino de este listado, el eje "
            "que estructura toda visita a Galápagos: el número de visitantes, los sitios de "
            "desembarco y los operadores autorizados están sujetos a un control estricto por "
            "parte de las autoridades ecuatorianas, con el objetivo declarado de proteger un "
            "ecosistema único que sigue siendo, más de un siglo y medio después de la visita de "
            "Darwin, un referente mundial de la biología evolutiva.</p> "
            "<p>Cada isla del archipiélago tiene, además, su propio carácter: la isla Isabela, la "
            "mayor de todas, concentra varios volcanes activos y una fauna distinta a la de las "
            "islas "
            "orientales más antiguas geológicamente, mientras que la isla Española, en el extremo "
            "sur, alberga colonias de albatros que no anidan en ningún otro lugar del planeta. Esa "
            "combinación de historia evolutiva única y geografía volcánica activa explica por qué "
            "Galápagos sigue siendo, más de siglo y medio después del viaje de Darwin, un destino "
            "de "
            "referencia obligada tanto para la ciencia como para el ecoturismo.</p> "
            "<p>El Parque Nacional Galápagos, creado en 1959, fue uno de los primeros grandes "
            "parques "
            "nacionales de Suramérica, y la estación científica Charles Darwin, fundada poco "
            "después "
            "en la isla de Santa Cruz, sigue siendo hoy un centro de referencia mundial para la "
            "investigación de especies endémicas y los programas de recuperación de tortugas "
            "gigantes, cuya población se redujo drásticamente en los siglos de caza histórica "
            "anteriores a la protección del archipiélago.</p>"
        ),
        tipos_slugs=["buceo-y-snorkel", "safari-y-observacion-de-fauna", "surf"],
        dificultad=2,
        meses_mejor_epoca=[6, 7, 8, 9, 12, 1],
        duracion_min_dias=4,
        duracion_max_dias=8,
        nivel_presupuesto=4,
        clima=(
            "<p>Clima ecuatorial marino con dos estaciones marcadas por la corriente oceánica "
            "dominante: una más cálida y húmeda (diciembre-mayo, aguas más cálidas y mejor "
            "visibilidad de buceo) y otra más fresca y seca (junio-noviembre, aguas más frías y "
            "mayor actividad de fauna marina por el afloramiento de nutrientes).</p>"
        ),
        altitud_max_m=1700,
        como_llegar=(
            "<p>El acceso es en vuelo doméstico desde Quito o Guayaquil hasta los aeropuertos de "
            "Baltra o San Cristóbal, en el archipiélago; desde allí, los traslados a cada isla o "
            "embarcación se organizan con las agencias autorizadas, y el ingreso al Parque "
            "Nacional Galápagos requiere el pago de una tarifa de conservación regulada por las "
            "autoridades ecuatorianas.</p>"
        ),
        seguridad_riesgos=(
            "<p>Las corrientes marinas, a veces fuertes en los puntos de buceo más alejados, y la "
            "exposición solar intensa sobre el agua son los riesgos principales; la práctica "
            "totalidad de las actividades se realizan con guías naturalistas y operadores de "
            "buceo certificados por el Parque Nacional, cuyas indicaciones sobre corrientes y "
            "puntos de inmersión deben seguirse siempre.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El sistema de guías obligatorios, senderos fijos y sitios de visita regulados "
            "busca minimizar el impacto sobre una fauna endémica muy sensible a la alteración de "
            "su comportamiento natural; no tocar ni alimentar a los animales, mantener siempre la "
            "distancia indicada por el guía y usar protector solar apto para arrecifes son normas "
            "centrales de cualquier visita a Galápagos.</p>"
        ),
        latitud=-0.7393,
        longitud=-90.3157,
        seo_titulo="Islas Galápagos: guía experta de buceo y fauna endémica",
        seo_descripcion=(
            "Buceo, fauna endémica y surf en San Cristóbal: guía experta para visitar las Islas "
            "Galápagos, Ecuador, de forma responsable."
        ),
        relacionados_slugs=["gran-barrera-de-coral", "cenotes-de-yucatan", "delta-del-okavango"],
    ),
    DestinoSemilla(
        n=10,
        titulo="Volcán Arenal y Monteverde",
        slug="arenal-y-monteverde",
        pais_slug="costa-rica",
        resumen=(
            "Un volcán cónico rodeado de aguas termales y, a poca distancia, el bosque nuboso "
            "de Monteverde suspendido entre puentes colgantes."
        ),
        descripcion_experta=(
            "<p>El Volcán Arenal, con su silueta cónica casi perfecta, fue durante varias "
            "décadas del siglo XX uno de los volcanes más activos de Centroamérica, con "
            "erupciones frecuentes visibles desde la localidad de La Fortuna hasta que entró en "
            "una fase de reposo eruptivo a comienzos del siglo XXI. Aunque hoy no se observa "
            "actividad eruptiva, el volcán sigue siendo monitoreado y su entorno conserva un "
            "paisaje de coladas de lava antiguas cubiertas de vegetación tropical, además de las "
            "aguas termales de origen volcánico que han convertido la zona en un destino de "
            "descanso además de aventura.</p> "
            "<p>A poca distancia por carretera de montaña, el bosque nuboso de Monteverde ofrece "
            "un ecosistema radicalmente distinto: una franja de bosque permanentemente envuelta "
            "en niebla por la condensación de la humedad que sube desde ambas vertientes de la "
            "cordillera, con una biodiversidad de orquídeas, helechos gigantes y aves como el "
            "quetzal resplandeciente, una de las especies más buscadas por observadores de aves "
            "de todo el mundo. Los puentes colgantes suspendidos sobre el dosel del bosque "
            "permiten observar este ecosistema desde una perspectiva que rara vez se consigue a "
            "pie de suelo.</p> "
            "<p>Costa Rica ha construido buena parte de su identidad turística en torno a esta "
            "combinación de volcanes activos o en reposo, bosque nuboso y una política de "
            "conservación ambiental que destina una proporción considerable de su territorio a "
            "parques nacionales y reservas protegidas; Arenal y Monteverde son, junto con el "
            "Parque Nacional Manuel Antonio en la costa, de los destinos más representativos de "
            "esa apuesta por el llamado turismo de naturaleza.</p> "
            "<p>Las actividades en la zona de Arenal incluyen senderismo por antiguas coladas de "
            "lava y miradores del volcán, así como el baño en aguas termales de origen "
            "geotérmico; en Monteverde, la observación de fauna y aves con guías especializados "
            "es la actividad central, complementada con los recorridos por puentes colgantes y "
            "plataformas suspendidas entre los árboles del dosel.</p> "
            "<p>La humedad constante del bosque nuboso y el terreno con frecuencia embarrado de "
            "los senderos de montaña exigen calzado de buen agarre y ropa de secado rápido, más "
            "que una condición física excepcional: la mayoría de rutas de la zona son accesibles "
            "para un rango amplio de visitantes, con recorridos cortos y bien señalizados tanto "
            "en Arenal como en Monteverde.</p> "
            "<p>El clima de la vertiente donde se sitúa Monteverde, expuesta de forma directa a "
            "los vientos húmedos del Caribe que chocan contra la cordillera, produce niebla y "
            "llovizna de forma prácticamente constante durante buena parte del año, un rasgo que "
            "define tanto el nombre del bosque como la experiencia de visitarlo, y que conviene "
            "anticipar llevando siempre una capa impermeable a mano, incluso en días que "
            "amanecen despejados.</p> "
            "<p>Costa Rica abolió su ejército en 1948 y destinó buena parte de los recursos "
            "liberados "
            "a educación y, con el tiempo, a un modelo de desarrollo que sitúa la conservación "
            "ambiental como eje de su economía turística; Monteverde, protegida desde la década de "
            "1970 gracias en buena medida al impulso de una comunidad cuáquera instalada en la "
            "zona, "
            "es uno de los ejemplos más citados de ese modelo. El volcán Arenal, por su parte, "
            "sigue "
            "siendo objeto de estudio geológico constante pese a su fase de reposo eruptivo "
            "actual, como recordatorio de que buena parte de Costa Rica se asienta sobre un "
            "territorio volcánicamente activo del Cinturón de Fuego del Pacífico.</p> "
            "<p>La técnica de observación en Monteverde se apoya a menudo en guías locales con "
            "años de experiencia identificando cantos de aves y rastros de fauna que resultan "
            "prácticamente imperceptibles para un visitante sin formación; el quetzal "
            "resplandeciente, ave sagrada para varias culturas mesoamericanas precolombinas por su "
            "plumaje verde iridiscente y su cola extremadamente larga, sigue siendo el objetivo "
            "más buscado por observadores de aves de todo el mundo que visitan este bosque "
            "nuboso.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dificultad=2,
        meses_mejor_epoca=[12, 1, 2, 3],
        duracion_min_dias=2,
        duracion_max_dias=4,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima tropical con estación seca (aproximadamente diciembre-abril, la más "
            "recomendada) y una estación lluviosa más larga el resto del año; el bosque nuboso de "
            "Monteverde mantiene niebla y humedad elevada de forma casi constante por su "
            "exposición a los vientos húmedos del Caribe, incluso en la estación seca.</p>"
        ),
        altitud_max_m=1842,
        como_llegar=(
            "<p>El acceso habitual es por carretera desde San José, la capital costarricense, "
            "hasta La Fortuna (base del volcán Arenal) y, por una carretera de montaña más lenta, "
            "hasta Monteverde; también existen vuelos domésticos cortos y traslados combinados en "
            "bote y autobús entre ambas zonas que reducen el tiempo de trayecto por carretera.</p>"
        ),
        seguridad_riesgos=(
            "<p>El terreno embarrado y resbaladizo del bosque nuboso, la humedad constante y la "
            "posibilidad de tormentas eléctricas en zonas expuestas son los riesgos principales "
            "de la región; aunque el volcán Arenal no presenta actividad eruptiva en la "
            "actualidad, el acceso a las zonas más cercanas al cráter sigue restringido por las "
            "autoridades del parque como medida de precaución.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Monteverde es, en buena parte, resultado de un esfuerzo de conservación "
            "comunitaria sostenido durante décadas: mantenerse en los senderos y puentes "
            "habilitados, contratar guías locales certificados y evitar cualquier alimentación de "
            "fauna silvestre son normas centrales para no alterar un ecosistema de una fragilidad "
            "comparable a la de otros bosques nubosos tropicales del mundo.</p>"
        ),
        latitud=10.4627,
        longitud=-84.7033,
        seo_titulo="Arenal y Monteverde: guía de volcán y bosque nuboso",
        seo_descripcion=(
            "Volcán Arenal, bosque nuboso y puentes colgantes de Monteverde: guía experta de "
            "naturaleza y senderismo en Costa Rica."
        ),
        relacionados_slugs=["cenotes-de-yucatan", "islas-galapagos", "delta-del-okavango"],
    ),
    DestinoSemilla(
        n=11,
        titulo="Cenotes de la Península de Yucatán",
        slug="cenotes-de-yucatan",
        pais_slug="mexico",
        resumen=(
            "Miles de pozos de agua dulce cristalina esculpidos en roca caliza, sagrados para "
            "los mayas y hoy uno de los mejores destinos de buceo en cuevas del mundo."
        ),
        descripcion_experta=(
            "<p>La península de Yucatán, en el sureste de México, se asienta sobre una enorme "
            "plataforma de roca caliza kárstica que, con el tiempo, ha desarrollado uno de los "
            "sistemas de cuevas inundadas más extensos del planeta. Cuando el techo de una de "
            "estas cavidades colapsa y queda expuesta al exterior, se forma un cenote: un pozo "
            "natural de agua dulce, a menudo de una transparencia excepcional, que puede estar "
            "completamente abierto al cielo, parcialmente cubierto o ser una cueva casi por "
            "completo, según el grado de colapso de la roca sobre el agua.</p> "
            "<p>Para la civilización maya, que habitó y sigue habitando esta región, los cenotes "
            "tenían un valor que iba mucho más allá del práctico: eran la principal fuente de "
            "agua dulce en una zona sin ríos superficiales significativos, y a la vez lugares "
            "sagrados asociados al inframundo y a rituales que en algunos casos incluían "
            "ofrendas arqueológicas, encontradas por buceadores e investigadores en varios "
            "cenotes de la región a lo largo de las últimas décadas.</p> "
            "<p>La experiencia de visitar un cenote varía enormemente según cuál se elija: "
            "algunos son grandes pozos abiertos aptos para el baño y el esnórquel sin ninguna "
            "formación técnica, con rayos de luz que atraviesan el agua desde la abertura "
            "superior; otros son sistemas de cuevas semi o totalmente sumergidas que solo pueden "
            "explorarse con equipo de buceo y, en el caso de los tramos más profundos o "
            "laberínticos, con una certificación específica de buceo en cavernas.</p> "
            "<p>El buceo en cenotes se considera, dentro del buceo recreativo, una modalidad de "
            "mayor exigencia técnica que el buceo en arrecife abierto: la ausencia de acceso "
            "vertical directo a la superficie en los tramos de cueva, la necesidad de seguir "
            "siempre un hilo guía y la gestión de la flotabilidad en espacios confinados exigen "
            "formación y experiencia específicas, y los operadores serios de la región exigen "
            "verificar la certificación antes de aceptar a un buceador en los tramos más "
            "técnicos.</p> "
            "<p>La fragilidad de este sistema de acuíferos es considerable: toda la región "
            "depende del mismo sistema kárstico subterráneo para su abastecimiento de agua "
            "dulce, lo que hace que la contaminación por protectores solares químicos, basura o "
            "productos de limpieza en un cenote pueda propagarse por el acuífero mucho más allá "
            "del punto concreto de la visita, un motivo por el que numerosos cenotes exigen hoy "
            "protector solar biodegradable como condición de acceso.</p> "
            "<p>Más allá del propio cenote, la región de Yucatán combina esta oferta de buceo y "
            "espeleología acuática con un patrimonio arqueológico maya de primer nivel —Chichén "
            "Itzá y Uxmal, entre otros sitios— lo que convierte a la península en un destino que "
            "combina con facilidad la aventura acuática con el interés histórico y cultural en un "
            "mismo viaje.</p> "
            "<p>Algunos cenotes de la región han revelado a lo largo de las últimas décadas "
            "hallazgos "
            "arqueológicos y paleontológicos de gran valor científico, desde ofrendas mayas hasta "
            "restos de fauna del Pleistoceno conservados por la ausencia de oxígeno en ciertas "
            "zonas "
            "profundas del sistema de cuevas; estos descubrimientos han convertido la exploración "
            "de "
            "cenotes en una disciplina que combina buceo deportivo e investigación científica. La "
            "red "
            "de cuevas inundadas de Yucatán incluye, además, algunos de los sistemas de cuevas "
            "sumergidas más largos documentados en el mundo, con decenas de kilómetros de galerías "
            "cartografiadas por espeleobuceadores a lo largo de los años.</p> "
            "<p>Algunos operadores de la región combinan la visita a un cenote con recorridos por "
            "ruinas mayas cercanas en una misma jornada, aprovechando que buena parte de los "
            "asentamientos prehispánicos de Yucatán se ubicaron precisamente junto a cenotes por "
            "su papel como única fuente fiable de agua dulce en una región sin ríos superficiales; "
            "esa relación histórica entre agua, asentamiento humano y religión sigue siendo "
            "visible hoy en el trazado de buena parte de las rutas turísticas de la península.</p>"
        ),
        tipos_slugs=["espeleologia-y-cenotes", "buceo-y-snorkel"],
        dificultad=2,
        meses_mejor_epoca=[11, 12, 1, 2, 3, 4],
        duracion_min_dias=2,
        duracion_max_dias=5,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima cálido tropical durante todo el año, con una temporada seca más agradable "
            "(aproximadamente noviembre-abril) y una temporada más húmeda y calurosa el resto del "
            "año; la temperatura del agua de los cenotes se mantiene fresca y estable durante "
            "todo el año por su origen subterráneo.</p>"
        ),
        altitud_max_m=50,
        como_llegar=(
            "<p>El acceso habitual es por vuelo internacional hasta Cancún o Mérida, en la "
            "península de Yucatán, y desde allí por carretera hasta las distintas zonas de "
            "cenotes, muchas de ellas cercanas a poblaciones como Tulum, Valladolid o Puerto "
            "Morelos. La mayoría de cenotes turísticos cuentan con guías o personal local en el "
            "propio sitio.</p>"
        ),
        seguridad_riesgos=(
            "<p>El riesgo principal en los cenotes abiertos es el resbalón en accesos de roca "
            "mojada; en el buceo de cuevas, la desorientación y la pérdida del hilo guía son los "
            "riesgos más serios, por lo que esta modalidad exige siempre certificación específica "
            "de buceo en cavernas y guía local certificado, nunca explorar tramos de cueva sin esa"
            "formación.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Toda la península depende del mismo acuífero subterráneo que alimenta los "
            "cenotes: usar exclusivamente protector solar biodegradable, no dejar ningún residuo "
            "y no tocar las formaciones de roca ni la fauna acuática son normas mínimas para "
            "proteger una fuente de agua dulce de la que dependen tanto los ecosistemas como las "
            "comunidades locales de Yucatán.</p>"
        ),
        latitud=20.2114,
        longitud=-87.4654,
        seo_titulo="Cenotes de Yucatán: guía de buceo y espeleología acuática",
        seo_descripcion=(
            "Buceo en cuevas, cenotes abiertos y respeto al acuífero maya: guía experta de los "
            "cenotes de la península de Yucatán, México."
        ),
        relacionados_slugs=["islas-galapagos", "arenal-y-monteverde", "gran-barrera-de-coral"],
    ),
    DestinoSemilla(
        n=12,
        titulo="Parque Nacional Yosemite",
        slug="yosemite",
        pais_slug="estados-unidos",
        resumen=(
            "Valles glaciares, cascadas y las paredes de granito de El Capitán y Half Dome, "
            "cuna de la escalada moderna en Estados Unidos."
        ),
        descripcion_experta=(
            "<p>El Parque Nacional Yosemite, en la Sierra Nevada de California, es uno de los "
            "parques nacionales más antiguos de Estados Unidos y una referencia histórica del "
            "propio concepto de conservación de espacios naturales, gracias en parte a la "
            "defensa que de él hizo el naturalista John Muir a finales del siglo XIX. El valle "
            "de Yosemite, su zona más visitada, fue esculpido por glaciares que retrocedieron "
            "hace miles de años y dejaron expuestas paredes de granito casi verticales, entre "
            "ellas El Capitán, uno de los monolitos de roca más grandes del mundo, y Half Dome, "
            "una cúpula partida por la mitad que domina el perfil del valle.</p> "
            "<p>El Capitán es, para la escalada mundial, un lugar casi mítico: sus rutas de "
            "varios días por más de 900 metros de roca prácticamente vertical han sido escenario "
            "de algunos de los hitos más comentados de la historia del montañismo, y siguen "
            "atrayendo cada temporada a escaladores de elite de todo el mundo. Junto a la "
            "escalada de varios días en pared grande, Yosemite ofrece también escalada deportiva "
            "de un solo largo y bulder en cantos rodados repartidos por todo el valle, lo que ha "
            "convertido al parque en una escuela histórica para generaciones de escaladores "
            "estadounidenses.</p> "
            "<p>Para quien no practica escalada técnica, Yosemite ofrece una red de senderos de "
            "senderismo extraordinariamente variada: desde paseos cortos y accesibles hasta la "
            "base de las cascadas del valle (algunas de las más altas de Norteamérica) hasta "
            "rutas de un día completo con desnivel considerable, como la ascensión a la cima de "
            "Half Dome, que en su tramo final exige progresar agarrado a unos cables de acero "
            "fijos sobre roca muy inclinada, y que requiere un permiso especial limitado por "
            "sorteo debido a la afluencia de solicitantes.</p> "
            "<p>El parque presenta una marcada variación estacional: los meses de primavera, con "
            "el deshielo de la Sierra Nevada, ofrecen el caudal más espectacular en las cascadas "
            "del valle, mientras que en verano ese caudal disminuye de forma notable y algunas "
            "cascadas menores pueden llegar a secarse por completo. El acceso a las zonas de alta "
            "montaña del parque, por encima de los pasos de Tioga, suele estar cerrado por nieve "
            "buena parte del otoño, el invierno y comienzos de la primavera.</p> "
            "<p>La gestión de la afluencia de visitantes es uno de los grandes retos operativos "
            "del parque en la actualidad: Yosemite recibe varios millones de visitas al año, "
            "concentradas en gran medida en el valle principal durante los meses de verano, lo "
            "que ha llevado a implementar sistemas de reserva de entrada y permisos limitados "
            "para determinadas rutas y actividades en las temporadas de mayor demanda.</p> "
            "<p>Más allá del valle principal, Yosemite protege también extensos bosques de "
            "secuoyas gigantes, entre los árboles más grandes del planeta por volumen de madera, "
            "y una alta montaña de granito y lagos alpinos que se extiende mucho más allá de lo "
            "que ve la mayoría de visitantes que se limitan a recorrer el valle en un día.</p> "
            "<p>El propio John Muir, cuyos escritos sobre Yosemite influyeron directamente en la "
            "creación del sistema de parques nacionales estadounidense y en la fundación del "
            "Sierra Club, describió el valle como un templo natural; esa herencia conservacionista "
            "sigue presente en la gestión actual del parque, que combina la protección estricta de "
            "sus ecosistemas con una de las mayores afluencias de visitantes de cualquier parque "
            "nacional "
            "de Estados Unidos. Las secuoyas gigantes del parque, algunas con más de dos mil años "
            "de "
            "antigüedad, son testigos vivos de una escala temporal muy distinta a la de la propia "
            "historia humana de la región.</p> "
            "<p>El valle de Yosemite fue, mucho antes de convertirse en parque nacional, "
            "territorio habitado durante generaciones por el pueblo ahwahneechee, cuyo nombre para "
            "el valle—Ahwahnee, «lugar de la boca abierta»— precede en siglos a la denominación "
            "actual del parque; el reconocimiento de esa historia indígena, silenciada durante "
            "buena parte del siglo XX en la narrativa oficial del parque, forma hoy parte de los "
            "programas educativos "
            "del propio Servicio de Parques Nacionales estadounidense.</p>"
        ),
        tipos_slugs=["escalada-y-via-ferrata", "senderismo-y-trekking"],
        dificultad=3,
        meses_mejor_epoca=[5, 6, 9, 10],
        duracion_min_dias=2,
        duracion_max_dias=5,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima de montaña mediterránea de Sierra Nevada: veranos secos y cálidos en el "
            "valle (con nieve conservada en la alta montaña), inviernos fríos con nieve "
            "abundante que cierra buena parte de las carreteras de alta montaña, y una primavera "
            "con el mejor caudal de cascadas por el deshielo.</p>"
        ),
        altitud_max_m=3997,
        como_llegar=(
            "<p>El acceso habitual es en vehículo de alquiler desde San Francisco o Sacramento, "
            "en California, por carretera hasta alguna de las entradas del parque; en temporada "
            "alta el parque limita el número de vehículos con un sistema de reserva de entrada, y "
            "conviene consultarlo con antelación antes de planificar la fecha del viaje.</p>"
        ),
        seguridad_riesgos=(
            "<p>Las caídas en miradores y bordes de cascada sin protección, el agua fría y rápida "
            "en la base de las cascadas durante el deshielo, y la exposición en el tramo de "
            "cables de Half Dome son los riesgos más citados por el servicio de guardaparques del "
            "parque; respetar siempre el cierre de rutas por nieve o por riesgo de incendio "
            "forestal, habitual en verano en Sierra Nevada, es igualmente importante.</p>"
            + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El sistema de reserva de entrada y de permisos limitados para rutas como Half "
            "Dome busca proteger un parque que recibe varios millones de visitas al año; "
            "mantenerse en los senderos marcados, guardar correctamente la comida ante la "
            "presencia de osos negros en el parque y llevarse toda la basura son normas centrales "
            "de una visita responsable a Yosemite.</p>"
        ),
        latitud=37.8651,
        longitud=-119.5383,
        seo_titulo="Yosemite: guía de escalada y senderismo en Sierra Nevada",
        seo_descripcion=(
            "El Capitán, Half Dome y las cascadas del valle: guía experta de escalada y "
            "senderismo en el Parque Nacional Yosemite, Estados Unidos."
        ),
        relacionados_slugs=["banff", "dolomitas", "queenstown"],
    ),
    DestinoSemilla(
        n=13,
        titulo="Parque Nacional Banff",
        slug="banff",
        pais_slug="canada",
        resumen=(
            "El primer parque nacional de Canadá: lagos glaciares de turquesa intenso entre las "
            "Rocosas canadienses, ideales para el senderismo y el piragüismo."
        ),
        descripcion_experta=(
            "<p>El Parque Nacional Banff, fundado en 1885 en torno a unas fuentes termales de "
            "las Montañas Rocosas canadienses, fue el primer parque nacional de Canadá y sigue "
            "siendo uno de los más visitados del país, en gran parte por la combinación de "
            "picos nevados, glaciares y lagos de un turquesa muy intenso, un color producido por "
            "la harina de roca —sedimento finísimo generado por la erosión glaciar— en "
            "suspensión en el agua, que dispersa la luz de una forma muy particular. El lago "
            "Louise y el lago Moraine, ambos dentro del parque, son de los ejemplos más "
            "fotografiados de este fenómeno en todo el mundo.</p> "
            "<p>La red de senderos de Banff recorre valles glaciares, bosques de coníferas y "
            "praderas de alta montaña, con rutas que van desde paseos cortos junto a los lagos "
            "principales hasta travesías de varios días hacia glaciares y picos más remotos del "
            "parque. La fauna de las Rocosas —osos negros y grizzly, alces, cabras montesas— es "
            "parte habitual del paisaje, lo que exige a quien camina por el parque conocer y "
            "aplicar los protocolos de convivencia con osos, incluida la práctica de hacer ruido "
            "regular al caminar y llevar siempre spray de defensa contra osos en las rutas más "
            "alejadas de los núcleos turísticos.</p> "
            "<p>El piragüismo y el kayak en los lagos glaciares del parque, en especial en el lago "
            "Louise y el lago Moraine, es una de las actividades más asociadas a Banff: remar "
            "sobre estas aguas de un turquesa casi irreal, rodeado de paredes de roca y glaciares "
            "colgados, es una experiencia que no exige ninguna formación técnica previa más allá "
            "de las nociones básicas de manejo de la embarcación, aunque el agua, de origen "
            "glaciar, se mantiene fría durante todo el año.</p> "
            "<p>El parque forma parte de un sistema más amplio de parques de las Rocosas "
            "canadienses que incluye también Jasper, Yoho y Kootenay, conectados por una de las "
            "carreteras panorámicas más reconocidas del mundo, la Icefields Parkway, que discurre "
            "junto a glaciares, cascadas y miradores de alta montaña entre Banff y Jasper.</p> "
            "<p>La temporada condiciona de forma drástica la experiencia en Banff: el verano "
            "(junio a septiembre) concentra la mayor accesibilidad de senderos de alta montaña y "
            "la mejor temporada para el piragüismo, mientras que el invierno transforma el "
            "parque en un destino de esquí y de paisajes helados, con buena parte de los senderos "
            "de alta montaña cerrados o solo accesibles con equipo de nieve específico.</p> "
            "<p>La gestión de la fauna salvaje y la afluencia turística son los dos grandes retos "
            "de conservación del parque: el crecimiento sostenido de visitantes en las últimas "
            "décadas ha llevado a reforzar los sistemas de transporte compartido hacia los lagos "
            "más populares en temporada alta, precisamente para reducir la presión de "
            "aparcamiento y tráfico sobre las zonas más frágiles del entorno de los lagos.</p> "
            "<p>El descubrimiento de aguas termales por parte de trabajadores del ferrocarril "
            "canadiense en la década de 1880 fue el origen directo de la creación del parque, "
            "cuando "
            "el gobierno canadiense decidió proteger la zona para evitar su explotación privada "
            "descontrolada; ese mismo ferrocarril transcontinental abrió después la región al "
            "turismo "
            "de montaña que hoy sostiene buena parte de la economía de Banff. El parque forma, "
            "junto "
            "con Jasper, Yoho y Kootenay, un conjunto de áreas protegidas de las Rocosas "
            "canadienses "
            "declarado Patrimonio de la Humanidad por su geología y su biodiversidad de alta "
            "montaña.</p> "
            "<p>El Skywalk de Glacier, una pasarela de cristal suspendida sobre un cañón de la "
            "Icefields Parkway entre Banff y Jasper, se ha convertido en una de las paradas más "
            "populares de la carretera panorámica que conecta ambos parques, con vistas directas "
            "sobre el glaciar Athabasca, uno de los más accesibles y visitados de todo el sistema "
            "de "
            "campos de hielo de las Rocosas canadienses.</p>"
        ),
        tipos_slugs=["kayak-y-navegacion", "senderismo-y-trekking"],
        dificultad=2,
        meses_mejor_epoca=[6, 7, 8, 9],
        duracion_min_dias=3,
        duracion_max_dias=6,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima de montaña subártico continental: veranos cortos y suaves (junio-septiembre, "
            "la temporada más accesible) e inviernos largos y fríos con nieve abundante que "
            "cierra buena parte de los senderos de alta montaña entre otoño y primavera.</p>"
        ),
        altitud_max_m=3618,
        como_llegar=(
            "<p>El acceso habitual es en vuelo hasta Calgary, en la provincia canadiense de "
            "Alberta, y desde allí por carretera hasta el pueblo de Banff, dentro del parque. "
            "Durante la temporada alta de verano existen sistemas de transporte compartido hacia "
            "los lagos más visitados para reducir la presión de tráfico y aparcamiento.</p>"
        ),
        seguridad_riesgos=(
            "<p>Los encuentros con osos son el riesgo más específico del parque: hacer ruido "
            "regular al caminar, viajar en grupo y llevar spray de defensa contra osos en rutas "
            "alejadas son medidas recomendadas por el servicio de parques canadiense; el agua fría "
            "de origen glaciar de los lagos es otro riesgo a considerar en caso de vuelco durante "
            "el piragüismo.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Usar el transporte compartido hacia los lagos más populares en temporada alta, "
            "almacenar correctamente los alimentos para no atraer fauna y mantenerse en los "
            "senderos marcados son prácticas centrales para proteger un parque con una población "
            "activa de osos negros y grizzly y una afluencia de visitantes en aumento.</p>"
        ),
        latitud=51.4968,
        longitud=-115.9281,
        seo_titulo="Parque Nacional Banff: guía de lagos glaciares y senderismo",
        seo_descripcion=(
            "Lagos turquesa, piragüismo y osos: guía experta de senderismo y kayak en el Parque "
            "Nacional Banff, Rocosas canadienses."
        ),
        relacionados_slugs=["yosemite", "chamonix-mont-blanc", "fiordos-de-noruega"],
    ),
    DestinoSemilla(
        n=14,
        titulo="Ruta Laugavegur",
        slug="ruta-laugavegur",
        pais_slug="islandia",
        resumen=(
            "Una travesía de varios días entre montañas de riolita multicolor, campos de lava "
            "y glaciares en las tierras altas de Islandia."
        ),
        descripcion_experta=(
            "<p>La ruta Laugavegur, en las tierras altas del interior de Islandia, conecta la "
            "zona geotérmica de Landmannalaugar con el valle glaciar de Þórsmörk a lo largo de "
            "un recorrido que atraviesa algunos de los paisajes más variados y menos comunes del "
            "senderismo mundial: montañas de riolita con bandas de colores que van del amarillo "
            "azufre al rosa y el verde, extensos campos de lava negra de erupciones "
            "relativamente recientes, glaciares visibles en el horizonte y valles de vegetación "
            "sorprendentemente verde para tratarse de una isla situada justo bajo el círculo "
            "polar ártico.</p> "
            "<p>El origen geotérmico de buena parte del paisaje —Islandia se asienta sobre la "
            "dorsal centroatlántica, el límite entre dos placas tectónicas— se hace evidente en "
            "varios puntos de la ruta, con fumarolas activas, suelo caliente al tacto en algunas "
            "zonas y, en el punto de partida de Landmannalaugar, aguas termales naturales donde "
            "es habitual bañarse antes o después de la travesía. Esa misma actividad geológica "
            "es la que da forma, a lo largo de milenios, a las montañas de riolita multicolor que "
            "dan a la ruta buena parte de su fama fotográfica.</p> "
            "<p>La ruta se recorre habitualmente en cuatro o cinco días, con pernoctación en una "
            "red de refugios de montaña gestionados por la asociación islandesa de senderismo, "
            "que requieren reserva con bastante antelación en la temporada de verano, la única en "
            "que la ruta es transitable de forma segura sin equipo de expedición invernal. Fuera "
            "de esa ventana estival, corta incluso para los estándares de otras zonas de alta "
            "montaña, las condiciones de nieve, hielo y ríos crecidos hacen la travesía "
            "extremadamente peligrosa para quien no cuente con experiencia de montaña "
            "invernal.</p> <p>Uno de los rasgos más particulares de la ruta es el cruce de varios "
            "ríos glaciares a pie, sin puente, con el agua helada procedente directamente del "
            "deshielo y un caudal que puede variar de un día a otro según la temperatura y las "
            "lluvias recientes; los senderistas suelen quitarse las botas y cruzar con calzado "
            "específico o descalzos, evaluando siempre la profundidad y la fuerza de la corriente "
            "antes de avanzar.</p> "
            "<p>El clima islandés, notoriamente cambiante incluso en pleno verano, puede alternar "
            "sol, viento fuerte, niebla y lluvia fría en cuestión de horas, incluso a las "
            "latitudes y altitudes relativamente moderadas de esta ruta; la ropa de capas y el "
            "equipo impermeable de calidad no son opcionales, y muchos senderistas experimentados "
            "consideran el viento, más que el frío en sí, el factor climático más exigente de la "
            "travesía.</p> "
            "<p>Laugavegur suele combinarse con una extensión de dos días adicionales hacia el "
            "sur, hasta Skógar, que añade un tramo de alta montaña volcánica junto al glaciar "
            "Eyjafjallajökull —el volcán cuya erupción de 2010 afectó al tráfico aéreo europeo— "
            "antes de descender hacia la costa sur de la isla por una serie de cascadas, lo que "
            "convierte a la ruta completa en una de las travesías de varios días más variadas de "
            "toda Europa.</p> "
            "<p>El paisaje de riolita de Landmannalaugar es, geológicamente, resultado de "
            "erupciones "
            "volcánicas ácidas mucho menos frecuentes que las basálticas que dominan el resto de "
            "Islandia, lo que explica la rareza de sus colores en comparación con el resto de la "
            "isla; la zona sigue siendo geotérmicamente activa, con fumarolas y manantiales "
            "calientes "
            "visibles en varios puntos de la ruta. La red de refugios que hace posible recorrer "
            "Laugavegur sin equipo de expedición completo es gestionada por voluntarios y personal "
            "de "
            "la asociación islandesa de senderismo, un modelo de gestión comunitaria de montaña "
            "con una larga tradición en el país.</p> "
            "<p>El descenso final de la ruta hacia Þórsmörk atraviesa un cañón estrecho conocido "
            "como "
            "Cañón del Infierno (Helvítisgil), flanqueado por paredes de roca volcánica y "
            "vegetación "
            "densa que contrasta con la aridez de los tramos anteriores de la travesía; ese cambio "
            "final de paisaje, de la desolación volcánica de Landmannalaugar al verde protegido "
            "del valle de Þórsmörk, resume bien la variedad geológica que hace de Laugavegur una "
            "de las rutas de trekking más completas de Europa en solo unos días.</p>"
        ),
        tipos_slugs=["senderismo-y-trekking"],
        dificultad=4,
        meses_mejor_epoca=[6, 7, 8],
        duracion_min_dias=4,
        duracion_max_dias=6,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima subártico de tierras altas, transitable de forma segura solo durante el "
            "verano (aproximadamente finales de junio a principios de septiembre, según el "
            "deshielo de cada temporada); incluso en esa ventana, el clima puede cambiar con "
            "rapidez entre sol, viento fuerte, niebla y lluvia fría en una misma jornada.</p>"
        ),
        altitud_max_m=1100,
        como_llegar=(
            "<p>El acceso habitual es en vuelo hasta Reikiavik y, desde allí, en autobús de "
            "montaña (con neumáticos y vados aptos para pistas no asfaltadas) hasta "
            "Landmannalaugar, el punto de inicio de la ruta; el regreso desde Þórsmörk, al final "
            "de la travesía, se organiza de la misma forma. Reservar los refugios de la "
            "asociación islandesa de senderismo con bastante antelación es indispensable en "
            "temporada alta.</p>"
        ),
        seguridad_riesgos=(
            "<p>Los cruces de ríos glaciares sin puente son el riesgo técnico más particular de "
            "esta ruta, junto con los cambios meteorológicos rápidos y el viento fuerte en tramos "
            "expuestos; salir de la ventana de verano transitable, sin equipo y experiencia de "
            "montaña invernal, se considera un riesgo serio que las autoridades islandesas "
            "desaconsejan de forma explícita.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Mantenerse siempre sobre los senderos marcados es especialmente importante en "
            "este entorno volcánico de vegetación y musgo de crecimiento muy lento, que tarda "
            "años o décadas en regenerarse tras un daño; usar los refugios y zonas de camping "
            "designadas y llevarse toda la basura son normas centrales de la asociación islandesa "
            "de senderismo que gestiona la ruta.</p>"
        ),
        latitud=63.9932,
        longitud=-19.0567,
        seo_titulo="Ruta Laugavegur: guía de trekking en las tierras altas de Islandia",
        seo_descripcion=(
            "Montañas de riolita, cruces de ríos glaciares y refugios: guía experta de la ruta "
            "Laugavegur, trekking en las tierras altas de Islandia."
        ),
        relacionados_slugs=["fiordos-de-noruega", "dolomitas", "chamonix-mont-blanc"],
    ),
    DestinoSemilla(
        n=15,
        titulo="Dolomitas",
        slug="dolomitas",
        pais_slug="italia",
        resumen=(
            "Torres y paredes de roca dolomítica en los Alpes italianos, cuna histórica de la "
            "vía ferrata y Patrimonio de la Humanidad."
        ),
        descripcion_experta=(
            "<p>Las Dolomitas, en el norte de Italia, son un macizo de los Alpes formado por "
            "roca caliza de un tipo particular —la dolomía, que da nombre a la cordillera— cuya "
            "erosión ha esculpido torres, agujas y paredes verticales de una geometría muy "
            "distinta a la de otras cadenas alpinas de roca cristalina, con tonos que van del "
            "gris claro al rosado, especialmente intensos al amanecer y al atardecer, un "
            "fenómeno conocido localmente como «enrosadira». La UNESCO declaró el conjunto "
            "Patrimonio de la Humanidad por la singularidad de este paisaje y su valor geológico "
            "excepcional.</p> "
            "<p>Esta región es, además, la cuna histórica de la vía ferrata: durante la Primera "
            "Guerra Mundial, el frente entre los ejércitos italiano y austrohúngaro atravesó "
            "estas montañas, y ambos bandos instalaron cables, escalones y pasarelas metálicas "
            "para mover tropas y suministros por un terreno que de otro modo habría sido "
            "infranqueable. Muchas de esas instalaciones militares, restauradas y aseguradas con "
            "estándares modernos, son hoy las vías ferratas que atraen cada verano a miles de "
            "aficionados de toda Europa, lo que convierte a las Dolomitas en el destino con la "
            "mayor concentración y variedad de vías ferratas del mundo.</p> "
            "<p>El abanico de dificultad entre las distintas vías ferratas de la región es muy "
            "amplio: existen rutas introductorias, con tramos de cable corto y exposición "
            "moderada, aptas para quien se inicia en la disciplina, y otras de nivel muy "
            "avanzado, con largos tramos verticales, techos en desplome y una exposición "
            "considerable, reservadas a quien ya cuenta con experiencia previa y buena forma "
            "física. Consultar siempre la clasificación de dificultad y exposición de cada vía "
            "antes de elegirla es una recomendación constante de los guías de montaña locales.</p> "
            "<p>Más allá de la vía ferrata, las Dolomitas ofrecen una de las redes de senderismo "
            "alpino más desarrolladas de Europa, con una infraestructura de refugios de montaña "
            "(«rifugi») que permite planificar travesías de varios días sin necesidad de cargar "
            "equipo de campamento completo, de forma similar a los refugios de otras zonas "
            "alpinas como los Pirineos o los Alpes suizos.</p> "
            "<p>El buen tiempo alpino de verano puede degradarse con rapidez en tormenta, "
            "especialmente por la tarde tras jornadas calurosas, lo que hace recomendable "
            "comenzar las vías ferratas y rutas de montaña temprano por la mañana y estar atento "
            "a la previsión meteorológica del día. El material de vía ferrata —arnés, kit con "
            "disipador de energía y casco— debe revisarse siempre antes de cada salida, y el "
            "alquiler en las localidades base de la región es una opción habitual para quien no "
            "viaja con equipo propio.</p> "
            "<p>La región combina, además, un patrimonio gastronómico y cultural propio, con "
            "influencia tanto italiana como austríaca por su historia fronteriza, y localidades "
            "como Cortina d'Ampezzo o Val Gardena que funcionan como base tanto para el "
            "senderismo y la vía ferrata de verano como para el esquí alpino en invierno.</p> "
            "<p>El nombre «Dolomitas» honra al geólogo francés Déodat de Dolomieu, quien a finales "
            "del siglo XVIII describió por primera vez de forma científica la roca caliza "
            "magnésica característica de esta cordillera; ese origen científico convive hoy con "
            "una identidad cultural propia de la región, donde conviven el italiano, el alemán y "
            "el ladino, una lengua romance minoritaria hablada en varios valles dolomíticos desde "
            "hace siglos. La combinación de historia bélica, identidad cultural fronteriza y "
            "geología excepcional es "
            "parte de lo que distingue a las Dolomitas de otras grandes cordilleras alpinas.</p> "
            "<p>La localidad de Cortina d'Ampezzo, una de las bases más conocidas de la región, "
            "fue sede de los Juegos Olímpicos de Invierno de 1956 y volverá a serlo en 2026, lo "
            "que ha consolidado a las Dolomitas como uno de los grandes centros alpinos de "
            "deportes de invierno de Europa además de su fama estival de senderismo y vía ferrata; "
            "esa doble vocación, verano e invierno, explica la solidez de la infraestructura de "
            "refugios, teleféricos y alojamiento de la región durante todo el año.</p>"
        ),
        tipos_slugs=["escalada-y-via-ferrata"],
        dificultad=4,
        meses_mejor_epoca=[6, 7, 8, 9],
        duracion_min_dias=3,
        duracion_max_dias=7,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima alpino de montaña, con veranos (junio-septiembre) la única temporada "
            "recomendada para vía ferrata y senderismo de altura; las tormentas de tarde son "
            "frecuentes en pleno verano, y en invierno la región se cubre de nieve y cambia por "
            "completo su perfil de actividades hacia el esquí alpino.</p>"
        ),
        altitud_max_m=3343,
        como_llegar=(
            "<p>El acceso habitual es en vuelo hasta Venecia, Innsbruck o Múnich y, desde "
            "cualquiera de estas ciudades, por carretera hasta las localidades base de la región "
            "dolomítica, como Cortina d'Ampezzo, Val Gardena o Alta Badia. La red de refugios de "
            "montaña conviene reservarla con antelación en temporada alta de verano.</p>"
        ),
        seguridad_riesgos=(
            "<p>Las caídas por fallo o mal uso del sistema de doble mosquetón en vía ferrata, la "
            "exposición a tormentas de tarde en tramos verticales y la caída de piedras sueltas "
            "en rutas concurridas son los riesgos más citados; revisar el material antes de cada "
            "salida y comenzar temprano para evitar las tormentas de la tarde son medidas de "
            "seguridad básicas en la región.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>La alta afluencia de senderistas y aficionados a la vía ferrata en temporada alta "
            "ejerce presión sobre los refugios y senderos de la región: reservar con antelación, "
            "mantenerse en los senderos marcados y usar el transporte público de montaña "
            "disponible en varias zonas de las Dolomitas ayuda a reducir el impacto sobre este "
            "paisaje protegido.</p>"
        ),
        latitud=46.4102,
        longitud=11.8440,
        seo_titulo="Dolomitas: guía experta de vía ferrata en los Alpes italianos",
        seo_descripcion=(
            "Historia, dificultad y refugios de montaña: guía experta de vía ferrata y "
            "senderismo en las Dolomitas, Alpes italianos."
        ),
        relacionados_slugs=["chamonix-mont-blanc", "yosemite", "ruta-laugavegur"],
    ),
    DestinoSemilla(
        n=16,
        titulo="Chamonix-Mont-Blanc",
        slug="chamonix-mont-blanc",
        pais_slug="francia",
        resumen=(
            "La capital histórica del alpinismo mundial, a los pies del Mont Blanc, con "
            "glaciares, alta montaña técnica y parapente sobre el valle."
        ),
        descripcion_experta=(
            "<p>Chamonix, en el valle francés a los pies del Mont Blanc —la cumbre más alta de "
            "los Alpes occidentales—, es considerada por buena parte de la comunidad "
            "montañera como la cuna del alpinismo moderno: fue aquí donde, en 1786, se realizó "
            "la primera ascensión documentada del Mont Blanc, un hito que suele señalarse como el "
            "nacimiento simbólico del alpinismo como disciplina deportiva. Más de dos siglos "
            "después, Chamonix sigue siendo uno de los centros de alta montaña más importantes "
            "del mundo, con un tejido de guías, escuelas de montaña y refugios que no tiene "
            "equivalente en muchas otras regiones alpinas.</p> "
            "<p>El teleférico de la Aiguille du Midi, que asciende desde el propio pueblo hasta "
            "una cota superior a los 3.800 metros en pocos minutos, ofrece una de las vistas "
            "panorámicas de alta montaña más accesibles del planeta y es, a la vez, el punto de "
            "partida de varias de las rutas de alpinismo y esquí de travesía más clásicas del "
            "macizo, entre ellas la propia vía normal al Mont Blanc y el descenso de la Vallée "
            "Blanche, un glaciar de más de veinte kilómetros que es, probablemente, el descenso "
            "de esquí fuera de pista más conocido del mundo.</p> "
            "<p>La ascensión al Mont Blanc por su vía normal, aunque no es técnicamente la más "
            "difícil del macizo, exige buena forma física, aclimatación, experiencia de "
            "progresión con crampones y piolet en terreno glaciar, y una ventana meteorológica "
            "estable, ya que la ruta atraviesa zonas expuestas a caída de piedras y grietas de "
            "glaciar; la inmensa mayoría de ascensiones se realizan con guías de alta montaña "
            "certificados por la reconocida escuela local de guías, una de las más antiguas del "
            "mundo.</p> "
            "<p>Más allá del Mont Blanc, el valle de Chamonix es también uno de los grandes "
            "centros europeos del parapente, con despegues a media montaña orientados a "
            "aprovechar las térmicas del valle y vuelos en tándem que permiten sobrevolar "
            "glaciares y bosques alpinos sin necesidad de formación previa por parte del "
            "pasajero.</p> "
            "<p>El valle es también el punto de partida del Tour du Mont Blanc, una de las "
            "travesías de trekking de larga distancia más populares de Europa, que rodea todo el "
            "macizo a lo largo de varios días atravesando Francia, Italia y Suiza; existen "
            "también tramos más cortos de uno o varios días que recorren solo una parte del "
            "circuito para quien no dispone de tiempo para la vuelta completa.</p> "
            "<p>El retroceso glaciar es un fenómeno especialmente visible en Chamonix: la Mer de "
            "Glace, el mayor glaciar francés y una de las atracciones históricas del valle "
            "accesible por tren de montaña, ha perdido una parte considerable de su espesor y "
            "longitud en las últimas décadas, un cambio documentado con paneles informativos a "
            "lo largo del propio acceso al glaciar que lo convierten, además de en un destino de "
            "montaña, en un testimonio visible del cambio climático en los Alpes.</p> "
            "<p>La primera ascensión al Mont Blanc, en 1786, por Jacques Balmat y Michel Paccard, "
            "se "
            "considera el punto de partida simbólico del alpinismo como actividad deportiva "
            "organizada, y desde entonces Chamonix ha acumulado una historia montañera de más de "
            "dos "
            "siglos que incluye la fundación, en 1821, de la Compagnie des Guides de Chamonix, una "
            "de "
            "las asociaciones de guías de montaña más antiguas del mundo y todavía en activo. Esa "
            "tradición explica por qué la ciudad sigue siendo, más de dos siglos después, un punto "
            "de "
            "referencia obligado para cualquier persona interesada en el alpinismo alpino.</p> "
            "<p>El macizo del Mont Blanc, compartido entre Francia, Italia y Suiza, exige a menudo "
            "cruzar fronteras nacionales en una misma jornada de alpinismo o en el propio Tour du "
            "Mont Blanc, una peculiaridad geográfica que refleja la larga tradición alpina "
            "compartida "
            "entre estos tres países y que se traduce en una red de refugios, guías y rescate en "
            "montaña coordinada entre las tres administraciones fronterizas.</p>"
        ),
        tipos_slugs=["alta-montana-y-alpinismo", "parapente-y-deportes-aereos"],
        dificultad=4,
        meses_mejor_epoca=[6, 7, 8, 9],
        duracion_min_dias=3,
        duracion_max_dias=7,
        nivel_presupuesto=4,
        clima=(
            "<p>Clima alpino de montaña, con veranos (junio-septiembre) la temporada más "
            "estable para alpinismo, trekking y parapente, e inviernos largos y nevados "
            "orientados al esquí; el buen tiempo en alta montaña puede degradarse con rapidez "
            "incluso en verano, por lo que la ventana meteorológica se confirma siempre a corto "
            "plazo.</p>"
        ),
        altitud_max_m=4809,
        como_llegar=(
            "<p>El acceso habitual es en vuelo hasta Ginebra, en Suiza, y desde allí por "
            "carretera hasta Chamonix, en el valle francés a los pies del Mont Blanc; también "
            "existen conexiones en tren desde varias ciudades francesas. El teleférico de la "
            "Aiguille du Midi parte del propio pueblo.</p>"
        ),
        seguridad_riesgos=(
            "<p>La caída de piedras y las grietas de glaciar son los riesgos técnicos principales "
            "del alpinismo en el macizo del Mont Blanc, junto con los cambios meteorológicos "
            "rápidos propios de la alta montaña alpina; la ascensión al Mont Blanc y la mayoría "
            "de rutas técnicas de la zona se realizan con guías de alta montaña certificados, cuya"
            "decisión sobre las condiciones del día debe respetarse siempre.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El retroceso documentado de glaciares como la Mer de Glace es un recordatorio "
            "visible del impacto del cambio climático en los Alpes; usar el transporte de "
            "montaña (teleféricos y trenes) en lugar del vehículo propio cuando sea posible y "
            "mantenerse en los senderos e itinerarios señalizados ayuda a reducir la presión "
            "sobre un valle con una afluencia turística muy alta.</p>"
        ),
        latitud=45.9237,
        longitud=6.8694,
        seo_titulo="Chamonix-Mont-Blanc: guía de alpinismo en los Alpes franceses",
        seo_descripcion=(
            "Mont Blanc, Aiguille du Midi y parapente: guía experta de alta montaña en "
            "Chamonix, cuna del alpinismo en los Alpes franceses."
        ),
        relacionados_slugs=["dolomitas", "banff", "kilimanjaro"],
    ),
    DestinoSemilla(
        n=17,
        titulo="Fiordos del oeste de Noruega",
        slug="fiordos-de-noruega",
        pais_slug="noruega",
        resumen=(
            "Paredes de roca que caen a plomo sobre aguas de fiordo, con miradores icónicos "
            "como el Preikestolen y el Trolltunga y rutas de kayak entre cascadas."
        ),
        descripcion_experta=(
            "<p>Los fiordos del oeste de Noruega son valles glaciares inundados por el mar, "
            "formados cuando el hielo de sucesivas glaciaciones excavó valles muy por debajo del "
            "nivel del mar y, al retirarse, dejó que el agua marina ocupara esos cañones "
            "profundos entre paredes de roca casi verticales. El resultado es un paisaje de "
            "una escala difícil de transmitir en fotografía: acantilados de varios cientos de "
            "metros que caen directamente sobre aguas de un fiordo estrecho, con cascadas "
            "alimentadas por el deshielo que se precipitan desde lo alto de las paredes "
            "directamente al agua.</p> "
            "<p>Dos miradores se han convertido en símbolo de esta región: el Preikestolen (o "
            "«púlpito»), una plataforma de roca plana que sobresale a pico sobre el fiordo de "
            "Lysefjord sin apenas barandilla, y el Trolltunga («lengua de troll»), una repisa de "
            "roca horizontal suspendida sobre un lago de montaña cerca del Hardangerfjord, cuya "
            "fotografía —una persona de pie sobre la roca con el vacío debajo— se ha convertido "
            "en una de las imágenes más compartidas del senderismo noruego. Ambas rutas son "
            "caminatas de un día completo, exigentes por la distancia y el desnivel más que por "
            "la técnica, y accesibles sin experiencia de montaña previa si se cuenta con buena "
            "condición física.</p> "
            "<p>El kayak es, junto con el senderismo hacia estos miradores, la forma más "
            "característica de explorar los propios fiordos: remar entre paredes verticales, "
            "cerca de cascadas y con la posibilidad de acercarse a zonas inaccesibles por "
            "carretera, ofrece una perspectiva del paisaje muy distinta a la que se obtiene desde "
            "los miradores en altura, y existen tanto salidas guiadas de pocas horas como "
            "travesías de varios días por fiordos menos frecuentados.</p> "
            "<p>El clima noruego, con precipitaciones frecuentes durante buena parte del año por "
            "la exposición de la costa oeste a los sistemas atlánticos, hace que la ropa "
            "impermeable de calidad sea indispensable en cualquier época, incluso en los meses de "
            "verano en los que se concentra la mayoría de visitas a los grandes miradores; las "
            "rutas hacia el Preikestolen y el Trolltunga pueden cerrarse o desaconsejarse en "
            "condiciones de niebla densa o hielo por el riesgo real de caída en los tramos más "
            "expuestos.</p> "
            "<p>Noruega ha desarrollado una tradición legal particular, el «allemannsretten» o "
            "derecho de acceso libre a la naturaleza, que permite a cualquier persona caminar, "
            "acampar y moverse por la mayor parte del territorio no cultivado del país, siempre "
            "que se respeten unas normas básicas de distancia a viviendas y de cuidado del "
            "entorno; este derecho es parte de la cultura noruega de relación con la naturaleza y "
            "convive con una exigencia igualmente fuerte de dejar el entorno sin rastro de la "
            "propia visita.</p> "
            "<p>La red de ferris y carreteras panorámicas que conecta los distintos fiordos "
            "noruegos —muchas de ellas consideradas entre las rutas en carretera más "
            "espectaculares de Europa— permite combinar en un mismo viaje varios fiordos "
            "distintos, cada uno con su propio carácter, desde el más visitado Geirangerfjord "
            "hasta fiordos más recónditos del interior de la región occidental del país.</p> "
            "<p>El Geirangerfjord y el Nærøyfjord, dos de los fiordos noruegos declarados "
            "Patrimonio "
            "de la Humanidad, ejemplifican la escala de estos paisajes: paredes de roca de más de "
            "mil "
            "metros de desnivel caen directamente sobre aguas de apenas unos cientos de metros de "
            "ancho en algunos tramos, un contraste vertical que ha convertido a la navegación por "
            "fiordos noruegos en una de las experiencias de paisaje más citadas de Europa. "
            "Pequeñas granjas abandonadas, encaramadas en repisas de roca a las que antes solo se "
            "accedía por "
            "barco o por senderos verticales, salpican todavía las laderas de varios fiordos como "
            "testimonio de una forma de vida rural hoy prácticamente desaparecida.</p>"
        ),
        tipos_slugs=["kayak-y-navegacion", "senderismo-y-trekking"],
        dificultad=3,
        meses_mejor_epoca=[6, 7, 8],
        duracion_min_dias=3,
        duracion_max_dias=7,
        nivel_presupuesto=4,
        clima=(
            "<p>Clima oceánico templado con precipitaciones frecuentes durante todo el año; el "
            "verano (junio-agosto) concentra los días más largos y estables, y es la temporada "
            "recomendada tanto para el senderismo a los grandes miradores como para el kayak, "
            "aunque la lluvia puede aparecer en cualquier momento del año.</p>"
        ),
        altitud_max_m=1100,
        como_llegar=(
            "<p>El acceso habitual es en vuelo hasta Stavanger (para el Preikestolen) o Bergen "
            "(para el Trolltunga y buena parte de los fiordos occidentales), y desde allí en "
            "autobús, ferri o vehículo propio hasta los distintos puntos de inicio de las rutas. "
            "La red de ferris noruega es parte habitual de cualquier desplazamiento entre "
            "fiordos.</p>"
        ),
        seguridad_riesgos=(
            "<p>La caída en los tramos expuestos del Preikestolen y el Trolltunga, sin apenas "
            "barandillas, es el riesgo más citado de la región, agravado por niebla o hielo; el "
            "agua fría de los fiordos y el cambio brusco de tiempo son los riesgos principales "
            "del kayak. Consultar siempre la previsión meteorológica y no aventurarse en los "
            "miradores con niebla densa son recomendaciones constantes de las autoridades "
            "locales.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El derecho de acceso libre a la naturaleza («allemannsretten») convive con la "
            "exigencia de no dejar rastro: llevarse toda la basura, no encender fuego fuera de "
            "zonas designadas y respetar la distancia a viviendas y cultivos son las normas "
            "básicas que sostienen este modelo de acceso abierto a la naturaleza noruega.</p>"
        ),
        latitud=59.9856,
        longitud=6.1897,
        seo_titulo="Fiordos de Noruega: guía de senderismo y kayak",
        seo_descripcion=(
            "Preikestolen, Trolltunga y kayak entre fiordos: guía experta de senderismo y "
            "navegación en los fiordos del oeste de Noruega."
        ),
        relacionados_slugs=["ruta-laugavegur", "banff", "bahia-de-ha-long"],
    ),
    DestinoSemilla(
        n=18,
        titulo="Monte Kilimanjaro",
        slug="kilimanjaro",
        pais_slug="tanzania",
        resumen=(
            "El techo de África: un volcán inactivo que se puede coronar sin escalada técnica, "
            "solo con buena aclimatación y varios días de ascenso."
        ),
        descripcion_experta=(
            "<p>El Kilimanjaro, en el norte de Tanzania, es la montaña más alta de África y una "
            "de las llamadas «Siete Cumbres» (el pico más elevado de cada continente), una "
            "categoría que ha contribuido a su fama mundial como objetivo de montaña accesible "
            "para quien busca un reto de altitud sin necesidad de experiencia previa de escalada "
            "técnica. Se trata de un volcán inactivo, el más alto de África, cuya vía normal de "
            "ascenso no exige cuerdas, crampones ni piolet, sino una caminata larga y sostenida "
            "durante varios días, lo que ha hecho de esta montaña un destino relativamente "
            "popular pese a su altitud extrema.</p> "
            "<p>Esa accesibilidad técnica es, paradójicamente, uno de los motivos por los que el "
            "Kilimanjaro exige tanto respeto: al no haber una barrera técnica que filtre a los "
            "aspirantes, el principal factor de éxito o fracaso —y de riesgo real para la salud— "
            "es el mal de altura, que puede afectar a cualquier persona independientemente de su "
            "forma física, y que se gestiona sobre todo con tiempo: las rutas más largas, de seis "
            "o siete días, tienen tasas de éxito y de seguridad notablemente mejores que las más "
            "cortas, precisamente porque permiten una aclimatación más gradual.</p> "
            "<p>El ascenso atraviesa varios pisos climáticos muy distintos en pocos días: se "
            "inicia en selva tropical húmeda en las faldas de la montaña, continúa por landas de "
            "alta montaña con vegetación achaparrada y muy particular —los géneros Senecio y "
            "Lobelia han desarrollado especies gigantes exclusivas de estas montañas africanas de "
            "altitud—, cruza un desierto alpino de roca volcánica desnuda y termina en la zona "
            "ártica de la cumbre, cubierta por los restos de los antiguos glaciares del "
            "Kilimanjaro, que han retrocedido de forma muy marcada en las últimas décadas.</p> "
            "<p>La ascensión final hacia el punto más alto, el Uhuru Peak, se realiza "
            "habitualmente de madrugada, en la oscuridad y con temperaturas muy por debajo de "
            "cero, para coronar la cumbre al amanecer; es el tramo más duro física y "
            "mentalmente de toda la ruta, por la combinación de fatiga acumulada de varios días, "
            "frío extremo y la menor disponibilidad de oxígeno a esa altitud.</p> "
            "<p>Toda ascensión al Kilimanjaro se organiza con una agencia autorizada por el "
            "parque nacional, con un equipo de guías, cocineros y porteadores tanzanos que "
            "sostienen toda la logística de la expedición; como en el Camino Inca peruano, las "
            "condiciones laborales de los porteadores —peso máximo de carga, equipo de abrigo "
            "adecuado y alimentación— se han convertido en un criterio relevante para elegir "
            "operador, y varias organizaciones locales certifican a las agencias que cumplen "
            "estándares mínimos.</p> "
            "<p>Elegir la ruta adecuada —existen varias vías de ascenso, con distinta duración, "
            "paisaje y perfil de aclimatación— y, sobre todo, elegir la duración más larga que el "
            "tiempo disponible permita, es la decisión individual que más influye tanto en las "
            "probabilidades de alcanzar la cumbre como en la seguridad general de la "
            "ascensión.</p> <p>El Kilimanjaro fue escalado por primera vez en 1889 por el geógrafo "
            "alemán Hans Meyer "
            "junto al guía austríaco Ludwig Purtscheller, en una expedición que formó parte del "
            "contexto colonial de la época en el África oriental alemana; hoy la montaña se "
            "encuentra "
            "en territorio de Tanzania, un país independiente desde 1961, y su ascenso sostiene "
            "una parte significativa de la economía turística de la región de Moshi y Arusha. Los "
            "glaciares de cumbre del Kilimanjaro, documentados por primera vez por aquella "
            "expedición "
            "alemana, han perdido la mayor parte de su extensión histórica a lo largo del último "
            "siglo, un retroceso ampliamente estudiado por glaciólogos como indicador del cambio "
            "climático en África oriental.</p> "
            "<p>El parque nacional que rodea la montaña protege también varios pisos de vegetación "
            "muy distintos entre sí, desde bosque de montaña húmedo en las faldas hasta un "
            "desierto alpino casi sin vida vegetal cerca de la cumbre, lo que convierte al ascenso "
            "en un recorrido por varios ecosistemas africanos distintos en apenas una semana, una "
            "particularidad que comparte con muy pocas montañas del mundo fuera del propio "
            "continente "
            "africano.</p>"
        ),
        tipos_slugs=["alta-montana-y-alpinismo"],
        dificultad=4,
        meses_mejor_epoca=[1, 2, 6, 7, 8, 9],
        duracion_min_dias=6,
        duracion_max_dias=8,
        nivel_presupuesto=4,
        clima=(
            "<p>El ascenso atraviesa varios pisos climáticos, de la selva tropical húmeda de la "
            "base al frío ártico de la cumbre; las temporadas más secas y recomendadas son "
            "enero-febrero y junio-septiembre, mientras que las de lluvias largas "
            "(marzo-mayo) dificultan considerablemente el ascenso.</p>"
        ),
        altitud_max_m=5895,
        como_llegar=(
            "<p>El acceso habitual es en vuelo internacional hasta el aeropuerto de Kilimanjaro, "
            "en Tanzania, cercano a las localidades de Moshi y Arusha, donde se concentran las "
            "agencias autorizadas por el parque nacional para organizar la ascensión, incluidos "
            "el equipo de guías, cocineros y porteadores.</p>"
        ),
        seguridad_riesgos=(
            "<p>El mal de altura es, con diferencia, el riesgo principal del Kilimanjaro, agravado "
            "en las rutas más cortas por una aclimatación insuficiente; el frío extremo del "
            "ascenso nocturno final a la cumbre es otro factor de riesgo relevante. Elegir una "
            "ruta de duración suficiente para aclimatar de forma progresiva y viajar con una "
            "agencia autorizada con guías certificados en primeros auxilios de altitud son las "
            "medidas de seguridad más importantes.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Elegir agencias que cumplen estándares certificados de condiciones laborales para "
            "los porteadores tanzanos —peso máximo de carga, equipo y alimentación adecuados— es "
            "una decisión con impacto social directo; llevarse toda la basura de la expedición y "
            "respetar las rutas designadas por el parque nacional protege un ecosistema de "
            "montaña donde los glaciares de cumbre ya han retrocedido de forma muy marcada.</p>"
        ),
        latitud=-3.0674,
        longitud=37.3556,
        seo_titulo="Kilimanjaro: guía experta para ascender el techo de África",
        seo_descripcion=(
            "Rutas, aclimatación y porteadores: guía experta para ascender el Kilimanjaro, la "
            "montaña más alta de África, en Tanzania."
        ),
        relacionados_slugs=["everest-campo-base", "chamonix-mont-blanc", "delta-del-okavango"],
    ),
    DestinoSemilla(
        n=19,
        titulo="Delta del Okavango",
        slug="delta-del-okavango",
        pais_slug="botsuana",
        resumen=(
            "Un delta interior que inunda el desierto de Kalahari cada año, recorrido en "
            "canoas tradicionales entre elefantes, leones e hipopótamos."
        ),
        descripcion_experta=(
            "<p>El Delta del Okavango es uno de los pocos grandes deltas fluviales del mundo que "
            "no desemboca en el mar: el río Okavango, que nace en las tierras altas de Angola, "
            "se abre en abanico al llegar a la cuenca del Kalahari, en el norte de Botsuana, y se "
            "pierde progresivamente por evaporación e infiltración en la arena del desierto, sin "
            "llegar nunca al océano. Ese fenómeno hidrológico, poco común a esta escala, produce "
            "una de las mayores concentraciones de vida salvaje de África en pleno corazón de una "
            "de las regiones más áridas del continente.</p> "
            "<p>La crecida anual del delta no coincide con la temporada de lluvias local, sino "
            "que llega varios meses después, cuando el agua procedente de las lluvias angoleñas "
            "recorre lentamente el cauce del río hasta inundar el delta en plena temporada seca "
            "botsuana; ese desfase temporal concentra a una enorme cantidad de fauna alrededor "
            "del agua disponible justo quo el resto del Kalahari está más seco, lo que convierte "
            "a esos meses en la temporada de observación de fauna más intensa del año.</p> "
            "<p>La forma de explorar el delta que lo distingue de otros destinos de safari "
            "africano es el mokoro, una canoa tradicional tallada originalmente en un solo "
            "tronco (hoy, con frecuencia, en fibra de vidrio para proteger los bosques locales), "
            "impulsada con una pértiga por un guía local que conoce los canales de aguas poco "
            "profundas del delta. Deslizarse en mokoro entre juncos y nenúfares, en silencio y a "
            "ras de agua, ofrece una perspectiva de la fauna y el ecosistema muy distinta a la de "
            "un safari clásico en vehículo todoterreno, que también se practica en las zonas más "
            "secas del delta.</p> "
            "<p>El delta alberga una de las mayores poblaciones de elefantes de África, además de "
            "leones, leopardos, hipopótamos, cocodrilos del Nilo y una diversidad de aves "
            "acuáticas muy alta, lo que lo convierte en un destino de referencia tanto para el "
            "safari en vehículo como para la observación desde el agua. La combinación de ambos "
            "tipos de safari en una misma estancia —mokoro en las zonas inundadas y vehículo en "
            "las islas y zonas más secas— es habitual en los campamentos de la región.</p> "
            "<p>El acceso a buena parte del delta se realiza en avioneta desde Maun, la localidad "
            "que funciona como puerta de entrada a la región, dado que la mayoría de campamentos "
            "se ubican en islas dispersas por la zona inundada sin conexión por carretera; esta "
            "logística aérea, junto con el carácter de safari de lujo que predomina en buena "
            "parte de la oferta del delta, sitúa a este destino en un rango de presupuesto más "
            "alto que otros safaris africanos por carretera.</p> "
            "<p>La conservación del delta, declarado Patrimonio de la Humanidad, depende en gran "
            "medida de un modelo de turismo de bajo volumen y alto valor que Botsuana ha "
            "promovido de forma deliberada durante décadas, limitando el número de camas "
            "disponibles en la región para reducir la presión humana sobre un ecosistema "
            "hidrológico de un equilibrio muy delicado.</p> "
            "<p>La cuenca del río Okavango, que nace en las tierras altas de Angola y atraviesa "
            "Namibia antes de llegar a Botsuana, es un ejemplo destacado de gestión "
            "transfronteriza de un recurso hídrico compartido entre varios países africanos; "
            "Botsuana, en particular, "
            "ha apostado por declarar buena parte del delta como zona protegida de baja densidad "
            "turística, una estrategia que contrasta con el turismo de safari más masivo de otras "
            "regiones del continente y que se ha convertido en un modelo de referencia para la "
            "conservación de humedales africanos.</p> "
            "<p>La estación seca en la que el delta alcanza su mayor extensión de agua coincide "
            "también con la época de menor riesgo de malaria en la región, un factor sanitario que "
            "muchos viajeros tienen en cuenta al planificar la fecha de su safari; aun así, la "
            "profilaxis antipalúdica y el repelente de insectos siguen siendo recomendaciones "
            "estándar de los servicios de salud de viaje para cualquier visita al delta, "
            "independientemente de la temporada elegida.</p>"
        ),
        tipos_slugs=["safari-y-observacion-de-fauna", "kayak-y-navegacion"],
        dificultad=1,
        meses_mejor_epoca=[6, 7, 8, 9],
        duracion_min_dias=3,
        duracion_max_dias=6,
        nivel_presupuesto=4,
        clima=(
            "<p>Clima semiárido de sabana, con una temporada de lluvias (aproximadamente "
            "noviembre-marzo) y una temporada seca; la crecida de agua en el propio delta llega "
            "varios meses después de las lluvias de origen, por lo que la mayor concentración de "
            "fauna suele darse durante la temporada seca botsuana (junio-septiembre).</p>"
        ),
        altitud_max_m=1000,
        como_llegar=(
            "<p>El acceso habitual es en vuelo internacional hasta Maun, en Botsuana, y desde "
            "allí en avioneta hasta el campamento elegido dentro del delta, ya que la mayoría no "
            "tiene acceso por carretera durante la temporada de inundación. Los campamentos "
            "suelen incluir el traslado en avioneta dentro de su organización.</p>"
        ),
        seguridad_riesgos=(
            "<p>La proximidad a fauna potencialmente peligrosa —hipopótamos, cocodrilos, "
            "elefantes— es el riesgo principal, especialmente en los desplazamientos en mokoro "
            "cerca de aguas donde puede haber hipopótamos sumergidos; seguir en todo momento las "
            "indicaciones del guía local sobre distancia y comportamiento es la medida de "
            "seguridad más importante del delta.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El modelo botsuano de turismo de bajo volumen y alto valor limita de forma "
            "deliberada el número de visitantes en la región para proteger el equilibrio "
            "hidrológico del delta; elegir campamentos con políticas ambientales y de empleo "
            "local transparentes contribuye a sostener ese modelo de conservación a largo "
            "plazo.</p>"
        ),
        latitud=-19.2833,
        longitud=22.9833,
        seo_titulo="Delta del Okavango: guía de safari y mokoro en Botsuana",
        seo_descripcion=(
            "Safari en mokoro y en vehículo, fauna y temporada de crecida: guía experta del "
            "Delta del Okavango, Botsuana."
        ),
        relacionados_slugs=["kilimanjaro", "islas-galapagos", "wadi-rum"],
    ),
    DestinoSemilla(
        n=20,
        titulo="Campo base del Everest",
        slug="everest-campo-base",
        pais_slug="nepal",
        resumen=(
            "El trekking de altitud más célebre del mundo, hasta el campo base de la montaña "
            "más alta del planeta, por el valle sherpa del Khumbu."
        ),
        descripcion_experta=(
            "<p>El trekking al campo base del Everest recorre el valle del Khumbu, en el noreste "
            "de Nepal, hasta el campamento situado a los pies de la cara suroeste del Everest, la "
            "montaña más alta del planeta sobre el nivel del mar. A diferencia de la ascensión a "
            "la cumbre, reservada a montañistas de expedición con formación técnica avanzada, "
            "llegar al campo base es un trekking sin dificultad técnica —no requiere cuerdas, "
            "crampones ni piolet en condiciones normales— pero de una exigencia física y de "
            "altitud considerable, que lo convierte en uno de los grandes objetivos del "
            "senderismo mundial.</p> "
            "<p>La ruta atraviesa el territorio del pueblo sherpa, la comunidad de origen "
            "tibetano que habita esta región del Himalaya desde hace varios siglos y que ha "
            "jugado un papel central en la historia del montañismo himalayo, tanto como guías de "
            "alta montaña como en el propio ascenso de picos como el Everest. Poblados como "
            "Namche Bazaar, el principal centro comercial y punto de aclimatación de la ruta, "
            "muestran la vida cotidiana de esta comunidad y su economía, hoy muy ligada al "
            "trekking y al montañismo internacional.</p> "
            "<p>La aclimatación es, sin discusión, el factor que más condiciona el éxito y la "
            "seguridad de esta ruta: el trekking gana altitud de forma constante durante varios "
            "días hasta superar los 5.000 metros, y el itinerario estándar incluye "
            "deliberadamente días de aclimatación en Namche Bazaar y Dingboche, con caminatas "
            "cortas a cotas superiores seguidas de descenso para dormir más bajo, aplicando el "
            "mismo principio de «subir alto, dormir bajo» que rige en cualquier ascenso de altitud "
            "seria.</p> "
            "<p>El acceso a la región se realiza casi siempre en un vuelo corto hasta el "
            "aeródromo de Lukla, considerado uno de los aeropuertos más desafiantes del mundo por "
            "su pista corta e inclinada, encajada entre montañas; las condiciones meteorológicas "
            "pueden retrasar estos vuelos con cierta frecuencia, por lo que conviene prever "
            "siempre un margen de días adicional en el itinerario ante posibles cancelaciones.</p> "
            "<p>El paisaje del valle del Khumbu combina bosques de rododendros en las cotas más "
            "bajas, monasterios budistas como el de Tengboche —con el Ama Dablam, una de las "
            "montañas más fotogénicas del Himalaya, como telón de fondo— y un paisaje "
            "progresivamente más árido y de alta montaña a medida que se gana altitud, hasta "
            "llegar al propio glaciar Khumbu y las morrenas que rodean el campo base.</p> "
            "<p>Llegar al campo base no ofrece, contrariamente a lo que a veces se supone, una "
            "vista directa de la cumbre del Everest, oculta desde ese ángulo por otras montañas "
            "cercanas; el mirador de Kala Patthar, una colina cercana al campamento que muchos "
            "trekkers añaden a la ruta con una madrugada adicional, es en cambio el punto desde "
            "el que sí se aprecia la cumbre del Everest con claridad, y suele considerarse el "
            "broche final de la travesía.</p> "
            "<p>La primera ascensión documentada al Everest, en 1953, por Edmund Hillary y Tenzing "
            "Norgay, un sherpa nepalí, consolidó a este pueblo de origen tibetano como referencia "
            "mundial del montañismo de altitud; desde entonces, generaciones de sherpas han "
            "trabajado "
            "como guías, porteadores de alta montaña y, cada vez más, como montañistas de pleno "
            "derecho en expediciones internacionales. El campo base del Everest, situado sobre la "
            "morrena del glaciar Khumbu, se convierte durante la temporada de ascensiones en un "
            "campamento temporal de cientos de personas, aunque el trekking hasta allí puede "
            "realizarse durante todo el año dentro de la ventana climática recomendada.</p> "
            "<p>El monasterio de Tengboche, uno de los más importantes del budismo tibetano en la "
            "región del Khumbu, celebra cada otoño el festival de Mani Rimdu, una ceremonia de "
            "varios "
            "días con danzas rituales que atrae tanto a peregrinos sherpas como a trekkers que "
            "coinciden con la fecha en su ruta hacia el campo base; para muchos visitantes, este "
            "festival ofrece una de las ventanas más directas a la vida espiritual sherpa dentro "
            "de un itinerario centrado, en principio, en el trekking de montaña.</p>"
        ),
        tipos_slugs=["alta-montana-y-alpinismo"],
        dificultad=4,
        meses_mejor_epoca=[3, 4, 5, 10, 11],
        duracion_min_dias=10,
        duracion_max_dias=14,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima de alta montaña himalaya, con dos temporadas principales recomendadas: "
            "primavera (marzo-mayo, con rododendros en flor en las cotas bajas) y otoño "
            "(octubre-noviembre, cielos más despejados); el monzón de verano y el frío extremo "
            "del pleno invierno hacen mucho más difícil la travesía fuera de esas ventanas.</p>"
        ),
        altitud_max_m=5545,
        como_llegar=(
            "<p>El acceso habitual es en vuelo internacional hasta Katmandú, capital de Nepal, y "
            "desde allí en un vuelo corto hasta el aeródromo de montaña de Lukla, punto de inicio "
            "del trekking; las condiciones meteorológicas pueden retrasar estos vuelos, por lo "
            "que conviene prever varios días de margen en el itinerario general del viaje.</p>"
        ),
        seguridad_riesgos=(
            "<p>El mal de altura es el riesgo principal de esta ruta, dada la altitud sostenida "
            "por encima de los 4.000 y 5.000 metros durante buena parte de la travesía; respetar "
            "los días de aclimatación del itinerario estándar, ascender de forma progresiva y "
            "estar atento a los síntomas de mal de altura, con la posibilidad de descender si no "
            "mejoran, son las medidas de seguridad más importantes de la región del Khumbu.</p>"
            + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El valle del Khumbu forma parte del Parque Nacional de Sagarmatha, Patrimonio de "
            "la Humanidad: llevarse toda la basura, usar agua tratada en lugar de botellas de "
            "plástico de un solo uso y contratar guías y porteadores sherpas locales con "
            "condiciones laborales adecuadas son prácticas centrales de un trekking responsable "
            "en esta región de alta montaña.</p>"
        ),
        latitud=27.9881,
        longitud=86.9250,
        seo_titulo="Campo base del Everest: guía experta del trekking del Khumbu",
        seo_descripcion=(
            "Aclimatación, ruta sherpa y Kala Patthar: guía experta del trekking al campo base "
            "del Everest, valle del Khumbu, Nepal."
        ),
        relacionados_slugs=["kilimanjaro", "camino-inca-machu-picchu", "pnn-los-nevados"],
    ),
    DestinoSemilla(
        n=21,
        titulo="Bahía de Ha Long",
        slug="bahia-de-ha-long",
        pais_slug="vietnam",
        resumen=(
            "Miles de islotes de piedra caliza cubiertos de selva emergiendo de aguas "
            "esmeralda, recorridos en kayak entre cuevas y aldeas flotantes."
        ),
        descripcion_experta=(
            "<p>La bahía de Ha Long, en el norte de Vietnam, reúne varios miles de islas e "
            "islotes de piedra caliza cubiertos de vegetación que emergen de forma abrupta de "
            "aguas de un verde esmeralda característico, formados por la erosión kárstica de una "
            "plataforma caliza a lo largo de varios millones de años. La leyenda vietnamita que "
            "da nombre a la bahía —«Ha Long» significa aproximadamente «donde desciende el "
            "dragón»— cuenta que estos islotes son los restos de joyas escupidas al mar por un "
            "dragón para defender la costa de invasores, un relato que refleja bien la escala "
            "casi fantástica del paisaje.</p> "
            "<p>La forma más habitual de conocer la bahía es a bordo de un crucero tradicional de "
            "una o varias noches, con embarcaciones que navegan lentamente entre los islotes, "
            "haciendo paradas para explorar cuevas —algunas con formaciones de estalactitas y "
            "estalagmitas de gran tamaño— y para actividades de kayak entre formaciones rocosas "
            "y arcos naturales que solo son accesibles remando a ras de agua, demasiado estrechos "
            "o bajos para cualquier embarcación mayor.</p> "
            "<p>El kayak en Ha Long permite acercarse a rincones de la bahía inaccesibles de otra "
            "forma: túneles naturales excavados en la roca caliza que conectan lagunas interiores "
            "ocultas dentro de los propios islotes, y aldeas flotantes de pescadores, algunas con "
            "generaciones de historia sobre el agua, que muestran una forma de vida "
            "tradicionalmente ligada a la pesca y, cada vez más, al propio turismo de la "
            "bahía.</p> <p>La cercana bahía de Lan Ha, geológicamente parte del mismo sistema "
            "kárstico pero administrada de forma independiente, ofrece un paisaje muy similar con "
            "una afluencia de visitantes considerablemente menor, y se ha convertido en una "
            "alternativa habitual para quien busca una experiencia más tranquila que la bahía de "
            "Ha Long propiamente dicha, declarada Patrimonio de la Humanidad y uno de los "
            "destinos más visitados de Vietnam.</p> "
            "<p>El clima subtropical de la región, con una temporada de tifones que puede afectar "
            "la navegación entre finales de verano y otoño, y una temporada más fresca y a veces "
            "neblinosa en invierno, condiciona tanto la comodidad de la travesía en barco como la "
            "visibilidad del paisaje; la primavera y el otoño suelen considerarse las estaciones "
            "más equilibradas para visitar la bahía.</p> "
            "<p>El crecimiento del turismo en la bahía en las últimas décadas ha llevado a las "
            "autoridades vietnamitas a reforzar la regulación de las rutas de navegación y el "
            "número de embarcaciones autorizadas, en parte para proteger un ecosistema marino y "
            "kárstico de un valor geológico excepcional, y en parte para gestionar el propio "
            "tráfico de cruceros turísticos que la bahía recibe cada temporada.</p> "
            "<p>La bahía ha sido escenario de varias producciones cinematográficas internacionales "
            "que han contribuido a su fama global, pero su valor documentado va mucho más allá de "
            "la "
            "imagen: geólogos consideran el karst de Ha Long uno de los ejemplos mejor conservados "
            "a "
            "escala mundial de evolución kárstica en clima tropical húmedo, con formaciones que "
            "llevan desarrollándose varios cientos de millones de años. Las comunidades de "
            "pescadores "
            "que aún habitan algunas aldeas flotantes de la bahía mantienen una forma de vida que "
            "las "
            "autoridades vietnamitas han comenzado a documentar y proteger como patrimonio "
            "cultural, "
            "no solo como atractivo turístico.</p> "
            "<p>La bahía cuenta con más de una cueva marina de acceso exclusivo en kayak, entre "
            "ellas "
            "la Cueva Luon y la Cueva Sorpresa, cuyos nombres reflejan el asombro con el que "
            "navegantes y visitantes han descrito históricamente estos espacios interiores ocultos "
            "dentro de los propios islotes calizos; algunas de estas cuevas solo son accesibles "
            "durante determinadas horas de marea baja, lo que añade un componente de planificación "
            "adicional a las salidas de kayak más ambiciosas de la bahía.</p>"
        ),
        tipos_slugs=["kayak-y-navegacion"],
        dificultad=1,
        meses_mejor_epoca=[3, 4, 10, 11],
        duracion_min_dias=2,
        duracion_max_dias=3,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima subtropical húmedo, con una temporada de tifones posible entre finales de "
            "verano y otoño que puede afectar la navegación, y un invierno más fresco y a veces "
            "neblinoso; la primavera y el otoño suelen ofrecer el mejor equilibrio entre "
            "temperatura agradable y buena visibilidad.</p>"
        ),
        altitud_max_m=200,
        como_llegar=(
            "<p>El acceso habitual es en vuelo internacional hasta Hanói, la capital "
            "vietnamita, y desde allí por carretera hasta el puerto de la bahía de Ha Long, donde "
            "parten los cruceros; también existen traslados organizados directamente desde "
            "Hanói que incluyen el trayecto por carretera como parte del paquete de crucero.</p>"
        ),
        seguridad_riesgos=(
            "<p>El principal riesgo son las condiciones marítimas adversas, en particular durante "
            "la temporada de tifones de finales de verano y otoño, cuando algunas navegaciones "
            "pueden cancelarse o modificar su ruta por seguridad; verificar la fiabilidad y las "
            "medidas de seguridad (chalecos salvavidas, embarcaciones en buen estado) del "
            "operador de crucero elegido es la precaución más importante.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>La regulación de rutas y número de embarcaciones busca proteger un ecosistema "
            "kárstico marino único; elegir operadores de crucero con políticas activas contra el "
            "vertido de residuos al mar y respetar las aldeas flotantes de pescadores como "
            "comunidades habitadas, no como atracciones fotográficas, forma parte de una visita "
            "responsable a la bahía.</p>"
        ),
        latitud=20.9101,
        longitud=107.1839,
        seo_titulo="Bahía de Ha Long: guía de crucero y kayak en Vietnam",
        seo_descripcion=(
            "Cruceros, cuevas kársticas y kayak entre islotes: guía experta de la bahía de Ha "
            "Long, Patrimonio de la Humanidad en Vietnam."
        ),
        relacionados_slugs=["fiordos-de-noruega", "gran-barrera-de-coral", "islas-galapagos"],
    ),
    DestinoSemilla(
        n=22,
        titulo="Wadi Rum",
        slug="wadi-rum",
        pais_slug="jordania",
        resumen=(
            "El «valle de la luna» jordano: un desierto de arena roja y formaciones de arenisca "
            "monumentales, escenario de expediciones beduinas y escalada en roca del desierto."
        ),
        descripcion_experta=(
            "<p>Wadi Rum, en el sur de Jordania, es un valle desértico de arena rojiza dominado "
            "por macizos de arenisca y granito que se elevan de forma abrupta sobre el llano, "
            "esculpidos durante millones de años por la erosión del viento y, en épocas "
            "geológicas mucho más húmedas, del agua. La escala y el color del paisaje —a menudo "
            "descrito como un «valle de la luna» por su aspecto casi extraterrestre— lo han "
            "convertido en escenario de varias producciones cinematográficas ambientadas en Marte "
            "o en otros mundos, además de ser el territorio donde T. E. Lawrence («Lawrence de "
            "Arabia») operó durante la revuelta árabe de la Primera Guerra Mundial, un episodio "
            "histórico que sigue muy presente en la identidad del lugar.</p> "
            "<p>El valle está habitado desde hace generaciones por comunidades beduinas, cuyo "
            "conocimiento del desierto —la orientación sin referencias visuales aparentes, la "
            "localización de fuentes de agua, la lectura de las condiciones del terreno para "
            "vehículos 4x4 o camellos— sigue siendo hoy la base de la práctica totalidad de las "
            "expediciones turísticas por la zona. Dormir en un campamento beduino, muchos de "
            "ellos gestionados por familias locales, bajo un cielo con muy baja contaminación "
            "lumínica, es una parte central de la experiencia de visitar Wadi Rum, no solo un "
            "complemento logístico.</p> "
            "<p>Las formas de recorrer el valle son variadas: en vehículo 4x4 con conductor "
            "beduino por las pistas de arena entre los macizos, en camello siguiendo rutas más "
            "tradicionales, o a pie en travesías cortas o de varios días con guía, que permiten "
            "acceder a cañones estrechos, puentes de roca naturales y grabados rupestres "
            "milenarios dejados por las civilizaciones que han habitado esta región del desierto "
            "a lo largo de miles de años.</p> "
            "<p>Wadi Rum es también, desde hace décadas, un destino reconocido de escalada en "
            "roca de desierto: sus paredes de arenisca ofrecen rutas de varios largos con un "
            "estilo de escalada particular, en una roca más blanda y con una textura distinta a "
            "la del granito alpino, que ha atraído a escaladores internacionales junto a una "
            "comunidad local de guías beduinos formados en la disciplina.</p> "
            "<p>La amplitud térmica del desierto es uno de los rasgos que más sorprende a quien "
            "visita Wadi Rum por primera vez: el calor intenso del día, con el sol reflejándose "
            "en la arena y la roca, da paso a noches considerablemente frías, especialmente en "
            "los meses de invierno, lo que exige llevar ropa de abrigo incluso para un viaje "
            "pensado en clave estrictamente desértica.</p> "
            "<p>El turismo de expedición y campamento beduino se ha convertido en una fuente de "
            "ingresos central para las comunidades locales del valle, y elegir operadores y "
            "campamentos gestionados directamente por familias beduinas de la zona, en lugar de "
            "intermediarios externos, es una forma directa de que la visita beneficie a quienes "
            "han habitado y cuidado este desierto durante generaciones.</p> "
            "<p>Wadi Rum fue declarado Patrimonio de la Humanidad por la UNESCO tanto por su valor "
            "natural como cultural, en reconocimiento a los miles de años de presencia humana "
            "documentados en sus grabados rupestres e inscripciones, que narran la evolución de la "
            "fauna, el clima y las actividades humanas en la región desde tiempos prehistóricos. "
            "La gestión conjunta entre el gobierno jordano y las comunidades beduinas locales, que "
            "participan directamente en la administración del área protegida, se cita a menudo "
            "como un modelo de conservación que combina protección ambiental con reconocimiento de "
            "los derechos y el conocimiento de las comunidades tradicionales del desierto.</p> "
            "<p>Wadi Rum sirvió de escenario y también de inspiración para varias producciones "
            "cinematográficas ambientadas en paisajes marcianos, precisamente por el color rojizo "
            "de "
            "su arena y la escala de sus formaciones rocosas, lo que ha añadido en las últimas "
            "décadas una capa adicional de interés turístico al valle sin restar protagonismo a su "
            "historia beduina y arqueológica, mucho más antigua que cualquier producción "
            "audiovisual "
            "reciente.</p>"
        ),
        tipos_slugs=["travesias-por-desierto-y-expediciones"],
        dificultad=2,
        meses_mejor_epoca=[3, 4, 5, 10, 11],
        duracion_min_dias=2,
        duracion_max_dias=4,
        nivel_presupuesto=2,
        clima=(
            "<p>Clima desértico extremo: calor intenso durante el día, especialmente en verano, "
            "y noches frías todo el año, más acusadas en invierno; primavera y otoño ofrecen el "
            "equilibrio más cómodo de temperaturas para las expediciones y el senderismo por el "
            "valle.</p>"
        ),
        altitud_max_m=1750,
        como_llegar=(
            "<p>El acceso habitual es en vuelo internacional hasta Amán, la capital de Jordania, "
            "o hasta Aqaba, en el sur del país, y desde allí por carretera hasta la entrada del "
            "valle de Wadi Rum, donde los campamentos y operadores beduinos organizan el resto "
            "del traslado en vehículo 4x4.</p>"
        ),
        seguridad_riesgos=(
            "<p>La orientación en el desierto sin guía experimentado, el golpe de calor durante "
            "el día y el frío nocturno sin ropa de abrigo adecuada son los riesgos principales "
            "del valle; recorrer siempre el desierto con guías beduinos locales, que conocen el "
            "terreno y las condiciones cambiantes de la arena, es la medida de seguridad más "
            "relevante.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>Elegir campamentos y operadores gestionados directamente por familias beduinas "
            "locales sostiene la economía tradicional del valle; llevarse toda la basura, "
            "respetar los grabados rupestres milenarios sin tocarlos y minimizar la "
            "contaminación lumínica de los campamentos ayuda a conservar tanto el patrimonio "
            "arqueológico como los cielos oscuros que son parte del atractivo de Wadi Rum.</p>"
        ),
        latitud=29.5760,
        longitud=35.4206,
        seo_titulo="Wadi Rum: guía de expediciones por el desierto jordano",
        seo_descripcion=(
            "Campamentos beduinos, 4x4 y escalada en roca del desierto: guía experta de Wadi "
            "Rum, el valle de la luna en el sur de Jordania."
        ),
        relacionados_slugs=["salar-de-uyuni", "delta-del-okavango", "kilimanjaro"],
    ),
    DestinoSemilla(
        n=23,
        titulo="Queenstown",
        slug="queenstown",
        pais_slug="nueva-zelanda",
        resumen=(
            "La autoproclamada capital mundial de la aventura: bungee, parapente, rafting y "
            "ciclismo de montaña junto a un lago alpino de Nueva Zelanda."
        ),
        descripcion_experta=(
            "<p>Queenstown, a orillas del lago Wakatipu en la Isla Sur de Nueva Zelanda, se "
            "promociona a sí misma como la capital mundial de la aventura, un título que "
            "respalda con una concentración de actividades de adrenalina pocas veces igualada en "
            "un solo destino: fue aquí donde, en 1988, se inauguró la primera operación "
            "comercial de salto en bungee del mundo, sobre el puente Kawarau, y desde entonces la "
            "ciudad ha ido sumando prácticamente toda la gama de deportes de aventura moderna a "
            "su oferta turística.</p> "
            "<p>El parapente es una de las actividades más practicadas gracias a la orografía "
            "favorable de la región, con despegues desde la cercana montaña Bob's Peak que "
            "ofrecen vistas directas sobre el lago Wakatipu y la cordillera circundante en vuelos "
            "en tándem accesibles sin formación previa. El rafting y el jet boat —un tipo de "
            "lancha de propulsión a chorro desarrollada precisamente en Nueva Zelanda para "
            "navegar aguas poco profundas a gran velocidad— se practican en los cañones del río "
            "Shotover y en el río Kawarau, con tramos de distinta intensidad según la época y el "
            "caudal.</p> "
            "<p>El ciclismo de montaña es otro de los pilares de la oferta de Queenstown: el "
            "Queenstown Bike Park, en la ladera de la montaña Bob's Peak con acceso por "
            "telecabina, es uno de los circuitos de descenso más reconocidos internacionalmente, "
            "con rutas señalizadas por dificultad para todos los niveles, desde principiantes "
            "hasta descenso técnico avanzado; la región cuenta además con una extensa red de "
            "rutas de cross-country por los valles y colinas circundantes.</p> "
            "<p>Más allá de los deportes de mayor adrenalina, Queenstown es también punto de "
            "partida de senderismo de calidad, con rutas de montaña que se pueden combinar con "
            "otras actividades más tranquilas, y de esquí alpino en las estaciones cercanas "
            "durante el invierno austral, lo que convierte a la región en un destino activo "
            "durante todo el año, con una oferta que cambia según la temporada.</p> "
            "<p>El clima alpino de la región, con veranos australes templados (diciembre-febrero) "
            "e inviernos fríos con nieve en las montañas circundantes, condiciona qué actividades "
            "resultan más recomendables según la época: el rafting y el parapente son posibles "
            "durante buena parte del año según las condiciones del día, mientras que el ciclismo "
            "de montaña en el bike park se concentra sobre todo en la temporada cálida.</p> "
            "<p>La seguridad de esta concentración de deportes de aventura descansa en gran "
            "medida en la madurez regulatoria de Nueva Zelanda, uno de los países con estándares "
            "más exigentes y consolidados del mundo para la industria del turismo de aventura "
            "comercial; aun así, elegir siempre operadores certificados, con guías o pilotos "
            "acreditados y equipo revisado, sigue siendo la decisión más determinante para la "
            "seguridad de cualquier visitante.</p> "
            "<p>Antes de convertirse en sinónimo de deportes de aventura, Queenstown fue un centro "
            "minero de la fiebre del oro neozelandesa de la década de 1860, un pasado que todavía "
            "se "
            "puede rastrear en varios pueblos históricos cercanos convertidos hoy en atracción "
            "turística. La topografía glaciar de la región —el propio lago Wakatipu ocupa una "
            "antigua "
            "lengua de hielo con una forma de zeta característica— es la misma que, siglos "
            "después, ha dado a Queenstown la combinación de montaña, agua y desnivel que sostiene "
            "hoy su industria de deportes de aventura.</p> "
            "<p>El lago Wakatipu, a cuyas orillas se asienta Queenstown, tiene una profundidad "
            "considerable típica de los lagos glaciares de origen tectónico, y su nivel presenta "
            "un fenómeno natural de oscilación periódica de varios centímetros conocido localmente "
            "como "
            "«el latido» del lago, atribuido a variaciones de presión atmosférica sobre una masa "
            "de agua tan extensa; ese mismo lago es también escenario de recorridos en barco de "
            "vapor histórico, una alternativa más tranquila a la oferta de deportes extremos de la "
            "ciudad.</p>"
        ),
        tipos_slugs=[
            "parapente-y-deportes-aereos",
            "ciclismo-de-montana",
            "rafting-y-deportes-de-rio",
        ],
        dificultad=2,
        meses_mejor_epoca=[12, 1, 2, 3],
        duracion_min_dias=3,
        duracion_max_dias=6,
        nivel_presupuesto=4,
        clima=(
            "<p>Clima alpino templado del hemisferio sur: veranos australes (diciembre-febrero) "
            "suaves y agradables para la mayoría de actividades de aventura, e inviernos fríos "
            "con nieve en las montañas cercanas, orientados al esquí alpino en las estaciones de "
            "la región.</p>"
        ),
        altitud_max_m=1900,
        como_llegar=(
            "<p>El acceso habitual es en vuelo doméstico o internacional directo hasta el "
            "aeropuerto de Queenstown, en la Isla Sur de Nueva Zelanda; la propia ciudad es "
            "compacta y la mayoría de operadores de aventura ofrecen recogida desde el centro o "
            "el alojamiento.</p>"
        ),
        seguridad_riesgos=(
            "<p>Cada actividad tiene su propio riesgo específico —caída en bungee y parapente por "
            "fallo de equipo (muy infrecuente con operadores certificados), vuelco en rafting o "
            "jet boat, caídas en ciclismo de descenso—; Nueva Zelanda mantiene una regulación "
            "exigente sobre la industria de turismo de aventura, y elegir siempre operadores "
            "certificados con guías o pilotos acreditados es la medida de seguridad común a todas "
            "ellas.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>La alta concentración de actividades y visitantes en una región alpina "
            "relativamente pequeña exige un uso cuidadoso del entorno: mantenerse en los "
            "circuitos y senderos señalizados, especialmente en el bike park, y respetar los "
            "caudales ecológicos de los ríos Shotover y Kawarau forma parte de una visita "
            "responsable a esta región neozelandesa.</p>"
        ),
        latitud=-45.0312,
        longitud=168.6626,
        seo_titulo="Queenstown: guía de deportes de aventura en Nueva Zelanda",
        seo_descripcion=(
            "Parapente, rafting, ciclismo de montaña y bungee: guía experta de deportes de "
            "aventura en Queenstown, Nueva Zelanda."
        ),
        relacionados_slugs=["banff", "yosemite", "chamonix-mont-blanc"],
    ),
    DestinoSemilla(
        n=24,
        titulo="Gran Barrera de Coral",
        slug="gran-barrera-de-coral",
        pais_slug="australia",
        resumen=(
            "El mayor sistema de arrecifes de coral del mundo, frente a la costa australiana de "
            "Queensland, con buceo y esnórquel entre una biodiversidad marina extraordinaria."
        ),
        descripcion_experta=(
            "<p>La Gran Barrera de Coral, frente a la costa de Queensland en el noreste de "
            "Australia, es el mayor sistema de arrecifes de coral del mundo, una estructura viva "
            "formada por miles de arrecifes individuales e islas a lo largo de una extensión de "
            "costa de varios miles de kilómetros, visible incluso desde el espacio y reconocida "
            "como Patrimonio de la Humanidad por la UNESCO. Su biodiversidad marina es una de las "
            "más ricas del planeta: varios cientos de especies de coral duro conviven con miles "
            "de especies de peces, tortugas marinas, tiburones de arrecife, rayas y, de forma "
            "estacional, tiburones ballena y ballenas jorobadas en su ruta migratoria.</p> "
            "<p>El acceso al arrecife se organiza principalmente desde varias localidades "
            "costeras de Queensland, cada una con acceso a tramos distintos del sistema: Cairns y "
            "Port Douglas, en el norte, dan acceso a arrecifes exteriores de aguas más cálidas y "
            "coral especialmente vistoso, mientras que las islas Whitsunday, más al sur, combinan "
            "el buceo y el esnórquel con playas de arena blanca de sílice extremadamente fina, "
            "resultado de la composición mineral particular de esa zona de la costa.</p> "
            "<p>La oferta de inmersión cubre un rango muy amplio: desde salidas de esnórquel de "
            "un día en catamarán hasta cero embarcaciones especializadas de buceo de varios días "
            "que navegan hasta arrecifes exteriores más alejados de la costa, con mejor "
            "visibilidad y menor presión de visitantes que los puntos más cercanos a tierra. Para "
            "quien no cuenta con certificación de buceo, la mayoría de operadores ofrecen "
            "bautismos de buceo introductorios supervisados por instructor, además de amplias "
            "zonas de esnórquel accesibles sin ninguna formación previa.</p> "
            "<p>El blanqueamiento de coral, un fenómeno de estrés térmico que ocurre cuando la "
            "temperatura del agua sube por encima de los límites de tolerancia del coral y este "
            "expulsa las algas que le dan color y buena parte de su energía, ha afectado a "
            "distintas partes de la Gran Barrera en años recientes de forma documentada por "
            "investigadores marinos australianos. Este fenómeno ha situado al arrecife en el "
            "centro del debate internacional sobre el impacto del cambio climático en los "
            "ecosistemas marinos, y ha impulsado programas de monitoreo, restauración e "
            "investigación de gran escala en la región.</p> "
            "<p>La gestión del arrecife, a cargo de la autoridad marina australiana, combina la "
            "protección ambiental con un turismo regulado que incluye una tarifa ambiental "
            "aplicada a la mayoría de excursiones, destinada a financiar la investigación y "
            "conservación del ecosistema; los operadores autorizados siguen protocolos "
            "específicos sobre puntos de fondeo, número de personas por sitio de inmersión y "
            "comportamiento respetuoso con el coral y la fauna.</p> "
            "<p>Más allá del buceo y el esnórquel, sobrevolar la Gran Barrera en avioneta o "
            "helicóptero es una forma habitual de apreciar la escala completa del sistema de "
            "arrecifes, incluido el conocido Corazón de Arrecife (Heart Reef), una formación de "
            "coral con esa forma natural cerca de las islas Whitsunday que se ha convertido en "
            "una de las imágenes más reconocibles de la región.</p> "
            "<p>La Gran Barrera de Coral no es una estructura única sino un mosaico de cerca de "
            "tres "
            "mil arrecifes individuales y varios cientos de islas, lo que explica la enorme "
            "variedad "
            "de experiencias posibles dentro de un mismo sistema, desde arrecifes de aguas someras "
            "aptos para el esnórquel familiar hasta paredes de buceo profundo en el extremo "
            "exterior "
            "de la plataforma continental australiana. James Cook encalló su barco en parte de "
            "este sistema en 1770 durante su viaje de exploración por el Pacífico, un episodio "
            "histórico que dejó constancia temprana, en fuentes europeas, de la magnitud de este "
            "arrecife frente a la costa de lo que hoy es Queensland.</p>"
        ),
        tipos_slugs=["buceo-y-snorkel"],
        dificultad=2,
        meses_mejor_epoca=[6, 7, 8, 9, 10],
        duracion_min_dias=2,
        duracion_max_dias=5,
        nivel_presupuesto=3,
        clima=(
            "<p>Clima tropical, con una estación seca más fresca y estable (aproximadamente "
            "junio-octubre, la más recomendada para buceo por su mejor visibilidad) y una "
            "estación húmeda y calurosa el resto del año, con mayor probabilidad de ciclones "
            "tropicales en la costa de Queensland.</p>"
        ),
        altitud_max_m=None,
        como_llegar=(
            "<p>El acceso habitual es en vuelo hasta Cairns, Port Douglas o el aeropuerto de "
            "Whitsunday Coast, en el estado australiano de Queensland, puntos de partida "
            "habituales de las excursiones y cruceros de buceo y esnórquel hacia los distintos "
            "sectores del arrecife.</p>"
        ),
        seguridad_riesgos=(
            "<p>Las corrientes marinas y la presencia estacional de medusas de picadura "
            "peligrosa en algunas zonas costeras de Queensland son los riesgos más citados; los "
            "operadores autorizados exigen certificación vigente para el buceo autónomo y "
            "proporcionan trajes de protección contra medusas cuando corresponde según la "
            "temporada y la ubicación.</p>" + _DESCARGO
        ),
        sostenibilidad=(
            "<p>El blanqueamiento de coral por el aumento de la temperatura del agua es una "
            "amenaza documentada sobre el arrecife: usar protector solar apto para arrecifes, no "
            "tocar ni pisar el coral y elegir operadores certificados por la autoridad marina "
            "australiana, que financian con su tarifa ambiental la investigación y conservación "
            "del ecosistema, son prácticas centrales de una visita responsable.</p>"
        ),
        latitud=-18.2871,
        longitud=147.6992,
        seo_titulo="Gran Barrera de Coral: guía experta de buceo en Australia",
        seo_descripcion=(
            "Buceo, esnórquel y conservación del coral: guía experta de la Gran Barrera de "
            "Coral, Queensland, Australia."
        ),
        relacionados_slugs=["islas-galapagos", "cenotes-de-yucatan", "bahia-de-ha-long"],
    ),
]
