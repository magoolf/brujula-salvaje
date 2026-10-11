/** Derivado de imagen tal como lo exponen los modelos de vista (URL de mismo origen y ancho). */
export interface DerivadoImagenSeo {
  readonly url: string;
  readonly ancho: number;
}

/**
 * Ancho preferido para `og:image` (tarjetas grandes de Facebook, LinkedIn, X, WhatsApp: 1200 px
 * recomendados; por debajo de ~600 px varias redes muestran la miniatura pequeña).
 */
export const ANCHO_OBJETIVO_REDES = 1200;

/**
 * Formatos por orden de compatibilidad con los rastreadores de redes sociales: JPEG lo leen todos;
 * WebP la mayoría; AVIF (el primer derivado que reciben las vistas) varios no lo admiten.
 */
const PREFERENCIA_FORMATO: readonly RegExp[] = [/\.jpe?g$/i, /\.webp$/i];

function rutaSinConsulta(url: string): string {
  return url.split(/[?#]/, 1)[0];
}

/**
 * TKT-056 (QA TKT-048 OBS-QA048-05): URL de la imagen para Open Graph. Antes se publicaba el `src`
 * de la portada, que es el primer derivado (AVIF de 400 px): pequeño y en un formato que varias
 * redes no muestran. Elige el derivado del formato más compatible disponible (JPEG, si no WebP) con
 * el menor ancho >= `ANCHO_OBJETIVO_REDES`, o el mayor de ese formato si ninguno llega. Sin
 * derivados de esos formatos, conserva `src`.
 */
export function urlImagenRedes(src: string, derivados: readonly DerivadoImagenSeo[] = []): string {
  const validos = derivados.filter((d) => Number.isFinite(d.ancho) && d.ancho > 0 && d.url !== '');
  for (const formato of PREFERENCIA_FORMATO) {
    const candidatos = validos
      .filter((d) => formato.test(rutaSinConsulta(d.url)))
      .sort((a, b) => a.ancho - b.ancho);
    if (candidatos.length === 0) continue;
    return (
      candidatos.find((d) => d.ancho >= ANCHO_OBJETIVO_REDES) ?? candidatos[candidatos.length - 1]
    ).url;
  }
  return src;
}
