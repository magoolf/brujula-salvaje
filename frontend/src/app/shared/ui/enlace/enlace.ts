import { Directive, computed, input } from '@angular/core';

export type VarianteEnlace = 'inline' | 'standalone' | 'nav' | 'external';

/**
 * Primitiva Link (HANDOFF_UI_UX COMPONENTES.Link) sobre `<a>` nativo.
 * - inline: subrayado siempre (1.4.1).
 * - standalone / nav: estilos de src/styles/componentes.css; el estado actual lo marca
 *   `routerLinkActive` con `ariaCurrentWhenActive="page"`.
 * - external: rel="noopener noreferrer" y misma pestaña (DEC-AUTO-078); el texto «(sitio externo)»
 *   lo añade quien lo usa junto al icono.
 */
@Directive({
  selector: 'a[appEnlace]',
  host: {
    '[class]': 'clase()',
    '[attr.rel]': 'variante() === "external" ? "noopener noreferrer" : null',
  },
})
export class Enlace {
  readonly variante = input<VarianteEnlace>('inline');

  protected readonly clase = computed(() => `bs-enlace bs-enlace--${this.variante()}`);
}
