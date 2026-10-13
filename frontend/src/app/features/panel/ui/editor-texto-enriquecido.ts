import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import {
  RefContenido,
  ResultadoBusqueda,
  contarPalabras,
  esEnlaceExterno,
  esHrefPermitido,
  esSlugValido,
  textoContadorPalabras,
} from '../domain/formulario-contenido';
import { BuscadorContenidos } from './buscador-contenidos';
import { pintarHtmlSaneado, serializarHtmlSaneado } from './saneado-html';

type Bloque = 'p' | 'h2' | 'h3' | 'h4';
type Panel = 'ninguno' | 'enlace' | 'glosario';

const BLOQUES: readonly { readonly valor: Bloque; readonly etiqueta: string }[] = [
  { valor: 'p', etiqueta: 'Párrafo' },
  { valor: 'h2', etiqueta: 'Título 2' },
  { valor: 'h3', etiqueta: 'Título 3' },
  { valor: 'h4', etiqueta: 'Título 4' },
];

const MENSAJE_URL = 'Usa una dirección que empiece por http:// o https://, o una ruta interna que empiece por /.';

/**
 * RichTextEditor (HANDOFF COMPONENTES, RULE-022/021): área editable con barra de herramientas
 * role=toolbar (tabindex itinerante): Párrafo/Título 2-4 · Negrita · Cursiva · Lista · Lista
 * numerada · Cita · Enlace · Término de glosario. Atajos Ctrl/Cmd+B, I y K. Pegar inserta solo el
 * texto (se limpia al formato permitido; el servidor sanea igualmente). Contador de palabras
 * opcional («412 de 600 palabras mínimas»).
 *
 * Decisión DEC-DEV-023-03: sin librería de terceros (presupuesto del chunk del editor y licencias);
 * los comandos de formato usan `document.execCommand` (obsoleto pero soportado por los 3 motores y
 * sin alternativa nativa) y el HTML se pinta y se serializa con la lista blanca de
 * `saneado-html.ts` (nunca innerHTML). Controlado con `[valor]` + `(cambio)`.
 */
@Component({
  selector: 'app-editor-texto-enriquecido',
  imports: [Boton, BuscadorContenidos],
  template: `
    <div class="editor" [class.invalido]="error()">
      <span class="etiqueta-campo" [id]="idCampo() + '-etiqueta'">
        {{ etiqueta() }}
        @if (obligatorioPublicar()) {
          <span class="obligatorio">(obligatorio para publicar)</span>
        }
      </span>
      @if (ayuda(); as texto) {
        <p class="ayuda" [id]="idCampo() + '-ayuda'">{{ texto }}</p>
      }
      @if (!soloLectura()) {
        <div
          class="barra"
          role="toolbar"
          [attr.aria-label]="'Formato de ' + etiqueta()"
          [attr.aria-controls]="idCampo()"
          tabindex="-1"
          (keydown)="alTeclearBarra($event)"
        >
          <label class="bs-solo-lectores" [for]="idCampo() + '-bloque'">Tipo de bloque</label>
          <select
            class="control-barra"
            [id]="idCampo() + '-bloque'"
            [attr.tabindex]="indiceFoco() === 0 ? 0 : -1"
            (change)="aplicarBloque($event)"
            (focus)="indiceFoco.set(0)"
          >
            @for (b of bloques; track b.valor) {
              <option [value]="b.valor">{{ b.etiqueta }}</option>
            }
          </select>
          @for (accion of accionesBarra(); track accion.id; let i = $index) {
            <button
              type="button"
              class="control-barra"
              [attr.tabindex]="indiceFoco() === i + 1 ? 0 : -1"
              [attr.aria-label]="accion.etiqueta"
              [attr.title]="accion.atajo ? accion.etiqueta + ' (' + accion.atajo + ')' : accion.etiqueta"
              [attr.data-testid]="idCampo() + '-' + accion.id"
              (mousedown)="$event.preventDefault()"
              (click)="ejecutarAccion(accion.id)"
              (focus)="indiceFoco.set(i + 1)"
            >
              <span aria-hidden="true">{{ accion.simbolo }}</span>
            </button>
          }
        </div>
      }
      <div
        #area
        class="area"
        role="textbox"
        aria-multiline="true"
        [id]="idCampo()"
        [attr.contenteditable]="soloLectura() ? 'false' : 'true'"
        [attr.aria-readonly]="soloLectura() ? 'true' : null"
        [attr.aria-labelledby]="idCampo() + '-etiqueta'"
        [attr.aria-describedby]="descritoPor()"
        [attr.aria-invalid]="error() ? 'true' : null"
        [attr.data-testid]="idCampo()"
        tabindex="0"
        (input)="alEditar()"
        (blur)="alSalirArea()"
        (paste)="alPegar($event)"
        (keydown)="alTeclearArea($event)"
      ></div>

      @if (panel() === 'enlace') {
        <div class="panel-auxiliar" role="group" [attr.aria-labelledby]="idCampo() + '-enlace-titulo'">
          <p class="etiqueta-campo" [id]="idCampo() + '-enlace-titulo'">Añadir enlace</p>
          <label [for]="idCampo() + '-url'">Dirección</label>
          <input
            #url
            class="entrada-texto"
            type="text"
            inputmode="url"
            [id]="idCampo() + '-url'"
            [attr.aria-invalid]="errorEnlace() ? 'true' : null"
            [attr.aria-describedby]="idCampo() + '-url-ayuda' + (errorEnlace() ? ' ' + idCampo() + '-url-error' : '')"
            [attr.data-testid]="idCampo() + '-url'"
            [value]="urlEnlace()"
            (input)="urlEnlace.set($any($event.target).value)"
            (keydown.enter)="$event.preventDefault(); aplicarEnlace()"
            (keydown.escape)="cerrarPanel()"
          />
          <p class="ayuda" [id]="idCampo() + '-url-ayuda'">
            Solo http://, https:// o una ruta del sitio (/destinos/…).
            @if (avisoExterno()) {
              <strong>Es un sitio externo.</strong>
            }
          </p>
          @if (errorEnlace(); as mensaje) {
            <p class="error-campo" [id]="idCampo() + '-url-error'">{{ mensaje }}</p>
          }
          <div class="acciones">
            <button type="button" appBoton tamano="sm" [attr.data-testid]="idCampo() + '-url-aplicar'" (click)="aplicarEnlace()">Aplicar</button>
            <button type="button" appBoton tamano="sm" variante="secondary" (click)="cerrarPanel()">Cancelar</button>
          </div>
        </div>
      }
      @if (panel() === 'glosario' && buscarTerminos(); as buscar) {
        <div class="panel-auxiliar">
          <app-buscador-contenidos
            etiqueta="Término del glosario"
            [idBase]="idCampo() + '-glosario'"
            ayuda="Escribe al menos 2 letras del término."
            [buscar]="buscar"
            (elegir)="insertarTermino($event)"
          />
          <div class="acciones">
            <button type="button" appBoton tamano="sm" variante="secondary" (click)="cerrarPanel()">Cancelar</button>
          </div>
        </div>
      }

      @if (minimoPalabras(); as minimo) {
        <p class="ayuda contador" [id]="idCampo() + '-contador'" [class.pendiente]="palabras() < minimo">
          {{ textoPalabras() }}
        </p>
      }
      @if (error(); as mensaje) {
        <p class="error-campo" [id]="idCampo() + '-error'" [attr.data-testid]="idCampo() + '-error'">{{ mensaje }}</p>
      }
    </div>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .editor {
      display: grid;
      gap: var(--bs-space-1);
    }
    .barra {
      display: flex;
      flex-wrap: wrap;
      gap: var(--bs-space-1);
      padding: var(--bs-space-1);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-bottom: 0;
      border-radius: var(--bs-radius-md) var(--bs-radius-md) 0 0;
      background: var(--bs-color-bg-sunken);
    }
    .control-barra {
      min-width: var(--bs-size-target);
      min-height: var(--bs-size-target);
      padding: 0 var(--bs-space-2);
      border: var(--bs-border-width-hairline) solid transparent;
      border-radius: var(--bs-radius-sm);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      font: inherit;
      font-weight: var(--bs-font-weight-semibold);
      cursor: pointer;
    }
    .control-barra:hover {
      border-color: var(--bs-color-border-control);
    }
    .area {
      min-height: 8rem;
      max-height: 32rem;
      overflow-y: auto;
      padding: var(--bs-space-3);
      border: var(--bs-border-width-control) solid var(--bs-color-border-control);
      border-radius: 0 0 var(--bs-radius-md) var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
      color: var(--bs-color-text-default);
      line-height: var(--bs-typography-body-line-height);
    }
    .area[contenteditable='false'] {
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-sunken);
    }
    .invalido .area {
      border-color: var(--bs-color-status-error-fg);
      border-width: var(--bs-border-width-strong);
    }
    .area :where(p, ul, ol, blockquote, h2, h3, h4) {
      margin: 0 0 var(--bs-space-2);
    }
    .area :where(ul, ol) {
      padding-inline-start: var(--bs-space-6, 1.5rem);
    }
    .area blockquote {
      padding-inline-start: var(--bs-space-3);
      border-inline-start: 3px solid var(--bs-color-border-subtle);
    }
    .area a {
      color: var(--bs-color-text-link);
    }
    .panel-auxiliar {
      display: grid;
      gap: var(--bs-space-2);
      padding: var(--bs-space-3);
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-sunken);
    }
    .contador {
      font-variant-numeric: tabular-nums;
    }
    .pendiente {
      color: var(--bs-color-status-warning-fg);
      font-weight: var(--bs-font-weight-semibold);
    }
  `,
})
export class EditorTextoEnriquecido {
  readonly valor = input.required<string>();
  readonly cambio = output<string>();
  /** Al salir del área (CompletenessPanel: se recalcula al salir de cada campo). */
  readonly salir = output<void>();
  readonly etiqueta = input.required<string>();
  readonly idCampo = input.required<string>();
  readonly ayuda = input<string | null>(null);
  readonly error = input<string | null>(null);
  readonly obligatorioPublicar = input(false);
  readonly soloLectura = input(false);
  readonly minimoPalabras = input<number | null>(null);
  /** Búsqueda de términos del glosario (sin ella no se ofrece el botón). */
  readonly buscarTerminos = input<((q: string) => Promise<ResultadoBusqueda>) | null>(null);

  private readonly documento = inject(DOCUMENT);
  private readonly area = viewChild.required<ElementRef<HTMLDivElement>>('area');
  private readonly campoUrl = viewChild<ElementRef<HTMLInputElement>>('url');

  protected readonly bloques = BLOQUES;
  protected readonly indiceFoco = signal(0);
  protected readonly panel = signal<Panel>('ninguno');
  protected readonly urlEnlace = signal('');
  protected readonly errorEnlace = signal<string | null>(null);
  protected readonly palabras = signal(0);
  /** Último HTML emitido: si el valor de entrada coincide, no se repinta (conserva el cursor). */
  private ultimoEmitido: string | null = null;
  private rangoGuardado: Range | null = null;

  protected readonly accionesBarra = computed(() => {
    const acciones = [
      { id: 'negrita', etiqueta: 'Negrita', simbolo: 'N', atajo: 'Ctrl+B' },
      { id: 'cursiva', etiqueta: 'Cursiva', simbolo: 'K', atajo: 'Ctrl+I' },
      { id: 'lista', etiqueta: 'Lista', simbolo: '•', atajo: null },
      { id: 'lista-numerada', etiqueta: 'Lista numerada', simbolo: '1.', atajo: null },
      { id: 'cita', etiqueta: 'Cita', simbolo: '“', atajo: null },
      { id: 'enlace', etiqueta: 'Enlace', simbolo: 'Enlace', atajo: 'Ctrl+K' },
    ];
    return this.buscarTerminos() === null
      ? acciones
      : [...acciones, { id: 'glosario', etiqueta: 'Término de glosario', simbolo: 'Glosario', atajo: null }];
  });
  protected readonly avisoExterno = computed(() => {
    const url = this.urlEnlace().trim();
    return url !== '' && esHrefPermitido(url) && esEnlaceExterno(url);
  });
  protected readonly textoPalabras = computed(() =>
    textoContadorPalabras(this.palabras(), this.minimoPalabras() ?? 0),
  );
  protected readonly descritoPor = computed(() => {
    const id = this.idCampo();
    return (
      [
        this.ayuda() ? `${id}-ayuda` : null,
        this.minimoPalabras() !== null ? `${id}-contador` : null,
        this.error() ? `${id}-error` : null,
      ]
        .filter((v) => v !== null)
        .join(' ') || null
    );
  });

  constructor() {
    // Pinta el valor externo (carga, restauración, recarga) solo si no es el que acabamos de emitir.
    effect(() => {
      const valor = this.valor();
      const area = this.area().nativeElement;
      if (valor === this.ultimoEmitido) return;
      pintarHtmlSaneado(area, valor, (html) => new DOMParser().parseFromString(html, 'text/html'));
      this.ultimoEmitido = valor;
      this.palabras.set(contarPalabras(valor));
    });
  }

  protected alEditar(): void {
    const html = serializarHtmlSaneado(this.area().nativeElement);
    this.palabras.set(contarPalabras(html));
    if (html === this.ultimoEmitido) return;
    this.ultimoEmitido = html;
    this.cambio.emit(html);
  }

  protected alSalirArea(): void {
    this.guardarRango();
    this.salir.emit();
  }

  /** Pegar: solo texto (sin estilos ni etiquetas ajenas a RULE-022). */
  protected alPegar(evento: ClipboardEvent): void {
    evento.preventDefault();
    const texto = evento.clipboardData?.getData('text/plain') ?? '';
    if (texto !== '') this.documento.execCommand('insertText', false, texto);
    this.alEditar();
  }

  protected alTeclearArea(evento: KeyboardEvent): void {
    if (!(evento.ctrlKey || evento.metaKey)) return;
    const tecla = evento.key.toLowerCase();
    if (tecla === 'k') {
      evento.preventDefault();
      this.abrirPanel('enlace');
    } else if (tecla === 'b' || tecla === 'i') {
      evento.preventDefault();
      this.ejecutarAccion(tecla === 'b' ? 'negrita' : 'cursiva');
    }
  }

  /** Tabindex itinerante: flechas, Inicio y Fin dentro de la barra. */
  protected alTeclearBarra(evento: KeyboardEvent): void {
    const total = this.accionesBarra().length + 1;
    let destino: number | null = null;
    if (evento.key === 'ArrowRight') destino = (this.indiceFoco() + 1) % total;
    else if (evento.key === 'ArrowLeft') destino = (this.indiceFoco() - 1 + total) % total;
    else if (evento.key === 'Home') destino = 0;
    else if (evento.key === 'End') destino = total - 1;
    if (destino === null) return;
    evento.preventDefault();
    this.indiceFoco.set(destino);
    const controles = (evento.currentTarget as HTMLElement).querySelectorAll<HTMLElement>('.control-barra');
    controles[destino]?.focus();
  }

  protected aplicarBloque(evento: Event): void {
    const bloque = (evento.target as HTMLSelectElement).value as Bloque;
    this.enfocarArea();
    this.documento.execCommand('formatBlock', false, bloque);
    this.alEditar();
  }

  protected ejecutarAccion(id: string): void {
    if (this.soloLectura()) return;
    if (id === 'enlace' || id === 'glosario') {
      this.abrirPanel(id);
      return;
    }
    this.enfocarArea();
    const comandos: Readonly<Record<string, [string, string | undefined]>> = {
      negrita: ['bold', undefined],
      cursiva: ['italic', undefined],
      lista: ['insertUnorderedList', undefined],
      'lista-numerada': ['insertOrderedList', undefined],
      cita: ['formatBlock', 'blockquote'],
    };
    const [comando, valor] = comandos[id] ?? ['', undefined];
    if (comando !== '') this.documento.execCommand(comando, false, valor);
    this.alEditar();
  }

  protected aplicarEnlace(): void {
    const url = this.urlEnlace().trim();
    if (!esHrefPermitido(url)) {
      this.errorEnlace.set(MENSAJE_URL);
      return;
    }
    this.restaurarRango();
    const seleccion = this.documento.getSelection();
    if (seleccion === null || seleccion.rangeCount === 0 || seleccion.isCollapsed) {
      this.insertarEnlace(url, url, null);
    } else {
      this.documento.execCommand('createLink', false, url);
    }
    this.cerrarPanel();
    this.alEditar();
  }

  protected insertarTermino(termino: RefContenido): void {
    if (!esSlugValido(termino.slug)) return;
    this.restaurarRango();
    const seleccion = this.documento.getSelection();
    const texto = seleccion && !seleccion.isCollapsed ? seleccion.toString() : termino.titulo;
    this.insertarEnlace(`/glosario#${termino.slug}`, texto, termino.slug);
    this.cerrarPanel();
    this.alEditar();
  }

  protected cerrarPanel(): void {
    this.panel.set('ninguno');
    this.errorEnlace.set(null);
    this.enfocarArea();
    this.restaurarRango();
  }

  private abrirPanel(panel: Exclude<Panel, 'ninguno'>): void {
    this.guardarRango();
    this.urlEnlace.set('');
    this.errorEnlace.set(null);
    this.panel.set(panel);
    if (panel === 'enlace') queueMicrotask(() => this.campoUrl()?.nativeElement.focus());
  }

  /** Inserta un <a> con DOM (nunca HTML en texto) en la selección guardada o al final. */
  private insertarEnlace(href: string, texto: string, glosario: string | null): void {
    const area = this.area().nativeElement;
    const enlace = this.documento.createElement('a');
    enlace.setAttribute('href', href);
    if (glosario !== null) enlace.setAttribute('data-glosario', glosario);
    enlace.textContent = texto;
    const seleccion = this.documento.getSelection();
    const rango = seleccion && seleccion.rangeCount > 0 ? seleccion.getRangeAt(0) : null;
    if (rango !== null && area.contains(rango.commonAncestorContainer)) {
      rango.deleteContents();
      rango.insertNode(enlace);
      rango.setStartAfter(enlace);
      rango.collapse(true);
      seleccion?.removeAllRanges();
      seleccion?.addRange(rango);
    } else {
      const parrafo = this.documento.createElement('p');
      parrafo.appendChild(enlace);
      area.appendChild(parrafo);
    }
  }

  private enfocarArea(): void {
    this.area().nativeElement.focus();
  }

  private guardarRango(): void {
    const seleccion = this.documento.getSelection();
    if (seleccion === null || seleccion.rangeCount === 0) return;
    const rango = seleccion.getRangeAt(0);
    if (this.area().nativeElement.contains(rango.commonAncestorContainer)) {
      this.rangoGuardado = rango.cloneRange();
    }
  }

  private restaurarRango(): void {
    if (this.rangoGuardado === null) return;
    this.enfocarArea();
    const seleccion = this.documento.getSelection();
    seleccion?.removeAllRanges();
    seleccion?.addRange(this.rangoGuardado);
  }
}
