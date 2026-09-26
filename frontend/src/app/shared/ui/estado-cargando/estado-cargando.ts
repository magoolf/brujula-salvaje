import { Component, DestroyRef, PLATFORM_ID, computed, inject, input, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type FormaEsqueleto = 'tarjeta' | 'linea' | 'fila' | 'imagen';

/** Retardo antes de mostrar el esqueleto para evitar parpadeos en cargas rápidas (300 ms). */
export const RETARDO_ESQUELETO_MS = 300;

/**
 * Skeleton / ST-LOADING (HANDOFF_UI_UX): contenedor con aria-busy=true y esqueletos aria-hidden con
 * la altura final reservada (CLS 0). El pulso aparece solo tras 300 ms y es estático con
 * reduced-motion. La etiqueta accesible anuncia la carga una sola vez.
 */
@Component({
  selector: 'app-estado-cargando',
  template: `
    <div class="cargando" aria-busy="true" [attr.data-testid]="testId()">
      <span class="bs-solo-lectores" role="status">{{ etiqueta() }}</span>
      @for (i of elementos(); track i) {
        <div
          class="esqueleto"
          aria-hidden="true"
          [attr.data-forma]="forma()"
          [class.esqueleto--visible]="visible()"
        ></div>
      }
    </div>
  `,
  styles: `
    .cargando {
      display: grid;
      gap: var(--bs-space-4);
    }
    .esqueleto {
      background: var(--bs-color-bg-sunken);
      border-radius: var(--bs-radius-md);
      opacity: 0;
    }
    .esqueleto--visible {
      opacity: 1;
      animation: pulso 1.6s var(--bs-motion-easing-standard) infinite;
    }
    [data-forma='linea'] {
      height: 1rem;
    }
    [data-forma='fila'] {
      height: 3rem;
    }
    [data-forma='tarjeta'] {
      aspect-ratio: var(--bs-aspect-card);
      border-radius: var(--bs-radius-lg);
    }
    [data-forma='imagen'] {
      aspect-ratio: var(--bs-aspect-gallery);
      border-radius: var(--bs-radius-lg);
    }
    @keyframes pulso {
      50% {
        opacity: 0.55;
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .esqueleto--visible {
        animation: none;
      }
    }
  `,
})
export class EstadoCargando {
  readonly forma = input<FormaEsqueleto>('linea');
  readonly cantidad = input(3);
  readonly etiqueta = input('Cargando…');
  readonly testId = input('estado-cargando');

  private readonly _visible = signal(false);
  protected readonly visible = this._visible.asReadonly();

  constructor() {
    if (isPlatformBrowser(inject(PLATFORM_ID))) {
      const temporizador = setTimeout(() => this._visible.set(true), RETARDO_ESQUELETO_MS);
      inject(DestroyRef).onDestroy(() => clearTimeout(temporizador));
    }
  }

  protected readonly elementos = computed(() =>
    Array.from({ length: Math.max(1, Math.min(24, this.cantidad())) }, (_, i) => i),
  );
}
