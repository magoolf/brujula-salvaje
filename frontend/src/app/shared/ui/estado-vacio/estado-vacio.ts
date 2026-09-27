import { Component, input } from '@angular/core';

import { IlustracionBrujula } from '../ilustracion-brujula/ilustracion-brujula';

/**
 * EmptyState (ST-EMPTY, HANDOFF_UI_UX): título (h2), explicación y ≥2 rutas de salida, que quien lo
 * usa proyecta como enlaces reales (slot `[estado-salidas]`). Nunca una pantalla en blanco.
 */
@Component({
  selector: 'app-estado-vacio',
  imports: [IlustracionBrujula],
  template: `
    <section class="vacio" [attr.data-testid]="testId()" [attr.aria-labelledby]="idTitulo()">
      @if (ilustracion()) {
        <app-ilustracion-brujula [tamano]="96" />
      }
      <h2 [id]="idTitulo()">{{ titulo() }}</h2>
      <div class="texto"><ng-content /></div>
      <div class="salidas"><ng-content select="[estado-salidas]" /></div>
    </section>
  `,
  styles: `
    .vacio {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-4);
      padding-block: var(--bs-space-8);
      text-align: center;
    }
    .texto {
      max-width: var(--bs-size-measure-prose);
      color: var(--bs-color-text-muted);
    }
    .salidas {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: var(--bs-space-3) var(--bs-space-6);
    }
  `,
})
export class EstadoVacio {
  readonly titulo = input.required<string>();
  readonly ilustracion = input(true);
  readonly testId = input('estado-vacio');
  readonly idTitulo = input('estado-vacio-titulo');
}
