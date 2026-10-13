import { Component, computed, inject, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';

import { EditorContenido } from './editor-contenido';
import { ConSalidaControlada } from './salida-editor.guard';

/**
 * Ruta de SCR-036 (`/panel/contenido/:tipo/nuevo | :id`). El router reutiliza el componente al
 * cambiar de parámetros (p. ej. tras el alta, o al seguir un enlace a otro contenido): este
 * anfitrión vuelve a crear el editor —y sus stores, una instancia por contenido— cuando cambia el
 * tipo o el id, para que nunca se mezclen datos de dos contenidos.
 */
@Component({
  selector: 'app-pagina-editor-contenido',
  imports: [EditorContenido],
  template: `
    @for (clave of [clave()]; track clave) {
      <app-editor-contenido />
    }
  `,
})
export class PaginaEditorContenido implements ConSalidaControlada {
  private readonly params = toSignal(inject(ActivatedRoute).paramMap, { requireSync: true });
  protected readonly clave = computed(() => `${this.params().get('tipo')}:${this.params().get('id')}`);
  private readonly editor = viewChild(EditorContenido);

  puedeSalir(destino: string): boolean | Promise<boolean> {
    return this.editor()?.puedeSalir(destino) ?? true;
  }
}
