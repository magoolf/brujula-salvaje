# ADR-DB-003 — Búsqueda en español insensible a tildes y collation, dentro de PostgreSQL

| Campo | Valor |
|---|---|
| Estado | PROPOSED |
| Fecha | 2026-09-25 |
| Ticket | TKT-F4-002 |
| Trazabilidad | REQ-015, REQ-051 (búsqueda p95 ≤500 ms), RULE-018, RULE-019, RULE-026, AP-10, AP-02, AP-13, DEC-AUTO-011, DEC-AUTO-048; DEC-AUTO-086, 087 |

## Contexto
- [HECHO] Búsqueda interna en español, insensible a tildes y mayúsculas, sin servicio externo (REQ-015, DEC-AUTO-011, CON-003).
- [OBSERVADO] AP-10: consulta de 2 a 100 caracteres sobre título (peso alto), resumen, cuerpo/descripción, nombre de país y de tipo; solo contenido publicado; resultados agrupados por tipo (Destino, Itinerario, Guía, Tipo) y ordenados por relevancia; p95 ≤500 ms extremo a extremo con 20 req/s.
- [OBSERVADO] Volumen indexable a 3 años: ≤2.530 documentos (500 + 1.000 + 500 + 30).
- [OBSERVADO en las notas de la versión 18] La búsqueda de texto completo y pg_trgm usan el proveedor de collation por defecto del clúster (aquí `builtin C.UTF-8`) para la clasificación de caracteres.
- RULE-019: orden A-Z "según el alfabeto español (sin tildes)".

## Alternativas
| Alternativa | Pros | Contras |
|---|---|---|
| `ILIKE '%q%'` sobre `unaccent()` | Trivial | Sin ranking ni stemming; lectura secuencial del cuerpo completo |
| **tsvector con configuración `es_unaccent` (spanish_stem + unaccent) y pesos A-D en una tabla derivada `busqueda_documento`, + pg_trgm como respaldo difuso sobre el título** | Ranking, stemming español, sin tildes; índice GIN; datos de otras tablas (país, tipos) en el documento | Mantenimiento del índice derivado por la aplicación |
| tsvector como columna generada en cada tabla | Sin código de mantenimiento | No puede incluir datos de otras tablas (país, tipos); una consulta con 4 UNION |
| Motor externo (Elasticsearch, Meilisearch) | Relevancia avanzada | Viola §4.E y CON-003; más operación |

## Decisión
1. **Objetos creados por la migración `core.0001`** (reversible):
   - `CREATE EXTENSION unaccent SCHEMA ext; CREATE EXTENSION pg_trgm SCHEMA ext;`
   - `CREATE TEXT SEARCH CONFIGURATION app.es_unaccent (COPY = pg_catalog.spanish); ALTER TEXT SEARCH CONFIGURATION app.es_unaccent ALTER MAPPING FOR hword, hword_part, word WITH ext.unaccent, spanish_stem;`
   - `app.f_normalizar(text) RETURNS text`, IMMUTABLE, PARALLEL SAFE, `SET search_path = pg_catalog, ext`. Equivale a `lower(trim(regexp_replace(ext.unaccent('ext.unaccent'::regdictionary, $1), '[[:space:]]+', ' ', 'g')))`. Es el patrón documentado de envoltura inmutable de unaccent, con el diccionario cualificado.
   - `app.f_tsquery_prefijo(q text) RETURNS tsquery`, STABLE: normaliza q, lo parte en tokens alfanuméricos (se descarta cualquier otro carácter, así que no se inyecta sintaxis tsquery), limita a 10 tokens, los une con `&` y aplica `:*` al último (búsqueda de 2 caracteres y por prefijo). Construye el resultado con `to_tsquery('app.es_unaccent', …)`. Para una entrada vacía tras normalizar devuelve NULL.
2. **Tabla derivada `app.busqueda_documento`** (una fila por contenido PUBLICADO de tipo DESTINO, ITINERARIO, GUIA o TIPO). `documento tsvector` = `setweight(título,'A') || setweight(resumen,'B') || setweight(nombres de país y de tipos,'C') || setweight(cuerpo en texto plano,'D')`, con la configuración `app.es_unaccent`. Además: `titulo_norm`, slug, título, resumen y `pais_nombre` para pintar resultados sin joins. Índices: GIN(`documento`) y GIN(`titulo_norm gin_trgm_ops`). `DEC-AUTO-086`.
   - **Mantenimiento**: el servicio de publicación hace upsert o delete de la fila **en la misma transacción** que publicar, actualizar, retirar, reactivar o eliminar (y el cambio de nombre de un país o tipo reindexa los documentos afectados en la transacción TAXONOMIA). Como la tabla solo contiene publicados, RULE-001 se cumple por construcción. El HTML del texto enriquecido se convierte a texto plano en la aplicación antes de indexarlo.
   - **Reconstrucción**: el comando idempotente `reindexar_busqueda` (DELETE + INSERT en una transacción) se ejecuta tras cada restauración, tras migraciones que cambien la configuración y bajo demanda. El comando de verificación comprueba que el recuento de publicados en alcance es igual al recuento de filas del índice (lo usa QA).
3. **Consulta** (AP-10): `tsq := app.f_tsquery_prefijo($1)`; `WHERE documento @@ tsq`; `rank := ts_rank_cd(documento, tsq, 32)`; agrupación por `tipo_contenido` con `row_number() OVER (PARTITION BY tipo_contenido ORDER BY rank DESC, titulo)`, límite por grupo y recuento total por grupo. **Respaldo difuso**: si la consulta FTS devuelve 0 filas, se hace `WHERE titulo_norm % app.f_normalizar($1)` ordenado por `similarity` DESC (umbral `pg_trgm.similarity_threshold=0.3`, límite 10). Todo parametrizado (THREAT-008). La transacción de búsqueda aplica `SET LOCAL statement_timeout = '2s'` (THREAT-009).
4. **Collation**:
   - La base de datos usa `builtin C.UTF-8` (ADR-DB-001): comparaciones deterministas y estables, y clasificación Unicode para `lower()` y para el analizador FTS.
   - Orden lingüístico: la columna `contenido.titulo` se declara con `db_collation="es-x-icu"` (collation ICU predefinida). `ORDER BY titulo` ordena según el alfabeto español: á = a en el nivel primario, ñ tras n. El índice parcial de listados hereda esa collation.
   - Unicidad insensible a mayúsculas y tildes: `titulo_norm` (columna generada **STORED** = `app.f_normalizar(titulo)`; en PostgreSQL 18 las generadas son VIRTUAL por defecto, así que en Django `GeneratedField(db_persist=True)`) con `UNIQUE(tipo, titulo_norm)`. Se descarta una collation no determinista (`ks-level1`) para la unicidad porque complica LIKE/índices y depende de la versión de ICU. `DEC-AUTO-087`.

## Rendimiento esperado
- [INFERIDO] Con ≤2.530 documentos, el índice GIN completo ocupa pocos MB y reside en memoria. Una búsqueda con ranking sobre las coincidencias tarda del orden de milisegundos, muy por debajo del presupuesto de 500 ms. **No es un benchmark**: la evidencia exigida es el informe de carga de AC-051 con el dataset semilla, más `EXPLAIN (ANALYZE, BUFFERS)` de AP-10 adjunto por QA.

## Trade-offs y riesgos
- `unaccent` convierte "ñ" en "n" ("año" ≈ "ano"). Es coherente con "insensible a tildes" y el impacto es bajo (el ranking por título mitiga la ambigüedad).
- Si se actualizan las reglas de `unaccent` (versión de la extensión), hay que reindexar los índices que dependen de `f_normalizar` (se trata de una función declarada IMMUTABLE). Queda en el runbook de actualización.
- Una indexación desincronizada si el Developer olvida el upsert. Mitigación: un único servicio de publicación, la prueba de invariante (recuento publicados = índice) y la reconstrucción idempotente.
- Las stopwords de `spanish` eliminan consultas formadas solo por palabras vacías ("de la"): devuelven vacío. Hay que mostrar el estado vacío con salidas (SCR-017).

## Condiciones de invalidez
- Se requieren sinónimos, corrección ortográfica avanzada, autocompletado o multi-idioma (FUTURE §32).
- El corpus supera ~10^6 documentos o la búsqueda incumple el p95 de forma sostenida con evidencia de `EXPLAIN`.
