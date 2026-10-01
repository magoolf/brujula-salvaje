import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  model,
  output,
  signal,
  untracked,
  viewChild,
} from '@angular/core';

import { Conectividad } from '../../../core/layout/conectividad';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import {
  Medio,
  ModoSeleccion,
  anuncioMovimiento,
  derivadoPara,
  nombreMedio,
  textoAnadir,
  textoRecuentoSeleccion,
} from '../domain/medios';
import { SelectorMediosStore } from '../state/selector-medios.store';
import { EnlaceValor } from './enlace-valor';
import { MosaicoMedio } from './mosaico-medio';
import { SubidaMedios } from './subida-medios';

type Pestana = 'biblioteca' | 'subir';
const PESTANAS: readonly Pestana[] = ['biblioteca', 'subir'];
/** Elementos que pueden recibir el foco con Tab dentro del diálogo. */
const ENFOCABLES =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]):not([tabindex="-1"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * SCR-041 Selector de medios (FEAT-034/041, FLOW-011/013, RULE-005). Diálogo modal reutilizable
 * por el editor de contenidos (TKT-023) y los destacados de inicio (TKT-024).
 *
 * API estable:
 * ```html
 * <app-selector-medios
 *   [(abierto)]="selectorAbierto"          // boolean: abre/cierra el diálogo
 *   modo="varios"                          // 'uno' (radios, p. ej. portada) | 'varios' (casillas, galería)
 *   [seleccionInicial]="galeria()"         // readonly Medio[]: selección de partida (en su orden)
 *   [maximo]="null"                        // número máximo en modo 'varios' (null = sin límite)
 *   [permitirNoDisponibles]="false"        // true: también PENDIENTE_METADATOS (nunca RETIRADO)
 *   titulo="Elegir imágenes"               // título visible del diálogo
 *   (confirmar)="alElegir($event)"         // readonly Medio[] en el orden de la bandeja; luego se cierra
 *   (cancelado)="..."                      // Cancelar, «Cerrar» o Escape (también se cierra)
 * />
 * ```
 * Accesibilidad: <dialog> modal (resto inerte), foco atrapado (Tab y Mayús+Tab circulan dentro),
 * Escape cancela, el foco vuelve al control que lo abrió; pestañas ARIA con flechas/Inicio/Fin;
 * modo 'varios' con casillas y modo 'uno' con radios en un radiogroup (Espacio selecciona); recuento
 * de la selección en role=status; bandeja ordenable con «Subir»/«Bajar» (alternativa sin arrastre,
 * WCAG 2.5.7) y anuncio de cada movimiento. Los medios no seleccionables se ven con su motivo.
 */
@Component({
  selector: 'app-selector-medios',
  imports: [Boton, EstadoCargando, EstadoError, EnlaceValor, MosaicoMedio, SubidaMedios],
  providers: [SelectorMediosStore],
  host: { '(keydown)': 'atraparFoco($event)' },
  templateUrl: './selector-medios.html',
  styleUrls: ['./panel-formularios.css', './selector-medios.css'],
})
export class SelectorMedios {
  protected readonly store = inject(SelectorMediosStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);

  readonly abierto = model(false);
  readonly modo = input<ModoSeleccion>('varios');
  readonly seleccionInicial = input<readonly Medio[]>([]);
  readonly maximo = input<number | null>(null);
  readonly permitirNoDisponibles = input(false);
  readonly titulo = input('Elegir imágenes');
  /** Prefijo de los id del DOM (único si hay varios selectores en la página). */
  readonly idBase = input('selector-medios');
  readonly confirmar = output<readonly Medio[]>();
  readonly cancelado = output<void>();

  private readonly dialogo = viewChild.required<ElementRef<HTMLDialogElement>>('dialogo');
  private readonly busqueda = viewChild<ElementRef<HTMLInputElement>>('busqueda');
  private origen: HTMLElement | null = null;

  protected readonly pestanas = PESTANAS;
  protected readonly pestana = signal<Pestana>('biblioteca');
  protected readonly anuncio = signal('');
  protected readonly errorExistente = signal<string | null>(null);
  protected readonly q = linkedSignal(() => this.store.filtros().q);
  protected readonly licencia = linkedSignal<string>(() => this.store.filtros().licencia ?? '');
  protected readonly soloDisponibles = linkedSignal<string>(() =>
    this.store.filtros().estado === 'DISPONIBLE' ? 'si' : 'no',
  );

  protected readonly tipoControl = computed(() => (this.modo() === 'uno' ? 'radio' : 'casilla'));
  protected readonly recuento = computed(() => textoRecuentoSeleccion(this.store.seleccion().length));
  protected readonly textoAnadir = computed(() =>
    textoAnadir(this.store.seleccion().length, this.modo()),
  );
  protected readonly bandeja = computed(() =>
    this.store.seleccion().map((m) => ({
      medio: m,
      nombre: nombreMedio(m),
      miniatura: derivadoPara(m.derivados, 160)?.url ?? null,
    })),
  );

  constructor() {
    effect(() => {
      const abierto = this.abierto();
      untracked(() => (abierto ? this.abrir() : this.cerrarDialogo()));
    });
  }

  protected etiquetaPestana(pestana: Pestana): string {
    return pestana === 'biblioteca' ? 'Biblioteca' : 'Subir';
  }

  protected seleccionado(medio: Medio): boolean {
    return this.store.idsSeleccionados().has(medio.id);
  }

  protected alternar(medio: Medio): void {
    this.store.alternar(medio);
  }

  protected elegirPestana(pestana: Pestana, enfocar = false): void {
    this.pestana.set(pestana);
    if (enfocar) this.documento.getElementById(`${this.idBase()}-tab-${pestana}`)?.focus();
  }

  /** Pestañas ARIA: flechas, Inicio y Fin (activación automática). */
  protected alTeclearPestana(evento: KeyboardEvent): void {
    const indice = PESTANAS.indexOf(this.pestana());
    let destino: number | null = null;
    if (evento.key === 'ArrowRight') destino = (indice + 1) % PESTANAS.length;
    else if (evento.key === 'ArrowLeft') destino = (indice - 1 + PESTANAS.length) % PESTANAS.length;
    else if (evento.key === 'Home') destino = 0;
    else if (evento.key === 'End') destino = PESTANAS.length - 1;
    if (destino === null) return;
    evento.preventDefault();
    this.elegirPestana(PESTANAS[destino], true);
  }

  protected buscar(evento: Event): void {
    evento.preventDefault();
    this.store.filtrar({
      q: this.q().trim().slice(0, 100),
      licencia: this.licencia() === '' ? null : this.licencia(),
      estado: this.soloDisponibles() === 'si' ? 'DISPONIBLE' : null,
    });
  }

  protected mover(indice: number, desplazamiento: number): void {
    const total = this.store.seleccion().length;
    const destino = indice + desplazamiento;
    if (destino < 0 || destino >= total) return;
    const nombre = nombreMedio(this.store.seleccion()[indice]);
    this.store.moverSeleccion(indice, destino);
    this.anuncio.set(anuncioMovimiento(nombre, destino + 1, total));
    // El foco sigue al botón pulsado en la nueva posición del elemento (tras pintarla).
    const id = `${this.idBase()}-mover-${desplazamiento < 0 ? 'antes' : 'despues'}-${destino}`;
    afterNextRender(() => this.documento.getElementById(id)?.focus(), { injector: this.injector });
  }

  protected quitar(medio: Medio): void {
    this.store.quitar(medio.id);
    this.anuncio.set(`${nombreMedio(medio)} quitada de la selección.`);
  }

  protected alSubir(): void {
    this.store.recargar();
  }

  protected async usarExistente(id: number): Promise<void> {
    this.errorExistente.set(null);
    const error = await this.store.usarExistente(id);
    if (error !== null) {
      this.errorExistente.set(error.mensaje);
      return;
    }
    this.anuncio.set('Se seleccionó la imagen que ya estaba en la biblioteca.');
    this.elegirPestana('biblioteca', true);
  }

  protected anadir(): void {
    if (this.store.seleccion().length === 0 || !this.enLinea()) return;
    this.confirmar.emit(this.store.seleccion());
    this.abierto.set(false);
  }

  protected cancelar(): void {
    this.cancelado.emit();
    this.abierto.set(false);
  }

  /** Escape (evento cancel del <dialog>): cancela sin cerrar «a pelo» el diálogo nativo. */
  protected alCancelar(evento: Event): void {
    evento.preventDefault();
    this.cancelar();
  }

  /** Foco atrapado: Tab en el último salta al primero y Mayús+Tab en el primero, al último. */
  protected atraparFoco(evento: KeyboardEvent): void {
    if (evento.key !== 'Tab') return;
    const enfocables = Array.from(
      this.dialogo().nativeElement.querySelectorAll<HTMLElement>(ENFOCABLES),
    ).filter((el) => el.getClientRects().length > 0 && !el.closest('[hidden]'));
    if (enfocables.length === 0) return;
    const primero = enfocables[0];
    const ultimo = enfocables[enfocables.length - 1];
    const activo = this.documento.activeElement;
    if (evento.shiftKey && (activo === primero || !this.dialogo().nativeElement.contains(activo))) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && activo === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }

  private abrir(): void {
    const dialogo = this.dialogo().nativeElement;
    if (dialogo.open) return;
    this.origen = this.documento.activeElement as HTMLElement | null;
    this.pestana.set('biblioteca');
    this.anuncio.set('');
    this.errorExistente.set(null);
    this.store.abrir({
      modo: this.modo(),
      maximo: this.maximo(),
      permitirNoDisponibles: this.permitirNoDisponibles(),
      seleccionInicial: this.seleccionInicial(),
    });
    dialogo.showModal();
    this.busqueda()?.nativeElement.focus();
  }

  private cerrarDialogo(): void {
    const dialogo = this.dialogo().nativeElement;
    if (!dialogo.open) return;
    dialogo.close();
    this.store.cerrar();
    this.origen?.focus();
    this.origen = null;
  }
}
