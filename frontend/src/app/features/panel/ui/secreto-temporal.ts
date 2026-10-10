import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, afterNextRender, inject, input, output, signal, viewChild } from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';

/**
 * OneTimeSecret «contraseña temporal» (HANDOFF OneTimeSecret, DEC-AUTO-075, AC-106; SCR-045):
 * panel destacado con el secreto en fuente mono, «Copiar» y el aviso «Se muestra solo esta vez».
 * Solo se descarta con «Ya la guardé»; después no se puede volver a mostrar (quien lo usa olvida el
 * secreto). El secreto nunca va en un anuncio aria-live: al aparecer, el foco va al encabezado.
 */
@Component({
  selector: 'app-secreto-temporal',
  imports: [Boton],
  template: `
    <section class="secreto" aria-labelledby="secreto-titulo" data-testid="secreto-temporal">
      <h2 id="secreto-titulo" tabindex="-1" #titulo>Contraseña temporal de {{ usuario() }}</h2>
      <p>Se muestra solo esta vez. Cópiala y entrégala por un canal seguro fuera del sistema.</p>
      <p class="valor mono" data-testid="secreto-valor">{{ secreto() }}</p>
      <div class="acciones">
        <button type="button" appBoton variante="secondary" data-testid="secreto-copiar" (click)="copiar()">Copiar</button>
        <button type="button" appBoton data-testid="secreto-guardado" (click)="guardado.emit()">Ya la guardé</button>
      </div>
      <p class="ayuda" role="status">{{ copiado() ? 'Copiada al portapapeles.' : '' }}</p>
    </section>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .secreto {
      display: grid;
      gap: var(--bs-space-3);
      justify-items: start;
      padding: var(--bs-space-5);
      border-inline-start: 4px solid var(--bs-color-status-warning-fg);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-status-warning-bg);
    }
    h2,
    p {
      margin: 0;
    }
    .valor {
      padding: var(--bs-space-2) var(--bs-space-3);
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-sm);
      background: var(--bs-color-bg-surface);
      font-size: var(--bs-typography-body-lg-font-size);
      user-select: all;
    }
    @media (forced-colors: active) {
      .secreto {
        border: 1px solid CanvasText;
      }
    }
  `,
})
export class SecretoTemporal {
  readonly usuario = input.required<string>();
  readonly secreto = input.required<string>();
  readonly guardado = output<void>();

  private readonly documento = inject(DOCUMENT);
  private readonly titulo = viewChild.required<ElementRef<HTMLElement>>('titulo');
  protected readonly copiado = signal(false);

  constructor() {
    afterNextRender(() => this.titulo().nativeElement.focus());
  }

  protected async copiar(): Promise<void> {
    try {
      await this.documento.defaultView?.navigator.clipboard.writeText(this.secreto());
      this.copiado.set(true);
    } catch {
      this.copiado.set(false);
    }
  }
}
