import { DOCUMENT } from '@angular/common';
import {
  CSP_NONCE,
  Injectable,
  REQUEST,
  Renderer2,
  RendererFactory2,
  inject,
} from '@angular/core';
import { Meta, Title } from '@angular/platform-browser';

import { JsonLd, serializarJsonLd, urlAbsoluta } from './datos-estructurados';
import { LOCALE_OG, NOMBRE_MARCA, SEPARADOR_TITULO } from './marca';

export interface ImagenSeo {
  /** URL absoluta o ruta desde la raíz del mismo origen. */
  readonly url: string;
  readonly alt: string;
}

export interface MetadatosPagina {
  /** Título de la página sin la marca (se añade « — Brújula Salvaje»). */
  readonly titulo: string;
  readonly descripcion?: string;
  /** Ruta canónica (p. ej. `/destinos/patagonia`); por defecto, la ruta actual sin parámetros. */
  readonly rutaCanonica?: string;
  readonly imagen?: ImagenSeo;
  readonly tipoOg?: 'website' | 'article';
  /** `false` añade `noindex, nofollow` (vistas previas, errores). Por defecto `true`. */
  readonly indexable?: boolean;
  readonly datosEstructurados?: JsonLd | readonly JsonLd[];
}

const ID_JSON_LD = 'bs-json-ld';
const ID_CANONICA = 'bs-canonica';

/** Título completo con la marca. */
export function tituloConMarca(titulo: string): string {
  const limpio = titulo.trim();
  return limpio === '' || limpio === NOMBRE_MARCA ? NOMBRE_MARCA : `${limpio}${SEPARADOR_TITULO}${NOMBRE_MARCA}`;
}

/**
 * Servicio SEO reutilizable (FEAT-027, MOD-008): title, description, canónica, Open Graph,
 * robots y JSON-LD. Funciona igual en SSR (CON-007: los metadatos llegan en el HTML inicial) y en
 * el navegador. El JSON-LD lleva el nonce CSP de la petición y se escribe con textContent
 * (sin innerHTML) y serialización escapada.
 */
@Injectable({
  providedIn: 'root',
})
export class Seo {
  private readonly titulo = inject(Title);
  private readonly meta = inject(Meta);
  private readonly documento = inject(DOCUMENT);
  private readonly peticion = inject(REQUEST, { optional: true });
  private readonly nonce = inject(CSP_NONCE, { optional: true });
  private readonly renderer: Renderer2 = inject(RendererFactory2).createRenderer(null, null);

  /** Origen público (esquema + host) de la petición actual. */
  origen(): string {
    if (this.peticion !== null) {
      return new URL(this.peticion.url).origin;
    }
    return this.documento.location?.origin ?? '';
  }

  /** Ruta actual sin query string ni fragmento. */
  rutaActual(): string {
    const url = this.peticion !== null ? new URL(this.peticion.url) : this.documento.location;
    return url?.pathname ?? '/';
  }

  establecer(datos: MetadatosPagina): void {
    const titulo = tituloConMarca(datos.titulo);
    const canonica = urlAbsoluta(this.origen(), datos.rutaCanonica ?? this.rutaActual());

    this.titulo.setTitle(titulo);
    this.fijarMeta('name', 'description', datos.descripcion);
    this.fijarMeta('name', 'robots', datos.indexable === false ? 'noindex, nofollow' : undefined);
    this.fijarMeta('property', 'og:title', titulo);
    this.fijarMeta('property', 'og:description', datos.descripcion);
    this.fijarMeta('property', 'og:type', datos.tipoOg ?? 'website');
    this.fijarMeta('property', 'og:url', canonica);
    this.fijarMeta('property', 'og:site_name', NOMBRE_MARCA);
    this.fijarMeta('property', 'og:locale', LOCALE_OG);
    this.fijarMeta(
      'property',
      'og:image',
      datos.imagen ? urlAbsoluta(this.origen(), datos.imagen.url) : undefined,
    );
    this.fijarMeta('property', 'og:image:alt', datos.imagen?.alt);
    this.fijarMeta('name', 'twitter:card', datos.imagen ? 'summary_large_image' : 'summary');

    // Las vistas no indexables (errores, vistas previas) no declaran URL canónica.
    this.fijarCanonica(datos.indexable === false ? null : canonica);
    this.fijarJsonLd(datos.datosEstructurados);
  }

  private fijarMeta(atributo: 'name' | 'property', clave: string, valor: string | undefined): void {
    const selector = `${atributo}="${clave}"`;
    if (valor === undefined || valor === '') {
      this.meta.removeTag(selector);
      return;
    }
    this.meta.updateTag({ [atributo]: clave, content: valor }, selector);
  }

  private fijarCanonica(url: string | null): void {
    const cabeza = this.documento.head;
    let enlace = cabeza.querySelector<HTMLLinkElement>(`link#${ID_CANONICA}`) ?? null; // el DOM del SSR devuelve undefined
    if (url === null) {
      if (enlace !== null) this.renderer.removeChild(cabeza, enlace);
      return;
    }
    if (enlace === null) {
      enlace = this.renderer.createElement('link') as HTMLLinkElement;
      this.renderer.setAttribute(enlace, 'id', ID_CANONICA);
      this.renderer.setAttribute(enlace, 'rel', 'canonical');
      this.renderer.appendChild(cabeza, enlace);
    }
    this.renderer.setAttribute(enlace, 'href', url);
  }

  private fijarJsonLd(datos: JsonLd | readonly JsonLd[] | undefined): void {
    const cabeza = this.documento.head;
    const existente = cabeza.querySelector(`script#${ID_JSON_LD}`) ?? null;
    if (existente !== null) {
      this.renderer.removeChild(cabeza, existente);
    }
    if (datos === undefined) return;

    const script = this.renderer.createElement('script') as HTMLScriptElement;
    this.renderer.setAttribute(script, 'id', ID_JSON_LD);
    this.renderer.setAttribute(script, 'type', 'application/ld+json');
    if (this.nonce !== null) {
      this.renderer.setAttribute(script, 'nonce', this.nonce);
    }
    this.renderer.setProperty(script, 'textContent', serializarJsonLd(datos));
    this.renderer.appendChild(cabeza, script);
  }
}
