import { DOCUMENT } from '@angular/common';
import { Component, EnvironmentInjector, afterNextRender, inject } from '@angular/core';

import { ID_CONTENIDO_PRINCIPAL } from '../../../core/layout/navegacion';
import { CargaPanelStore } from '../state/carga-panel.store';

/**
 * Armazón mínimo de carga del panel (QA TKT-010 OBS-C3-01, AC_TKT022_07): en la carga completa de
 * una URL /panel/** se muestra al instante —con <main>, la marca y un estado de carga anunciado—
 * mientras se resuelve la sesión; después se repite la navegación original con los guards de
 * siempre (CargaPanelStore). Fondo y marca de TPL-PANEL-AUTH, sin datos de la sesión.
 *
 * Foco: la navegación repetida es interna para el router y FocoRuta llevaría el foco al h1, pero
 * para la persona sigue siendo la carga inicial de la página. Si nadie movió el foco durante la
 * carga, se devuelve al documento para que el primer Tab llegue a los saltos de accesibilidad.
 */
@Component({
  selector: 'app-carga-panel',
  template: `
    <main [id]="idContenido" tabindex="-1" class="lienzo" aria-busy="true" data-testid="panel-cargando">
      <p class="marca">
        <span class="nombre">Brújula Salvaje</span>
        <span class="etiqueta">Panel editorial</span>
      </p>
      <p class="estado" role="status">Cargando el panel…</p>
    </main>
  `,
  styles: `
    :host {
      display: block;
      min-height: 100dvh;
      background: var(--bs-color-bg-canvas-panel);
    }
    .lienzo {
      box-sizing: border-box;
      display: grid;
      place-content: center;
      justify-items: center;
      gap: var(--bs-space-4);
      min-height: 100dvh;
      padding: var(--bs-space-6) var(--bs-grid-margin-xs);
      outline: none;
    }
    .marca {
      display: grid;
      justify-items: center;
      gap: var(--bs-space-1);
    }
    .nombre {
      font-family: var(--bs-font-family-display);
      font-weight: var(--bs-font-weight-extrabold);
      font-size: var(--bs-typography-h2-font-size);
      color: var(--bs-color-text-brand);
    }
    .etiqueta,
    .estado {
      color: var(--bs-color-text-muted);
    }
  `,
})
export class CargaPanel {
  protected readonly idContenido = ID_CONTENIDO_PRINCIPAL;

  constructor() {
    const documento = inject(DOCUMENT);
    // Inyector raíz: este componente ya no existe cuando se pinta la pantalla de destino.
    const injector = inject(EnvironmentInjector);
    const focoInicial = documento.activeElement;
    void inject(CargaPanelStore)
      .continuar()
      .then(() => {
        afterNextRender(
          () => {
            const activo = documento.activeElement;
            const principal = documento.getElementById(ID_CONTENIDO_PRINCIPAL);
            const movidoPorRuta = activo !== null && principal !== null && principal.contains(activo);
            if (focoInicial !== documento.body || !movidoPorRuta) return;
            // Foco (y punto de partida del Tab) al inicio del documento, como en una carga normal.
            const cuerpo = documento.body;
            cuerpo.setAttribute('tabindex', '-1');
            cuerpo.focus({ preventScroll: true });
            cuerpo.removeAttribute('tabindex');
          },
          { injector },
        );
      });
  }
}
