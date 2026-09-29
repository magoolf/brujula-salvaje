"""Los 12 tipos de aventura semilla (requirements.yaml `contenido_semilla.tipos_aventura`,
DEC-AUTO-006; lista literal, no se inventan otros).

`checklist`: >=8 elementos (RULE de `reglas.MINIMO_CHECKLIST`) por tipo, material y medidas de
seguridad reales y apropiadas a la actividad (no genéricas).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChecklistItemSemilla:
    texto: str
    grupo: str
    esencial: bool = False


@dataclass(frozen=True)
class TipoAventuraSemilla:
    titulo: str
    slug: str
    resumen: str
    descripcion: str
    nivel_exigencia: int
    seo_titulo: str
    seo_descripcion: str
    checklist: list[ChecklistItemSemilla] = field(default_factory=list)


TIPOS: list[TipoAventuraSemilla] = [
    TipoAventuraSemilla(
        titulo="Senderismo y trekking",
        slug="senderismo-y-trekking",
        resumen=(
            "Caminatas de uno o varios días por senderos de montaña, selva o altiplano, desde "
            "rutas de un día hasta travesías de más de una semana."
        ),
        descripcion=(
            "<p>El senderismo y el trekking son la puerta de entrada más habitual al mundo de la "
            "aventura al aire libre: no exigen equipo técnico especializado, son escalables en "
            "dificultad y existen rutas de este tipo en prácticamente cualquier cordillera, "
            'selva o altiplano del planeta. La diferencia principal entre "senderismo" y '
            '"trekking" es de duración y logística: el senderismo suele resolverse en una '
            "jornada con regreso al mismo punto, mientras que el trekking implica varios días "
            "de caminata con pernoctación en refugios, campamentos o poblados intermedios, y por "
            "tanto una preparación más cuidadosa de comida, agua, abrigo y suelo de descanso.</p>"
            "<p>La exigencia real de una ruta no depende solo de la distancia: el desnivel "
            "acumulado, la altitud, el estado del terreno (barro, roca suelta, nieve) y la "
            "exposición climática pesan tanto o más que los kilómetros. Una misma distancia "
            "puede ser un paseo tranquilo o una jornada agotadora según cuánto se suba y baje, y "
            "a qué altitud sobre el nivel del mar. Por eso conviene revisar siempre el desnivel "
            "acumulado y la altitud máxima de una ruta, no solo su longitud.</p>"
            "<p>El calzado es, con diferencia, el elemento de equipo más determinante: unas "
            "botas o zapatillas de trekking ya rodadas (nunca estrenadas el día de la ruta) "
            "evitan la inmensa mayoría de los abandonos por ampollas o torceduras. Igual de "
            "importante es la gestión del agua y la energía: llevar más agua de la que se cree "
            "necesaria, comer con regularidad aunque no haya hambre, y conocer de antemano dónde "
            "hay fuentes fiables en la ruta.</p>"
        ),
        nivel_exigencia=2,
        seo_titulo="Senderismo y trekking: guía experta del tipo de aventura",
        seo_descripcion=(
            "Qué es el senderismo y el trekking, dificultad, equipo y checklist esencial para "
            "caminatas de uno o varios días."
        ),
        checklist=[
            ChecklistItemSemilla("Botas o zapatillas de trekking ya rodadas", "Calzado", True),
            ChecklistItemSemilla(
                "Mochila con cinturón lumbar ajustado al peso a cargar", "Carga", True
            ),
            ChecklistItemSemilla(
                "Sistema de hidratación o cantimploras con capacidad suficiente",
                "Hidratación",
                True,
            ),
            ChecklistItemSemilla("Capa impermeable y cortavientos", "Ropa", True),
            ChecklistItemSemilla(
                "Mapa o track descargado y sistema de navegación de respaldo", "Orientación", True
            ),
            ChecklistItemSemilla(
                "Botiquín básico con material para ampollas y torceduras", "Seguridad", True
            ),
            ChecklistItemSemilla("Protección solar y de labios de alto factor", "Salud"),
            ChecklistItemSemilla("Linterna frontal con pilas de repuesto", "Seguridad"),
            ChecklistItemSemilla(
                "Bastones de trekking si la ruta tiene desnivel sostenido", "Equipo"
            ),
            ChecklistItemSemilla("Comida energética y raciones de reserva", "Alimentación"),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Alta montaña y alpinismo",
        slug="alta-montana-y-alpinismo",
        resumen=(
            "Ascensos técnicos o de altitud extrema que combinan esfuerzo físico sostenido, "
            "aclimatación y, a menudo, terreno glaciar o nevado."
        ),
        descripcion=(
            "<p>La alta montaña reúne dos retos que rara vez aparecen juntos en otras "
            "actividades: la altitud (con su efecto fisiológico sobre el cuerpo, "
            "independientemente de la forma física de quien asciende) y, en muchos casos, un "
            "terreno técnico que exige piolet, crampones, cuerda y conocimiento de progresión "
            "glaciar. Un ascenso de alta montaña no se mide solo en metros de altitud absoluta: "
            "el mismo pico puede ser una caminata larga por una vía normal bien marcada o una "
            "escalada técnica seria por una arista, según la ruta elegida.</p>"
            "<p>La aclimatación es el factor que más separa el éxito del fracaso —o del "
            "riesgo— en altitud: el cuerpo necesita tiempo para adaptarse a la menor presión "
            "parcial de oxígeno, y forzar el ritmo de ascenso por encima de los 2.500-3.000 "
            'metros es la causa más habitual de mal de altura. La norma clásica de "subir alto, '
            'dormir bajo" y de no ganar más de 300-500 metros de altitud de pernocta por día por '
            "encima de esa cota sigue siendo la referencia más citada por la medicina de "
            "montaña, aunque cada organismo responde de forma distinta y ninguna guía sustituye "
            "la valoración de un profesional certificado.</p>"
            "<p>El clima en alta montaña cambia con una rapidez que no tiene equivalente en "
            "cotas bajas: una mañana despejada puede derivar en tormenta, viento fuerte o "
            "ventisca en cuestión de horas, y la ventana de buen tiempo para un ascenso final "
            "suele decidirse literalmente el día anterior. Por eso la mayoría de las "
            "expediciones de alta montaña trabajan con guías o agencias locales certificadas que "
            "conocen el terreno, gestionan los permisos necesarios y toman la decisión, siempre "
            "difícil, de dar la vuelta cuando las condiciones no acompañan.</p>"
        ),
        nivel_exigencia=5,
        seo_titulo="Alta montaña y alpinismo: guía experta del tipo de aventura",
        seo_descripcion=(
            "Qué es la alta montaña y el alpinismo, aclimatación, equipo técnico y checklist "
            "esencial para ascensos de altitud."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Piolet y crampones ajustados a la bota técnica", "Progresión", True
            ),
            ChecklistItemSemilla(
                "Arnés, cuerda y material de progresión glaciar", "Progresión", True
            ),
            ChecklistItemSemilla(
                "Sistema de capas técnicas: base, aislante y exterior impermeable", "Ropa", True
            ),
            ChecklistItemSemilla(
                "Gafas de glaciar con protección UV alta y crema solar de alta montaña",
                "Salud",
                True,
            ),
            ChecklistItemSemilla(
                "Plan de aclimatación progresiva con días de reposo en altitud",
                "Aclimatación",
                True,
            ),
            ChecklistItemSemilla(
                "Guía o agencia certificada local para la logística y los permisos",
                "Logística",
                True,
            ),
            ChecklistItemSemilla(
                "Botiquín de altitud y conocimiento de los síntomas de mal de altura",
                "Seguridad",
                True,
            ),
            ChecklistItemSemilla(
                "Saco de dormir y aislante térmico para condiciones extremas", "Refugio"
            ),
            ChecklistItemSemilla(
                "Comunicación satelital o dispositivo de emergencia en zonas sin cobertura",
                "Seguridad",
            ),
            ChecklistItemSemilla(
                "Guantes de recambio y protección facial contra congelación", "Ropa"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Escalada y vía ferrata",
        slug="escalada-y-via-ferrata",
        resumen=(
            "Progresión vertical sobre roca, desde vías ferratas equipadas con cable de "
            "seguridad hasta escalada deportiva o clásica en pared."
        ),
        descripcion=(
            "<p>Bajo este tipo conviven dos actividades de exigencia técnica muy distinta que "
            "comparten el medio (la roca vertical) y buena parte de la mentalidad. La vía "
            "ferrata es una ruta equipada de forma permanente con cable de acero, grapas, "
            "escalones metálicos y a veces puentes colgantes o tirolinas, pensada para que "
            "personas sin formación en escalada puedan progresar por paredes verticales con un "
            "kit de autoaseguramiento (arnés, disipador y dos mosquetones) enganchado siempre al "
            "cable. La escalada propiamente dicha, ya sea deportiva (con anclajes fijos) o "
            "clásica/tradicional (colocando la propia protección), exige en cambio formación "
            "técnica específica, ya sea en escalada en cordada, aseguramiento y progresión.</p>"
            "<p>La regla de oro de la vía ferrata es no desengancharse nunca por completo del "
            "cable: el sistema de doble mosquetón existe precisamente para que, al superar un "
            "anclaje intermedio, siempre haya al menos uno de los dos enganchado. La escalada, "
            "por su parte, exige revisar el material antes de cada salida (cuerda sin cortes ni "
            "deshilachados, arnés y mosquetones sin desgaste) y nunca escalar sin un compañero "
            "que asegure correctamente.</p>"
            "<p>La exposición —la sensación de vacío bajo los pies— es el factor psicológico más "
            "determinante en ambas disciplinas, y no siempre se corresponde con la dificultad "
            "técnica real: una vía ferrata sencilla en cuanto a movimiento puede resultar "
            "extremadamente expuesta, y viceversa. Por eso muchas guías clasifican las vías "
            "ferratas con dos escalas independientes, una de dificultad física y otra de "
            "exposición, y conviene revisar ambas antes de decidirse por una ruta.</p>"
        ),
        nivel_exigencia=4,
        seo_titulo="Escalada y vía ferrata: guía experta del tipo de aventura",
        seo_descripcion=(
            "Diferencias entre vía ferrata y escalada, equipo de aseguramiento y checklist "
            "esencial para progresión vertical en roca."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Arnés homologado y kit de vía ferrata con disipador de energía", "Progresión", True
            ),
            ChecklistItemSemilla("Casco de escalada", "Protección", True),
            ChecklistItemSemilla(
                "Guantes reforzados para el cable de la vía ferrata", "Protección", True
            ),
            ChecklistItemSemilla("Calzado de aproximación con buena adherencia", "Calzado", True),
            ChecklistItemSemilla(
                "Revisión del material (cuerda, cintas, mosquetones) antes de salir",
                "Seguridad",
                True,
            ),
            ChecklistItemSemilla(
                "Compañero de cordada y sistema de aseguramiento acordado", "Seguridad", True
            ),
            ChecklistItemSemilla(
                "Previsión meteorológica y plan de escape en caso de tormenta", "Seguridad"
            ),
            ChecklistItemSemilla(
                "Agua y snacks de fácil acceso durante la progresión", "Alimentación"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Buceo y snorkel",
        slug="buceo-y-snorkel",
        resumen=(
            "Inmersión con botella o snorkel para explorar arrecifes, cavernas inundadas o "
            "vida marina, desde bautismos de buceo hasta inmersiones certificadas."
        ),
        descripcion=(
            "<p>El buceo autónomo y el snorkel comparten el medio —el agua— pero exigen niveles "
            "de preparación muy distintos. El snorkel, con máscara, tubo y aletas, permite "
            "observar la superficie de un arrecife o una bahía sin formación previa más allá de "
            "saber nadar con soltura. El buceo con botella, en cambio, requiere una certificación "
            "reconocida (los organismos más extendidos son PADI y SSI, entre otros) porque "
            "introduce variables fisiológicas serias: la gestión de la presión en los oídos y "
            "senos, el control de la flotabilidad, y sobre todo la prevención de la enfermedad "
            "descompresiva mediante ascensos lentos y paradas de seguridad.</p>"
            "<p>La norma más citada del buceo recreativo es no realizar ascensos rápidos y "
            "respetar siempre los tiempos de intervalo en superficie antes de volar o subir a "
            "gran altitud, precisamente para dar tiempo al nitrógeno disuelto en el cuerpo a "
            'liberarse de forma segura. Bucear siempre en pareja (el sistema de "buddy"), '
            "revisar el equipo antes de cada inmersión y no superar el límite de la propia "
            "certificación son las otras reglas no negociables del buceo recreativo.</p>"
            "<p>El buceo en cuevas o cenotes inundados —una variante particular que combina "
            "buceo y espeleología— añade una capa adicional de riesgo por la ausencia de acceso "
            "directo a la superficie, y exige formación específica de buceo en cavernas, guía "
            "certificado local y nunca superar los límites del propio entrenamiento. Tanto en "
            "arrecife como en cenote, el respeto al entorno —no tocar el coral ni las "
            "formaciones, mantener una flotabilidad neutra— es a la vez una norma de seguridad y "
            "de conservación.</p>"
        ),
        nivel_exigencia=3,
        seo_titulo="Buceo y snorkel: guía experta del tipo de aventura",
        seo_descripcion=(
            "Diferencias entre buceo autónomo y snorkel, certificaciones y checklist esencial para "
            "inmersiones seguras."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Certificación de buceo vigente y acorde a la inmersión prevista", "Formación", True
            ),
            ChecklistItemSemilla(
                "Equipo de buceo revisado (regulador, chaleco, manómetro)", "Equipo", True
            ),
            ChecklistItemSemilla(
                "Máscara, tubo y aletas de snorkel bien ajustados", "Equipo", True
            ),
            ChecklistItemSemilla("Seguro de buceo con cobertura de evacuación", "Seguridad", True),
            ChecklistItemSemilla("Ordenador de buceo o tablas de descompresión", "Seguridad", True),
            ChecklistItemSemilla(
                "Protector solar apto para arrecifes (sin filtros dañinos para el coral)",
                "Sostenibilidad",
            ),
            ChecklistItemSemilla(
                'Compañero de inmersión ("buddy") acordado antes de entrar al agua',
                "Seguridad",
                True,
            ),
            ChecklistItemSemilla(
                "Traje de neopreno o protección térmica según la temperatura del agua", "Equipo"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Rafting y deportes de río",
        slug="rafting-y-deportes-de-rio",
        resumen=(
            "Descenso en balsa u otras embarcaciones por rápidos de río, clasificados por "
            "dificultad de clase I (suave) a clase V (extrema)."
        ),
        descripcion=(
            "<p>El rafting consiste en descender un tramo de río con rápidos a bordo de una "
            "balsa inflable, remando en equipo bajo la coordinación de un guía que dirige la "
            "maniobra desde la popa. Los ríos se clasifican por la escala internacional de "
            "dificultad de aguas bravas, de clase I (aguas planas o con pequeñas ondulaciones) "
            "a clase V (rápidos técnicos, continuos y con consecuencias serias en caso de "
            "error); la clase VI se reserva para tramos considerados no navegables de forma "
            "comercial. Un mismo río puede cambiar de clase según el caudal de la época, así "
            "que la dificultad real de una salida depende tanto del tramo como del momento del "
            "año.</p>"
            "<p>El equipo de seguridad no es negociable: chaleco salvavidas ajustado, casco y, "
            "en la mayoría de operadores serios, un briefing de seguridad obligatorio antes de "
            "embarcar que cubre la posición correcta dentro de la balsa, qué hacer si se cae al "
            "agua (flotar boca arriba, pies por delante, nunca de pie sobre el fondo del río por "
            "el riesgo de atrapamiento) y las señales de remo del guía.</p>"
            "<p>Además del rafting en balsa colectiva, la misma familia de deportes de río "
            'incluye el descenso en kayak individual o en "duckie" (kayak inflable de una o dos '
            "plazas), que exige más técnica personal de remada y de lectura del agua. En "
            "cualquiera de sus formas, contratar siempre operadores con guías certificados y "
            "material en buen estado es la decisión de seguridad más importante que toma quien "
            "practica este deporte.</p>"
        ),
        nivel_exigencia=3,
        seo_titulo="Rafting y deportes de río: guía experta del tipo de aventura",
        seo_descripcion=(
            "Clasificación de rápidos, equipo de seguridad y checklist esencial para el rafting "
            "y los deportes de río."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Chaleco salvavidas certificado y bien ajustado", "Seguridad", True
            ),
            ChecklistItemSemilla("Casco de aguas bravas", "Seguridad", True),
            ChecklistItemSemilla("Calzado cerrado sujeto al pie (no chanclas)", "Calzado", True),
            ChecklistItemSemilla(
                "Ropa de neopreno o secado rápido según temperatura del agua", "Ropa"
            ),
            ChecklistItemSemilla(
                "Briefing de seguridad y señales de remo antes de embarcar", "Seguridad", True
            ),
            ChecklistItemSemilla("Bolsa estanca para objetos personales", "Equipo"),
            ChecklistItemSemilla(
                "Cuerda de rescate y kit de primeros auxilios del guía", "Seguridad"
            ),
            ChecklistItemSemilla(
                "Conocimiento de la clase de dificultad del tramo y el caudal del día",
                "Planificación",
                True,
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Kayak y navegación",
        slug="kayak-y-navegacion",
        resumen=(
            "Recorridos en kayak, canoa o embarcación tradicional por fiordos, lagos, costas o "
            "deltas, desde salidas de medio día hasta travesías de varios días."
        ),
        descripcion=(
            "<p>A diferencia del rafting, centrado en aguas bravas, este tipo agrupa la "
            "navegación en aguas tranquilas o moderadas —fiordos, lagos glaciares, costas "
            "resguardadas, deltas y canales— en kayak, canoa o embarcaciones tradicionales según "
            "la región. Es una de las formas más silenciosas y respetuosas con el entorno de "
            "explorar un paisaje: permite acercarse a fauna, cascadas o formaciones costeras que "
            "serían inaccesibles a pie, sin el ruido ni el impacto de un motor.</p>"
            "<p>La técnica básica de remada, la lectura del viento y de las corrientes, y saber "
            'cómo actuar en caso de vuelco (el "rescate" de reentrada a la embarcación) son las '
            "competencias mínimas antes de una salida sin guía; en aguas abiertas o con marea, "
            "estas destrezas se vuelven imprescindibles porque el viento puede cambiar las "
            "condiciones con rapidez y alejar la orilla más de lo previsto. En salidas guiadas, "
            "esta responsabilidad recae en el guía, que además conoce los horarios de marea, las "
            "zonas de fondeo seguras y la normativa local de navegación.</p>"
            "<p>La hipotermia es el riesgo menos evidente y más subestimado de este tipo de "
            "actividad: el agua de fiordos glaciares o lagos de montaña puede estar a "
            "temperaturas muy bajas incluso en verano, y una caída prolongada sin la ropa "
            "adecuada es más peligrosa que el propio oleaje. Por eso la ropa técnica de neopreno "
            "o de secado rápido, y no solo el chaleco salvavidas, forma parte del equipo mínimo "
            "de seguridad en aguas frías.</p>"
        ),
        nivel_exigencia=2,
        seo_titulo="Kayak y navegación: guía experta del tipo de aventura",
        seo_descripcion=(
            "Técnica básica, riesgos del agua fría y checklist esencial para el kayak y la "
            "navegación en fiordos, lagos y costas."
        ),
        checklist=[
            ChecklistItemSemilla("Chaleco salvavidas certificado", "Seguridad", True),
            ChecklistItemSemilla("Pala de repuesto o amarrada a la embarcación", "Equipo"),
            ChecklistItemSemilla(
                "Ropa técnica o neopreno según temperatura del agua", "Ropa", True
            ),
            ChecklistItemSemilla(
                "Bolsa estanca para móvil, documentación y capa seca de recambio", "Equipo", True
            ),
            ChecklistItemSemilla(
                "Consulta de previsión de viento, marea y corrientes antes de salir",
                "Planificación",
                True,
            ),
            ChecklistItemSemilla("Silbato o señal acústica de emergencia", "Seguridad"),
            ChecklistItemSemilla(
                "Conocimiento básico de la técnica de reentrada tras un vuelco", "Formación", True
            ),
            ChecklistItemSemilla("Protección solar y gafas con cordón de sujeción", "Salud"),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Ciclismo de montaña",
        slug="ciclismo-de-montana",
        resumen=(
            "Recorridos en bicicleta por senderos, pistas o bosques de montaña, desde rutas "
            "panorámicas suaves hasta circuitos técnicos de descenso."
        ),
        descripcion=(
            "<p>El ciclismo de montaña (mountain bike o MTB) cubre un espectro muy amplio de "
            "actividad: desde rutas panorámicas por pistas forestales sin apenas dificultad "
            "técnica, pensadas para disfrutar del paisaje, hasta circuitos de descenso ("
            '"downhill") con saltos, raíces y pendientes pronunciadas que exigen bicicleta '
            "específica, protecciones y experiencia previa. Muchos destinos de montaña con "
            "vocación de esquí en invierno reconvierten sus remontes y pistas en circuitos de "
            'MTB en temporada de verano, lo que ha impulsado la creación de "bike parks" con '
            "rutas señalizadas por dificultad, de forma similar a las pistas de esquí.</p>"
            "<p>El equipo de protección —casco de montaña de cobertura amplia y, en circuitos "
            "técnicos, coderas, rodilleras y protector dorsal— reduce de forma drástica la "
            "gravedad de las caídas, que son la forma de incidente más común en esta actividad. "
            "La revisión mecánica de la bicicleta antes de salir (frenos, presión de neumáticos, "
            "suspensión) es tan importante como el equipo personal: un fallo mecánico a media "
            "bajada es mucho más peligroso que en una carretera llana.</p>"
            "<p>La señalización por colores (similar a la de las pistas de esquí: verde, azul, "
            "roja y negra según dificultad creciente) ayuda a elegir un circuito acorde al nivel "
            "real de quien lo recorre, y conviene respetarla en lugar de guiarse solo por la "
            "distancia. Como en cualquier actividad compartida con otros usuarios del sendero "
            "(caminantes, otros ciclistas), avisar antes de adelantar y ceder el paso cuando "
            "corresponde forma parte tanto de la seguridad como de la buena convivencia en el "
            "monte.</p>"
        ),
        nivel_exigencia=3,
        seo_titulo="Ciclismo de montaña: guía experta del tipo de aventura",
        seo_descripcion=(
            "Del cross-country al descenso técnico: protección, revisión mecánica y checklist "
            "esencial del ciclismo de montaña."
        ),
        checklist=[
            ChecklistItemSemilla("Casco de montaña de cobertura amplia", "Seguridad", True),
            ChecklistItemSemilla(
                "Bicicleta revisada: frenos, presión de neumáticos y suspensión", "Equipo", True
            ),
            ChecklistItemSemilla("Guantes y gafas de protección", "Protección"),
            ChecklistItemSemilla(
                "Coderas, rodilleras y protector dorsal en circuitos técnicos", "Protección"
            ),
            ChecklistItemSemilla(
                "Kit de reparación de pinchazos y multiherramienta", "Equipo", True
            ),
            ChecklistItemSemilla(
                "Hidratación suficiente para la duración del circuito", "Hidratación", True
            ),
            ChecklistItemSemilla(
                "Conocimiento del código de colores de dificultad del circuito",
                "Planificación",
                True,
            ),
            ChecklistItemSemilla(
                "Teléfono cargado y ruta compartida con alguien de confianza", "Seguridad"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Parapente y deportes aéreos",
        slug="parapente-y-deportes-aereos",
        resumen=(
            "Vuelo libre en parapente, ala delta o salto en paracaídas, en tándem con piloto "
            "certificado o de forma autónoma tras la formación adecuada."
        ),
        descripcion=(
            "<p>El parapente es, de lejos, el deporte aéreo más accesible para quien se inicia: "
            "un vuelo en tándem con un piloto certificado no requiere ninguna formación previa "
            "por parte del pasajero, solo seguir las instrucciones de carrera de despegue y "
            "aterrizaje. El ala delta y el salto en paracaídas (en tándem o mediante cursos de "
            "apertura automática) comparten esa misma lógica de iniciación acompañada antes de "
            "plantearse, para quien quiera continuar, una formación reglada y progresiva hacia "
            "el vuelo autónomo.</p>"
            "<p>La ventana meteorológica es el factor que más condiciona estos deportes: el "
            "viento (su velocidad, dirección y estabilidad térmica) determina no solo si se "
            "puede volar, sino también la calidad y seguridad del vuelo, y es habitual que "
            "vuelos programados se cancelen o se retrasen por decisión del piloto ante "
            "condiciones cambiantes. Confiar en el criterio del piloto o instructor certificado "
            'para tomar esa decisión, sin presionar por volar "de todas formas", es la actitud '
            "de seguridad más importante de quien participa en un vuelo tándem.</p>"
            "<p>Los destinos con tradición de parapente suelen combinar una geografía favorable "
            "—valles con térmicas predecibles, despegues a media montaña con buena orientación "
            "al viento dominante— con una comunidad de pilotos y escuelas certificadas que "
            "garantizan revisiones periódicas del material (velas, arneses, paracaídas de "
            "reserva) y seguros de responsabilidad civil y accidentes específicos para la "
            "actividad.</p>"
        ),
        nivel_exigencia=3,
        seo_titulo="Parapente y deportes aéreos: guía experta del tipo de aventura",
        seo_descripcion=(
            "Vuelo en tándem, ventana meteorológica y checklist esencial del parapente y otros "
            "deportes aéreos."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Piloto o instructor certificado por la federación local", "Formación", True
            ),
            ChecklistItemSemilla("Arnés, vela y paracaídas de reserva revisados", "Equipo", True),
            ChecklistItemSemilla("Casco homologado para vuelo", "Seguridad", True),
            ChecklistItemSemilla("Seguro específico de deportes aéreos", "Seguridad", True),
            ChecklistItemSemilla("Ropa de abrigo (la temperatura baja rápido en altura)", "Ropa"),
            ChecklistItemSemilla(
                "Calzado cerrado apto para la carrera de despegue y aterrizaje", "Calzado", True
            ),
            ChecklistItemSemilla(
                "Confirmación de la ventana meteorológica el mismo día del vuelo",
                "Planificación",
                True,
            ),
            ChecklistItemSemilla(
                "Cámara sujeta con correa (nunca suelta durante el vuelo)", "Equipo"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Safari y observación de fauna",
        slug="safari-y-observacion-de-fauna",
        resumen=(
            "Salidas guiadas en vehículo, embarcación tradicional o a pie para observar fauna "
            "salvaje en su hábitat natural, con foco en la mínima interferencia."
        ),
        descripcion=(
            "<p>El safari clásico en vehículo todoterreno abierto, guiado por un rastreador o "
            "guía naturalista con conocimiento profundo del territorio y del comportamiento "
            "animal, sigue siendo la forma más habitual de observar fauna salvaje a distancia "
            "segura. En algunos destinos, como los deltas y humedales, esa observación se hace "
            "también desde embarcaciones tradicionales de calado muy bajo, que permiten "
            "acercarse a zonas de agua poco profunda sin motor y con un impacto mínimo sobre el "
            "hábitat.</p>"
            "<p>La norma de oro de cualquier safari responsable es no interferir en el "
            "comportamiento natural del animal: mantener la distancia que marca el guía, no "
            "salir del vehículo o embarcación salvo en los puntos autorizados, no imitar sonidos "
            "ni ofrecer comida, y evitar los movimientos bruscos o el ruido excesivo que puedan "
            "alterar una manada en descanso o un ave en su nido. Los mejores momentos de "
            "observación —el amanecer y el atardecer— coinciden además con las horas de mayor "
            "actividad de buena parte de la fauna, por lo que los safaris suelen organizarse en "
            "esas franjas.</p>"
            "<p>La preparación de un safari tiene más que ver con la paciencia y el respeto que "
            "con la condición física: ropa de colores neutros que no llame la atención, "
            "prismáticos de calidad, protección solar y contra insectos, y la aceptación de que "
            "la fauna salvaje no se comporta según un guion, por lo que cada salida es distinta "
            "y ninguna observación está garantizada.</p>"
        ),
        nivel_exigencia=1,
        seo_titulo="Safari y observación de fauna: guía experta del tipo de aventura",
        seo_descripcion=(
            "Cómo observar fauna salvaje con mínima interferencia: distancia, comportamiento y "
            "checklist esencial del safari."
        ),
        checklist=[
            ChecklistItemSemilla("Guía o rastreador local certificado", "Formación", True),
            ChecklistItemSemilla("Prismáticos", "Equipo", True),
            ChecklistItemSemilla("Ropa de colores neutros, sin estampados llamativos", "Ropa"),
            ChecklistItemSemilla("Repelente de insectos y profilaxis según la zona", "Salud", True),
            ChecklistItemSemilla("Protección solar y sombrero de ala ancha", "Salud"),
            ChecklistItemSemilla(
                "Distancia mínima de seguridad respetada en todo momento", "Seguridad", True
            ),
            ChecklistItemSemilla("Agua suficiente para toda la salida", "Hidratación"),
            ChecklistItemSemilla("Cámara con teleobjetivo para no necesitar acercarse", "Equipo"),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Surf",
        slug="surf",
        resumen=(
            "Deslizamiento sobre olas con tabla, desde clases de iniciación en olas suaves "
            "hasta sesiones en breaks de arrecife para nivel avanzado."
        ),
        descripcion=(
            "<p>El surf es, ante todo, una actividad de lectura del mar: entender cómo se forman "
            "las series de olas, dónde rompen según la marea y el fondo (arena, arrecife o "
            "punta rocosa) y cómo identificar y usar las corrientes de retorno para volver al "
            "punto de despegue sin gastar energía nadando contra la ola son las competencias que "
            "distinguen a un surfista con experiencia de quien se inicia. La mayoría de escuelas "
            'de surf empiezan con tablas largas ("longboard" o "foamies") en playas de arena '
            "con olas suaves, precisamente porque ofrecen más estabilidad y un fondo más seguro "
            "para las caídas.</p>"
            "<p>El riesgo más citado del surf no es la ola en sí, sino la corriente de resaca ("
            '"rip current"): un canal de agua que fluye mar adentro y que puede arrastrar a '
            "quien no la reconoce. La respuesta correcta ante una corriente de resaca es nunca "
            "nadar contra ella, sino nadar en paralelo a la costa hasta salir de su influencia y "
            "entonces dirigirse a la orilla; entender esto antes de entrar al agua es la lección "
            "de seguridad más importante de este deporte.</p>"
            '<p>Los breaks de arrecife ("reef breaks"), habituales en destinos tropicales, '
            "producen olas más potentes y de mejor forma que los de arena, pero también un "
            "fondo de coral o roca que exige mucha más experiencia para evitar golpes o cortes; "
            "por eso conviene surfear siempre acorde al propio nivel y, en un break desconocido, "
            "observar antes desde la orilla o preguntar a surfistas o escuelas locales por sus "
            "particularidades.</p>"
        ),
        nivel_exigencia=3,
        seo_titulo="Surf: guía experta del tipo de aventura",
        seo_descripcion=(
            "Lectura del mar, corrientes de resaca y checklist esencial para iniciarse o "
            "practicar surf con seguridad."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Tabla acorde al nivel (longboard o foamie para iniciación)", "Equipo", True
            ),
            ChecklistItemSemilla("Invento (cordón de seguridad tabla-tobillo)", "Seguridad", True),
            ChecklistItemSemilla("Traje de neopreno según temperatura del agua", "Ropa"),
            ChecklistItemSemilla("Protección solar resistente al agua", "Salud", True),
            ChecklistItemSemilla(
                "Conocimiento de cómo identificar y salir de una corriente de resaca",
                "Seguridad",
                True,
            ),
            ChecklistItemSemilla(
                "Clase con escuela local certificada en la primera sesión", "Formación"
            ),
            ChecklistItemSemilla(
                "Consulta previa del parte de olas y mareas", "Planificación", True
            ),
            ChecklistItemSemilla(
                "Respeto de la prioridad de ola y del resto de surfistas en el agua", "Convivencia"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Espeleología y cenotes",
        slug="espeleologia-y-cenotes",
        resumen=(
            "Exploración de cuevas, sistemas kársticos y cenotes inundados, a pie o buceando, "
            "en entornos sin luz natural y de orientación compleja."
        ),
        descripcion=(
            "<p>La espeleología explora cavidades subterráneas —cuevas secas, sistemas de "
            "galerías o cenotes, esos pozos naturales de agua dulce típicos del terreno kárstico "
            "de la península de Yucatán— combinando progresión física (a veces con cuerdas, "
            "arneses y técnicas de descenso) con una orientación mucho más exigente que en "
            "superficie, porque no hay luz natural ni referencias visuales lejanas. La regla más "
            "repetida por cualquier guía de espeleología es no explorar nunca en solitario y no "
            "aventurarse en pasajes no señalizados sin un guía que conozca el sistema.</p>"
            "<p>En los cenotes, la actividad se divide entre el snorkel o baño en la superficie "
            "iluminada por la abertura natural —accesible sin formación técnica— y el buceo en "
            "cuevas inundadas, que exige una certificación específica de buceo en cavernas "
            "distinta de la de buceo en mar abierto, por la ausencia de acceso vertical directo "
            "a la superficie y la necesidad de seguir un hilo guía en todo momento.</p>"
            "<p>La iluminación es, junto con el guía, el elemento de seguridad más crítico: al "
            "menos dos fuentes de luz independientes (una frontal y una de repuesto) evitan que "
            "un fallo técnico deje a alguien a oscuras en un entorno donde la orientación ya es "
            "de por sí compleja. El respeto a las formaciones —estalactitas, estalagmitas y la "
            "propia agua del cenote, a menudo conectada a acuíferos de los que depende el "
            "abastecimiento local— es tanto una norma de seguridad frente a superficies "
            "resbaladizas como de conservación de un ecosistema muy frágil.</p>"
        ),
        nivel_exigencia=3,
        seo_titulo="Espeleología y cenotes: guía experta del tipo de aventura",
        seo_descripcion=(
            "Exploración de cuevas y cenotes, iluminación de seguridad y checklist esencial de la "
            "espeleología y el buceo en cavernas."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Casco con linterna frontal y fuente de luz de repuesto", "Seguridad", True
            ),
            ChecklistItemSemilla(
                "Guía local certificado que conozca el sistema de cuevas", "Formación", True
            ),
            ChecklistItemSemilla(
                "Certificación de buceo en cavernas si hay tramos inundados", "Formación"
            ),
            ChecklistItemSemilla("Calzado de agarre con suela antideslizante", "Calzado", True),
            ChecklistItemSemilla(
                "Ropa que se pueda mojar y proteja del frío del agua subterránea", "Ropa"
            ),
            ChecklistItemSemilla(
                "Protector solar biodegradable si hay tramo de baño al aire libre", "Sostenibilidad"
            ),
            ChecklistItemSemilla(
                "Comunicación de la ruta prevista a alguien fuera de la cueva", "Seguridad", True
            ),
            ChecklistItemSemilla(
                "Respeto de las formaciones y prohibición de tocarlas", "Sostenibilidad"
            ),
        ],
    ),
    TipoAventuraSemilla(
        titulo="Travesías por desierto y expediciones",
        slug="travesias-por-desierto-y-expediciones",
        resumen=(
            "Recorridos de varios días por paisajes desérticos o de sal, a pie, en vehículo "
            "4x4 o en camello, con logística autónoma de agua y combustible."
        ),
        descripcion=(
            "<p>Las travesías por desierto —ya sea arena, roca o los inmensos salares de "
            "altiplano— comparten un mismo reto de fondo: la ausencia casi total de recursos "
            "naturales (agua, sombra, referencias de orientación) obliga a que toda la logística "
            "viaje con la expedición, ya sea a pie con apoyo de vehículos, en 4x4 o en camello "
            "según la región y la tradición local. La navegación es también distinta a la de "
            "montaña o bosque: en ausencia de sendero marcado, GPS, mapas y el conocimiento de "
            "guías beduinos o locales son la referencia principal, no las señales visuales del "
            "terreno.</p>"
            "<p>La amplitud térmica es el rasgo más subestimado del desierto: el calor extremo "
            "del día puede convivir con temperaturas cercanas a cero por la noche, así que la "
            "ropa por capas y un buen saco de dormir son tan importantes como la protección "
            "solar. La hidratación se planifica de forma mucho más estricta que en otros tipos "
            "de aventura: se calcula el agua necesaria por persona y día con margen de reserva, "
            "porque no hay fuentes naturales en las que reponer.</p>"
            "<p>En los salares de altiplano, a la sequedad extrema se suma la altitud (muchos "
            "están por encima de los 3.500 metros) y una reverberación solar intensísima sobre "
            "la superficie blanca, que exige protección ocular y cutánea reforzada. En ambos "
            "entornos —arena y sal— la orientación por cuenta propia sin guía experimentado es "
            "desaconsejable: la ausencia de referencias visuales hace muy fácil perder el rumbo, "
            "incluso a poca distancia del punto de partida.</p>"
        ),
        nivel_exigencia=4,
        seo_titulo="Travesías por desierto y expediciones: guía del tipo de aventura",
        seo_descripcion=(
            "Logística de agua, amplitud térmica y checklist esencial de las travesías por "
            "desierto y expediciones."
        ),
        checklist=[
            ChecklistItemSemilla(
                "Reserva de agua calculada con margen por persona y día", "Hidratación", True
            ),
            ChecklistItemSemilla("Ropa por capas para la amplitud térmica día/noche", "Ropa", True),
            ChecklistItemSemilla(
                "Protección solar y ocular de alto factor (reverberación en sal o arena)",
                "Salud",
                True,
            ),
            ChecklistItemSemilla(
                "Guía local o agencia con conocimiento probado de la ruta", "Formación", True
            ),
            ChecklistItemSemilla("GPS o navegación satelital de respaldo", "Orientación", True),
            ChecklistItemSemilla(
                "Vehículo 4x4 revisado con repuestos y combustible de margen", "Equipo"
            ),
            ChecklistItemSemilla(
                "Comunicación satelital para zonas sin cobertura", "Seguridad", True
            ),
            ChecklistItemSemilla(
                "Botiquín ampliado para varios días sin acceso a asistencia cercana", "Seguridad"
            ),
        ],
    ),
]

TIPO_POR_SLUG: dict[str, TipoAventuraSemilla] = {t.slug: t for t in TIPOS}
