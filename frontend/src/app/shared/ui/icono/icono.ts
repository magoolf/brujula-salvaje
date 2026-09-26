import { Component, computed, input } from '@angular/core';

import { ICONOS_LUCIDE, NodoIcono, NombreIcono } from './iconos-lucide';

/**
 * Icono SVG en línea (Lucide vendorizado, trazo 1.75, currentColor; HANDOFF_UI_UX Icon_System).
 * Decorativo por defecto (aria-hidden). Con `etiqueta` se expone como imagen con nombre accesible;
 * en botones de solo icono el nombre va en el botón (aria-label), no aquí.
 */
@Component({
  selector: 'app-icono',
  template: `
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      focusable="false"
      [attr.width]="tamano()"
      [attr.height]="tamano()"
      [attr.aria-hidden]="etiqueta() ? null : 'true'"
      [attr.role]="etiqueta() ? 'img' : null"
      [attr.aria-label]="etiqueta()"
      [attr.data-testid]="'icono-' + nombre()"
    >
      @for (nodo of nodos(); track $index) {
        @switch (nodo.tipo) {
          @case ('path') {
            <svg:path [attr.d]="nodo.d" />
          }
          @case ('circle') {
            <svg:circle [attr.cx]="nodo.cx" [attr.cy]="nodo.cy" [attr.r]="nodo.r" />
          }
          @case ('line') {
            <svg:line
              [attr.x1]="nodo.x1"
              [attr.x2]="nodo.x2"
              [attr.y1]="nodo.y1"
              [attr.y2]="nodo.y2"
            />
          }
        }
      }
    </svg>
  `,
  styles: `
    :host {
      display: inline-flex;
      flex-shrink: 0;
      line-height: 0;
    }
  `,
})
export class Icono {
  readonly nombre = input.required<NombreIcono>();
  readonly tamano = input<16 | 20 | 24 | 32>(20);
  readonly etiqueta = input<string | null>(null);

  protected readonly nodos = computed(() =>
    (ICONOS_LUCIDE[this.nombre()] as readonly NodoIcono[]).map(aNodoPlano),
  );
}

/** Nodo SVG con atributos opcionales para la plantilla (evita estrechar tuplas en el template). */
export interface NodoPlano {
  readonly tipo: NodoIcono[0];
  readonly d?: string;
  readonly cx?: string;
  readonly cy?: string;
  readonly r?: string;
  readonly x1?: string;
  readonly x2?: string;
  readonly y1?: string;
  readonly y2?: string;
}

export function aNodoPlano(nodo: NodoIcono): NodoPlano {
  return { tipo: nodo[0], ...nodo[1] };
}
