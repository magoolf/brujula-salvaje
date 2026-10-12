# ADR-medios-002 — Subida de fotos de cámara grandes y de lotes de 10 dentro del timeout de gunicorn

| Campo | Valor |
|---|---|
| Estado | PROPOSED (pendiente de QA y de la integración por el Orquestador) |
| Fecha | 2026-10-12 |
| Ticket | TKT-072 (MEDIUM, OBS-QA071-01; ampliado con OBS-QA071-03 MEDIUM y OBS-QA071-04 LOW por DEC-AUTO-1005) |
| Autor | Skill_Developer |
| Trazabilidad | DEC-AUTO-044 (JPEG/PNG/WebP ≤ 10 MB y ≤ 40 MP, recodificar, sin EXIF, derivados responsivos), THREAT-006/007, FLOW-013, ALT-017, ADR-API-002 §8 (subida síncrona, gunicorn 120 s), ADR-DB-005 (sin broker), ADR-medios-001 (DEC-AUTO-1315), HANDOFF_UI_UX ASM-UX-001 (anchos 320-1920); DEC-AUTO-1320..1324 |
| Archivos | `backend/apps/medios/services.py`, `backend/apps/medios/tests/test_tkt072_subida_fotos_grandes.py`, `frontend/src/app/features/panel/state/subida-medios.store.ts`, `frontend/src/app/features/panel/ui/subida-medios.ts`, sus specs y `frontend/e2e/panel-medios.spec.ts` |

## Contexto
- El panel admite fotos de hasta 40 MP y 10 MB, y hasta 10 por subida. El backend las valida, sanea y codifica de forma síncrona: gunicorn usa workers síncronos con timeout de 120 s, y no hay broker (ADR-DB-005).
- [MEDIDO por QA, OBS-QA071-01] Con una foto de 4800×3600 (17 MP), `_resanear` tardaba ~406 s y gunicorn mataba el worker (WORKER TIMEOUT + SIGKILL).
- [MEDIDO por QA, OBS-QA071-03] Una sola petición con 10 fotos de 4,3 MP también superaba los 120 s, también antes de TKT-071.
- Mediciones propias en el contenedor del backend (1,5 CPU y 1 GiB, Pillow 12.3.0 con libavif 1.4.2/aom). Se usaron fotos sintéticas «detalladas» (ruido multiescala, JPEG de hasta 10 MB con EXIF + GPS + XMP). Las tablas separan tres fases: validación y decodificación, resaneado y codificación de los derivados.

  | Foto | Antes: resanear | Antes: codificar | Antes: total | Antes: pico RSS |
  |---|---|---|---|---|
  | 12 MP (4000×3000) | 2,8 s | 34,4 s | 37,4 s | 1009 MB |
  | 17 MP (4800×3600) | 86,4 s | 34,3 s | **120,8 s** | 1020 MB |
  | 24 MP y 40 MP | no medidas: el resaneado ya agotaba la memoria del contenedor con 17 MP | | | |

- [MEDIDO] Causas, por orden de peso:
  1. **El resaneado** copiaba los píxeles con `putdata(get_flattened_data())`, que crea una tupla de Python por píxel. Con 17 MP son varios GiB frente al límite de 1 GiB del contenedor: el proceso llegaba al techo de memoria y el tiempo se disparaba (86-406 s según la presión de memoria).
  2. **Los hilos del AVIF.** Pillow pasa a libavif `max_threads = len(sched_getaffinity)`, que dentro del contenedor son las 20 CPU del host. La cuota de CPU es de 1,5 (cgroup v2 `cpu.max` = `150000 100000`), y con 20 hilos el planificador estrangula el proceso. Un AVIF de 2000 px tardaba 3,6 s con 20 hilos y 1,7 s con 2, con **el mismo resultado byte a byte** (536 342 B en ambos casos).
  3. **El derivado al ancho original.** Se codificaba en los tres formatos, y en AVIF con hasta 2-4 codificaciones por el presupuesto de TKT-071. Con fotos de cámara (4000-7300 px) suponía la mayor parte de los píxeles codificados.
  4. **El lote en una sola petición.** Cada foto suma su tiempo en la misma petición y la preparación retiene en memoria los derivados de todas (OBS-QA071-04).

## Decisión
1. **DEC-AUTO-1320. Copia sin metadatos en C.** `_imagen_sin_metadatos` copia los píxeles con `Image.new` + `paste`, sin crear objetos de Python por píxel:
   - El resultado es idéntico píxel a píxel al anterior en los modos RGB, RGBA, L, LA, P, CMYK e I;16.
   - Mantiene la misma regla de modos: RGB y RGBA se conservan; el resto pasa a RGB.
   - Sale sin `info`, EXIF, XMP ni ICC (THREAT-007).
   - DEC-AUTO-1322 (memoria): el decodificado original se libera en cuanto se copia, y los derivados se generan desde esa copia limpia (mismos píxeles).
   - `_codificar_derivados` no copia la imagen si ya es RGB y libera cada redimensionada.
2. **DEC-AUTO-1321. Derivado mayor acotado.** El derivado mayor es el ancho original acotado a `ANCHO_MAXIMO_DERIVADO = 2560` (función `anchos_derivados`). Por debajo de 2560 px no cambia nada; en particular la semilla, cuyo ancho máximo es 1920 px.
3. **DEC-AUTO-1323. Hilos del AVIF según la cuota de CPU.** `hilos_codificador()` = techo de la cuota de `cpu.max`, acotado por la afinidad. Sin cuota, o fuera de Linux, se usa la afinidad. En el contenedor da 2. Los bytes del AVIF no cambian respecto a 20 hilos.
4. **DEC-AUTO-1324. Un archivo por petición.** El panel envía el lote en secuencia, un archivo por petición, cada uno con su Idempotency-Key (cambio en el frontend).
   - Cada petición dura lo que una foto.
   - El resultado de cada archivo aparece en cuanto llega, y el progreso dice «Subiendo n de m… x %».
   - Si un archivo falla (red o error del servidor), la subida se detiene en él. Los resultados anteriores se conservan, el banner nombra el archivo fallido, y «Reintentar» continúa desde ese archivo con la misma clave (ALT-017), sin repetir los ya subidos.
   - Los medios ya aceptados se notifican aunque el lote falle a medias, para que el listado se recargue.
   - Se envían en secuencia y no en paralelo: con 1,5 CPU, dos fotos a la vez solo alargarían cada petición.
   - **El contrato no cambia:** `panelSubirMedios` sigue admitiendo 1..10 archivos, y la regla del cliente de un máximo de 10 por selección se mantiene.

### Por qué 2560 px es suficiente (DEC-AUTO-1321)
- El diseño fija anchos objetivo de 320 a 1920 px (HANDOFF_UI_UX, ASM-UX-001). Ninguna plantilla pide más de 1920 px de ancho CSS, y el mayor ancho CSS fijo es el de la portada de destino: `SIZES_PORTADA`, 1184 px.
- Demanda en píxeles físicos con DPR 2:

  | Plantilla | `sizes` | Ancho que pide con DPR 2 | ¿Cubierto por 2560? |
  |---|---|---|---|
  | Portada de destino | 1184 px | 2368 px | Sí |
  | Tarjetas | ≤ 50 vw (≤ 33 vw en escritorio) | — | Sí, en todos los casos |
  | Vista previa del panel | 960 px | 1920 px | Sí |
  | Imagen principal de inicio | 100 vw | por encima de 2560 solo con DPR ≥ 2 y más de 1280 px CSS (p. ej. 1440×2 = 2880) | No: recibe 2560, un reescalado ≤ 1,5× |

- Antes, una foto de cámara en ese caso descargaba el derivado de 4000-7300 px: varios MB en AVIF de una imagen LCP (REQ-052). Hoy la imagen principal de inicio viene de la semilla (≤ 1920 px), así que no cambia nada.

### Qué hace `regenerar_derivados` con los medios ya subidos
- Medios con original ≤ 2560 px, entre ellos toda la semilla: no cambian. Los parámetros de codificación son los mismos, y los hilos no alteran los bytes.
- Medios con original > 2560 px: el comando borra las filas de los derivados más anchos que la cota, y sus archivos al confirmar la transacción (`on_commit`, igual que con cualquier derivado descartado, TKT-048). Si no existía un derivado de 2560 px, lo crea. Prueba: `test_AC_TKT072_10_regenerar_un_medio_mas_ancho_que_la_cota`.
- Las URL publicadas de esos derivados anchos dejan de existir. Las páginas nuevas ya no las piden, porque el `srcset` sale de las filas. Una página en caché que las pida recibe 404 en ese único candidato del `srcset`.
- Mientras no se ejecute el comando, esos medios conservan el derivado ancho tal cual.
- Hasta este ticket no hay medios subidos por el panel en ningún entorno compartido.

## Alternativas
| # | Alternativa | Motivo del descarte |
|---|---|---|
| A | Subir `GUNICORN_TIMEOUT` (compose) | Fuera de `archivos_permitidos` (infra). Solo esconde el problema: un lote de 10 tardaría minutos con el worker ocupado, y el proxy cortaría antes |
| B | Procesar en segundo plano (Celery u otra cola) | No hay broker (ADR-DB-005). Cambia el contrato (la respuesta sería asíncrona). Botón de Pánico innecesario: el objetivo se cumple con margen |
| C | Rechazar fotos de más de N MP antes de procesar | Contradice DEC-AUTO-044 (≤ 40 MP), y medido no hace falta: 40 MP tardan 13,6 s |
| D | `speed` mayor del AVIF para los anchos grandes | Cambia (degrada) los derivados. Los hilos dan la misma ganancia sin tocar los bytes |
| E | Cota de 2000 px (el mayor de `ANCHOS_DERIVADOS`) | No cubre la portada de destino con DPR 2 (2368 px) |
| F | Lote en paralelo (concurrencia 2) desde el frontend | Con 1,5 CPU cada petición tarda más. Duplica la memoria de pico por editor |
| **G (elegida)** | **Copia en C + hilos según la cuota + cota de 2560 px + un archivo por petición** | Arregla las causas medidas sin cambiar el contrato, la infraestructura ni la calidad de los derivados por debajo de 2560 px |

## Consecuencias
- [MEDIDO] Tiempos en el contenedor después del cambio (preparación completa):

  | Foto | Total (antes → después) | Pico RSS |
  |---|---|---|
  | 12 MP | 37,4 s → **13,2 s** | 279 MB |
  | 17 MP | 120,8 s (QA: ~406 s) → **13,1 s** | 316 MB |
  | 24 MP | — → **13,4 s** | 380 MB |
  | 40 MP | — → **13,7 s** | 532 MB |

  El resaneado baja a 0,1-0,4 s. Por encima de 2560 px el coste ya no crece con los megapíxeles.
- [MEDIDO] Reproducción real por el panel (Chromium, stack `brujuladev072`, 2 workers de gunicorn):
  - Subida de 4 fotos (12, 17, 24 y 40 MP): 4 POST con 200, de 13,3, 13,2, 13,7 y 13,6 s; 57,6 s en total.
  - Lote de 10 fotos de 4,3 MP (el caso de OBS-QA071-03): 10 POST con 200, de 7,1-7,2 s cada uno; 73,6 s en total. Antes era una sola petición de más de 120 s, que acababa en SIGKILL.
  - En el log del backend: 0 «WORKER TIMEOUT», 0 SIGKILL.
  - En `pg_stat_activity` (muestras cada 2 s): 0 muestras «idle in transaction» de `app_rw`.
- [MEDIDO] Saneo: en los 266 archivos guardados de esas 14 subidas (originales saneados y derivados, en `privado/` y `publico/`) hay 0 marcadores `Exif\0\0`, `<x:xmpmeta`, `ns.adobe.com` ni los valores EXIF inyectados; `getexif()` vacío; sin `exif`/`xmp`/`icc_profile` en `info`. Los originales de entrada sí los llevaban.
- [MEDIDO] `cargar_semilla` completa en el contenedor: 151 s. ADR-medios-001 midió 353 s (con presupuesto) y 286 s (sin él); la mejora viene de los hilos del AVIF.
- Derivados:
  - Mismos píxeles de origen, mismos parámetros y el mismo presupuesto de TKT-071.
  - Bytes iguales con los hilos medidos.
  - La única diferencia es que en fotos de más de 2560 px no hay derivado a su ancho original.
- Memoria: con una foto por petición, el servidor solo retiene los derivados de una (OBS-QA071-04). El pico por petición de 40 MP es de unos 530 MB.
- Riesgo residual (LOW): el contenedor tiene 1 GiB y `GUNICORN_WORKERS` vale 3 por omisión. Dos o tres editores subiendo a la vez fotos de 40 MP podrían sumar más de 1 GiB. Antes ya bastaba una sola foto de 17 MP para llegar al techo. Mitigación posible fuera de este ticket (DevOps): 2 workers o más memoria.
- Riesgo: la imagen principal de inicio con una foto de cámara, en pantallas de más de 1280 px CSS con DPR ≥ 2, recibe 2560 px (ver Decisión). Es reversible: se cambia la constante y se ejecuta `regenerar_derivados`.
- Sin cambios de contrato OpenAPI ni migraciones. El mapeo 413/503 del proxy es de DevOps (TKT-OPS-034).
