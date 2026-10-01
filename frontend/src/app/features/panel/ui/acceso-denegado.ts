import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';

/**
 * SCR-048 Acceso denegado (ST-FORBIDDEN, FEAT-029, AC-105). Se muestra como ruta (guard de rol, en
 * la misma URL) y como estado de cualquier pantalla del panel cuyo API responda 403 (tratamiento
 * del 403 en la feature, Skill_Frontend §12). Reutilizable por TKT-022/023/024.
 */
@Component({
  selector: 'app-acceso-denegado',
  imports: [RouterLink, Boton],
  template: `
    <section class="denegado" data-testid="acceso-denegado" aria-labelledby="acceso-denegado-titulo">
      <svg class="candado" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </svg>
      <h1 id="acceso-denegado-titulo" tabindex="-1">No tienes permiso para ver esta sección</h1>
      <p>Si crees que es un error, pide a un administrador que revise tu rol.</p>
      <a appBoton routerLink="/panel" data-testid="acceso-denegado-tablero">Ir al tablero</a>
    </section>
  `,
  styles: `
    .denegado {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-4);
      max-width: 35rem;
      margin-inline: auto;
      padding-block: var(--bs-space-10);
      text-align: center;
    }
    h1 {
      outline: none;
    }
    .candado {
      width: var(--bs-size-icon-xl);
      height: var(--bs-size-icon-xl);
      fill: none;
      stroke: currentColor;
      stroke-width: 1.75;
      stroke-linecap: round;
      stroke-linejoin: round;
      color: var(--bs-color-text-muted);
    }
  `,
})
export class AccesoDenegado {
  constructor() {
    inject(Seo).establecer({ titulo: 'Acceso denegado', indexable: false });
  }
}
