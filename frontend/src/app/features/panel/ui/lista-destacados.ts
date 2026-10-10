import { DOCUMENT } from '@angular/common';
import { Component, Injector, afterNextRender, computed, inject, input, output, signal } from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  DEFINICION_LISTA,
  ListaDestacada,
  TEXTO_LISTA_VACIA,
  esNoPublicado,
  listaLlena,
  motivoListaLlena,
  textoContadorLista,
} from '../domain/destacados';
import {
  RefContenido,
  ResultadoBusqueda,
  anadirSinDuplicados,
  anuncioMovido,
  moverEn,
  quitarEn,
} from '../domain/formulario-contenido';
import { EstadoEditorial } from '../domain/modelos';
import { ETIQUETA_ESTADO, varianteEstado } from '../domain/tablero';
import { BuscadorContenidos } from './buscador-contenidos';

/**
 * Una lista de destacados de SCR-042 (HANDOFF Combobox + SortableList): contador «{n} de {mínimo}
 * mínimo» (role=status), lista ordenada con «Subir»/«Bajar»/«Quitar» (alternativa sin arrastre,
 * WCAG 2.5.7) y combobox de contenido PUBLICADO del tipo de la lista. Al llegar al máximo, «Añadir»
 * se deshabilita con su motivo. Controlado: recibe los elementos y emite la lista nueva.
 */
@Component({
  selector: 'app-lista-destacados',
  imports: [Boton, Insignia, BuscadorContenidos],
  template: `
    <section class="seccion" [attr.aria-labelledby]="idBase() + '-titulo'" [attr.data-testid]="idBase()">
      <div class="cabecera-lista">
        <h2 [id]="idBase() + '-titulo'">{{ def().titulo }}</h2>
        <p class="ayuda contador" role="status" [attr.data-testid]="idBase() + '-contador'">{{ contador() }}</p>
      </div>
      @if (error(); as mensaje) {
        <p class="error-campo" [id]="idBase() + '-error'" [attr.data-testid]="idBase() + '-error'">{{ mensaje }}</p>
      }
      @if (elementos().length === 0) {
        <p class="ayuda" [attr.data-testid]="idBase() + '-vacia'">{{ textoVacio }}</p>
      } @else {
        <ol class="lista-ordenable" [attr.aria-label]="def().titulo + ' destacados, en orden'" [id]="idBase() + '-lista'" tabindex="-1">
          @for (ref of elementos(); track ref.tipo + ref.id; let i = $index; let primero = $first; let ultimo = $last) {
            <li class="fila" [attr.data-testid]="idBase() + '-elemento'">
              <span class="titulo"><span class="posicion">{{ i + 1 }}.</span> {{ ref.titulo }}</span>
              @if (estadoNoPublicado(ref); as estado) {
                <app-insignia [variante]="variante(estado)" [attr.data-testid]="idBase() + '-no-publicado'">{{ etiquetaEstado[estado] }}</app-insignia>
              }
              <div class="acciones-fila">
                <button type="button" appBoton tamano="sm" variante="ghost" [id]="idBase() + '-subir-' + i" [disabled]="primero" (click)="mover(i, -1)">
                  Subir <span class="bs-solo-lectores">{{ ref.titulo }}</span>
                </button>
                <button type="button" appBoton tamano="sm" variante="ghost" [id]="idBase() + '-bajar-' + i" [disabled]="ultimo" (click)="mover(i, 1)">
                  Bajar <span class="bs-solo-lectores">{{ ref.titulo }}</span>
                </button>
                <button type="button" appBoton tamano="sm" variante="ghost" [attr.data-testid]="idBase() + '-quitar-' + i" (click)="quitar(i)">
                  Quitar <span class="bs-solo-lectores">{{ ref.titulo }}</span>
                </button>
              </div>
            </li>
          }
        </ol>
      }
      <app-buscador-contenidos
        [etiqueta]="def().etiquetaAnadir"
        [idBase]="idBase() + '-buscar'"
        [ayuda]="llena() ? motivoLlena() : 'Escribe al menos 2 letras del título. Solo aparece contenido publicado.'"
        [buscar]="buscar()"
        [excluidos]="excluidos()"
        [deshabilitado]="llena() || deshabilitado()"
        (elegir)="anadir($event)"
      />
      <p class="bs-solo-lectores" role="status">{{ anuncio() }}</p>
    </section>
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
  styles: `
    .cabecera-lista {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: var(--bs-space-2);
    }
    .cabecera-lista h2 {
      margin: 0;
    }
    .contador {
      margin: 0;
      font-variant-numeric: tabular-nums;
    }
    .lista-ordenable {
      display: grid;
      gap: var(--bs-space-2);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .fila {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-2) var(--bs-space-3);
      padding: var(--bs-space-2) var(--bs-space-3);
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-md);
    }
    .titulo {
      flex: 1 1 14rem;
      overflow-wrap: anywhere;
    }
    .posicion {
      font-variant-numeric: tabular-nums;
      color: var(--bs-color-text-muted);
    }
  `,
})
export class ListaDestacados {
  readonly lista = input.required<ListaDestacada>();
  readonly elementos = input.required<readonly RefContenido[]>();
  readonly error = input<string | null>(null);
  readonly deshabilitado = input(false);
  readonly buscar = input.required<(q: string) => Promise<ResultadoBusqueda>>();
  readonly cambio = output<readonly RefContenido[]>();

  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  protected readonly textoVacio = TEXTO_LISTA_VACIA;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO;
  protected readonly variante = varianteEstado;
  protected readonly anuncio = signal('');

  protected readonly def = computed(() => DEFINICION_LISTA[this.lista()]);
  protected readonly idBase = computed(() => `destacados-${this.lista()}`);
  protected readonly contador = computed(() => textoContadorLista(this.lista(), this.elementos().length));
  protected readonly llena = computed(() => listaLlena(this.lista(), this.elementos().length));
  protected readonly motivoLlena = computed(() => motivoListaLlena(this.lista()));
  protected readonly excluidos = computed(() => this.elementos().map((r) => `${r.tipo}:${r.id}`));

  /** Estado que se señala (solo si ya no está publicado: retirado después de elegirlo). */
  protected estadoNoPublicado(ref: RefContenido): EstadoEditorial | null {
    return ref.estado !== null && esNoPublicado(ref) ? ref.estado : null;
  }

  protected anadir(ref: RefContenido): void {
    this.cambio.emit(anadirSinDuplicados(this.elementos(), [ref], this.def().maximo));
  }

  protected quitar(indice: number): void {
    const ref = this.elementos()[indice];
    this.cambio.emit(quitarEn(this.elementos(), indice));
    this.anuncio.set(`${ref?.titulo ?? 'Elemento'} quitado de ${this.def().titulo.toLowerCase()}.`);
    afterNextRender(
      () => {
        const siguiente =
          this.documento.querySelector<HTMLElement>(`[data-testid="${this.idBase()}-quitar-${Math.min(indice, this.elementos().length - 1)}"]`) ??
          this.documento.getElementById(`${this.idBase()}-buscar`);
        siguiente?.focus();
      },
      { injector: this.injector },
    );
  }

  protected mover(indice: number, desplazamiento: number): void {
    const destino = indice + desplazamiento;
    const lista = this.elementos();
    if (destino < 0 || destino >= lista.length) return;
    this.cambio.emit(moverEn(lista, indice, destino));
    this.anuncio.set(anuncioMovido(lista[indice].titulo, destino + 1, lista.length));
    const base = this.idBase();
    afterNextRender(
      () => {
        const boton = this.documento.getElementById(`${base}-${desplazamiento < 0 ? 'subir' : 'bajar'}-${destino}`) as HTMLButtonElement | null;
        (boton && !boton.disabled ? boton : this.documento.getElementById(`${base}-${desplazamiento < 0 ? 'bajar' : 'subir'}-${destino}`))?.focus();
      },
      { injector: this.injector },
    );
  }
}
