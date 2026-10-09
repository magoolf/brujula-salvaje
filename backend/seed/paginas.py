"""4 páginas institucionales (REQ-025). El modelo `PaginaInstitucional.clave` (apps/contenido/
models.py, `ClavePagina`) solo admite 4 valores fijos (ACERCA_DE, POLITICA_DATOS,
POLITICA_COOKIES, AVISO_LEGAL) — no 5: el ticket mencionaba también "Créditos de imágenes", que
no tiene una `clave` disponible en el esquema actual (fuera de archivos_permitidos de este
ticket); el crédito por imagen ya se satisface de forma estructural con REQ-043 (autor/fuente/
licencia por medio, mostrados junto a cada imagen), así que no hay una funcionalidad pública sin
cubrir, solo una página institucional adicional que no cabe en el esquema. Ver HANDOFF (gap).

Contenido honesto y verificable a partir de las decisiones ya tomadas en requirements.yaml
(DEC-AUTO-002 sin hosting, DEC-AUTO-005 panel interno, DEC-AUTO-967 fotografías de Wikimedia
Commons con licencia libre, DEC-AUTO-015 sin analítica ni cookies no esenciales en el sitio
público): no se inventan datos de un responsable legal real (ConfigSitio.responsable_* queda como
marcador, GAP-004, fuera de alcance de este comando).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PaginaSemilla:
    clave: str
    titulo: str
    slug: str
    cuerpo: str
    version_documento: str
    vigente_desde: date
    seo_titulo: str
    seo_descripcion: str


_VIGENTE_DESDE = date(2026, 9, 29)

PAGINAS: list[PaginaSemilla] = [
    PaginaSemilla(
        clave="ACERCA_DE",
        titulo="Acerca de Brújula Salvaje / Metodología editorial",
        slug="acerca-de",
        cuerpo=(
            "<h2>Qué es Brújula Salvaje</h2>"
            "<p>Brújula Salvaje es un sitio editorial independiente sobre destinos y actividades "
            "de aventura al aire libre: senderismo y trekking, alta montaña, escalada y vía "
            "ferrata, buceo, deportes de río, kayak, ciclismo de montaña, parapente, safari, "
            "surf, espeleología y travesías por desierto, entre otros. No vendemos reservas, "
            "paquetes ni servicios de viaje: nuestro contenido es informativo y editorial.</p>"
            "<h2>Cómo se elabora el contenido</h2>"
            "<p>Cada destino, itinerario y guía de este sitio pasa por un proceso editorial "
            "interno antes de publicarse: verificación de los datos geográficos y factuales "
            "citados, revisión de la dificultad y los riesgos descritos frente a fuentes "
            "públicas y criterio experto, y una revisión de estilo y accesibilidad. Todo "
            "contenido publicado muestra la fecha de su última revisión.</p>"
            "<p>Cuando la información disponible no permite afirmar una cifra exacta con "
            "confianza razonable (por ejemplo, un precio, un horario o un dato que cambia con "
            "frecuencia), preferimos una descripción cualitativa a una cifra que podría quedar "
            "desactualizada o ser incorrecta.</p>"
            "<h2>Autoría</h2>"
            "<p>El contenido de Brújula Salvaje se firma como obra del equipo editorial, no de "
            "una persona individual: refleja un proceso de creación, revisión y publicación "
            "compartido por quienes mantienen el sitio.</p>"
            "<h2>Medios e imágenes</h2>"
            "<p>Las fotografías que acompañan cada contenido proceden de Wikimedia Commons y "
            "solo se usan con licencias libres que permiten su publicación: dominio público, "
            "CC0, Creative Commons Atribución (CC BY) o Atribución-CompartirIgual (CC BY-SA). "
            "Antes de publicarla comprobamos que cada foto muestra de verdad el lugar o la "
            "actividad que ilustra. Cada imagen indica su autoría, su licencia y un enlace a la "
            "página de origen, y lleva una descripción alternativa; la página de Créditos las "
            "reúne todas.</p>"
            "<h2>Lo que este sitio no es</h2>"
            "<p>Este sitio no sustituye la valoración de guías certificados, operadores locales "
            "autorizados ni las fuentes oficiales de cada destino o parque. Los descargos de "
            "seguridad que acompañan a cada destino e itinerario son orientativos: siempre "
            "verifica las condiciones reales, los permisos vigentes y las recomendaciones "
            "oficiales antes de viajar.</p>"
        ),
        version_documento="1.0",
        vigente_desde=_VIGENTE_DESDE,
        seo_titulo="Acerca de Brújula Salvaje y nuestra metodología editorial",
        seo_descripcion=(
            "Qué es Brújula Salvaje, cómo elaboramos y revisamos el contenido, y de dónde "
            "vienen las imágenes que usamos."
        ),
    ),
    PaginaSemilla(
        clave="POLITICA_DATOS",
        titulo="Política de Tratamiento de la Información",
        slug="politica-de-tratamiento-de-la-informacion",
        cuerpo=(
            "<h2>Alcance de esta política</h2>"
            "<p>Esta política describe cómo se trata la información en Brújula Salvaje. El "
            "sitio público de destinos, itinerarios y guías no requiere registro, cuenta ni "
            "ningún dato personal para consultarse: no hay formularios de contacto, boletín "
            "informativo, comentarios ni perfiles de visitante en la parte pública del sitio.</p>"
            "<h2>Qué información no recopilamos</h2>"
            "<ul>"
            "<li>No usamos analítica de terceros ni píxeles publicitarios en el sitio "
            "público.</li>"
            "<li>No creamos perfiles de navegación de quienes visitan el sitio.</li>"
            "<li>No solicitamos datos personales para leer o guardar contenido de forma "
            "local en tu propio navegador.</li>"
            "</ul>"
            "<h2>Cuentas del equipo editorial</h2>"
            "<p>El panel de administración de contenidos, de uso exclusivamente interno para el "
            "equipo editorial, sí gestiona cuentas de personal con autenticación, registro de "
            "auditoría y controles de seguridad proporcionados a esa función; esos datos "
            "corresponden a personal del equipo, no a personas visitantes del sitio público, y "
            "se tratan conforme a la normativa de protección de datos aplicable, incluida la "
            "posibilidad de solicitar la actualización o eliminación de los datos de una cuenta "
            "desactivada.</p>"
            "<h2>Registros técnicos</h2>"
            "<p>Como cualquier servicio web, el servidor puede registrar información técnica "
            "básica de las peticiones (por ejemplo, para diagnosticar errores o proteger el "
            "servicio frente a abusos), sin asociarla a un perfil identificable de la persona "
            "visitante.</p>"
            "<h2>Contacto</h2>"
            "<p>Si tienes preguntas sobre esta política, puedes consultarlas a través de los "
            "canales de contacto que el equipo editorial mantenga publicados en cada momento.</p>"
        ),
        version_documento="1.0",
        vigente_desde=_VIGENTE_DESDE,
        seo_titulo="Política de Tratamiento de la Información de Brújula Salvaje",
        seo_descripcion=(
            "Cómo trata Brújula Salvaje la información: sin registro ni datos personales "
            "necesarios para consultar el sitio público."
        ),
    ),
    PaginaSemilla(
        clave="POLITICA_COOKIES",
        titulo="Política de cookies",
        slug="politica-de-cookies",
        cuerpo=(
            "<h2>Cookies en el sitio público</h2>"
            "<p>El sitio público de Brújula Salvaje (destinos, itinerarios, guías, tipos de "
            "aventura, colecciones y páginas institucionales) no utiliza cookies de analítica, "
            "publicidad ni seguimiento de ningún tipo. Cualquier preferencia que decidas "
            "guardar en tu navegador, cuando el sitio ofrezca esa función, se almacena "
            "localmente en tu propio dispositivo, no en nuestros servidores.</p>"
            "<h2>Cookies del panel editorial</h2>"
            "<p>El panel de administración de contenidos, de acceso exclusivo para el equipo "
            "editorial autenticado, sí utiliza una cookie de sesión estrictamente necesaria "
            "para mantener la sesión iniciada y una cookie de protección contra falsificación "
            "de peticiones entre sitios (CSRF). Ambas son técnicas y esenciales para el "
            "funcionamiento del panel: no se usan con fines de seguimiento ni se comparten con "
            "terceros.</p>"
            "<h2>Por qué no hay un banner de cookies</h2>"
            "<p>Al no usar cookies no esenciales en la parte pública del sitio, no es necesario "
            "solicitar consentimiento mediante un banner: las únicas cookies del sistema son "
            "estrictamente necesarias para el panel interno, que no visita el público general.</p>"
        ),
        version_documento="1.0",
        vigente_desde=_VIGENTE_DESDE,
        seo_titulo="Política de cookies de Brújula Salvaje",
        seo_descripcion=(
            "Brújula Salvaje no usa cookies de analítica ni publicidad en el sitio público: "
            "solo cookies técnicas esenciales en el panel editorial."
        ),
    ),
    PaginaSemilla(
        clave="AVISO_LEGAL",
        titulo="Aviso legal y términos de uso",
        slug="aviso-legal-y-terminos-de-uso",
        cuerpo=(
            "<h2>Naturaleza del sitio</h2>"
            "<p>Brújula Salvaje es un sitio editorial informativo sobre destinos y actividades "
            "de aventura al aire libre. No ofrece reservas, venta de productos o servicios, ni "
            "actúa como agencia de viajes, operador turístico ni intermediario de ningún tipo.</p>"
            "<h2>Carácter orientativo del contenido</h2>"
            "<p>La información publicada, incluidos dificultad, riesgos, mejor época, duración "
            "recomendada y cualquier otro dato de un destino, itinerario o guía, tiene "
            "carácter orientativo y editorial. No sustituye la valoración de guías "
            "certificados, operadores locales autorizados, autoridades del parque o reserva "
            "correspondiente, ni las fuentes oficiales vigentes en el momento del viaje. Cada "
            "actividad de aventura conlleva riesgos inherentes que la persona usuaria asume al "
            "practicarla.</p>"
            "<h2>Propiedad de los contenidos</h2>"
            "<p>Los textos y demás elementos originales de Brújula Salvaje son obra del equipo "
            "editorial. Las fotografías son obra de sus autores y se publican bajo la licencia "
            "libre que se indica junto a cada una, con enlace a su página de origen. El uso de "
            "enlaces internos entre contenidos del propio sitio está permitido; la reproducción "
            "de textos o imágenes fuera del sitio requiere atribución adecuada según se indique "
            "en cada caso.</p>"
            "<h2>Enlaces y menciones a terceros</h2>"
            "<p>Las menciones a lugares, parques, operadores, comunidades o instituciones no "
            "constituyen recomendación comercial ni relación contractual alguna con Brújula "
            "Salvaje; se citan con fines exclusivamente informativos.</p>"
            "<h2>Limitación de responsabilidad</h2>"
            "<p>Brújula Salvaje no se hace responsable de decisiones de viaje tomadas "
            "exclusivamente con base en el contenido de este sitio, ni de cambios posteriores "
            "en las condiciones de acceso, seguridad o normativa de los destinos descritos.</p>"
        ),
        version_documento="1.0",
        vigente_desde=_VIGENTE_DESDE,
        seo_titulo="Aviso legal y términos de uso de Brújula Salvaje",
        seo_descripcion=(
            "Naturaleza editorial e informativa de Brújula Salvaje, carácter orientativo del "
            "contenido y limitación de responsabilidad."
        ),
    ),
]
