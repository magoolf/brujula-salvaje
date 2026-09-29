"""10 guías expertas (REQ-041, Must >=10) repartidas en las 8 categorías semilla ya sembradas por
`apps.catalogos.migrations.0002_semilla` (slugs literales, no se crean categorías nuevas).

Todas marcan `remite_a_metodologia=True` (RULE-004): en vez de citar fuentes externas concretas
—que este comando no puede verificar de forma fiable, DEC-AUTO-033—, remiten a la página
"Acerca de / Metodología editorial" (REQ-025) que explica el criterio editorial del equipo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuiaSemilla:
    titulo: str
    slug: str
    categoria_slug: str
    resumen: str
    cuerpo: str
    destinos_slugs: list[str]
    tipos_slugs: list[str]
    seo_titulo: str
    seo_descripcion: str
    relacionados_slugs: list[str] = field(default_factory=list)
    terminos_slugs: list[str] = field(default_factory=list)


GUIAS: list[GuiaSemilla] = [
    GuiaSemilla(
        titulo="Cómo entrenar antes de tu primera aventura de varios días",
        slug="como-entrenar-antes-de-tu-primera-aventura",
        categoria_slug="preparacion-fisica",
        resumen=(
            "Una guía práctica para preparar el cuerpo antes de un trekking o una expedición de "
            "varios días, sin necesidad de ser un atleta."
        ),
        cuerpo=(
            "<p>La preparación física para una aventura de varios días no exige convertirse en "
            "un atleta de élite: exige, sobre todo, acostumbrar al cuerpo a sostener un esfuerzo "
            "moderado de forma repetida, día tras día, algo bastante distinto de la capacidad de "
            "hacer un esfuerzo intenso y puntual. Por eso el entrenamiento más útil para un "
            "trekking de varios días no es necesariamente el que mejora la marca en una carrera "
            "corta, sino el que construye resistencia acumulada.</p>"
            "<h2>Resistencia cardiovascular de base</h2>"
            "<p>Caminar, correr suave, nadar o pedalear con regularidad, varias veces por "
            "semana durante las semanas previas al viaje, construye la base aeróbica que "
            "sostendrá varias horas diarias de esfuerzo. Es preferible la constancia moderada a "
            "sesiones ocasionales muy intensas: el cuerpo se adapta mejor a un estímulo "
            "repetido que a picos aislados de esfuerzo.</p>"
            "<h2>Fuerza de piernas y núcleo</h2>"
            "<p>El desnivel, tanto de subida como de bajada, es el factor que más fatiga las "
            "piernas en una ruta de montaña; ejercicios de fuerza como sentadillas, zancadas o "
            "subir escaleras con carga progresiva ayudan a preparar los músculos que "
            "amortiguan el impacto de los descensos, a menudo más exigentes para las "
            "articulaciones que las subidas.</p>"
            "<h2>Caminatas de práctica con la mochila real</h2>"
            "<p>Nada sustituye a salir a caminar varias horas seguidas con el mismo calzado y "
            "una mochila con un peso similar al que se llevará en el viaje: es la mejor forma "
            "de detectar puntos de roce, ajustar el sistema de la mochila y comprobar cómo "
            "responde el cuerpo a un esfuerzo prolongado antes de que importe de verdad.</p>"
            "<h2>Cuándo empezar</h2>"
            "<p>Para un trekking de dificultad moderada, entre seis y ocho semanas de "
            "preparación regular suelen ser suficientes para la mayoría de personas con una "
            "condición física de partida razonable; para rutas de alta montaña o mayor "
            "exigencia, ese margen conviene ampliarlo, y siempre es preferible llegar "
            "ligeramente sobrepreparado que justo al límite.</p>"
        ),
        destinos_slugs=["ciudad-perdida-teyuna", "torres-del-paine", "camino-inca-machu-picchu"],
        tipos_slugs=["senderismo-y-trekking"],
        seo_titulo="Cómo entrenar para tu primera aventura de varios días",
        seo_descripcion=(
            "Guía práctica de preparación física para un trekking o expedición de varios días, "
            "sin necesidad de ser un atleta."
        ),
        relacionados_slugs=["primeros-pasos-para-elegir-tu-primera-aventura"],
    ),
    GuiaSemilla(
        titulo="Cómo elegir y organizar la mochila de trekking",
        slug="como-elegir-y-organizar-la-mochila-de-trekking",
        categoria_slug="equipo-y-mochila",
        resumen=(
            "Qué tamaño de mochila elegir, cómo distribuir el peso y qué llevar siempre a "
            "mano en una ruta de varios días."
        ),
        cuerpo=(
            "<p>La mochila es, junto con el calzado, el elemento de equipo que más influye en "
            "cómo se siente una caminata de varios días: una mochila mal ajustada o mal "
            "cargada puede convertir una ruta razonable en una experiencia incómoda, "
            "independientemente de la forma física de quien la lleva.</p>"
            "<h2>El tamaño adecuado</h2>"
            "<p>Para excursiones de un día, entre 20 y 30 litros suele ser suficiente; para "
            "trekkings de varios días con pernocta en refugios (sin necesidad de cargar tienda "
            "ni comida completa), entre 35 y 50 litros; y para expediciones autosuficientes con "
            "campamento propio, 50 litros o más. Elegir una mochila más grande de lo necesario "
            "suele acabar en exceso de peso, porque el espacio disponible tiende a llenarse.</p>"
            "<h2>Cómo distribuir el peso</h2>"
            "<p>Los objetos más pesados deben ir cerca de la espalda y a la altura de los "
            "hombros u omóplatos, para que el peso se transmita a las caderas a través del "
            "cinturón lumbar en lugar de tirar hacia atrás de los hombros; los objetos ligeros "
            "y voluminosos, como el saco de dormir, suelen ir en la parte baja.</p>"
            "<h2>Qué llevar siempre accesible</h2>"
            "<ul>"
            "<li>Agua y snacks, sin tener que abrir la mochila entera.</li>"
            "<li>Capa impermeable, ante un cambio de tiempo repentino.</li>"
            "<li>Botiquín básico y protección solar.</li>"
            "<li>Mapa, track descargado o el sistema de navegación elegido.</li>"
            "</ul>"
            "<h2>Ajuste antes de salir</h2>"
            "<p>El cinturón lumbar debe apoyar sobre la cresta de la cadera, no sobre la "
            "cintura, y las correas de los hombros solo deben estabilizar la carga, no "
            "sostener su peso principal. Probar el ajuste completo, con el peso real que se "
            "llevará, antes del primer día de ruta evita sorpresas incómodas a mitad de "
            "camino.</p>"
        ),
        destinos_slugs=["torres-del-paine", "pnn-los-nevados"],
        tipos_slugs=["senderismo-y-trekking", "alta-montana-y-alpinismo"],
        seo_titulo="Cómo elegir y organizar la mochila de trekking",
        seo_descripcion=(
            "Tamaño de mochila, distribución del peso y qué llevar siempre a mano en una ruta "
            "de trekking de varios días."
        ),
        relacionados_slugs=["como-entrenar-antes-de-tu-primera-aventura"],
    ),
    GuiaSemilla(
        titulo="Cómo evaluar riesgos antes de salir al terreno",
        slug="como-evaluar-riesgos-antes-de-salir-al-terreno",
        categoria_slug="seguridad-y-gestion-de-riesgos",
        resumen=(
            "Una checklist mental para evaluar el riesgo real de una ruta antes de salir, más "
            "allá de la dificultad indicada."
        ),
        cuerpo=(
            "<p>La dificultad indicada de una ruta es solo un punto de partida: el riesgo real "
            "de una jornada concreta depende también del clima del día, del estado físico de "
            "quien la recorre, de la información disponible y de la capacidad de respuesta "
            "ante un imprevisto. Evaluar estos factores antes de salir, no solo la etiqueta de "
            "dificultad, es la base de cualquier gestión de riesgo razonable.</p>"
            "<h2>El terreno y las condiciones del día</h2>"
            "<p>Una misma ruta puede tener un riesgo muy distinto según la lluvia reciente, la "
            "presencia de nieve o hielo fuera de temporada, o el caudal de los ríos a cruzar. "
            "Consultar la previsión meteorológica actualizada y, cuando exista, el parte de "
            "condiciones de la autoridad local del parque o reserva, es un paso "
            "imprescindible antes de cualquier salida.</p>"
            "<h2>El propio estado</h2>"
            "<p>La fatiga acumulada de días anteriores, un malestar leve que podría empeorar, o "
            "la falta de aclimatación en altitud son factores tan relevantes como el terreno "
            "en sí. Ser honesto sobre el propio estado, y no solo sobre la dificultad "
            "«oficial» de la ruta, evita buena parte de los incidentes evitables.</p>"
            "<h2>El plan de comunicación y de respuesta</h2>"
            "<ul>"
            "<li>Compartir la ruta y la hora prevista de regreso con alguien que no participa "
            "en la actividad.</li>"
            "<li>Conocer el punto de cobertura telefónica más cercano o llevar comunicación "
            "satelital si la ruta lo requiere.</li>"
            "<li>Saber cuál es el protocolo de rescate o evacuación de la zona antes de salir, "
            "no averiguarlo cuando ya hace falta.</li>"
            "</ul>"
            "<h2>La decisión de dar la vuelta</h2>"
            "<p>La decisión más difícil, y a menudo la más importante, es la de dar la vuelta "
            "antes de completar la ruta cuando las condiciones cambian a peor; tratarla como "
            "una opción normal y no como un fracaso es, según coinciden guías y rescatistas de "
            "montaña, una de las actitudes que más incidentes evita.</p>"
        ),
        destinos_slugs=["torres-del-paine", "everest-campo-base", "pnn-los-nevados"],
        tipos_slugs=["alta-montana-y-alpinismo", "senderismo-y-trekking"],
        seo_titulo="Cómo evaluar riesgos antes de salir al terreno",
        seo_descripcion=(
            "Checklist práctica para evaluar el riesgo real de una ruta de aventura antes de "
            "salir, más allá de la dificultad indicada."
        ),
        relacionados_slugs=["que-llevar-en-un-botiquin-de-aventura"],
    ),
    GuiaSemilla(
        titulo="Qué llevar en un botiquín de aventura",
        slug="que-llevar-en-un-botiquin-de-aventura",
        categoria_slug="seguridad-y-gestion-de-riesgos",
        resumen=(
            "El contenido mínimo de un botiquín para trekking y actividades al aire libre, y "
            "cómo adaptarlo según la actividad."
        ),
        cuerpo=(
            "<p>Un botiquín de aventura no necesita ser exhaustivo para ser útil: la mayoría de "
            "incidentes en el terreno son menores (ampollas, pequeños cortes, molestias "
            "digestivas) y se resuelven con un kit compacto y bien pensado, más que con una "
            "farmacia completa que nadie termina de cargar de verdad.</p>"
            "<h2>El núcleo básico</h2>"
            "<ul>"
            "<li>Material para ampollas: apósitos específicos y cinta adhesiva.</li>"
            "<li>Antisépticos y gasas para heridas pequeñas.</li>"
            "<li>Vendas elásticas para torceduras.</li>"
            "<li>Analgésicos y antiinflamatorios básicos.</li>"
            "<li>Medicación personal habitual, con margen suficiente para toda la duración del "
            "viaje.</li>"
            "</ul>"
            "<h2>Adaptaciones según la actividad</h2>"
            "<p>En rutas de altitud conviene sumar medicación para el mal de altura solo bajo "
            "indicación médica previa; en climas cálidos y húmedos, sales de rehidratación oral "
            "y tratamiento para picaduras de insecto; en actividades acuáticas, protección "
            "adicional para los oídos y prevención de la otitis del nadador.</p>"
            "<h2>Lo que no debe faltar aunque parezca menor</h2>"
            "<p>Una manta térmica ligera, un silbato para pedir ayuda y una linterna frontal de "
            "repuesto ocupan muy poco espacio y pueden marcar la diferencia en un imprevisto "
            "que se alarga más de lo previsto.</p>"
            "<h2>Formación básica</h2>"
            "<p>Llevar un botiquín completo tiene un valor limitado sin saber usarlo: un curso "
            "básico de primeros auxilios, y en actividades de mayor exigencia uno específico de "
            "primeros auxilios en montaña, es una inversión de tiempo que complementa "
            "cualquier equipo, por bueno que sea.</p>"
        ),
        destinos_slugs=["kilimanjaro", "delta-del-okavango", "cenotes-de-yucatan"],
        tipos_slugs=["senderismo-y-trekking", "buceo-y-snorkel"],
        seo_titulo="Qué llevar en un botiquín de aventura",
        seo_descripcion=(
            "Contenido mínimo de un botiquín para trekking y actividades al aire libre, "
            "adaptado según el tipo de aventura."
        ),
        relacionados_slugs=["como-evaluar-riesgos-antes-de-salir-al-terreno"],
    ),
    GuiaSemilla(
        titulo="Mal de altura: cómo prevenirlo y reconocerlo",
        slug="mal-de-altura-como-prevenirlo-y-reconocerlo",
        categoria_slug="salud-en-altitud-y-en-viaje",
        resumen=(
            "Qué es el mal de altura, cómo prevenirlo con una buena aclimatación y qué "
            "síntomas indican que hay que descender."
        ),
        cuerpo=(
            "<p>El mal de altura, o mal agudo de montaña, aparece cuando el cuerpo no ha tenido "
            "tiempo suficiente para adaptarse a la menor disponibilidad de oxígeno por encima "
            "de los 2.500-3.000 metros, aproximadamente. Puede afectar a cualquier persona, "
            "independientemente de su forma física, y no guarda relación directa con la edad o "
            "el entrenamiento previo.</p>"
            "<h2>La regla de la aclimatación progresiva</h2>"
            "<p>La estrategia más citada por la medicina de montaña es «subir alto, dormir "
            "bajo»: hacer excursiones cortas a una cota superior durante el día, pero volver a "
            "dormir a una altitud menor, y no ganar más de 300 a 500 metros de altitud de "
            "pernocta por día una vez superados los 3.000 metros, con un día de descanso cada "
            "pocos días de ascenso.</p>"
            "<h2>Síntomas a los que prestar atención</h2>"
            "<ul>"
            "<li>Dolor de cabeza persistente que no mejora con analgésicos habituales.</li>"
            "<li>Náuseas, pérdida de apetito o mareo.</li>"
            "<li>Fatiga desproporcionada al esfuerzo realizado.</li>"
            "<li>Dificultad para dormir, más allá de lo esperable en altitud.</li>"
            "</ul>"
            "<p>Síntomas más graves, como confusión, dificultad respiratoria en reposo o "
            "pérdida de coordinación, son señal de una urgencia médica que exige descenso "
            "inmediato.</p>"
            "<h2>Qué hacer si aparecen síntomas</h2>"
            "<p>La respuesta correcta ante síntomas persistentes de mal de altura es no seguir "
            "ascendiendo hasta que remitan, y descender si empeoran; ninguna medicación "
            "sustituye esta regla básica, aunque algunos fármacos, siempre bajo indicación "
            "médica previa al viaje, pueden ayudar a la aclimatación en ascensos programados "
            "con poco margen de tiempo.</p>"
        ),
        destinos_slugs=["kilimanjaro", "everest-campo-base", "pnn-los-nevados", "salar-de-uyuni"],
        tipos_slugs=["alta-montana-y-alpinismo"],
        seo_titulo="Mal de altura: cómo prevenirlo y reconocerlo",
        seo_descripcion=(
            "Guía práctica sobre el mal de altura: prevención con aclimatación progresiva y "
            "síntomas que exigen descender."
        ),
        relacionados_slugs=["que-llevar-en-un-botiquin-de-aventura"],
        terminos_slugs=["aclimatacion", "mal-de-altura"],
    ),
    GuiaSemilla(
        titulo="Principios de no dejar rastro en la naturaleza",
        slug="principios-de-no-dejar-rastro-en-la-naturaleza",
        categoria_slug="viaje-sostenible-y-no-dejar-rastro",
        resumen=(
            "Los principios básicos de «no dejar rastro» para minimizar el impacto ambiental "
            "de cualquier salida al aire libre."
        ),
        cuerpo=(
            "<p>«No dejar rastro» es un conjunto de principios, adoptados por parques "
            "nacionales y organizaciones de montaña de todo el mundo, para minimizar el "
            "impacto humano en espacios naturales cada vez más visitados. No son normas "
            "exclusivas de expediciones remotas: aplican igual de bien a una caminata de un "
            "día cerca de casa.</p>"
            "<h2>Planificar con anticipación</h2>"
            "<p>Conocer las normas del lugar, llevar el equipo adecuado para no improvisar "
            "soluciones de impacto (como encender fuego fuera de zonas habilitadas) y "
            "planificar la ruta reduce buena parte del impacto antes incluso de salir de "
            "casa.</p>"
            "<h2>Mantenerse en superficies resistentes</h2>"
            "<p>Caminar por senderos marcados, en lugar de abrir atajos, evita la erosión y la "
            "compactación del suelo en ecosistemas que pueden tardar años o décadas en "
            "recuperarse, especialmente en alta montaña, páramo o desierto.</p>"
            "<h2>Gestionar los residuos correctamente</h2>"
            "<ul>"
            "<li>Llevarse toda la basura generada, incluidos restos orgánicos que tardan mucho "
            "en degradarse en ciertos climas.</li>"
            "<li>No dejar papel higiénico ni restos sanitarios a la vista.</li>"
            "<li>Usar jabón biodegradable, y nunca directamente en ríos, lagos o cenotes.</li>"
            "</ul>"
            "<h2>Respetar la fauna y a otros visitantes</h2>"
            "<p>Observar la fauna desde la distancia, sin alimentarla ni intentar acercarse, y "
            "moderar el volumen y el impacto sobre otros visitantes, especialmente en zonas de "
            "silencio o de observación de fauna, completa un conjunto de hábitos que, aplicados "
            "de forma constante, hacen una diferencia real a largo plazo en los lugares que "
            "más nos gusta visitar.</p>"
        ),
        destinos_slugs=["cano-cristales", "pnn-los-nevados", "delta-del-okavango"],
        tipos_slugs=["senderismo-y-trekking", "safari-y-observacion-de-fauna"],
        seo_titulo="Principios de no dejar rastro en la naturaleza",
        seo_descripcion=(
            "Guía de los principios de «no dejar rastro» para minimizar el impacto ambiental "
            "de cualquier salida al aire libre."
        ),
        relacionados_slugs=["como-elegir-y-organizar-la-mochila-de-trekking"],
    ),
    GuiaSemilla(
        titulo="Cómo planificar el presupuesto de un viaje de aventura",
        slug="como-planificar-el-presupuesto-de-un-viaje-de-aventura",
        categoria_slug="presupuesto-y-planificacion",
        resumen=(
            "Cómo estimar el presupuesto de un viaje de aventura por partidas, sin depender de "
            "cifras exactas que cambian con el tiempo."
        ),
        cuerpo=(
            "<p>El presupuesto de un viaje de aventura depende de tantas variables —temporada, "
            "duración, nivel de comodidad, si se viaja de forma independiente o con operador— "
            "que cualquier cifra exacta pierde vigencia rápido. Es más útil pensar en "
            "partidas y en su peso relativo que en un número cerrado.</p>"
            "<h2>Las grandes partidas de cualquier viaje de aventura</h2>"
            "<ul>"
            "<li>Transporte internacional y traslados internos hasta el punto de inicio de la "
            "actividad.</li>"
            "<li>Operador o guía local, cuando la actividad lo exige (buena parte de las "
            "actividades técnicas de este sitio se recorren siempre con guía).</li>"
            "<li>Alojamiento y comida durante la actividad y en los días de traslado.</li>"
            "<li>Equipo propio o de alquiler específico de la actividad.</li>"
            "<li>Seguro de viaje con cobertura de rescate y evacuación en la actividad "
            "concreta.</li>"
            "</ul>"
            "<h2>El nivel de presupuesto como referencia relativa</h2>"
            "<p>En lugar de cifras, este sitio usa un nivel de presupuesto relativo de uno a "
            "cuatro para cada destino, pensado para comparar el coste esperado de un destino "
            "frente a otro, no como una cifra fija: factores como la temporada, la "
            "anticipación de la reserva y el nivel de comodidad elegido pueden mover ese coste "
            "de forma considerable dentro de un mismo destino.</p>"
            "<h2>Reservar con antelación</h2>"
            "<p>En destinos con cupos regulados —Camino Inca, Galápagos, algunos parques "
            "patagónicos— reservar con varios meses de antelación no es solo una cuestión de "
            "presupuesto, sino a menudo la única forma de conseguir plaza en la temporada "
            "deseada.</p>"
            "<h2>Márgenes razonables</h2>"
            "<p>Prever un margen adicional para imprevistos —un cambio de vuelo, un día extra "
            "por mal tiempo, equipo que falla— es una práctica habitual entre viajeros "
            "experimentados, especialmente en destinos remotos donde las alternativas son "
            "limitadas y suelen costar más resolverlas sobre la marcha.</p>"
        ),
        destinos_slugs=["islas-galapagos", "camino-inca-machu-picchu", "torres-del-paine"],
        tipos_slugs=[],
        seo_titulo="Cómo planificar el presupuesto de un viaje de aventura",
        seo_descripcion=(
            "Guía para estimar el presupuesto de un viaje de aventura por partidas, sin "
            "depender de cifras exactas que cambian con el tiempo."
        ),
        relacionados_slugs=["primeros-pasos-para-elegir-tu-primera-aventura"],
    ),
    GuiaSemilla(
        titulo="Fotografía de paisaje en condiciones de montaña",
        slug="fotografia-de-paisaje-en-condiciones-de-montana",
        categoria_slug="fotografia-de-aventura",
        resumen=(
            "Consejos prácticos de composición, luz y cuidado del equipo para fotografiar "
            "paisajes de montaña y aventura."
        ),
        cuerpo=(
            "<p>Fotografiar paisajes de aventura combina dos retos distintos: conseguir buenas "
            "imágenes y hacerlo sin que la fotografía condicione la seguridad o el ritmo de la "
            "actividad. Un equipo sencillo bien usado suele dar mejores resultados que uno "
            "avanzado mal gestionado en el terreno.</p>"
            "<h2>La luz de los extremos del día</h2>"
            "<p>El amanecer y el atardecer —la «hora dorada»— ofrecen una luz lateral y cálida "
            "que resalta el relieve del terreno mucho mejor que la luz cenital del mediodía, "
            "que suele aplanar el paisaje y generar sombras duras. Planificar la llegada a un "
            "mirador para esas horas, cuando sea posible, suele merecer la pena.</p>"
            "<h2>Composición con elementos del propio viaje</h2>"
            "<p>Incluir un elemento humano o de escala —una persona, una mochila, un sendero— "
            "ayuda a transmitir la magnitud real del paisaje de montaña, algo que resulta "
            "difícil de apreciar en una fotografía sin referencia de tamaño.</p>"
            "<h2>Cuidado del equipo en condiciones exigentes</h2>"
            "<ul>"
            "<li>Proteger la cámara de la humedad y el polvo con una funda o bolsa estanca "
            "cuando no se está fotografiando.</li>"
            "<li>Llevar baterías de repuesto: el frío reduce notablemente su duración en alta "
            "montaña.</li>"
            "<li>Limpiar el objetivo con frecuencia en ambientes de spray marino, arena o "
            "polvo volcánico.</li>"
            "</ul>"
            "<h2>La fotografía nunca por delante de la seguridad</h2>"
            "<p>Acercarse a un borde expuesto, distraerse del sendero por conseguir una toma o "
            "retrasar al grupo de forma sistemática por fotografiar son riesgos evitables: la "
            "mejor fotografía de una aventura es siempre la que se toma sin comprometer la "
            "seguridad propia ni la del grupo.</p>"
        ),
        destinos_slugs=["torres-del-paine", "fiordos-de-noruega", "wadi-rum"],
        tipos_slugs=[],
        seo_titulo="Fotografía de paisaje en condiciones de montaña",
        seo_descripcion=(
            "Consejos prácticos de luz, composición y cuidado del equipo para fotografiar "
            "paisajes de montaña y aventura."
        ),
        relacionados_slugs=["como-entrenar-antes-de-tu-primera-aventura"],
    ),
    GuiaSemilla(
        titulo="Primeros pasos para elegir tu primera aventura",
        slug="primeros-pasos-para-elegir-tu-primera-aventura",
        categoria_slug="primera-aventura",
        resumen=(
            "Cómo elegir un primer destino de aventura acorde a tu condición física y tu "
            "experiencia, sin sobreestimar ni infravalorar el reto."
        ),
        cuerpo=(
            "<p>Elegir bien la primera aventura de varios días marca en buena medida si la "
            "experiencia anima a repetir o, al contrario, desanima por haber elegido un reto "
            "mal ajustado. No hace falta empezar por lo más exigente para vivir algo "
            "memorable.</p>"
            "<h2>Empezar por la dificultad, no por la fama</h2>"
            "<p>Un destino muy conocido no es necesariamente el más adecuado para empezar: "
            "conviene revisar la dificultad indicada, la duración y la altitud máxima de la "
            "ruta antes de dejarse llevar solo por la reputación del lugar. Destinos con "
            "dificultad 1 o 2 en la escala de este sitio suelen ser puntos de partida "
            "razonables.</p>"
            "<h2>Sumar guía o grupo organizado en la primera experiencia</h2>"
            "<p>Para quien se inicia, viajar con un operador o guía certificado reduce buena "
            "parte de la carga logística y de decisión que sí exige un viaje totalmente "
            "independiente, y permite concentrarse en disfrutar y aprender del terreno sin la "
            "presión añadida de la planificación completa.</p>"
            "<h2>Probar antes de comprometerse con lo más largo</h2>"
            "<p>Una excursión de un día o un fin de semana, antes de un trekking de varios "
            "días, es una forma razonable de comprobar cómo responde el cuerpo al desnivel, la "
            "altitud o el calor de una región concreta antes de comprometerse con una "
            "travesía más larga.</p>"
            "<h2>No subestimar la logística</h2>"
            "<p>Vacunas o profilaxis recomendadas, seguro de viaje con cobertura adecuada a la "
            "actividad, y tiempo de margen para imprevistos son parte tan importante de una "
            "primera aventura como la propia ruta o actividad elegida.</p>"
        ),
        destinos_slugs=["arenal-y-monteverde", "bahia-de-ha-long", "gran-barrera-de-coral"],
        tipos_slugs=[],
        seo_titulo="Primeros pasos para elegir tu primera aventura",
        seo_descripcion=(
            "Cómo elegir un primer destino de aventura acorde a tu condición física y "
            "experiencia, sin sobreestimar el reto."
        ),
        relacionados_slugs=["como-entrenar-antes-de-tu-primera-aventura"],
    ),
    GuiaSemilla(
        titulo="Qué preguntar antes de reservar con un operador local",
        slug="que-preguntar-antes-de-reservar-con-un-operador-local",
        categoria_slug="primera-aventura",
        resumen=(
            "Las preguntas clave para evaluar la seriedad de un operador de aventura antes de "
            "reservar una actividad guiada."
        ),
        cuerpo=(
            "<p>La calidad y la seguridad de una actividad guiada dependen en gran medida del "
            "operador elegido, más incluso que del propio destino. Hacer unas pocas preguntas "
            "antes de reservar ayuda a distinguir operadores serios de otros menos fiables, "
            "algo especialmente relevante en actividades de mayor riesgo.</p>"
            "<h2>Certificaciones del personal</h2>"
            "<p>Preguntar por la certificación específica de los guías (de montaña, de buceo, "
            "de vuelo, según la actividad) y por su experiencia concreta en la ruta o el "
            "destino elegido es una de las preguntas más reveladoras: un operador serio "
            "responde con datos concretos, no con evasivas.</p>"
            "<h2>Ratio de guías por participante y tamaño de grupo</h2>"
            "<p>Un grupo demasiado grande para el número de guías disponibles reduce la "
            "capacidad de atención individual y de respuesta ante un imprevisto; preguntar por "
            "el tamaño máximo del grupo y el número de guías asignados es una forma directa de "
            "evaluar este aspecto.</p>"
            "<h2>Seguro y protocolo de emergencia</h2>"
            "<ul>"
            "<li>Si el operador cuenta con seguro de responsabilidad civil propio.</li>"
            "<li>Cuál es el protocolo y el punto de contacto en caso de emergencia en el "
            "terreno.</li>"
            "<li>Si el material técnico se revisa de forma periódica y quién lo hace.</li>"
            "</ul>"
            "<h2>Reseñas y trayectoria</h2>"
            "<p>Una trayectoria de varios años operando en la misma región, y reseñas "
            "recientes y verificables de otros viajeros, son señales razonables de fiabilidad; "
            "el precio más bajo del mercado, sin explicación clara de por qué, es a menudo "
            "señal de que algo —material, formación del guía, seguro— se está recortando en "
            "algún punto de la cadena.</p>"
        ),
        destinos_slugs=["san-gil-canon-del-chicamocha", "islas-galapagos", "kilimanjaro"],
        tipos_slugs=[],
        seo_titulo="Qué preguntar antes de reservar con un operador local",
        seo_descripcion=(
            "Preguntas clave para evaluar la seriedad de un operador de aventura antes de "
            "reservar una actividad guiada."
        ),
        relacionados_slugs=["como-evaluar-riesgos-antes-de-salir-al-terreno"],
    ),
]
