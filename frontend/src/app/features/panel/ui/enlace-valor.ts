import { Directive, ElementRef, WritableSignal, effect, inject, input } from '@angular/core';

type ControlTexto = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

/**
 * Enlace bidireccional entre un control nativo de texto y una señal:
 * `<input [appEnlaceValor]="campo">`, `<textarea [appEnlaceValor]="campo">` o
 * `<select [appEnlaceValor]="campo">` (se pasa la propia WritableSignal, sin enlaces intermedios).
 * Sustituye a @angular/forms en el panel (QA TKT-010 ciclo 1, FALLO-02: sus internos de core
 * acababan en el chunk compartido con la carga inicial pública). El DOM se sincroniza comparando con
 * el valor real del control, así que vaciar el campo funciona aunque no haya habido detección de
 * cambios entre lo que se escribió y el reinicio.
 *
 * TKT-022 amplía los límites heredados de TKT-010: escucha también `change` (el autocompletado de
 * algunos navegadores y los <select> solo emiten ese evento) y admite <textarea> y <select>. En un
 * <select> cuyas opciones se pintan en la misma plantilla, márcalas además con `[selected]`: el
 * valor puede fijarse antes de que existan las opciones. Las casillas (checkbox/radio) no usan esta
 * directiva: su valor es booleano.
 */
@Directive({
  selector: 'input[appEnlaceValor], textarea[appEnlaceValor], select[appEnlaceValor]',
  host: { '(input)': 'alCambiar($event)', '(change)': 'alCambiar($event)' },
})
export class EnlaceValor {
  readonly appEnlaceValor = input.required<WritableSignal<string>>();

  private readonly elemento = inject<ElementRef<ControlTexto>>(ElementRef).nativeElement;

  constructor() {
    effect(() => {
      const valor = this.appEnlaceValor()();
      if (this.elemento.value !== valor) this.elemento.value = valor;
    });
  }

  protected alCambiar(evento: Event): void {
    const valor = (evento.target as ControlTexto).value;
    if (this.appEnlaceValor()() !== valor) this.appEnlaceValor().set(valor);
  }
}
