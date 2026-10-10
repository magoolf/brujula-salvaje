import { DOCUMENT } from '@angular/common';
import { DestroyRef, RendererFactory2, Signal, effect, inject } from '@angular/core';

import {
  DerivadoImagen,
  construirSrcset,
  planificarFormatos,
} from '../../../shared/ui/imagen-responsiva/imagen-responsiva';

/** `id` del `<link rel="preload">` de la imagen LCP (uno por documento). */
export const ID_PRECARGA_PORTADA = 'bs-precarga-portada';

/** Atributos del `<link rel="preload" as="image">` responsivo. */
export interface PrecargaImagen {
  /** Tipo MIME del formato precargado; `null` para el respaldo (sin `type`, todos lo admiten). */
  readonly tipo: string | null;
  readonly srcset: string;
  readonly sizes: string;
}

/**
 * TKT-048 (PERFORMANCE_SPEC.carga: «imagen LCP con fetchpriority=high y preload responsivo»): qué
 * precargar para que coincida EXACTAMENTE con lo que elegirá el `<picture>` de `ImagenResponsiva`
 * y no haya doble descarga:
 * - el primer `<source>` del plan (AVIF si existe), con su `type`: un navegador que no lo soporta
 *   ignora el preload (no descarga nada) y el que lo soporta elige ese mismo `<source>`, con el
 *   mismo `srcset` y `sizes`, y reutiliza la respuesta precargada;
 * - sin `<source>` (solo JPEG), el `srcset` del `<img>` de respaldo, sin `type`.
 */
export function precargaDe(
  derivados: readonly DerivadoImagen[],
  sizes: string,
): PrecargaImagen | null {
  const plan = planificarFormatos(derivados);
  const fuente = plan.fuentes[0];
  if (fuente !== undefined) return { tipo: fuente.tipo, srcset: fuente.srcset, sizes };
  const srcset = construirSrcset(plan.respaldo);
  return srcset === '' ? null : { tipo: null, srcset, sizes };
}

/**
 * Mantiene en `<head>` un `<link rel="preload" as="image" fetchpriority="high">` para la imagen
 * LCP mientras viva el componente que la llama (contexto de inyección). En el SSR el enlace sale en
 * el HTML inicial ANTES de los `modulepreload` del bundle, así que la imagen compite antes por la
 * red; en la hidratación se reutiliza el mismo elemento (por `id`, sin otra descarga) y al salir de
 * la ruta se retira. No es un script ni un estilo en línea: la CSP (`img-src 'self'`) lo admite.
 */
export function mantenerPrecargaImagen(precarga: Signal<PrecargaImagen | null>): void {
  const documento = inject(DOCUMENT);
  const renderer = inject(RendererFactory2).createRenderer(null, null);
  const cabeza = documento.head;
  const buscar = (): HTMLLinkElement | null =>
    cabeza.querySelector<HTMLLinkElement>(`link#${ID_PRECARGA_PORTADA}`) ?? null; // el DOM del SSR devuelve undefined
  const retirar = (): void => {
    const enlace = buscar();
    if (enlace !== null) renderer.removeChild(cabeza, enlace);
  };

  effect(() => {
    const datos = precarga();
    if (datos === null) {
      retirar();
      return;
    }
    const atributos: Readonly<Record<string, string | null>> = {
      // Orden deliberado: `type` e `imagesizes` antes que `imagesrcset`, que es el que dispara la
      // descarga.
      type: datos.tipo,
      imagesizes: datos.sizes,
      imagesrcset: datos.srcset,
    };
    const existente = buscar();
    const enlace = existente ?? (renderer.createElement('link') as HTMLLinkElement);
    // Solo se escribe lo que cambia (en la hidratación, nada: el navegador no vuelve a evaluar el
    // preload) y, en un enlace nuevo, todo ANTES de insertarlo en `<head>`.
    for (const [nombre, valor] of Object.entries(atributos)) {
      if (enlace.getAttribute(nombre) === valor) continue;
      if (valor === null) renderer.removeAttribute(enlace, nombre);
      else renderer.setAttribute(enlace, nombre, valor);
    }
    if (existente === null) {
      renderer.setAttribute(enlace, 'id', ID_PRECARGA_PORTADA);
      renderer.setAttribute(enlace, 'rel', 'preload');
      renderer.setAttribute(enlace, 'as', 'image');
      renderer.setAttribute(enlace, 'fetchpriority', 'high');
      renderer.appendChild(cabeza, enlace);
    }
  });
  inject(DestroyRef).onDestroy(retirar);
}
