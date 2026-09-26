import { DestroyRef, Directive, ElementRef, computed, inject, input } from '@angular/core';

export type VarianteBoton =
  'primary' | 'accent' | 'secondary' | 'ghost' | 'danger' | 'ghost-inverse';
export type TamanoBoton = 'sm' | 'md' | 'lg';

/**
 * Primitiva Button (HANDOFF_UI_UX COMPONENTES.Button) aplicada sobre `<button>` o `<a>` nativos,
 * para conservar su semántica y accesibilidad. Estilos en src/styles/componentes.css.
 * - `cargando`: aria-busy + aria-disabled y clics bloqueados (protege del doble clic, ALT-017).
 * - `deshabilitadoEnfocable`: aria-disabled para seguir recibiendo foco y explicar el motivo.
 * El bloqueo usa un listener en fase de captura sobre el propio elemento, que se ejecuta antes que
 * los manejadores `(click)` de la plantilla que lo usa.
 */
@Directive({
  selector: 'button[appBoton], a[appBoton]',
  host: {
    '[class]': 'clases()',
    '[attr.aria-busy]': 'cargando() ? "true" : null',
    '[attr.aria-disabled]': 'bloqueado() ? "true" : null',
    '[attr.data-variante]': 'variante()',
  },
})
export class Boton {
  readonly variante = input<VarianteBoton>('primary');
  readonly tamano = input<TamanoBoton>('md');
  readonly cargando = input(false);
  readonly deshabilitadoEnfocable = input(false);

  protected readonly bloqueado = computed(() => this.cargando() || this.deshabilitadoEnfocable());
  protected readonly clases = computed(() => {
    const clases = ['bs-boton', `bs-boton--${this.variante()}`];
    if (this.tamano() !== 'md') clases.push(`bs-boton--${this.tamano()}`);
    return clases.join(' ');
  });

  constructor() {
    const elemento = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
    const alPulsar = (evento: Event): void => {
      if (this.bloqueado()) {
        evento.preventDefault();
        evento.stopImmediatePropagation();
      }
    };
    elemento.addEventListener('click', alPulsar, { capture: true });
    inject(DestroyRef).onDestroy(() =>
      elemento.removeEventListener('click', alPulsar, { capture: true }),
    );
  }
}
