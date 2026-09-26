import { DOCUMENT } from '@angular/common';
import { Component, inject, input } from '@angular/core';

/**
 * SkipLink (HANDOFF_UI_UX): primer elemento enfocable, oculto hasta recibir foco. Sin JS funciona
 * como ancla nativa; con JS mueve el foco al destino (main con tabindex=-1) de forma fiable en todos
 * los navegadores sin cambiar la URL.
 */
@Component({
  selector: 'app-skip-link',
  template: `
    <a class="salto" [href]="'#' + destino()" data-testid="skip-link" (click)="saltar($event)">{{
      texto()
    }}</a>
  `,
  styles: `
    .salto {
      position: absolute;
      top: var(--bs-space-2);
      left: var(--bs-space-2);
      z-index: var(--bs-z-skip-link);
      padding: var(--bs-space-3) var(--bs-space-4);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-inverse);
      color: var(--bs-color-text-inverse);
      font-weight: var(--bs-font-weight-semibold);
      text-decoration: underline;
      transform: translateY(-200%);
    }
    .salto:focus,
    .salto:focus-visible {
      transform: none;
      outline: var(--bs-border-width-focus) solid var(--bs-color-focus-ring-inverse);
      outline-offset: var(--bs-border-width-focus-offset);
    }
  `,
})
export class SkipLink {
  readonly destino = input('contenido-principal');
  readonly texto = input('Saltar al contenido principal');

  private readonly documento = inject(DOCUMENT);

  protected saltar(evento: Event): void {
    const objetivo = this.documento.getElementById(this.destino());
    if (objetivo === null) return;
    evento.preventDefault();
    if (!objetivo.hasAttribute('tabindex')) objetivo.setAttribute('tabindex', '-1');
    objetivo.focus();
    objetivo.scrollIntoView({ block: 'start' });
  }
}
