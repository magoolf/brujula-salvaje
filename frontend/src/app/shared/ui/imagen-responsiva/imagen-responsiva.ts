import { Component, computed, input, signal } from '@angular/core';

/** Derivado responsivo de una imagen (DEC-AUTO-044): URL de mismo origen y ancho intrínseco. */
export interface DerivadoImagen {
  readonly url: string;
  readonly ancho: number;
}

/** `srcset` ordenado por ancho, sin duplicados ni anchos inválidos. */
export function construirSrcset(derivados: readonly DerivadoImagen[]): string {
  const vistos = new Set<number>();
  return [...derivados]
    .filter((d) => Number.isInteger(d.ancho) && d.ancho > 0 && d.url.trim() !== '')
    .sort((a, b) => a.ancho - b.ancho)
    .filter((d) => (vistos.has(d.ancho) ? false : (vistos.add(d.ancho), true)))
    .map((d) => `${encodeURI(d.url)} ${d.ancho}w`)
    .join(', ');
}

/**
 * Imagen responsiva (DEC-AUTO-072, PERFORMANCE_SPEC): srcset + sizes, width/height o aspect-ratio
 * reservados (CLS 0), `loading=lazy` salvo la imagen LCP (`prioritaria`: eager + fetchpriority high).
 * Si la imagen no carga (ALT-009) el contenedor conserva su tamaño y muestra el texto alternativo.
 * `alt=""` marca la imagen como decorativa (p. ej. en tarjetas cuyo título ya nombra el contenido).
 */
@Component({
  selector: 'app-imagen-responsiva',
  template: `
    <div class="marco" [style.aspect-ratio]="proporcion()" [attr.data-testid]="testId()">
      @if (!fallida()) {
        <img
          [src]="src()"
          [attr.srcset]="srcset() || null"
          [attr.sizes]="srcset() ? sizes() : null"
          [alt]="alt()"
          [attr.width]="ancho()"
          [attr.height]="alto()"
          [attr.loading]="prioritaria() ? 'eager' : 'lazy'"
          [attr.fetchpriority]="prioritaria() ? 'high' : null"
          decoding="async"
          (error)="alFallar()"
        />
      } @else if (alt()) {
        <p class="alternativo" data-testid="imagen-fallida">{{ alt() }}</p>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    .marco {
      position: relative;
      overflow: hidden;
      background: var(--bs-color-bg-sunken);
      border-radius: inherit;
    }
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center;
    }
    .alternativo {
      position: absolute;
      inset: auto 0 0 0;
      padding: var(--bs-space-2) var(--bs-space-3);
      font-size: var(--bs-typography-caption-font-size);
      line-height: var(--bs-typography-caption-line-height);
      color: var(--bs-color-text-muted);
    }
  `,
})
export class ImagenResponsiva {
  readonly src = input.required<string>();
  readonly alt = input.required<string>();
  readonly ancho = input.required<number>();
  readonly alto = input.required<number>();
  readonly derivados = input<readonly DerivadoImagen[]>([]);
  /** Atributo sizes por plantilla (PERFORMANCE_SPEC.Sizes_Recomendados). */
  readonly sizes = input('100vw');
  readonly prioritaria = input(false);
  /** Relación de aspecto CSS (p. ej. `var(--bs-aspect-card)` o `4 / 3`); por defecto ancho/alto. */
  readonly relacion = input<string | null>(null);
  readonly testId = input('imagen-responsiva');

  private readonly _fallida = signal(false);
  protected readonly fallida = this._fallida.asReadonly();
  protected readonly srcset = computed(() => construirSrcset(this.derivados()));
  protected readonly proporcion = computed(
    () => this.relacion() ?? `${this.ancho()} / ${this.alto()}`,
  );

  protected alFallar(): void {
    this._fallida.set(true);
  }
}
