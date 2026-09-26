import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icono } from '../icono/icono';

export interface Miga {
  readonly etiqueta: string;
  /** Ruta interna; se omite en el último elemento (página actual). */
  readonly ruta?: string;
}

/**
 * Breadcrumbs GI-03 (HANDOFF_UI_UX): nav «Migas de pan» con ol; el último elemento lleva
 * aria-current=page y no es enlace. < md muestra solo el nivel padre («‹ Destinos»).
 * Los datos estructurados BreadcrumbList los emite la página con core/seo (FEAT-027).
 */
@Component({
  selector: 'app-migas-de-pan',
  imports: [RouterLink, Icono],
  template: `
    <nav aria-label="Migas de pan" class="migas" data-testid="migas-de-pan">
      <ol class="completa">
        @for (miga of migas(); track $index; let ultimo = $last) {
          <li>
            @if (ultimo || !miga.ruta) {
              <span aria-current="page">{{ miga.etiqueta }}</span>
            } @else {
              <a [routerLink]="miga.ruta">{{ miga.etiqueta }}</a>
              <app-icono nombre="chevron-right" [tamano]="16" />
            }
          </li>
        }
      </ol>
      @if (padre(); as p) {
        <a class="compacta" [routerLink]="p.ruta" data-testid="migas-de-pan-padre">
          <app-icono nombre="chevron-left" [tamano]="16" />
          <span>{{ p.etiqueta }}</span>
        </a>
      }
    </nav>
  `,
  styles: `
    .migas {
      font-size: var(--bs-typography-body-sm-font-size);
      line-height: var(--bs-typography-body-sm-line-height);
      color: var(--bs-color-text-muted);
    }
    ol {
      display: none;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-1);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    li {
      display: inline-flex;
      align-items: center;
      gap: var(--bs-space-1);
    }
    a {
      display: inline-flex;
      align-items: center;
      min-height: var(--bs-size-target-min);
      color: var(--bs-color-text-link);
    }
    [aria-current='page'] {
      color: var(--bs-color-text-default);
      font-weight: var(--bs-font-weight-semibold);
    }
    .compacta {
      gap: var(--bs-space-1);
      min-height: var(--bs-size-target);
    }
    @media (min-width: 48rem) {
      ol { display: flex; }
      .compacta { display: none; }
    }
  `,
})
export class MigasDePan {
  readonly migas = input.required<readonly Miga[]>();

  /** Nivel padre (penúltimo con ruta) para la variante compacta. */
  protected readonly padre = computed(() => {
    const lista = this.migas();
    for (let i = lista.length - 2; i >= 0; i--) {
      const ruta = lista[i].ruta;
      if (ruta) return { etiqueta: lista[i].etiqueta, ruta };
    }
    return null;
  });
}
