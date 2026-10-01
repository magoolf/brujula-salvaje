import { Directive, ElementRef, WritableSignal, effect, inject, input } from '@angular/core';

/**
 * Enlace bidireccional entre un <input> nativo y una señal: `<input [appEnlaceValor]="campo">`
 * (se pasa la propia WritableSignal, sin enlaces intermedios).
 * Sustituye a @angular/forms en el panel (QA TKT-010 ciclo 1, FALLO-02: sus internos de core
 * acababan en el chunk compartido con la carga inicial pública). El DOM se sincroniza comparando con
 * el valor real del control, así que vaciar el campo funciona aunque no haya habido detección de
 * cambios entre lo que se escribió y el reinicio.
 */
@Directive({
  selector: 'input[appEnlaceValor]',
  host: { '(input)': 'alEscribir($event)' },
})
export class EnlaceValor {
  readonly appEnlaceValor = input.required<WritableSignal<string>>();

  private readonly elemento = inject<ElementRef<HTMLInputElement>>(ElementRef).nativeElement;

  constructor() {
    effect(() => {
      const valor = this.appEnlaceValor()();
      if (this.elemento.value !== valor) this.elemento.value = valor;
    });
  }

  protected alEscribir(evento: Event): void {
    this.appEnlaceValor().set((evento.target as HTMLInputElement).value);
  }
}
