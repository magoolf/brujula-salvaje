import { Dialog } from '@angular/cdk/dialog';
import { Overlay } from '@angular/cdk/overlay';
import {
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { CampoBusqueda } from '../../../shared/ui/campo-busqueda/campo-busqueda';
import { Enlace } from '../../../shared/ui/enlace/enlace';
import { Icono } from '../../../shared/ui/icono/icono';
import { NOMBRE_MARCA } from '../../seo/marca';
import { MenuMovil } from '../menu-movil/menu-movil';
import { NAVEGACION_PRINCIPAL } from '../navegacion';

/**
 * SiteHeader GI-01 (HANDOFF_UI_UX): fija arriba (64 px; 72 px ≥ xl).
 * - ≥ xl: logo · navegación principal · búsqueda en línea.
 * - < xl: logo · botón Buscar (fila desplegable, Esc la cierra) · botón Menú (cajón CDK Dialog).
 * Enlaces SHOULD/COULD (Colecciones*, Cuándo ir*, Guardados*) omitidos hasta que existan (RULE-030).
 */
@Component({
  selector: 'app-cabecera-sitio',
  host: { '(keydown.escape)': 'cerrarBusqueda()' },
  imports: [RouterLink, RouterLinkActive, CampoBusqueda, Enlace, Icono],
  template: `
    <header class="cabecera" data-testid="cabecera-sitio">
      <div class="fila bs-contenedor">
        <a routerLink="/" class="logo" data-testid="cabecera-logo">
          <svg
            class="logo-icono"
            viewBox="0 0 24 24"
            width="28"
            height="28"
            aria-hidden="true"
            focusable="false"
          >
            <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" />
            <path
              d="m16.24 7.76-1.8 5.41a2 2 0 0 1-1.27 1.27l-5.41 1.8 1.8-5.41a2 2 0 0 1 1.27-1.27z"
              fill="currentColor"
            />
          </svg>
          <span>{{ marca }}</span>
        </a>

        <nav aria-label="Principal" class="navegacion">
          <ul>
            @for (enlace of navegacion; track enlace.id) {
              <li>
                <a
                  appEnlace
                  variante="nav"
                  [routerLink]="enlace.ruta"
                  routerLinkActive
                  ariaCurrentWhenActive="page"
                  [attr.data-testid]="'nav-' + enlace.id"
                  >{{ enlace.etiqueta }}</a
                >
              </li>
            }
          </ul>
        </nav>

        <div class="busqueda-en-linea">
          <app-campo-busqueda idCampo="busqueda-cabecera" testId="cabecera-busqueda" />
        </div>

        <div class="acciones-compactas">
          <button
            #botonBuscar
            type="button"
            class="boton-icono"
            [attr.aria-expanded]="busquedaAbierta()"
            aria-controls="busqueda-desplegable"
            data-testid="cabecera-boton-buscar"
            (click)="alternarBusqueda()"
          >
            <app-icono nombre="search" [tamano]="24" />
            <span class="bs-solo-lectores">Buscar</span>
          </button>
          <button
            #botonMenu
            type="button"
            class="boton-icono"
            aria-haspopup="dialog"
            data-testid="cabecera-boton-menu"
            (click)="abrirMenu()"
          >
            <app-icono nombre="menu" [tamano]="24" />
            <span class="bs-solo-lectores">Menú</span>
          </button>
        </div>
      </div>

      @if (busquedaAbierta()) {
        <div id="busqueda-desplegable" class="busqueda-desplegable bs-contenedor">
          <app-campo-busqueda
            #busquedaDesplegable
            idCampo="busqueda-desplegable-campo"
            testId="cabecera-busqueda-desplegable"
          />
        </div>
      }
    </header>
  `,
  styles: `
    :host {
      display: block;
      position: sticky;
      top: 0;
      z-index: var(--bs-z-sticky);
    }
    .cabecera {
      background: var(--bs-color-bg-canvas);
      border-bottom: 1px solid var(--bs-color-border-subtle);
    }
    .fila {
      display: flex;
      align-items: center;
      gap: var(--bs-space-6);
      min-height: var(--bs-size-header);
    }
    .logo {
      display: inline-flex;
      align-items: center;
      gap: var(--bs-space-2);
      min-height: var(--bs-size-target);
      margin-inline-end: auto;
      color: var(--bs-color-text-brand);
      font-family: var(--bs-font-family-display);
      font-size: 1.25rem;
      font-weight: var(--bs-font-weight-extrabold);
      text-decoration: none;
      white-space: nowrap;
    }
    .navegacion,
    .busqueda-en-linea {
      display: none;
    }
    .navegacion ul {
      display: flex;
      gap: var(--bs-space-6);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .busqueda-en-linea {
      width: 18rem;
    }
    .acciones-compactas {
      display: flex;
      gap: var(--bs-space-1);
    }
    .boton-icono {
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
    .boton-icono:hover {
      background: var(--bs-color-bg-brand-faint);
    }
    .busqueda-desplegable {
      padding-block: var(--bs-space-3);
      border-top: 1px solid var(--bs-color-border-subtle);
    }
    @media (min-width: 80rem) {
      .fila {
        min-height: var(--bs-size-header-xl);
      }
      .navegacion,
      .busqueda-en-linea {
        display: block;
      }
      .acciones-compactas,
      .busqueda-desplegable {
        display: none;
      }
    }
  `,
})
export class CabeceraSitio {
  protected readonly marca = NOMBRE_MARCA;
  protected readonly navegacion = NAVEGACION_PRINCIPAL;

  private readonly dialogo = inject(Dialog);
  private readonly overlay = inject(Overlay);
  private readonly injector = inject(Injector);
  private readonly botonMenu = viewChild.required<ElementRef<HTMLButtonElement>>('botonMenu');
  private readonly botonBuscar = viewChild.required<ElementRef<HTMLButtonElement>>('botonBuscar');
  private readonly busquedaDesplegable = viewChild<CampoBusqueda>('busquedaDesplegable');
  private readonly _busquedaAbierta = signal(false);
  protected readonly busquedaAbierta = this._busquedaAbierta.asReadonly();

  protected abrirMenu(): void {
    this.dialogo.open(MenuMovil, {
      ariaLabelledBy: 'menu-movil-titulo',
      backdropClass: 'bs-fondo-dialogo',
      positionStrategy: this.overlay.position().global().left('0').top('0'),
      autoFocus: 'first-tabbable',
      restoreFocus: this.botonMenu().nativeElement,
    });
  }

  protected alternarBusqueda(): void {
    const abrir = !this._busquedaAbierta();
    this._busquedaAbierta.set(abrir);
    if (abrir) {
      afterNextRender(() => this.busquedaDesplegable()?.enfocar(), { injector: this.injector });
    }
  }

  /** Esc cierra la fila de búsqueda y devuelve el foco al botón Buscar. */
  protected cerrarBusqueda(): void {
    if (!this._busquedaAbierta()) return;
    this._busquedaAbierta.set(false);
    this.botonBuscar().nativeElement.focus();
  }
}
