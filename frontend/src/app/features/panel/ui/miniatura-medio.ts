import {
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';

import { DerivadoMedio, derivadoPara } from '../domain/medios';

/** Margen con el que una miniatura empieza a cargarse antes de entrar en pantalla. */
const MARGEN_CARGA = '200px';
/** Reintentos de una miniatura que falló (p. ej. un 429 del límite por IP) y su espera base. */
const REINTENTOS = 2;
const ESPERA_REINTENTO_MS = 1500;

/**
 * Miniatura 1:1 de un medio para la rejilla de la biblioteca y del selector. Las miniaturas salen
 * del endpoint autenticado del panel (cada una es una petición a /api, sujeta al límite por IP del
 * borde): se piden solo cuando están a punto de verse (IntersectionObserver con un margen corto,
 * más estricto que `loading="lazy"`) y, si fallan, se reintentan hasta 2 veces con espera
 * creciente. Si aun así no cargan, el hueco se conserva con un texto (ALT-009, CLS 0).
 */
@Component({
  selector: 'app-miniatura-medio',
  template: `
    @if (src(); as url) {
      @if (visible() && !fallo()) {
        @for (intento of [intento()]; track intento) {
          <img [src]="url" alt="" decoding="async" (error)="alFallar()" />
        }
      }
    }
    @if (!src() || fallo()) {
      <span class="sin-vista">Vista previa no disponible</span>
    }
  `,
  styles: `
    :host {
      display: grid;
      place-items: center;
      aspect-ratio: 1;
      overflow: hidden;
      border-radius: var(--bs-radius-sm);
      background: var(--bs-color-bg-sunken);
    }
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .sin-vista {
      padding: var(--bs-space-2);
      font-size: var(--bs-typography-body-sm-font-size);
      line-height: var(--bs-typography-body-sm-line-height);
      color: var(--bs-color-text-muted);
      text-align: center;
    }
  `,
})
export class MiniaturaMedio {
  readonly derivados = input.required<readonly DerivadoMedio[]>();
  /** Ancho mínimo del derivado (px CSS × densidad aproximada). */
  readonly ancho = input(320);

  protected readonly visible = signal(false);
  protected readonly fallo = signal(false);
  protected readonly intento = signal(0);
  protected readonly src = computed(() => derivadoPara(this.derivados(), this.ancho())?.url ?? null);

  private temporizador: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    const elemento = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
    const destroyRef = inject(DestroyRef);
    destroyRef.onDestroy(() => clearTimeout(this.temporizador));
    afterNextRender(() => {
      if (typeof IntersectionObserver === 'undefined') {
        this.visible.set(true);
        return;
      }
      const observador = new IntersectionObserver(
        (entradas) => {
          if (entradas.some((e) => e.isIntersecting)) {
            this.visible.set(true);
            observador.disconnect();
          }
        },
        { rootMargin: MARGEN_CARGA },
      );
      observador.observe(elemento);
      destroyRef.onDestroy(() => observador.disconnect());
    });
  }

  protected alFallar(): void {
    const intento = this.intento();
    if (intento >= REINTENTOS) {
      this.fallo.set(true);
      return;
    }
    // Se vuelve a crear el <img> (la respuesta es no-store: el navegador la pide de nuevo).
    this.temporizador = setTimeout(() => this.intento.set(intento + 1), ESPERA_REINTENTO_MS * (intento + 1));
  }
}
