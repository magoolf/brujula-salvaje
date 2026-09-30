import { isPlatformBrowser } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  PLATFORM_ID,
  afterNextRender,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';

/**
 * Distancia de pre-carga (TKT-018): margen del `IntersectionObserver` propio que sustituye la
 * confianza ciega en `loading="lazy"` nativo. Medido con evidencia real (stack Docker + semilla +
 * Playwright): el umbral nativo de Chromium en una conexión sin limitar es tan generoso que una
 * rejilla de 24 tarjetas dispara sus 24 peticiones de imagen casi en el mismo milisegundo (confirmado
 * por captura de red real), lo que por sí solo agota una fracción relevante del burst=60 del
 * limitador de nginx (infra/proxy/nginx.conf) -- y se suma al de la página anterior si el visitante
 * navega poco después (TKT-008/009). Un margen de 300px (~0.4 alturas de viewport de escritorio)
 * solo adelanta las imágenes realmente próximas a aparecer, escalonando el resto con el scroll real
 * del usuario en vez de una ráfaga única al montar la ruta.
 */
const MARGEN_PRECARGA_PX = 300;

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
 *
 * TKT-018: `loading="lazy"` nativo se conserva como respaldo (progresivo: sin JS o sin soporte de
 * `IntersectionObserver` la imagen carga igual, con la heurística del navegador), pero la petición
 * real de red para una imagen no prioritaria se retiene hasta que un `IntersectionObserver` propio
 * (margen `MARGEN_PRECARGA_PX`) confirma que está realmente próxima al viewport -- ver justificación
 * completa junto a esa constante. El `<img>` permanece siempre en el DOM (Regla de composición de
 * TarjetaContenido y sus pruebas): solo se retiene el binding de `src`/`srcset`, nunca el elemento.
 */
@Component({
  selector: 'app-imagen-responsiva',
  template: `
    <div class="marco" [style.aspect-ratio]="proporcion()" [attr.data-testid]="testId()">
      @if (!fallida()) {
        <img
          [attr.src]="mostrar() ? src() : null"
          [attr.srcset]="mostrar() && srcset() ? srcset() : null"
          [attr.sizes]="mostrar() && srcset() ? sizes() : null"
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

  private readonly elementoHost = inject(ElementRef<HTMLElement>);
  private readonly injector = inject(Injector);
  private readonly destroyRef = inject(DestroyRef);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));

  private readonly _fallida = signal(false);
  protected readonly fallida = this._fallida.asReadonly();
  protected readonly srcset = computed(() => construirSrcset(this.derivados()));
  protected readonly proporcion = computed(
    () => this.relacion() ?? `${this.ancho()} / ${this.alto()}`,
  );

  /**
   * TKT-018: visible de inmediato solo para imágenes prioritarias; el resto espera al
   * IntersectionObserver. Deliberadamente IGUAL en SSR y en el primer render del cliente (ambos en
   * `false` para las no prioritarias): si SSR mostrara la imagen real y el cliente arrancara
   * ocultándola, la hidratación de Angular vería un DOM distinto al del servidor en el primer pase
   * (halla incompatibilidad / posible re-creación del nodo) además de un parpadeo visible. Como
   * `alt=""` en todo uso actual (decorativa, RULE del propio componente), no perder estas imágenes
   * en SSR/sin JS no tiene coste de SEO ni de accesibilidad -- degradan a "sin imagen todavía", no a
   * contenido roto.
   */
  private readonly _cercaDelViewport = signal(false);
  protected readonly mostrar = computed(() => this.prioritaria() || this._cercaDelViewport());

  constructor() {
    afterNextRender(
      () => {
        if (!this.esNavegador || this.prioritaria()) return;
        if (typeof IntersectionObserver === 'undefined') {
          // Sin soporte (o entorno de pruebas sin polyfill): degrada al comportamiento previo,
          // carga inmediata confiando solo en el `loading="lazy"` nativo del <img>.
          this._cercaDelViewport.set(true);
          return;
        }
        const observador = new IntersectionObserver(
          (entradas) => {
            if (entradas.some((e) => e.isIntersecting)) {
              this._cercaDelViewport.set(true);
              observador.disconnect();
            }
          },
          { rootMargin: `${MARGEN_PRECARGA_PX}px 0px` },
        );
        observador.observe(this.elementoHost.nativeElement);
        this.destroyRef.onDestroy(() => observador.disconnect());
      },
      { injector: this.injector },
    );
  }

  protected alFallar(): void {
    this._fallida.set(true);
  }
}
