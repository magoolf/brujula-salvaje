# ADR-medios-001 — Presupuesto de peso por píxel del AVIF de los derivados

| Campo | Valor |
|---|---|
| Estado | PROPOSED (pendiente de QA y de la integración por el Orquestador) |
| Fecha | 2026-10-12 |
| Ticket | TKT-071 (MEDIUM, residual de TKT-021) |
| Autor | Skill_Developer |
| Trazabilidad | REQ-052 (LCP ≤ 2,5 s), TKT-021, TKT-048 (parámetros explícitos y `regenerar_derivados`), DEC-AUTO-1001; PERFORMANCE_SPEC de HANDOFF_UI_UX (imagen LCP ≤ 200 KB, tarjeta ≤ 60 KB); DEC-AUTO-1310..1315; QA TKT-071 ciclo 1 (F-QA071-01, F-QA071-02) |
| Archivos | `backend/apps/medios/services.py`, `backend/apps/medios/api/views.py`, `backend/apps/medios/tests/test_tkt071_presupuesto_peso.py`, `backend/apps/medios/tests/test_tkt048_codificacion.py` |

## Contexto
- [MEDIDO] Tras TKT-021, el LCP móvil de `/colecciones` era de 2984 ms (Lighthouse devtools, Slow 4G, CPU x4). Seis de las siete rutas de listado ya cumplían.
- [MEDIDO] La imagen LCP es la portada de la primera colección por título, «Deportes de adrenalina y expediciones». Es la foto del puente de Kawarau (`seed/fotos/destino-queenstown-3.jpg`, 1200×900, compartida con la galería de Queenstown). Su AVIF de 800 px pesaba 87 305 bytes. Las imágenes LCP de las demás rutas pesan 50-56 KB.
- [MEDIDO] La causa es el contenido, no un parámetro mal puesto:
  - La foto tiene mucho detalle fino: follaje, roca fracturada y la estructura del puente.
  - Es 4:3 (800×600), con un 12 % más de píxeles que las 3:2. La tarjeta (`--bs-aspect-card: 4 / 3`) la muestra entera, así que recortarla no ayuda.
  - Con la calidad fija de TKT-048 (AVIF q52, speed 6) pesa 0,18 B/px. La mediana de las 129 fotos de la semilla a 800 px es de 0,10 B/px y el p90 de 0,16.
- [MEDIDO] Ninguna opción del códec reduce el peso a calidad igual. Se probaron `speed` 4, `enable-qm`, `tune` (`ssim`, `iq`), `deltaq-mode`, `aq-mode`, `sharpness`, 4:4:4 y `enable-chroma-deltaq`: el peso cambió entre −2 % y +60 %. Solo la calidad mueve el peso de forma útil.

## Decisión
El AVIF de cada derivado lleva un presupuesto de bytes por píxel: `PRESUPUESTO_BYTES_POR_PIXEL[AVIF] = 0.15`. Si el AVIF a la calidad base (52) lo supera, se recodifica con `CALIDADES_PRESUPUESTO[AVIF] = (48, 44)` hasta que cabe. La última calidad es el suelo: su resultado se conserva aunque no quepa. El orden de pesos de TKT-048 (AVIF ≤ WebP ≤ JPEG) se sigue aplicando después, y sus reintentos solo usan calidades inferiores a la que ya resultó.
- Se aplica a todas las imágenes y anchos por igual. Las de detalle normal (unas 112 de 129 a 800 px) no cambian ni un byte.
- El suelo, 44, es la misma calidad que TKT-048 ya aceptaba como primer reintento. No se pierde más nitidez de la que ya se admitía.
- El WebP (respaldo de navegadores sin AVIF) y el JPEG (respaldo universal) no llevan presupuesto.
- La validación, el resaneado y la codificación de los derivados se hacen **fuera de toda transacción**. Ver Consecuencias.
  - Subida: `subir_medios` se divide en dos fases (DEC-AUTO-1315). `preparar_subida` valida, resanea y codifica solo en memoria: no escribe en disco ni en la BD (solo lee para detectar un DUPLICADO y no codificarlo). `persistir_subida` crea las filas y escribe los archivos ya codificados.
  - Panel: la vista `POST /api/v1/panel/medios` llama a `preparar_subida` **antes** de `idempotencia.ejecutar`, que abre la transacción con o sin `Idempotency-Key`. Dentro del efecto solo va `persistir_subida`. `subir_medios` (las dos fases seguidas) queda para llamadas sin transacción exterior (`cargar_semilla`).
  - Regeneración: `regenerar_derivados` codifica antes de abrir la transacción y de bloquear la fila (DEC-AUTO-1314).
- Despliegue: los medios existentes se actualizan con `python manage.py regenerar_derivados` (TKT-048). Ese comando escribe cada derivado cuyo contenido cambia en una ruta nueva versionada (`<huella>-<ancho>-<sha12>.avif`), porque `/media/publico/**` es `immutable`, y borra el archivo antiguo al confirmar. Es idempotente.

## Alternativas
| # | Alternativa | Motivo del descarte |
|---|---|---|
| A | Bajar la calidad base del AVIF para todas (p. ej. 44) | Degrada también las ~112 fotos que ya cumplen, en las que la pérdida es más visible (zonas planas, cielo) |
| B | Opciones avanzadas de libaom | Medido: sin ganancia útil (ver Contexto) |
| C | Recortar el activo de semilla a 3:2 | La tarjeta es 4:3 y muestra la foto entera. Solo ahorraría ~11 % de píxeles y no protegería las subidas futuras de los editores |
| D | Cambiar la foto asignada a la colección en el manifiesto | Es una decisión editorial: la foto del puente de Kawarau, cuna del puenting, es la más representativa. Tampoco protege las subidas futuras |
| **E (elegida)** | **Presupuesto por píxel con suelo de calidad** | Corrige en origen y de forma general: acota el peso de las fotos con mucho detalle, que son justamente las que enmascaran mejor la pérdida (enmascaramiento por textura). No toca las demás |

## Consecuencias
- [MEDIDO] La imagen LCP de `/colecciones` pasa de 87 305 a 58 634 bytes en AVIF 800w (−33 %), dentro del presupuesto de tarjeta (≤ 60 KB).
- [MEDIDO] Las portadas de las cuatro colecciones quedan en ≤ 60 KB.
- [MEDIDO] Lighthouse 12.6.1 móvil, `--throttling-method=devtools`, mediana de 5, con la semilla regenerada sin presupuesto (antes) y con `regenerar_derivados` (después; 60 derivados AVIF actualizados de 1335, segunda ejecución sin cambios):

  | Ruta | LCP antes | LCP después |
  |---|---|---|
  | `/colecciones` | 2993 ms | **2336 ms** |
  | `/` | 2061 ms | 2087 ms |
  | `/destinos/everest-campo-base` | 2462 ms | 2458 ms |
  | `/destinos` | 1873 ms | 1860 ms |
  | `/guias` | 2306 ms | 2308 ms |

  CLS 0 en todas. Las demás rutas no cambian (sus imágenes LCP no superan el presupuesto).
- [MEDIDO] En la semilla a 800 px el presupuesto afecta a 17 de 129 fotos, que bajan a q48 o q44. El total de AVIF de 800 px baja un 6 %. Ningún derivado pesa más.
- [MEDIDO] La subida tarda algo más en las fotos afectadas: 1-2 codificaciones AVIF extra por ancho, de unos 0,1 s cada una a 800 px (ADR-DB-005, subida síncrona).
- [MEDIDO] La codificación de las fotos afectadas tarda más: en el contenedor del backend, la peor foto de la semilla pasa de 4,4 s a 11,2 s (todos los anchos y formatos), y el total de la semilla de 286 s a 353 s (+23 %).
- [MEDIDO] Antes, la subida codificaba dentro de la transacción, después del `INSERT` del medio. La conexión quedaba ociosa todo ese tiempo, y el rol `app_rw` tiene `idle_in_transaction_session_timeout = 30s` (INFRA-DB-000). Con el presupuesto, `cargar_semilla` como `app_rw` falló en local con `terminating connection due to idle-in-transaction timeout`. El riesgo ya existía para fotos grandes (2000 px) y el presupuesto lo agravaba. Por eso la codificación pasa a hacerse antes de abrir la transacción (DEC-AUTO-1314). Prueba: `test_AC_TKT071_06_subida_y_regeneracion_codifican_fuera_de_la_transaccion`, que falla sin el cambio.
- [MEDIDO] Corrección de QA (F-QA071-01, HIGH). DEC-AUTO-1314 solo movía la codificación dentro de `subir_medios`. La vista del panel la ejecuta dentro de `idempotencia.ejecutar` (`transaction.atomic`), así que por el panel seguía dentro de la transacción exterior. Una foto detallada de 3200×2400 respondía 500 por `idle_in_transaction_session_timeout`. Esta versión del ADR afirmaba por error que la subida del panel quedaba protegida. Se corrige con las dos fases de DEC-AUTO-1315. Prueba: `test_AC_TKT071_07_post_del_panel_codifica_fuera_de_la_transaccion` (HTTP real, `transaction=True`, con y sin `Idempotency-Key`), que falla sin el cambio de la vista.
- Idempotencia: la preparación no escribe nada, así que una repetición con la misma `Idempotency-Key` no deja filas ni archivos nuevos. Solo reproduce la respuesta guardada (lo comprueba la misma prueba). Como contrapartida, la repetición vuelve a validar y codificar (CPU) antes de saber que es una repetición. Se acepta porque las repeticiones son raras (reintentos de red) y el efecto no se duplica. Sin clave, un archivo ya subido se detecta como DUPLICADO antes de codificar.
- Memoria: la preparación guarda en memoria los derivados codificados de todos los archivos de la petición (máximo 10) hasta persistirlos. Antes se persistían uno a uno.
- Riesgo residual (F-QA071-02, LOW, previo a este ticket): si la transacción revierte después de escribir los archivos (p. ej. falla el `UPDATE` de `idempotencia_peticion`), quedan archivos huérfanos en `privado/`. No hay filas que apunten a ellos. No se corrige aquí: Django no ofrece un gancho de rollback, y escribir tras el commit podría dejar filas sin archivo, que es peor. La ventana se reduce, porque ahora tras escribir solo quedan `INSERT`s rápidos y el `UPDATE` de idempotencia.
- La nitidez baja ligeramente en las texturas de las fotos afectadas a q44. Se ve en una comparación 1:1 lado a lado, pero no a tamaño de tarjeta en móvil.
- Riesgo: las imágenes afectadas que sean imagen principal de una ficha a 1200-2000 px también bajan de calidad. Se acepta porque ya es la calidad de reintento de TKT-048. Si QA o los editores lo ven, se puede subir el suelo a 48 o el presupuesto a 0,16 B/px. Ambos cambios son reversibles con `regenerar_derivados`.
