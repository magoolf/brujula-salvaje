import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { DerivadoImagen, ImagenResponsiva } from '../imagen-responsiva/imagen-responsiva';

export interface ImagenTarjeta {
  readonly src: string;
  readonly ancho: number;
  readonly alto: number;
  readonly derivados?: readonly DerivadoImagen[];
}

/** sizes de tarjeta en rejilla (PERFORMANCE_SPEC.Sizes_Recomendados.tarjeta_rejilla). */
export const SIZES_TARJETA = '(min-width: 1536px) 25vw, (min-width: 1024px) 33vw, (min-width: 480px) 50vw, 100vw';

/**
 * Tarjeta de contenido base (CardDestino / CardItinerario / CardGuia / CardTipo…, HANDOFF_UI_UX):
 * un único enlace principal en el título extendido a toda la tarjeta con un pseudo-elemento; las
 * acciones (Guardar*) se proyectan en `[tarjeta-accion]` por encima (z raised), nunca anidadas en el
 * enlace. La imagen es decorativa (alt vacío) porque el título ya nombra el contenido.
 * Los metadatos (país, medidores…) se proyectan como contenido.
 */
@Component({
  selector: 'app-tarjeta-contenido',
  imports: [RouterLink, ImagenResponsiva],
  template: `
    <article class="tarjeta" [attr.data-testid]="testId()">
      @if (imagen(); as img) {
        <app-imagen-responsiva
          class="imagen"
          [src]="img.src"
          alt=""
          [ancho]="img.ancho"
          [alto]="img.alto"
          [derivados]="img.derivados ?? []"
          [sizes]="sizes()"
          [prioritaria]="prioritaria()"
          relacion="var(--bs-aspect-card)"
        />
      }
      <div class="cuerpo">
        @if (overline()) {
          <p class="bs-overline tipo">{{ overline() }}</p>
        }
        @switch (nivelTitulo()) {
          @case (2) {
            <h2 class="titulo"><a class="enlace" [routerLink]="ruta()">{{ titulo() }}</a></h2>
          }
          @case (4) {
            <h4 class="titulo"><a class="enlace" [routerLink]="ruta()">{{ titulo() }}</a></h4>
          }
          @default {
            <h3 class="titulo"><a class="enlace" [routerLink]="ruta()">{{ titulo() }}</a></h3>
          }
        }
        <div class="metadatos"><ng-content /></div>
      </div>
      <div class="accion"><ng-content select="[tarjeta-accion]" /></div>
    </article>
  `,
  styles: `
    :host { display: block; container-type: inline-size; }
    .tarjeta {
      position: relative;
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
      border-radius: var(--bs-radius-lg);
      background: var(--bs-color-bg-surface);
      box-shadow: var(--bs-shadow-1);
      transition: box-shadow var(--bs-motion-duration-slow) var(--bs-motion-easing-standard);
    }
    .imagen { border-radius: var(--bs-radius-lg) var(--bs-radius-lg) 0 0; }
    .cuerpo {
      display: grid;
      gap: var(--bs-space-2);
      padding: var(--bs-space-4);
    }
    .tipo { color: var(--bs-color-text-accent); }
    .titulo {
      font-family: var(--bs-typography-h3-font-family);
      font-size: var(--bs-typography-h3-font-size);
      font-weight: var(--bs-typography-h3-font-weight);
      line-height: var(--bs-typography-h3-line-height);
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .enlace {
      color: var(--bs-color-text-default);
      text-decoration: none;
    }
    .enlace::after {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: inherit;
    }
    .enlace:focus-visible {
      outline: none;
    }
    .tarjeta:has(.enlace:focus-visible) {
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring);
      outline-offset: var(--bs-border-width-focus-offset);
    }
    .metadatos {
      display: grid;
      gap: var(--bs-space-1);
      color: var(--bs-color-text-muted);
    }
    .accion {
      position: absolute;
      top: var(--bs-space-2);
      right: var(--bs-space-2);
      z-index: var(--bs-z-raised);
    }
    @media (hover: hover) and (pointer: fine) {
      .tarjeta:hover { box-shadow: var(--bs-shadow-2); }
      .tarjeta:hover .enlace { text-decoration: underline; }
    }
    @media (forced-colors: active) {
      .tarjeta { border: 1px solid CanvasText; }
    }
  `,
})
export class TarjetaContenido {
  readonly titulo = input.required<string>();
  /** Ruta interna del detalle (p. ej. `/destinos/patagonia`). */
  readonly ruta = input.required<string>();
  readonly overline = input<string | null>(null);
  readonly imagen = input<ImagenTarjeta | null>(null);
  readonly sizes = input(SIZES_TARJETA);
  readonly prioritaria = input(false);
  /** Nivel del encabezado del título según la jerarquía de la página (sin saltos). */
  readonly nivelTitulo = input<2 | 3 | 4>(3);
  readonly testId = input('tarjeta-contenido');
}
