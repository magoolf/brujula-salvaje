# ADR-DB-002 — Modelo físico del contenido editorial: supertipo `contenido` y relaciones polimórficas con integridad declarativa

| Campo | Valor |
|---|---|
| Estado | PROPOSED |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-002 |
| Trazabilidad | BLUEPRINT §18 (DATA-003, 005, 006, 009..014, 016..019, 022, 026), §39.1, RULE-001, 002, 007, 008, 011, 026, 027; STATE-001; DEC-AUTO-081..085, 095, 097, 098 |

## Contexto
- [OBSERVADO] BLUEPRINT §18.1 define `CONTENIDO` como abstracción lógica de 7 tipos (Destino, Itinerario, Guía, TipoAventura, Colección, TérminoGlosario, PáginaInstitucional) con atributos comunes (ATR-COMUN, §18.3), y siete relaciones "polimórficas" (DATA-011, 013, 017, 018, 019, 022, 026) cuya materialización corresponde a esta skill (§39.1).
- [OBSERVADO] Reglas que abarcan varios tipos: la descripción SEO debe ser única entre las páginas publicadas (RULE-027); el sitemap y SCR-022 listan todo lo publicado (AP-12); el slug es único por tipo e inmutable tras publicarse (RULE-008); el borrado físico solo es posible en los borradores nunca publicados (§39.2).
- [HECHO] Skill_Base_datos §2: la integridad crítica se defiende en la base de datos.

## Alternativas
| Alternativa | Integridad referencial | Reglas entre tipos | Encaje en Django | Veredicto |
|---|---|---|---|---|
| A. Una tabla por tipo + `GenericForeignKey` (contenttypes) | **Ninguna** (id suelto, sin FK) | Solo en la aplicación | Nativo | Rechazada: viola §2 |
| B. Una tabla por tipo + arco exclusivo (una FK anulable por tipo destino y `CHECK num_nonnulls(...) = 1`) | Sí | La unicidad SEO entre tipos no es declarable | Aceptable, pero de 5 a 7 columnas FK por tabla de relación | Rechazada: esquema frágil al añadir tipos |
| C. Tablas por pares (p. ej. `destino_medio`, `guia_medio`…) | Sí | No | Muchas tablas (≈25) | Rechazada: explosión de tablas y de consultas UNION |
| **D. Supertipo `contenido` (ATR-COMUN) + subtipos 1:1 (PK = FK) + relaciones hacia `contenido(id)`, con restricción del tipo mediante FK compuesta `(contenido_id, tipo_contenido) → contenido(id, tipo)`** | Sí, total | Sí: la unicidad de SEO, slug y título se resuelve con índices sobre una sola tabla | `OneToOneField(primary_key=True)` + `ForeignKey` + `RunSQL` para la FK compuesta | **Elegida** |

## Decisión
1. **Supertipo** `app.contenido`: id, `tipo` ∈ {DESTINO, ITINERARIO, GUIA, TIPO, COLECCION, TERMINO, PAGINA}, slug, título, `titulo_norm` (generada STORED), estado editorial, fechas de publicación y retiro, SEO, `portada_id`, autoría, `version` (bloqueo optimista, DEC-AUTO-050). `UNIQUE(tipo, slug)`, `UNIQUE(tipo, titulo_norm)`, `UNIQUE(id, tipo)` (destino de las FK compuestas) y un índice único parcial sobre la descripción SEO normalizada `WHERE estado_editorial='PUBLICADO'`. `DEC-AUTO-081`.
2. **Subtipos** (`destino`, `itinerario`, `guia`, `tipo_aventura`, `coleccion`, `termino_glosario`, `pagina_institucional`): la PK es `contenido_id` (FK a `contenido`, ON DELETE CASCADE). La columna `tipo_contenido` es constante (`CHECK = '<TIPO>'`) y la FK compuesta `(contenido_id, tipo_contenido) → contenido(id, tipo)` impide que un subtipo cuelgue de un contenido de otro tipo. En Django se usa `OneToOneField(Contenido, primary_key=True, on_delete=CASCADE)` explícito (se recomienda no usar la herencia multi-tabla implícita, para evitar joins ocultos).
3. **Relaciones polimórficas**: cada tabla guarda `contenido_id` (FK) + `tipo_contenido` (CHECK con los tipos admitidos) + la FK compuesta hacia `contenido(id, tipo)`. Así el tipo queda garantizado por la base de datos (p. ej., un elemento de colección solo puede ser un DESTINO o un ITINERARIO). `DEC-AUTO-082`.
   - DATA-011 → `elemento_coleccion` (DESTINO, ITINERARIO).
   - DATA-013 → `contenido_termino` (DESTINO, ITINERARIO, GUIA, TIPO) + FK a `termino_glosario`.
   - DATA-017 → `contenido_medio`: **solo el rol GALERIA** (DESTINO, ITINERARIO, GUIA, TIPO, COLECCION). El rol PORTADA se materializa como la FK directa `contenido.portada_id` y el hero de inicio como `config_inicio.hero_medio_id`. La vista `v_medio_uso` une los tres usos (AC-117, AP-11, AP-22). `DEC-AUTO-085`.
   - DATA-018 → `fuente` (FK a `contenido`, sin restricción de tipo).
   - DATA-019 → `relacion_contenido` (origen y relacionado, ambos con FK compuesta; `CHECK origen_id <> relacionado_id`).
   - DATA-022 → `destacado_inicio` (el CHECK liga la sección con el tipo).
   - DATA-026 → `revision_contenido` (FK con **ON DELETE RESTRICT**: un contenido con revisiones, es decir, publicado alguna vez, no puede borrarse físicamente).
4. **Atributos multivaluados**:
   - `meses_mejor_epoca` → `smallint[]` con `CHECK (meses <@ '{1..12}')` + la función IMMUTABLE `app.f_sin_duplicados(smallint[])`. Se consulta con `&&` (OR dentro de la faceta) y `unnest` para el conteo por mes. **Sin índice GIN**: con ≤500 destinos, una lectura secuencial cuesta menos que mantener el índice. Se revalúa por encima de 5.000 destinos. `DEC-AUTO-083`.
   - `derivados` del medio → tabla hija `medio_derivado` (formato, ancho, ruta y sha256), con `UNIQUE(medio_id, formato, ancho_px)`. Se descarta JSONB porque se necesitan checksums por archivo para AC-054 y unicidad declarativa. `DEC-AUTO-084`.
   - N:M simples (destino–tipo, itinerario–tipo, guía–destino, guía–tipo) → tablas intermedias con `UNIQUE(a, b)`. `tipo_principal` pertenece a los tipos del destino mediante la FK compuesta `(contenido_id, tipo_principal_id) → destino_tipo_aventura(destino_id, tipo_aventura_id)` DEFERRABLE INITIALLY DEFERRED.
5. **Guardas declarativas del ciclo de vida (STATE-001)**:
   - CHECK por estado: PUBLICADO ⇒ fecha de revisión, `primera_publicacion_en` y `publicado_actualizado_en` no nulas; descripción SEO obligatoria (salvo TERMINO); portada obligatoria (salvo TERMINO y PAGINA). RETIRADO ⇒ `retirado_en` y `motivo_retiro` no nulos y `primera_publicacion_en` no nula. PAGINA nunca pasa a RETIRADO.
   - Trigger `trg_contenido_guardas` (BEFORE UPDATE/DELETE): `tipo` inmutable; `slug` inmutable si `primera_publicacion_en` no es nula (RULE-008, AC-101); `primera_publicacion_en` no se modifica una vez fijada; DELETE prohibido si el contenido se publicó alguna vez o si `tipo='PAGINA'` (§39.2, AC-033).
   - Las reglas que dependen de conteos y relaciones (≥3 medios DISPONIBLES en la galería, ≥600 palabras, días = duración, ≥3 relacionados elegibles, ≥4 elementos de colección, licencia compatible) **se validan en el servicio de publicación**, dentro de la transacción con bloqueo de fila. No son expresables como CHECK sin triggers cross-row de alto coste de mantenimiento.
6. **Longitudes**: los `varchar(n)` siguen §18. Los textos enriquecidos (`text`) llevan `CHECK (char_length(x) <= 100000)` como defensa contra el abuso de almacenamiento (THREAT-009). `[SUPUESTO]` 100.000 caracteres ≫ el contenido experto previsto. `DEC-AUTO-097`.
7. **Unicidad del título**: `UNIQUE(tipo, titulo_norm)` para **todos** los tipos (normalización: minúsculas, sin tildes, espacios colapsados). Cubre el nombre único de Destino y Tipo y el término insensible a mayúsculas y tildes (RULE-026). `[INFERIDO]` de §18.3 ("Único: Por tipo"). `DEC-AUTO-098`.
8. **Autoría de la carga semilla**: `creado_por_id`, `actualizado_por_id`, `subido_por_id` y `revision_contenido.creado_por_id` son **anulables**. NULL significa "carga inicial por procedimiento operativo". No se crea ninguna cuenta de sistema (THREAT-027). Toda operación del panel debe fijarlos (validación del servicio). `DEC-AUTO-095`.

## Trade-offs y riesgos
- Cada lectura de detalle hace un join `contenido ⋈ subtipo` (PK-PK, coste despreciable con este volumen).
- Django no modela FK compuestas: se crean con `migrations.RunSQL` (con `reverse_sql`) y no aparecen en el estado de Django. Mitigación: una prueba de esquema que las verifique por introspección (`pg_constraint`), y `makemigrations --check` en CI.
- La columna constante `tipo_contenido` en los subtipos ocupa unos bytes por fila (irrelevante).

## Complejidad operacional
Media-baja: unas 12 sentencias `RunSQL` (FK compuestas, trigger, funciones), todas reversibles.

## Condiciones de invalidez
- Se añaden tipos de contenido con atributos comunes divergentes (el supertipo deja de ser cohesivo).
- Se adopta un CMS externo o edición colaborativa en tiempo real (OUT OF SCOPE §31).
- El volumen supera 10^6 filas de contenido: habría que revisar índices y particionado.
