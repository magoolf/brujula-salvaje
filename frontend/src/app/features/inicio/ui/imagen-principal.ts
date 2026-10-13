import {
  FuenteImagen,
  construirSrcset,
  elegirSrcRespaldo,
  planificarFormatos,
} from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { ImagenVista } from '../domain/modelos';

/**
 * `sizes` de la imagen del bloque principal (PERFORMANCE_SPEC.Sizes_Recomendados.hero): ocupa todo
 * el ancho del viewport.
 */
export const SIZES_IMAGEN_PRINCIPAL = '100vw';

/** Lo que la plantilla necesita para pintar el `<picture>` del bloque principal. */
export interface PlanImagenPrincipal {
  readonly alt: string;
  /** Un `<source>` por formato eficiente (AVIF, WebP), del más al menos eficiente. */
  readonly fuentes: readonly FuenteImagen[];
  /** `srcset` del `<img>` de respaldo (JPEG); cadena vacía si no hay candidatos. */
  readonly srcset: string;
  readonly src: string;
}

/**
 * TKT-048 (QA TKT-041 OBS-C2-02; solapa con TKT-029): la portada de Inicio era un `<img>` con el
 * primer derivado de la lista (`…-400.avif`) sin `srcset` ni respaldo: reescalada en escritorio e
 * invisible en navegadores sin AVIF (WebKit). Ahora reparte los derivados igual que
 * `ImagenResponsiva` (TKT-020): AVIF y WebP en `<source type>` (un navegador sin soporte los salta
 * sin descargarlos) y JPEG en el `<img>` de respaldo, todos con `srcset` por ancho.
 * No se usa el componente `ImagenResponsiva` porque su marco fija la altura por `aspect-ratio`, y
 * esta imagen debe cubrir el bloque principal (posición absoluta, `object-fit: cover`).
 */
export function planImagenPrincipal(imagen: ImagenVista | null): PlanImagenPrincipal | null {
  if (imagen === null) return null;
  const plan = planificarFormatos(imagen.derivados);
  return {
    alt: imagen.alt,
    fuentes: plan.fuentes,
    srcset: construirSrcset(plan.respaldo),
    src: elegirSrcRespaldo(imagen.src, imagen.derivados, plan.respaldo),
  };
}
