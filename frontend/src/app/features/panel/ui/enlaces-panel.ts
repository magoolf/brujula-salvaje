import { Component, input, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { SeccionPanel, activoSoloExacto } from '../domain/secciones';

/**
 * Lista de enlaces de la navegación del panel, compartida por la barra lateral (≥ lg) y el cajón
 * modal (< lg). Componente propio en lugar de NgTemplateOutlet para no traer CommonModule al chunk
 * compartido con la carga inicial pública (QA TKT-010 ciclo 1, FALLO-02).
 */
@Component({
  selector: 'app-enlaces-panel',
  imports: [RouterLink, RouterLinkActive],
  template: `
    <ul>
      @for (seccion of secciones(); track seccion.id) {
        <li>
          <a
            [routerLink]="seccion.ruta"
            routerLinkActive="activo"
            ariaCurrentWhenActive="page"
            [routerLinkActiveOptions]="{ exact: soloExacto(seccion) }"
            [attr.data-testid]="prefijo() + seccion.id"
            (click)="navegar.emit()"
            >{{ seccion.etiqueta }}</a
          >
        </li>
      }
    </ul>
  `,
  styles: `
    ul {
      display: grid;
      gap: var(--bs-space-1);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    a {
      display: flex;
      align-items: center;
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-3);
      border-inline-start: 3px solid transparent;
      border-radius: var(--bs-radius-sm);
      color: var(--bs-color-text-default);
      text-decoration: none;
    }
    a:hover {
      background: var(--bs-color-bg-sunken);
    }
    a.activo {
      border-inline-start-color: var(--bs-color-action-primary-bg);
      background: var(--bs-color-action-selected-bg);
      font-weight: var(--bs-font-weight-semibold);
    }
    @media (forced-colors: active) {
      a.activo {
        border-inline-start-color: Highlight;
      }
    }
  `,
})
export class EnlacesPanel {
  readonly secciones = input.required<readonly SeccionPanel[]>();
  /** Prefijo del data-testid de cada enlace. */
  readonly prefijo = input.required<string>();
  readonly navegar = output<void>();

  protected soloExacto(seccion: SeccionPanel): boolean {
    return activoSoloExacto(seccion);
  }
}
