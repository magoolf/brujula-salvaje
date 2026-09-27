import { Component, input } from '@angular/core';

/**
 * Ilustración decorativa de brújula en SVG en línea (≤ 4 KB, sin dependencias ni JS;
 * TPL-PUB-ERROR y EmptyState). Siempre aria-hidden: el mensaje está en el texto.
 */
@Component({
  selector: 'app-ilustracion-brujula',
  template: `
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 120 120"
      [attr.width]="tamano()"
      [attr.height]="tamano()"
      aria-hidden="true"
      focusable="false"
      data-testid="ilustracion-brujula"
    >
      <circle cx="60" cy="60" r="54" class="aro" />
      <circle cx="60" cy="60" r="44" class="esfera" />
      <path d="M60 22 68 60 60 98 52 60Z" class="aguja-base" />
      <path d="M60 22 68 60H52Z" class="aguja-norte" />
      <circle cx="60" cy="60" r="5" class="eje" />
      <path d="M60 8v8M60 104v8M8 60h8M104 60h8" class="marcas" />
    </svg>
  `,
  styles: `
    :host {
      display: inline-block;
    }
    .aro {
      fill: var(--bs-color-bg-brand-subtle);
      stroke: var(--bs-color-border-brand);
      stroke-width: 3;
    }
    .esfera {
      fill: var(--bs-color-bg-surface);
      stroke: var(--bs-color-border-subtle);
      stroke-width: 2;
    }
    .aguja-base {
      fill: var(--bs-color-text-muted);
    }
    .aguja-norte {
      fill: var(--bs-color-action-accent-bg);
    }
    .eje {
      fill: var(--bs-color-text-default);
    }
    .marcas {
      stroke: var(--bs-color-border-brand);
      stroke-width: 3;
      stroke-linecap: round;
    }
    @media (forced-colors: active) {
      .aro,
      .esfera,
      .aguja-base,
      .aguja-norte,
      .eje {
        fill: CanvasText;
        stroke: CanvasText;
      }
      .esfera {
        fill: Canvas;
      }
    }
  `,
})
export class IlustracionBrujula {
  readonly tamano = input(120);
}
