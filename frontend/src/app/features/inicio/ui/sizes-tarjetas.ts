/**
 * `sizes` de las tarjetas de Inicio (TKT-056, QA TKT-048 OBS-QA048-05). El `SIZES_TARJETA` genérico
 * declara 100vw en móvil, así que en las rejillas de varias columnas el navegador pedía el derivado
 * de 800 px para cajas de ~180 px. Se calculan desde pagina-inicio.css y `.bs-contenedor`
 * (máx. 1280 px con margen lateral 16/32/48 px en xs/md/lg y separación de 16 px); en los tramos con
 * número de columnas variable se toma el ancho mayor posible (cota superior, nunca menor que el
 * pintado).
 */

/**
 * «Explora por tipo de aventura» (`.rejilla--tipos`): 2 columnas, 3 desde 48rem y 6 desde 80rem
 * (6 × 184 px + 5 × 16 px = 1184 px).
 */
export const SIZES_TARJETA_TIPO_INICIO =
  '(min-width: 80rem) 184px, (min-width: 48rem) calc((100vw - 6rem) / 3), calc(50vw - 1.5rem)';

/**
 * Destinos, itinerarios y guías (`.rejilla`, columnas `auto-fill` de mínimo 16rem): 1 columna hasta
 * 35rem, 2 hasta 54rem, 3-4 hasta 80rem y 4 de 284 px desde 80rem.
 */
export const SIZES_TARJETA_REJILLA_INICIO =
  '(min-width: 80rem) 284px, (min-width: 54rem) calc((100vw - 6rem) / 3), ' +
  '(min-width: 48rem) calc(50vw - 2.5rem), (min-width: 35rem) calc(50vw - 1.5rem), calc(100vw - 2rem)';
