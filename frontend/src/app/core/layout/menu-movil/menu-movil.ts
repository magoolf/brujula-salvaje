import { DialogRef } from '@angular/cdk/dialog';
import { Component, effect, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationStart, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs';

import { CampoBusqueda } from '../../../shared/ui/campo-busqueda/campo-busqueda';
import { Icono } from '../../../shared/ui/icono/icono';
import { NAVEGACION_PRINCIPAL } from '../navegacion';

/**
 * Cajón lateral modal de navegación (< xl) de GI-01, sobre CDK Dialog: trampa de foco, Esc cierra,
 * el foco vuelve al botón Menú al cerrar (HANDOFF_UI_UX Dialog, variante drawer).
 */
@Component({
  selector: 'app-menu-movil',
  imports: [RouterLink, RouterLinkActive, CampoBusqueda, Icono],
  template: `
    <div class="cajon" data-testid="menu-movil">
      <div class="encabezado">
        <h2 id="menu-movil-titulo" class="titulo">Menú</h2>
        <button type="button" class="cerrar" aria-label="Cerrar menú" data-testid="menu-movil-cerrar" (click)="cerrar()">
          <app-icono nombre="x" [tamano]="24" />
        </button>
      </div>
      <app-campo-busqueda idCampo="busqueda-menu" testId="menu-movil-busqueda" [soloIcono]="false" />
      <nav aria-label="Principal">
        <ul>
          @for (enlace of navegacion; track enlace.id) {
            <li>
              <a
                [routerLink]="enlace.ruta"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                [attr.data-testid]="'menu-movil-' + enlace.id"
                (click)="cerrar()"
              >{{ enlace.etiqueta }}</a>
            </li>
          }
        </ul>
      </nav>
    </div>
  `,
  styles: `
    .cajon {
      display: grid;
      align-content: start;
      gap: var(--bs-space-6);
      width: min(22rem, 100vw);
      height: 100dvh;
      box-sizing: border-box;
      padding: var(--bs-space-4);
      overflow-y: auto;
      background: var(--bs-color-bg-canvas);
      box-shadow: var(--bs-shadow-4);
    }
    .encabezado {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .cerrar {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: var(--bs-size-target);
      height: var(--bs-size-target);
      border: 0;
      border-radius: var(--bs-radius-md);
      background: transparent;
      color: var(--bs-color-text-default);
      cursor: pointer;
    }
    ul {
      display: grid;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    a {
      display: flex;
      align-items: center;
      min-height: var(--bs-size-control-lg);
      color: var(--bs-color-text-default);
      font-size: var(--bs-typography-body-lg-font-size);
      font-weight: var(--bs-font-weight-semibold);
      text-decoration: none;
      border-bottom: 1px solid var(--bs-color-border-subtle);
    }
    a.activo {
      color: var(--bs-color-text-brand);
      text-decoration: underline;
      text-decoration-thickness: 2px;
    }
  `,
})
export class MenuMovil {
  private readonly dialogo = inject(DialogRef, { optional: true });
  protected readonly navegacion = NAVEGACION_PRINCIPAL;
  private readonly navegacionIniciada = toSignal(
    inject(Router).events.pipe(filter((e): e is NavigationStart => e instanceof NavigationStart)),
  );

  constructor() {
    // Cualquier navegación (enlace o búsqueda enviada) cierra el cajón.
    effect(() => {
      if (this.navegacionIniciada() !== undefined) this.cerrar();
    });
  }

  protected cerrar(): void {
    this.dialogo?.close();
  }
}
