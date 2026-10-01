import { DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter, map } from 'rxjs';

import { RUTA_ACCESO_PANEL, esDestinoSeguro } from '../../../core/auth/destino-seguro';
import { ID_CONTENIDO_PRINCIPAL } from '../../../core/layout/navegacion';
import { ZonaOutlet } from '../../../core/layout/shell-publico/zona-outlet';
import { Boton } from '../../../shared/ui/boton/boton';
import { ETIQUETA_ROL, seccionDeRuta } from '../domain/secciones';
import { ExpiracionSesionStore } from '../state/expiracion-sesion.store';
import { SesionPanelStore } from '../state/sesion-panel.store';
import { AvisoExpiracion } from './aviso-expiracion';
import { EnlacesPanel } from './enlaces-panel';

/** Destino de «Saltar a la navegación». */
export const ID_NAVEGACION_PANEL = 'panel-navegacion';
export const ID_CAJON_PANEL = 'panel-cajon';
/** Punto de corte lg (64 rem): desde aquí la navegación es una barra lateral fija. */
const MEDIA_LG = '(min-width: 64rem)';

/**
 * TPL-PANEL-SHELL (PanelShell, DEC-AUTO-070): saltos «Saltar al contenido» + «Saltar a la
 * navegación», barra superior (marca, sección actual, nombre con su rol y «Cerrar sesión»),
 * navegación lateral según el rol (cajón < lg) y área principal. Las entradas de la navegación salen
 * del catálogo de dominio (DEC-ESTRUCTURA-03): ningún enlace a secciones no implementadas.
 */
@Component({
  selector: 'app-shell-panel',
  imports: [ZonaOutlet, RouterLink, Boton, AvisoExpiracion, EnlacesPanel],
  providers: [ExpiracionSesionStore],
  template: `
    <div class="saltos">
      <a class="salto" [href]="'#' + idContenido" data-testid="panel-saltar-contenido" (click)="saltarAlContenido($event)"
        >Saltar al contenido</a
      >
      <a class="salto" [href]="'#' + idNavegacion" data-testid="panel-saltar-navegacion" (click)="saltarANavegacion($event)"
        >Saltar a la navegación</a
      >
    </div>
    <header class="barra" data-testid="panel-barra-superior">
      <button
        #botonMenu
        type="button"
        class="boton-menu"
        aria-haspopup="dialog"
        [attr.aria-expanded]="menuAbierto()"
        [attr.aria-controls]="idCajon"
        data-testid="panel-menu"
        (click)="abrirMenu()"
      >
        Menú
      </button>
      <a routerLink="/panel" class="marca">
        <span class="nombre">Brújula Salvaje</span>
        <span class="etiqueta">Panel editorial</span>
      </a>
      @if (seccionActual(); as seccion) {
        <p class="seccion-actual" data-testid="panel-seccion-actual">{{ seccion.etiqueta }}</p>
      }
      <div class="usuario">
        <p class="persona">
          <span data-testid="panel-usuario-nombre">{{ nombreVisible() }}</span>
          <span class="rol" data-testid="panel-usuario-rol">{{ etiquetaRol() }}</span>
        </p>
        <button
          type="button"
          appBoton
          variante="secondary"
          tamano="sm"
          [cargando]="cerrando()"
          data-testid="panel-cerrar-sesion"
          (click)="cerrarSesion()"
        >
          {{ cerrando() ? 'Cerrando…' : 'Cerrar sesión' }}
        </button>
      </div>
    </header>
    @if (errorCierre(); as mensaje) {
      <p class="error-cierre" role="alert">{{ mensaje }}</p>
    }
    <div class="cuerpo">
      <nav
        [id]="idNavegacion"
        class="navegacion"
        aria-label="Navegación del panel"
        tabindex="-1"
        data-testid="panel-navegacion"
      >
        <app-enlaces-panel [secciones]="secciones()" prefijo="panel-nav-" />
      </nav>
      <main [id]="idContenido" class="principal" tabindex="-1" data-testid="panel-contenido">
        <router-outlet appZona="panel" />
      </main>
    </div>
    <!-- Cajón modal < lg (HANDOFF TPL-PANEL-SHELL): <dialog> con showModal(): fondo, resto inerte,
         Escape cierra y el foco vuelve al botón «Menú». -->
    <dialog
      #cajon
      [id]="idCajon"
      class="cajon"
      aria-modal="true"
      aria-label="Menú del panel"
      data-testid="panel-cajon"
      (cancel)="alCancelarCajon($event)"
    >
      <div class="cajon-contenido">
        <button type="button" class="cerrar-cajon" data-testid="panel-cajon-cerrar" (click)="cerrarMenu()">
          Cerrar menú
        </button>
        <nav aria-label="Navegación del panel" data-testid="panel-cajon-navegacion">
          <app-enlaces-panel [secciones]="secciones()" prefijo="panel-cajon-nav-" (navegar)="cerrarMenu()" />
        </nav>
      </div>
    </dialog>
    <app-aviso-expiracion (cerrarSesion)="cerrarSesion()" (volverAEntrar)="volverAEntrar()" />
  `,
  styles: `
    :host {
      display: block;
      min-height: 100dvh;
      background: var(--bs-color-bg-canvas-panel);
    }
    .salto {
      position: absolute;
      top: var(--bs-space-2);
      left: var(--bs-space-2);
      z-index: var(--bs-z-skip-link, 700);
      padding: var(--bs-space-3) var(--bs-space-4);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-inverse);
      color: var(--bs-color-text-inverse);
      font-weight: var(--bs-font-weight-semibold);
      transform: translateY(-200%);
    }
    .salto:focus,
    .salto:focus-visible {
      transform: none;
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring-inverse);
      outline-offset: var(--bs-border-width-focus-offset);
    }
    .barra {
      position: sticky;
      top: 0;
      z-index: 100;
      box-sizing: border-box;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-2) var(--bs-space-4);
      min-height: var(--bs-size-panel-topbar);
      padding: var(--bs-space-2) var(--bs-grid-margin-xs);
      border-bottom: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      background: var(--bs-color-bg-surface);
    }
    .boton-menu {
      min-width: var(--bs-size-target);
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-3);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      font: inherit;
      cursor: pointer;
    }
    .marca {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: var(--bs-space-2);
      color: inherit;
      text-decoration: none;
    }
    .nombre {
      font-family: var(--bs-font-family-display);
      font-weight: var(--bs-font-weight-extrabold);
      color: var(--bs-color-text-brand);
    }
    .etiqueta,
    .rol {
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-muted);
    }
    .seccion-actual {
      font-weight: var(--bs-font-weight-semibold);
    }
    .usuario {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-3);
      margin-inline-start: auto;
    }
    .persona {
      display: grid;
    }
    .error-cierre {
      margin: 0;
      padding: var(--bs-space-2) var(--bs-grid-margin-xs);
      background: var(--bs-color-status-error-bg);
      color: var(--bs-color-status-error-fg);
    }
    .cuerpo {
      display: block;
    }
    .navegacion {
      display: none;
      box-sizing: border-box;
      padding: var(--bs-space-4);
      border-bottom: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      background: var(--bs-color-bg-surface);
      outline: none;
    }
    .cajon {
      box-sizing: border-box;
      width: min(85vw, var(--bs-size-panel-sidebar));
      max-width: none;
      height: 100dvh;
      max-height: none;
      margin: 0;
      padding: 0;
      border: 0;
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      box-shadow: var(--bs-shadow-4);
    }
    .cajon::backdrop {
      background: var(--bs-color-overlay-backdrop);
    }
    .cajon-contenido {
      display: grid;
      gap: var(--bs-space-4);
      padding: var(--bs-space-4);
    }
    .cerrar-cajon {
      justify-self: end;
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-3);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      font: inherit;
      cursor: pointer;
    }
    .principal {
      box-sizing: border-box;
      width: 100%;
      max-width: 80rem;
      padding: var(--bs-space-6) var(--bs-grid-margin-xs);
      outline: none;
    }
    @media (min-width: 48rem) {
      .barra,
      .principal {
        padding-inline: var(--bs-grid-margin-md);
      }
    }
    @media (min-width: 64rem) {
      .boton-menu {
        display: none;
      }
      .cuerpo {
        display: grid;
        grid-template-columns: var(--bs-size-panel-sidebar) minmax(0, 1fr);
        align-items: start;
      }
      .cajon {
        display: none;
      }
      .navegacion {
        display: block;
        position: sticky;
        top: var(--bs-size-panel-topbar);
        min-height: calc(100dvh - var(--bs-size-panel-topbar));
        border-bottom: 0;
        border-inline-end: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      }
    }
    @media (forced-colors: active) {
      .cajon {
        border-inline-end: 1px solid CanvasText;
      }
    }
  `,
})
export class ShellPanel {
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);
  private readonly documento = inject(DOCUMENT);

  protected readonly idContenido = ID_CONTENIDO_PRINCIPAL;
  protected readonly idNavegacion = ID_NAVEGACION_PANEL;
  protected readonly secciones = this.sesion.secciones;
  protected readonly idCajon = ID_CAJON_PANEL;
  protected readonly menuAbierto = signal(false);
  private readonly cajon = viewChild.required<ElementRef<HTMLDialogElement>>('cajon');
  private readonly botonMenu = viewChild.required<ElementRef<HTMLButtonElement>>('botonMenu');
  protected readonly cerrando = signal(false);
  protected readonly errorCierre = signal<string | null>(null);
  protected readonly nombreVisible = computed(() => this.sesion.sesion()?.nombreVisible ?? '');
  protected readonly etiquetaRol = computed(() => {
    const rol = this.sesion.rol();
    return rol === null ? '' : ETIQUETA_ROL[rol];
  });

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
    ),
    { initialValue: this.router.url },
  );
  protected readonly seccionActual = computed(() => seccionDeRuta(this.url()));

  constructor() {
    // Si la ventana pasa a ≥ lg con el cajón abierto, se cierra: si no, el diálogo modal oculto por
    // CSS dejaría el resto de la página inerte.
    const consulta = this.documento.defaultView?.matchMedia?.(MEDIA_LG);
    if (consulta) {
      const alCambiar = (e: MediaQueryListEvent): void => {
        if (e.matches) this.cerrarMenu();
      };
      consulta.addEventListener('change', alCambiar);
      inject(DestroyRef).onDestroy(() => consulta.removeEventListener('change', alCambiar));
    }
  }

  /** Abre el cajón modal (< lg) y lleva el foco al primer enlace. */
  protected abrirMenu(): void {
    const cajon = this.cajon().nativeElement;
    if (!cajon.open) cajon.showModal();
    this.menuAbierto.set(true);
    cajon.querySelector<HTMLElement>('nav a')?.focus();
  }

  /** Cierra el cajón y devuelve el foco al botón «Menú». */
  protected cerrarMenu(): void {
    const cajon = this.cajon().nativeElement;
    if (!cajon.open) return;
    cajon.close();
    this.menuAbierto.set(false);
    this.botonMenu().nativeElement.focus();
  }

  /** Escape (evento cancel del diálogo nativo). */
  protected alCancelarCajon(evento: Event): void {
    evento.preventDefault();
    this.cerrarMenu();
  }

  protected saltarAlContenido(evento: Event): void {
    evento.preventDefault();
    this.enfocar(this.idContenido);
  }

  /** Bajo lg la navegación es un cajón modal: se abre y recibe el foco. */
  protected saltarANavegacion(evento: Event): void {
    evento.preventDefault();
    if (this.esEscritorio()) this.enfocar(this.idNavegacion);
    else this.abrirMenu();
  }

  private esEscritorio(): boolean {
    const ventana = this.documento.defaultView;
    return typeof ventana?.matchMedia !== 'function' || ventana.matchMedia(MEDIA_LG).matches;
  }

  protected async cerrarSesion(): Promise<void> {
    this.cerrando.set(true);
    this.errorCierre.set(null);
    const error = await this.sesion.cerrarSesion();
    this.cerrando.set(false);
    if (error !== null) {
      this.errorCierre.set(error.mensaje);
      return;
    }
    await this.router.navigate([RUTA_ACCESO_PANEL], { queryParams: { motivo: 'cerrada' } });
  }

  /** ALT-014: tras expirar, SCR-030 con `siguiente` para volver a la misma pantalla. */
  protected async volverAEntrar(): Promise<void> {
    const actual = this.router.url;
    const queryParams: Record<string, string> = { motivo: 'expirada' };
    if (esDestinoSeguro(actual)) queryParams['siguiente'] = actual;
    await this.router.navigate([RUTA_ACCESO_PANEL], { queryParams });
  }

  private enfocar(id: string): void {
    const objetivo = this.documento.getElementById(id);
    objetivo?.focus();
    objetivo?.scrollIntoView?.({ block: 'start' });
  }
}
