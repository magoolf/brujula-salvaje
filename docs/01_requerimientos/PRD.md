# PRD — Portal editorial de viajes de aventura (nombre de marca provisional: "Brújula Salvaje")

| Campo | Valor |
|---|---|
| Documento | PRD v1.0 (F2, Modo Expansor) |
| Ticket | TKT-F2-001 |
| Fecha | 2026-09-24 |
| Productor | Skill_Requerimientos (subagente `requerimientos`) |
| Consumidor | skill_arquitecto_funcional (F3) |
| Autoridad de aprobación | Orquestador (Autoridad Delegada, CLAUDE.md §0.2) |
| Fuente estructurada | `docs/01_requerimientos/requirements.yaml` (fuente de verdad para IDs, AC y trazabilidad) |
| Estado del conjunto | PROPOSED — Health Check del conjunto: PASS (revisión estática). No es APPROVED hasta que lo marque la autoridad. |

> **Convención de origen.** Cada elemento lleva `ORIGEN: USUARIO (Pn)` cuando procede de una respuesta literal de la Entrevista Pública, u `ORIGEN: EXPANSIÓN_AUTÓNOMA (DEC-AUTO-XXX)` cuando lo infiere o propone este agente. Una expansión no es un requisito del usuario (CLAUDE.md §0.2).
>
> **Stack.** Este PRD no fija tecnología: el stack lo fijan los Contratos Técnicos en F5. Las menciones a "panel editorial", "búsqueda" o "mapa" describen capacidades, no soluciones.

---

## 1. Procedencia y evidencia

| Fuente | Tipo | Contenido | Fiabilidad |
|---|---|---|---|
| Idea original | Literal del usuario | "crear una página web nivel experto sobre vacaciones" | HECHO |
| Entrevista Pública P1 | Literal | "a" — opción A: guía/portal de viajes y destinos con inspiración, contenido experto e itinerarios | HECHO |
| P2 | Literal | "enfoque de aventura" | HECHO |
| P3 | Literal | "que sea algo de inspiracion, de explorar de aventuras, descubrimientos" | HECHO |
| P4 | Literal | "no tiene un objetivo de negocios, es de explorar de vivir" | HECHO |
| P5 | Literal | "todo tipo de visitantes que ingresen" | HECHO |
| P6 | Literal | "no" (sin cuentas de usuario) | HECHO |
| P7 | Literal | "que sea completo" | HECHO |
| P8 | Literal | "inspirar a explorar" | HECHO |
| P9 | Literal | "solo español." | HECHO |
| P10 | Literal | "no" (sin datos personales) | HECHO |
| P11 | Literal | "colombia" | HECHO |
| P12 | Literal | "no" (sin integraciones externas) | HECHO |
| P13 | Literal | "pueden haber mas de 100 personas diarias además pon por lo menos 20 destinos distintos" | HECHO |
| P14, P15, P16 | Sin respuesta | Presupuesto/hosting, disponibilidad, marca/estilo | DESCONOCIDO → GAP-001/002/003 cerrados con DEC-AUTO |
| Restricciones del Orquestador | Autoridad delegada | Sin costes ni despliegue; entrega local con Docker Compose; panel editorial como expansión; ≥20 destinos reales; Ley 1581; sin API de pago | DECISIÓN de autoridad delegada |
| Fuentes normativas | Secundarias consultadas 2026-09-24 | Ley 1581 de 2012; Decreto 1074 de 2015 (compila el Decreto 1377 de 2013), art. 2.2.2.25.3.1 | Fuente primaria (SUIN-Juriscol / Secretaría del Senado) NO consultada → GAP-006 |

**Nota sobre P1.** La opción A que eligió el usuario nombraba "inspiración, contenido experto e itinerarios". Por eso los destinos, el contenido experto (guías) y los itinerarios llevan `ORIGEN: USUARIO (P1)`. Sus cantidades, campos y formato son expansión autónoma.

---

## 2. Visión y contexto

### 2.1 Problema (PRB-001)
El usuario quiere un sitio web de nivel experto sobre vacaciones con enfoque de aventura. Su propósito es inspirar a explorar, descubrir y vivir experiencias, no alcanzar un objetivo comercial. Debe ser accesible para cualquier visitante, estar solo en español y no exigir registro ni recoger datos personales. ORIGEN: USUARIO (idea, P1-P3, P8).

### 2.2 Objetivos
| ID | Objetivo | Métrica | Target | Origen |
|---|---|---|---|---|
| OBJ-001 | Inspirar a explorar mediante contenido de aventura | Métricas sustitutas de producto (el usuario no fijó objetivo de negocio, P4): destinos publicados; porcentaje de páginas de contenido con ≥3 enlaces a contenido relacionado; páginas huérfanas | ≥20 destinos; 100 %; 0 | USUARIO (P4, P8) + métrica por DEC-AUTO-032 |
| OBJ-002 | Ofrecer contenido de nivel experto y creíble | Porcentaje de contenidos publicados con autor/equipo, fecha de última revisión, nivel de dificultad y advertencias de seguridad | 100 % | USUARIO (idea "nivel experto") + métrica por DEC-AUTO-023/033 |
| OBJ-003 | Servir a todo tipo de visitantes | Conformidad WCAG 2.2 AA; ninguna función pública exige registro | 0 violaciones axe serious/critical; 0 formularios de registro | USUARIO (P5, P6) + métrica por DEC-AUTO-029 |

> No existe objetivo de negocio medible (P4). El sitio no mide conversiones ni usa analítica de visitantes (REQ-003, REQ-059). La validación del cumplimiento de OBJ-001 es cualitativa (VAL-001: revisión del producto por el usuario en la entrega). GAP-005 queda ACCEPTED.

### 2.3 Stakeholders
| Stakeholder | Descripción | Origen |
|---|---|---|
| Visitante anónimo | "Todo tipo de visitantes": público hispanohablante, sin cuenta | USUARIO (P5, P6, P9) |
| Equipo editorial | Personal interno que crea, revisa y publica contenido. Su cuenta es de staff, no una cuenta pública | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-005) |
| Usuario / propietario del proyecto | Autor de la visión; valida el producto final | HECHO |
| Orquestador | Autoridad Delegada (Sponsor, PO, Architecture y Acceptance Authority) para decisiones reversibles | CLAUDE.md §0.2 |

### 2.4 Necesidades de stakeholder (STN)
| ID | Necesidad | Origen |
|---|---|---|
| STN-001 | El visitante quiere inspirarse con destinos de aventura en todo el mundo | USUARIO (P2, P3, P8) |
| STN-002 | El visitante quiere explorar y descubrir por sí mismo (navegar, buscar, filtrar, encontrar contenido relacionado) | USUARIO (P3) |
| STN-003 | El visitante quiere información experta y fiable para planear una aventura (itinerarios, guías, consejos) | USUARIO (idea, P1) |
| STN-004 | El visitante quiere usar el sitio sin registrarse y sin entregar datos personales | USUARIO (P6, P10) |
| STN-005 | El visitante quiere el contenido en español | USUARIO (P9) |
| STN-006 | El sitio debe ofrecer al menos 20 destinos distintos y soportar más de 100 visitantes diarios | USUARIO (P13) |
| STN-007 | El equipo editorial necesita mantener y ampliar el contenido sin tocar código | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-005) |

---

## 3. Alcance

### 3.1 Dentro del alcance (MVP "completo", P7)
Portal editorial público de solo lectura, con navegación interconectada entre: Inicio → Explorar destinos (filtros/búsqueda/mapa) → Ficha de destino → Itinerario / Tipo de aventura / Guías relacionadas → seguir explorando. Además: páginas institucionales y legales, y un panel editorial interno.

### 3.2 Fuera de alcance (Won't en este MVP) — DEC-AUTO-024
| Excluido | Motivo |
|---|---|
| Reservas, pagos, precios en tiempo real, afiliados | P1 eligió "guía/portal", no comparador ni agencia (opciones B y C descartadas) |
| Cuentas públicas, perfiles, comentarios, valoraciones de visitantes | P6 |
| Newsletter, formulario de contacto, cualquier captura de datos de visitantes | P10 |
| Analítica de terceros, píxeles publicitarios, SDKs de redes sociales | P10, P12, REQ-059 |
| Mapas o APIs de terceros (teselas, geocodificación, clima en vivo) | P12; sin API keys ni costes |
| Multi-idioma | P9 |
| Despliegue a producción u hosting con coste | P14 sin respuesta + restricción del Orquestador; queda tras Puerta Humana (CLAUDE.md §0.5) |

### 3.3 Restricciones generales (CR)
- REQ-002: sin cuentas públicas (P6).
- REQ-003: sin tratar datos personales de visitantes (P10).
- REQ-004: sin integraciones ni dependencias de terceros en tiempo de ejecución (P12).
- REQ-005: solo español (P9).
- REQ-006: la entrega es la construcción y las pruebas en local (Docker Compose), sin costes recurrentes (DEC-AUTO-002).

---

## 4. Requisitos funcionales (resumen; el detalle y los AC están en `requirements.yaml`)

| ID | Requisito | MoSCoW | Criticidad | Origen |
|---|---|---|---|---|
| REQ-001 | Portal editorial de viajes de aventura en español orientado a inspirar la exploración (BR) | Must | CRITICAL | USUARIO (P1, P2, P3, P8) |
| REQ-010 | Página de inicio inspiracional: destinos destacados, tipos de aventura, itinerarios y guías destacadas, accesos a explorar | Must | HIGH | USUARIO (P3) + formato DEC-AUTO-008 |
| REQ-011 | Listado/catálogo de todos los destinos publicados, con paginación u orden | Must | HIGH | USUARIO (P1, P13) |
| REQ-012 | Ficha de destino con el modelo de contenido mínimo (§6.2) | Must | CRITICAL | USUARIO (P1) + campos DEC-AUTO-008 |
| REQ-013 | Taxonomía de tipos de aventura (≥10), cada una con página y sus destinos | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-006) |
| REQ-014 | Filtros combinables: tipo de aventura, continente/región, país, dificultad, mejor época (mes), duración, nivel de presupuesto | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-012) |
| REQ-015 | Búsqueda interna de texto en español, insensible a tildes y mayúsculas, sin servicio externo | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-011) |
| REQ-016 | Itinerarios día a día vinculados a un destino | Must | HIGH | USUARIO (P1) + formato DEC-AUTO-009 |
| REQ-017 | Guías y consejos expertos (preparación, equipo, seguridad, salud, sostenibilidad, presupuesto) | Must | HIGH | USUARIO (P1 "contenido experto") + categorías DEC-AUTO-010 |
| REQ-018 | Mapa interactivo de destinos con cartografía local, sin teselas ni API de terceros | Should | MEDIUM | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-013) |
| REQ-019 | Galería de imágenes por destino con texto alternativo y créditos | Must | MEDIUM | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-014) |
| REQ-020 | Bloque "Sigue explorando": cada página de contenido enlaza al menos 3 contenidos relacionados | Must | HIGH | USUARIO (P3 "explorar, descubrimientos") + regla DEC-AUTO-032 |
| REQ-021 | Navegación global (cabecera, pie, migas de pan), mapa del sitio HTML, páginas de error 404/500 útiles | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-018) |
| REQ-022 | Panel editorial interno: alta, edición, borrador/publicado y retirada de todos los tipos de contenido y medios | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-005) |
| REQ-023 | Cada contenido experto muestra autoría (equipo editorial), fecha de última revisión y fuentes/metodología | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-023) |
| REQ-024 | Advertencias de seguridad por destino y actividad, más un descargo de responsabilidad visible | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-023) |
| REQ-025 | Páginas institucionales y legales: Acerca de / Metodología editorial, Política de tratamiento de datos, Política de cookies, Aviso legal / Términos de uso, Créditos de imágenes | Must | HIGH | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-017); REG-derivado REQ-070 |
| REQ-026 | SEO técnico: títulos y descripciones únicos, Open Graph, `sitemap.xml`, `robots.txt`, datos estructurados schema.org, URLs legibles en español | Must | MEDIUM | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-018) |
| REQ-027 | Colecciones curadas (p. ej., "Aventuras para principiantes", "Retos de alta montaña", "Aventura en Colombia") | Should | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-019) |
| REQ-028 | "¿Dónde ir cada mes?": vista por mes generada a partir de la mejor época de cada destino | Should | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-019) |
| REQ-029 | Checklist de equipo por tipo de aventura | Should | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-022) |
| REQ-030 | "Mis aventuras guardadas" solo en el navegador del visitante (sin cuenta y sin envío al servidor) | Could | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-020) |
| REQ-031 | Compartir: copiar enlace o compartir nativo del dispositivo, sin SDKs de redes sociales | Could | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-021) |
| REQ-032 | Glosario de términos de aventura enlazado desde los contenidos | Could | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-022) |
| REQ-033 | Versión imprimible de itinerarios y checklists | Could | LOW | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-022) |

### 4.1 Requisitos de datos / contenido semilla
| ID | Requisito | MoSCoW | Origen |
|---|---|---|---|
| REQ-040 | El sistema SHALL publicar como mínimo 20 destinos reales y distintos, con contenido en español | Must | **USUARIO (P13)** |
| REQ-041 | El contenido semilla SHALL incluir ≥10 tipos de aventura, ≥10 itinerarios (Should: 1 por destino), ≥10 guías expertas y ≥3 colecciones (si REQ-027 entra en el alcance) | Must | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-006/009/010) |
| REQ-042 | El 100 % de los destinos publicados SHALL tener completos los campos obligatorios del modelo (§6.2) | Must | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-008) |
| REQ-043 | El 100 % de los medios SHALL tener licencia compatible registrada, créditos y texto alternativo en español | Must | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-014); REG REQ-071 |
| REQ-044 | La distribución geográfica SHALL cubrir ≥5 continentes e incluir ≥4 destinos de Colombia | Should | EXPANSIÓN_AUTÓNOMA (DEC-AUTO-007) |

---

## 5. Requisitos no funcionales (obligatorios según §47, con métrica)

Mapeados a ISO/IEC 25010:2023. Las métricas provisionales se apoyan en ASM.

| ID | Característica / Sub | Requisito y métrica | Condición de medición | Origen |
|---|---|---|---|---|
| REQ-050 | Reliability / Availability | Disponibilidad objetivo ≥ 99,5 % mensual en producción futura (ASM-004). En el alcance local: 100 % de los servicios con healthcheck en estado `healthy` tras `compose up` en ≤ 120 s | Local: Docker Compose. Producción: monitor externo (tras Puerta Humana) | DEC-AUTO-003 (P15 sin respuesta) |
| REQ-051 | Performance / Time behaviour | Latencia p95 de la API de lectura ≤ 300 ms; búsqueda p95 ≤ 500 ms; tasa de error < 1 % | 20 req/s sostenidas durante 5 min, dataset semilla completo, entorno local de referencia | DEC-AUTO-026 |
| REQ-052 | Performance / Time behaviour + Interaction | LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1 (umbral "good" en p75). Proxy de laboratorio: Lighthouse móvil con rendimiento ≥ 90 y TBT ≤ 200 ms | Lighthouse CI (móvil, throttling por defecto) en Inicio, Listado, Ficha de destino, Itinerario y Guía | DEC-AUTO-026 |
| REQ-053 | Performance / Capacity + Flexibility / Scalability | Soportar 10× el volumen declarado: 1.000 visitas/día y 50 usuarios concurrentes sin degradar REQ-051 | Prueba de carga local | USUARIO (P13 ">100/día") + factor DEC-AUTO-025 |
| REQ-054 | Reliability / Recoverability | RPO ≤ 24 h; RTO ≤ 4 h (contenido y medios). Copia diaria y procedimiento de restauración probado | Simulacro de restauración en local | DEC-AUTO-027 |
| REQ-055 | Security / Integrity, Authenticity, Resistance | OWASP ASVS 4.0.3 nivel L2 en el alcance aplicable (panel editorial y superficie pública). Cabeceras: CSP sin `unsafe-inline` para scripts, X-Content-Type-Options, Referrer-Policy, frame-ancestors; HSTS en producción. 0 hallazgos HIGH/CRITICAL abiertos en SAST/secretos/dependencias | Semgrep, gitleaks, auditoría de dependencias, revisión ASVS (QA F8, F9) | Obligatorio §47 (ASVS L2 por defecto) — DEC-AUTO-028 |
| REQ-056 | Interaction capability / Inclusivity | WCAG 2.2 nivel AA: 0 violaciones axe serious/critical; navegación completa por teclado; foco visible; 100 % de imágenes informativas con alt | axe + Playwright en todas las plantillas de página; revisión manual por teclado | Obligatorio §47 — DEC-AUTO-029; USUARIO (P5) |
| REQ-057 | Security / Confidentiality (retención) | Visitantes: 0 datos personales almacenados. Registros técnicos sin IP completa (truncada/anonimizada), conservados ≤ 30 días. Auditoría editorial: 365 días. Cuentas editoriales: mientras estén activas; se eliminan o anonimizan ≤ 30 días tras la baja. Contenido: indefinido, con versión archivada al retirarse | Inspección de configuración y del esquema | Obligatorio §47 — DEC-AUTO-016/034 |
| REQ-058 | Functional suitability / Appropriateness (idioma) | 100 % de la interfaz pública y del contenido en español; `lang="es"`; locale es-CO para fechas y números; unidades métricas | Inspección + prueba automatizada de `lang` | USUARIO (P9) |
| REQ-059 | Security / Confidentiality (privacidad) | El sitio público SHALL realizar 0 solicitudes a dominios de terceros y fijar 0 cookies no esenciales (solo sesión/CSRF del panel editorial, con Secure, HttpOnly y SameSite) | Playwright: captura de red y cookies en todas las plantillas | USUARIO (P10, P12) + DEC-AUTO-015 |
| REQ-060 | Compatibility + Flexibility / Adaptability | Funciona en las 2 últimas versiones estables de Chrome, Firefox, Safari y Edge, y en Safari iOS y Chrome Android; diseño responsive de 320 px a 1920 px sin scroll horizontal | Playwright (chromium, firefox, webkit) + viewports 320/768/1280/1920 | DEC-AUTO-030 |
| REQ-061 | Performance / Resource utilization | Peso de transferencia de la carga inicial ≤ 1,5 MB en Inicio y Ficha; imágenes en formato moderno con tamaños responsivos y carga diferida fuera del primer viewport | Lighthouse / análisis de red | DEC-AUTO-026 |
| REQ-062 | Maintainability / Testability | Cobertura de pruebas automatizadas ≥ 80 % de líneas en la lógica de dominio y API; las rutas públicas cubiertas por E2E | Informe de cobertura en CI | DEC-AUTO-028 (umbral provisional, ASM-007) |
| REQ-063 | Reliability / Faultlessness + Maintainability / Analysability (OR) | Endpoints de salud (liveness/readiness) y registros estructurados sin datos personales | Inspección + prueba | DEC-AUTO-027 |

---

## 6. Modelo de contenido (propuesta para el Arquitecto Funcional; no es modelo físico)

### 6.1 Entidades de contenido — DEC-AUTO-008
Destino, Tipo de aventura, Itinerario (con Días), Guía/Artículo experto (con categoría), Colección, Imagen/Medio (con licencia y créditos), Región/Continente y País, Término de glosario, Página institucional. Todas tienen estado editorial (borrador/publicado/retirado), slug y fecha de última revisión.

### 6.2 Campos mínimos de un Destino (REQ-012, REQ-042)
Nombre; slug; país y región/continente; resumen inspiracional (≤ 300 caracteres); descripción experta (≥ 600 palabras); tipos de aventura (≥ 1); nivel de dificultad (escala de 1 a 5 con definición publicada); mejor época (meses); duración recomendada (días, rango); nivel de presupuesto orientativo (escala cualitativa de 1 a 4, sin precios en tiempo real); clima y altitud cuando aplique; cómo llegar (texto); consejos de seguridad y riesgos; recomendaciones de sostenibilidad; coordenadas (lat/long); ≥ 3 imágenes con alt y créditos; contenidos relacionados; fecha de última revisión.

### 6.3 Propuesta de 24 destinos reales — DEC-AUTO-007 (Must ≥ 20, REQ-040)
| # | Destino | País | Continente | Aventura principal |
|---|---|---|---|---|
| 1 | Ciudad Perdida (Teyuna), Sierra Nevada de Santa Marta | Colombia | América del Sur | Trekking |
| 2 | Caño Cristales, Serranía de La Macarena | Colombia | América del Sur | Senderismo / naturaleza |
| 3 | San Gil y Cañón del Chicamocha | Colombia | América del Sur | Rafting, parapente |
| 4 | Parque Nacional Natural Los Nevados | Colombia | América del Sur | Alta montaña |
| 5 | Torres del Paine | Chile | América del Sur | Trekking |
| 6 | El Chaltén y Monte Fitz Roy | Argentina | América del Sur | Trekking / escalada |
| 7 | Camino Inca a Machu Picchu | Perú | América del Sur | Trekking |
| 8 | Salar de Uyuni | Bolivia | América del Sur | Travesía / expedición |
| 9 | Islas Galápagos | Ecuador | América del Sur | Buceo / fauna |
| 10 | Volcán Arenal y Monteverde | Costa Rica | América Central | Canopy / senderismo |
| 11 | Cenotes de la Península de Yucatán | México | América del Norte | Buceo en cavernas / espeleología |
| 12 | Parque Nacional Yosemite | Estados Unidos | América del Norte | Escalada / senderismo |
| 13 | Parque Nacional Banff | Canadá | América del Norte | Kayak / montaña |
| 14 | Ruta Laugavegur | Islandia | Europa | Trekking |
| 15 | Dolomitas | Italia | Europa | Vía ferrata |
| 16 | Chamonix-Mont-Blanc | Francia | Europa | Alpinismo |
| 17 | Fiordos del oeste | Noruega | Europa | Kayak / senderismo |
| 18 | Monte Kilimanjaro | Tanzania | África | Alta montaña |
| 19 | Delta del Okavango | Botsuana | África | Safari / fauna |
| 20 | Campo base del Everest | Nepal | Asia | Trekking de altitud |
| 21 | Bahía de Ha Long | Vietnam | Asia | Kayak / navegación |
| 22 | Wadi Rum | Jordania | Asia | Travesía por desierto |
| 23 | Queenstown | Nueva Zelanda | Oceanía | Deportes extremos |
| 24 | Gran Barrera de Coral | Australia | Oceanía | Buceo |

### 6.4 Tipos de aventura propuestos — DEC-AUTO-006 (≥ 10)
Senderismo y trekking; Alta montaña y alpinismo; Escalada y vía ferrata; Buceo y snorkel; Rafting y deportes de río; Kayak y navegación; Ciclismo de montaña; Parapente y deportes aéreos; Safari y observación de fauna; Surf; Espeleología y cenotes; Travesías por desierto y expediciones.

### 6.5 Categorías de guías expertas — DEC-AUTO-010
Preparación física; Equipo y mochila; Seguridad y gestión de riesgos; Salud en altitud y en viaje; Viaje sostenible y "no dejar rastro"; Presupuesto y planificación; Fotografía de aventura; Primera aventura (principiantes). Mínimo 10 artículos semilla.

---

## 7. Requisitos regulatorios (REG) — Colombia (P11)

> No constituye asesoramiento jurídico (§1.2). Estado: PROPOSED. Solo se consultaron fuentes secundarias (2026-09-24). La verificación en la fuente primaria está pendiente (GAP-006), así que ningún REG puede pasar a APPROVED todavía (§7.4).

| ID | Norma | Aplicabilidad | Requisito |
|---|---|---|---|
| REQ-070 | Ley 1581 de 2012 (Régimen General de Protección de Datos Personales) y Decreto 1074 de 2015, Libro 2, Parte 2, Título 2, Capítulo 25 (compila el Decreto 1377 de 2013), art. 2.2.2.25.3.1 (políticas de tratamiento). Autoridad: Superintendencia de Industria y Comercio | **Parcial.** Los visitantes no aportan datos (P10). Sí aplica a: (a) datos de las cuentas del equipo editorial; (b) una dirección IP en los registros técnicos puede considerarse dato personal, por lo que se mitiga con REQ-057. INFERENCIA: la inscripción en el RNBD depende del tamaño del Responsable, que es DESCONOCIDO → GAP-004 | El sitio SHALL publicar una Política de Tratamiento de la Información que identifique al Responsable, las finalidades, los derechos del titular y el canal de atención. Las cuentas editoriales SHALL registrar la autorización del titular |
| REQ-071 | Ley 23 de 1982 (derechos de autor) y Decisión Andina 351 de 1993 | Aplica a imágenes y textos publicados | El sitio SHALL publicar solo medios con licencia que permita su uso y SHALL mostrar los créditos/atribución exigidos por la licencia |

**Evaluación de no aplicabilidad (evidencia de evaluación §19.1).** Ley 1618 de 2013 / Resolución MinTIC 1519 de 2020 (accesibilidad web): INFERENCIA de que no es obligatoria, porque el sitio no es un sujeto obligado de la Ley 1712 de 2014. Aun así se adopta WCAG 2.2 AA por DEC-AUTO-029. Ley 1480 de 2011 (Estatuto del Consumidor): no aplica por inferencia, porque no hay venta ni oferta de servicios.

---

## 8. Decisiones autónomas (DEC-AUTO)

Todas tienen Autoridad = Orquestador (Autoridad Delegada), estado PROPOSED, son reversibles y llevan `ORIGEN: EXPANSIÓN_AUTÓNOMA`. El detalle (alternativas, motivo, riesgo) está en `requirements.yaml`.

| ID | Resumen |
|---|---|
| DEC-AUTO-001 | Nombre de marca provisional "Brújula Salvaje" (requiere verificación marcaria antes de producción) |
| DEC-AUTO-002 | Entrega limitada a construcción y pruebas locales con Docker Compose; sin hosting ni costes (P14 sin respuesta) |
| DEC-AUTO-003 | Disponibilidad objetivo provisional 99,5 % mensual para producción futura; en local se usan healthchecks (P15 sin respuesta) |
| DEC-AUTO-004 | Dirección de marca "aventura inspiradora": fotografía protagonista, tono cercano y experto; el detalle visual lo define UI/UX (P16 sin respuesta) |
| DEC-AUTO-005 | Panel editorial interno con cuentas de staff (no públicas) y flujo borrador/publicado |
| DEC-AUTO-006 | Taxonomía de 12 tipos de aventura (mínimo 10) |
| DEC-AUTO-007 | Propuesta de 24 destinos reales en 5 continentes (América, Europa, África, Asia, Oceanía), 4 de ellos en Colombia |
| DEC-AUTO-008 | Modelo de contenido y campos mínimos obligatorios de un destino |
| DEC-AUTO-009 | Itinerarios día a día: mínimo 10 (Must) y objetivo de 1 por destino (Should) |
| DEC-AUTO-010 | Guías expertas en 8 categorías, mínimo 10 artículos |
| DEC-AUTO-011 | Búsqueda interna de texto en español, insensible a tildes, sin servicio externo |
| DEC-AUTO-012 | Filtros facetados combinables (tipo, región, país, dificultad, mes, duración, presupuesto) |
| DEC-AUTO-013 | Mapa con cartografía estática servida por el propio sitio (sin teselas, API keys ni terceros) |
| DEC-AUTO-014 | Medios alojados localmente, con licencia libre o propia registrada, créditos y alt obligatorios |
| DEC-AUTO-015 | Sin analítica de terceros ni cookies no esenciales en el sitio público; sin banner de consentimiento, pero con política de cookies publicada |
| DEC-AUTO-016 | Registros técnicos con IP anonimizada y retención ≤ 30 días |
| DEC-AUTO-017 | Páginas legales e institucionales (privacidad, cookies, aviso legal, metodología editorial, créditos) |
| DEC-AUTO-018 | SEO técnico, navegación global, migas de pan, mapa del sitio y páginas de error |
| DEC-AUTO-019 | Colecciones curadas y "¿Dónde ir cada mes?" como Should |
| DEC-AUTO-020 | "Aventuras guardadas" solo en el navegador del visitante (Could) |
| DEC-AUTO-021 | Compartir mediante enlace o función nativa, sin SDKs sociales (Could) |
| DEC-AUTO-022 | Checklist de equipo (Should), glosario y versión imprimible (Could) |
| DEC-AUTO-023 | Autoría editorial, fecha de revisión, advertencias de seguridad y descargo de responsabilidad en todo contenido experto |
| DEC-AUTO-024 | Exclusiones Won't: reservas, pagos, cuentas públicas, comentarios, newsletter, formularios de contacto, multi-idioma, datos en vivo |
| DEC-AUTO-025 | Dimensionamiento de capacidad a 10× el volumen declarado (1.000 visitas/día, 50 concurrentes) |
| DEC-AUTO-026 | Objetivos de rendimiento: p95 de API ≤ 300 ms, búsqueda ≤ 500 ms, Core Web Vitals "good", ≤ 1,5 MB de carga inicial |
| DEC-AUTO-027 | RPO 24 h / RTO 4 h con copia diaria y simulacro de restauración; endpoints de salud |
| DEC-AUTO-028 | OWASP ASVS L2, cabeceras de seguridad, cobertura de pruebas ≥ 80 % de la lógica de dominio |
| DEC-AUTO-029 | Conformidad WCAG 2.2 AA verificada con axe y revisión por teclado |
| DEC-AUTO-030 | Matriz de navegadores (2 últimas versiones) y responsive de 320 a 1920 px, mobile-first |
| DEC-AUTO-031 | Locale es-CO, unidades métricas, español neutro con referencias colombianas |
| DEC-AUTO-032 | Métricas sustitutas de OBJ-001 (cobertura, ≥ 3 enlaces relacionados por página, 0 huérfanas), porque no hay objetivo de negocio (P4) |
| DEC-AUTO-033 | Contenido semilla redactado por el ecosistema, marcado con fecha de revisión y sin cifras volátiles (precios exactos, requisitos de visado) |
| DEC-AUTO-034 | Auditoría de cambios del panel editorial (quién, qué, cuándo) con retención de 365 días |

---

## 9. Supuestos (ASM)
| ID | Supuesto | Validación | Impacto si es falso |
|---|---|---|---|
| ASM-001 | La audiencia es mayoritariamente hispanohablante de Colombia/LatAm y navega sobre todo desde el móvil | Revisión del usuario en la entrega (VAL-001) | Ajuste de prioridades de diseño |
| ASM-002 | Los picos de tráfico no superan 10× el volumen declarado | Monitorización en producción futura | Hay que redimensionar REQ-053 |
| ASM-003 | El equipo editorial es pequeño (1-5 personas) | Usuario / Orquestador | Roles y permisos más finos |
| ASM-004 | La producción futura tendrá TLS y un hosting capaz de 99,5 % | Puerta Humana de despliegue | Hay que revisar REQ-050 |
| ASM-005 | El contenido semilla generado por el ecosistema es aceptable si se marca y se revisa | VAL-001 | Hace falta redacción humana experta |
| ASM-006 | Las fuentes legales secundarias reflejan fielmente las primarias | GAP-006 | Revisión de REQ-070/071 |
| ASM-007 | El 80 % de cobertura es un umbral adecuado a la complejidad del dominio | QA F8 | Ajuste del umbral |

## 10. Dependencias (DEP)
- DEP-001 (precondition): F3 Arquitecto Funcional consume este PRD.
- DEP-002 (technical): el stack se fija en F5. Los REQ son agnósticos a la tecnología.
- DEP-003 (technical): el contenido semilla (REQ-040..044) depende del modelo físico de F4 (Base de Datos) y se carga en F7.
- DEP-004 (regulatory/blocking para producción): el despliegue requiere Puerta Humana (§0.5) y resolver GAP-004 (identidad del Responsable del tratamiento).

## 11. GAPs
| ID | Descripción | Criticidad | Estado | Resolución |
|---|---|---|---|---|
| GAP-001 | Presupuesto/hosting (P14) sin respuesta | HIGH | CLOSED-WITH-DECISION | DEC-AUTO-002 |
| GAP-002 | Disponibilidad esperada (P15) sin respuesta | MEDIUM | CLOSED-WITH-DECISION | DEC-AUTO-003 |
| GAP-003 | Marca/estilo (P16) sin respuesta | LOW | CLOSED-WITH-DECISION | DEC-AUTO-001, DEC-AUTO-004 |
| GAP-004 | Identidad legal y datos de contacto del Responsable del tratamiento (necesarios para la política de REQ-070 y para decidir sobre el RNBD) | HIGH (solo para producción) | OPEN | En local se usa un marcador `[RESPONSABLE POR DEFINIR]`. Bloquea la publicación y la aprobación de REQ-070 |
| GAP-005 | No existe objetivo de negocio medible (P4) | MEDIUM | ACCEPTED | DEC-AUTO-032 (métricas sustitutas) + VAL-001 |
| GAP-006 | Fuente primaria normativa no consultada | MEDIUM | OPEN | Verificar en SUIN-Juriscol / SIC antes de producción |
| GAP-007 | Origen y licencia concretos del material gráfico real | MEDIUM | OPEN | Lo resuelve el Developer/editorial en F7 según DEC-AUTO-014. Si no hay imágenes libres verificables, se usan ilustraciones o marcadores propios |
| GAP-008 | Sin revisor experto humano del contenido de aventura | MEDIUM | OPEN | RSK-001; recomendar revisión humana antes de producción |

## 12. Riesgos (RSK)
| ID | Riesgo | Inherente | Tratamiento | Residual |
|---|---|---|---|---|
| RSK-001 | Contenido de aventura inexacto que podría inducir a una práctica insegura (Safety) | HIGH | REQ-023/024, descargo, sin cifras volátiles, niveles de dificultad definidos, fecha de revisión | MEDIUM. Se recomienda revisión humana antes de producción |
| RSK-002 | Uso de imágenes sin licencia válida | HIGH | REQ-043/071, registro de licencia obligatorio, marcadores propios como alternativa | LOW |
| RSK-003 | Conflicto marcario con el nombre provisional | MEDIUM | Nombre configurable; verificación en la SIC antes de producción | LOW |
| RSK-004 | Scope creep por "que sea completo" frente a un MVP realizable | MEDIUM | MoSCoW explícito; Could solo si no bloquea Must | LOW |
| RSK-005 | Compromiso de cuentas editoriales (desfiguración del sitio) | HIGH | ASVS L2, limitación de intentos, contraseñas robustas, MFA como Should, auditoría | MEDIUM |
| RSK-006 | Información desactualizada (temporadas, accesos) | MEDIUM | Fecha de revisión visible, avisos de "verifica con fuentes oficiales" | LOW |
| RSK-007 | Degradación del rendimiento por imágenes pesadas | MEDIUM | REQ-061, imágenes responsivas | LOW |

No queda ningún riesgo residual HIGH/CRITICAL, así que no se activa la Puerta Humana por aceptación de riesgo en F2.

## 13. Validación y verificación
- VER: cada REQ tiene AC y método (Test / Inspection / Analysis / Demonstration / Review) en `requirements.yaml`. La ejecución corresponde a QA (F8) y DevOps (F9).
- VAL-001: el usuario revisa el producto terminado frente a la visión "inspirar a explorar" (Informe de Entrega, F10).
- VAL-002: el Orquestador revisa este PRD como Autoridad Delegada antes de F3.

## 14. Health Check del conjunto (§25)
| Criterio | Resultado | Nota |
|---|---|---|
| Complete | PASS | Cubre todas las respuestas P1-P13. P14-P16 se cerraron con DEC-AUTO. Están los NFR obligatorios de §47 |
| Consistent | PASS | Sin contradicciones. "Completo" (P7) y "sin integraciones" (P12) se concilian con DEC-AUTO-013/024 |
| Feasible | PASS | Alcance de solo lectura + panel editorial, entrega local |
| Comprehensible | PASS | — |
| Able to be Validated | PASS | Con VAL-001 cualitativa, porque no hay objetivo de negocio |
| **Resultado** | **PASS** (revisión estática) | Quedan GAPs abiertos (004, 006, 007, 008) que solo bloquean producción o la aprobación de REQ-070/071. No bloquean F3 |

Health Check individual: los requisitos con ORIGEN: USUARIO tienen Correct = PASS (evidencia: respuesta literal). Los de EXPANSIÓN_AUTÓNOMA tienen Correct = UNKNOWN hasta VAL-001. El resto de criterios son PASS.
