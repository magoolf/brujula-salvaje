import { Component, DestroyRef, computed, inject, input, output, signal } from '@angular/core';

import {
  MINIMO_BUSQUEDA,
  RefContenido,
  ResultadoBusqueda,
} from '../domain/formulario-contenido';
import { ETIQUETA_ESTADO, ETIQUETA_TIPO_SINGULAR } from '../domain/tablero';

/** Espera tras la última tecla antes de buscar. */
const ESPERA_MS = 300;

/**
 * Combobox de búsqueda de contenido (HANDOFF Combobox, patrón ARIA combobox con listbox emergente y
 * aria-activedescendant): mínimo 2 caracteres, resultados con tipo y estado; los ya elegidos (o la
 * propia entidad) aparecen deshabilitados con su motivo («Ya está en la lista»). Flechas para
 * moverse, Enter para elegir, Escape para cerrar. La búsqueda la hace quien lo usa (`buscar`, que
 * delega en el store): este componente solo presenta.
 */
@Component({
  selector: 'app-buscador-contenidos',
  template: `
    <div class="combobox">
      <label [for]="idBase()" class="etiqueta-campo">{{ etiqueta() }}</label>
      @if (ayuda(); as texto) {
        <p class="ayuda" [id]="idBase() + '-ayuda'">{{ texto }}</p>
      }
      <input
        [id]="idBase()"
        class="entrada-texto"
        type="search"
        role="combobox"
        autocomplete="off"
        maxlength="100"
        aria-autocomplete="list"
        [attr.aria-expanded]="abierto()"
        [attr.aria-controls]="idBase() + '-lista'"
        [attr.aria-activedescendant]="activo() === null ? null : idBase() + '-opcion-' + activo()"
        [attr.aria-describedby]="ayuda() ? idBase() + '-ayuda' : null"
        [attr.data-testid]="idBase()"
        [disabled]="deshabilitado()"
        [value]="consulta()"
        (input)="alEscribir($event)"
        (keydown)="alTeclear($event)"
        (blur)="alSalir()"
      />
      <p class="bs-solo-lectores" role="status">{{ anuncio() }}</p>
      <ul class="lista" role="listbox" [id]="idBase() + '-lista'" [attr.aria-label]="etiqueta()" [hidden]="!abierto()">
        @if (abierto()) {
          @for (opcion of opciones(); track opcion.ref.tipo + opcion.ref.id; let i = $index) {
            <li
              role="option"
              [id]="idBase() + '-opcion-' + i"
              [class.activa]="activo() === i"
              [attr.aria-selected]="activo() === i"
              [attr.aria-disabled]="opcion.motivo ? 'true' : null"
              [attr.data-testid]="idBase() + '-opcion'"
              tabindex="-1"
              (mousedown)="$event.preventDefault()"
              (click)="elegirEn(i)"
              (keydown.enter)="elegirEn(i)"
            >
              <span class="titulo">{{ opcion.ref.titulo }}</span>
              <span class="meta">
                {{ etiquetaTipo[opcion.ref.tipo] }}@if (opcion.ref.estado; as estado) { · {{ etiquetaEstado[estado] }} }
                @if (opcion.motivo; as motivo) { · {{ motivo }} }
              </span>
            </li>
          } @empty {
            <li class="vacio" role="presentation">{{ textoVacio() }}</li>
          }
        }
      </ul>
    </div>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .combobox {
      position: relative;
      display: grid;
      gap: var(--bs-space-1);
    }
    .lista[hidden] {
      display: none;
    }
    .lista {
      position: absolute;
      inset-inline: 0;
      top: 100%;
      z-index: var(--bs-z-dropdown, 30);
      max-height: 18rem;
      overflow-y: auto;
      margin: var(--bs-space-1) 0 0;
      padding: var(--bs-space-1);
      list-style: none;
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      box-shadow: var(--bs-shadow-3);
    }
    [role='option'] {
      display: grid;
      gap: 2px;
      min-height: var(--bs-size-target);
      padding: var(--bs-space-2) var(--bs-space-3);
      border-radius: var(--bs-radius-sm);
      cursor: pointer;
    }
    [role='option'].activa {
      background: var(--bs-color-action-selected-bg);
      outline: 2px solid var(--bs-color-focus-ring, currentColor);
      outline-offset: -2px;
    }
    [role='option'][aria-disabled='true'] {
      cursor: not-allowed;
      color: var(--bs-color-text-muted);
    }
    .meta,
    .vacio {
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-muted);
    }
    .vacio {
      padding: var(--bs-space-2) var(--bs-space-3);
    }
    @media (forced-colors: active) {
      [role='option'].activa {
        outline-color: Highlight;
      }
    }
  `,
})
export class BuscadorContenidos {
  readonly etiqueta = input.required<string>();
  readonly idBase = input.required<string>();
  readonly ayuda = input<string | null>(null);
  readonly deshabilitado = input(false);
  /** Búsqueda (q ≥ 2 caracteres). */
  readonly buscar = input.required<(q: string) => Promise<ResultadoBusqueda>>();
  /** Claves `TIPO:id` ya elegidas o no elegibles (autorrelación). */
  readonly excluidos = input<readonly string[]>([]);
  readonly elegir = output<RefContenido>();

  protected readonly etiquetaTipo = ETIQUETA_TIPO_SINGULAR;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO;
  protected readonly consulta = signal('');
  private readonly resultados = signal<readonly RefContenido[]>([]);
  private readonly error = signal<string | null>(null);
  private readonly buscando = signal(false);
  protected readonly abierto = signal(false);
  protected readonly activo = signal<number | null>(null);
  protected readonly anuncio = signal('');
  private temporizador: ReturnType<typeof setTimeout> | null = null;
  private peticion = 0;

  protected readonly opciones = computed(() => {
    const excluidos = new Set(this.excluidos());
    return this.resultados().map((ref) => ({
      ref,
      motivo: excluidos.has(`${ref.tipo}:${ref.id}`) ? 'Ya está en la lista' : null,
    }));
  });
  protected readonly textoVacio = computed(() => {
    if (this.buscando()) return 'Buscando…';
    if (this.error()) return this.error();
    return 'Sin coincidencias.';
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => this.cancelar());
  }

  protected alEscribir(evento: Event): void {
    const valor = (evento.target as HTMLInputElement).value;
    this.consulta.set(valor);
    this.cancelar();
    const q = valor.trim();
    if (q.length < MINIMO_BUSQUEDA) {
      this.abierto.set(false);
      this.resultados.set([]);
      this.anuncio.set(q.length === 0 ? '' : `Escribe al menos ${MINIMO_BUSQUEDA} caracteres.`);
      return;
    }
    this.temporizador = setTimeout(() => void this.ejecutarBusqueda(q), ESPERA_MS);
  }

  private async ejecutarBusqueda(q: string): Promise<void> {
    const numero = ++this.peticion;
    this.buscando.set(true);
    this.abierto.set(true);
    this.activo.set(null);
    const resultado = await this.buscar()(q);
    if (numero !== this.peticion) return;
    this.buscando.set(false);
    this.resultados.set(resultado.resultados);
    this.error.set(resultado.error);
    const n = resultado.resultados.length;
    this.anuncio.set(resultado.error ?? (n === 1 ? '1 resultado.' : `${n} resultados.`));
  }

  protected alTeclear(evento: KeyboardEvent): void {
    const total = this.opciones().length;
    if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
      if (!this.abierto() || total === 0) return;
      evento.preventDefault();
      const actual = this.activo();
      const paso = evento.key === 'ArrowDown' ? 1 : -1;
      this.activo.set(actual === null ? (paso === 1 ? 0 : total - 1) : (actual + paso + total) % total);
    } else if (evento.key === 'Enter') {
      const actual = this.activo();
      if (this.abierto() && actual !== null) {
        evento.preventDefault();
        this.elegirEn(actual);
      }
    } else if (evento.key === 'Escape' && this.abierto()) {
      evento.preventDefault();
      this.abierto.set(false);
      this.activo.set(null);
    }
  }

  protected elegirEn(indice: number): void {
    const opcion = this.opciones()[indice];
    if (!opcion || opcion.motivo) return;
    this.elegir.emit(opcion.ref);
    this.anuncio.set(`${opcion.ref.titulo} añadido.`);
    this.consulta.set('');
    this.resultados.set([]);
    this.abierto.set(false);
    this.activo.set(null);
  }

  protected alSalir(): void {
    this.abierto.set(false);
    this.activo.set(null);
  }

  private cancelar(): void {
    if (this.temporizador !== null) clearTimeout(this.temporizador);
    this.temporizador = null;
    this.peticion++;
    this.buscando.set(false);
  }
}
