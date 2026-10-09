import { Component, ElementRef, computed, inject, input, output, signal, viewChild } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  ACEPTAR_ARCHIVOS,
  Medio,
  REGLAS_SUBIDA,
  ResultadoArchivo,
  TipoResultadoArchivo,
  mensajeResultado,
} from '../domain/medios';
import { SubidaMediosStore } from '../state/subida-medios.store';

/** Dónde se usa el componente (HANDOFF MediaUploader: biblioteca SCR-039 o pestaña de SCR-041). */
export type VarianteSubida = 'biblioteca' | 'selector';

const ETIQUETA_RESULTADO: Readonly<Record<TipoResultadoArchivo, string>> = {
  ACEPTADO: 'Aceptada',
  RECHAZADO: 'Rechazada',
  DUPLICADO: 'Duplicada',
};
const VARIANTE_RESULTADO: Readonly<Record<TipoResultadoArchivo, 'publicado' | 'rechazado' | 'pendiente'>> = {
  ACEPTADO: 'publicado',
  RECHAZADO: 'rechazado',
  DUPLICADO: 'pendiente',
};

/** Fila de la lista de resultados (sin condiciones de negocio en la plantilla, Regla 07). */
interface FilaResultado {
  readonly nombre: string;
  readonly resultado: TipoResultadoArchivo;
  readonly motivo: string | null;
  readonly etiqueta: string;
  readonly variante: 'publicado' | 'rechazado' | 'pendiente';
  readonly mensaje: string;
  /** Medio aceptado: enlace «Completar datos». */
  readonly completarId: number | null;
  /** Duplicado: «Usar la existente». */
  readonly existenteId: number | null;
}

function fila(r: ResultadoArchivo): FilaResultado {
  return {
    nombre: r.nombreArchivo,
    resultado: r.resultado,
    motivo: r.motivo,
    etiqueta: ETIQUETA_RESULTADO[r.resultado],
    variante: VARIANTE_RESULTADO[r.resultado],
    mensaje: mensajeResultado(r),
    completarId: r.resultado === 'ACEPTADO' ? (r.medio?.id ?? null) : null,
    existenteId: r.resultado === 'DUPLICADO' ? r.medioExistenteId : null,
  };
}

/**
 * MediaUploader (HANDOFF_UI_UX COMPONENTES; FLOW-013, FEAT-041, ALT-017/020/021). Botón visible
 * «Seleccionar imágenes» (el arrastre es opcional, WCAG 2.5.7), reglas visibles antes de subir,
 * validación previa en el cliente, progreso con <progress> y resultado por archivo persistente hasta
 * cerrarlo, con resumen en role=status. Tras subir: «Completar datos» de cada aceptada y «Usar la
 * existente» de cada duplicada. Sin conexión, la subida queda deshabilitada con el motivo.
 */
@Component({
  selector: 'app-subida-medios',
  imports: [RouterLink, Banner, Boton, Insignia],
  providers: [SubidaMediosStore],
  template: `
    <section class="subida" [attr.aria-labelledby]="idBase() + '-titulo'" [attr.data-testid]="'subida-' + variante()">
      <h2 class="titulo" [id]="idBase() + '-titulo'">Subir imágenes</h2>
      <p class="ayuda" [id]="idBase() + '-reglas'" data-testid="subida-reglas">{{ reglas }}</p>
      <div
        class="zona"
        [class.arrastrando]="arrastrando()"
        (dragover)="alArrastrar($event)"
        (dragleave)="arrastrando.set(false)"
        (drop)="alSoltar($event)"
      >
        <input
          #entrada
          type="file"
          class="oculto"
          tabindex="-1"
          aria-hidden="true"
          multiple
          [accept]="aceptar"
          [id]="idBase() + '-archivos'"
          data-testid="subida-archivos"
          (change)="alElegir($event)"
        />
        <button
          type="button"
          appBoton
          [cargando]="store.subiendo()"
          [deshabilitadoEnfocable]="!enLinea()"
          [attr.aria-describedby]="idBase() + '-reglas' + (enLinea() ? '' : ' ' + idBase() + '-offline')"
          data-testid="subida-seleccionar"
          (click)="abrirSelector()"
        >
          {{ store.subiendo() ? 'Subiendo…' : 'Seleccionar imágenes' }}
        </button>
        <p class="ayuda">o arrastra las imágenes hasta aquí.</p>
        @if (!enLinea()) {
          <p class="ayuda" [id]="idBase() + '-offline'" data-testid="subida-sin-conexion">
            Sin conexión: podrás subir imágenes cuando vuelva.
          </p>
        }
      </div>

      @if (store.subiendo()) {
        <div class="progreso" data-testid="subida-progreso">
          <label [for]="idBase() + '-progreso'">Subiendo… {{ store.porcentaje() }} %</label>
          <progress [id]="idBase() + '-progreso'" max="100" [value]="store.porcentaje()"></progress>
        </div>
      }

      @if (store.errorSeleccion(); as mensaje) {
        <app-banner variante="error" testId="subida-error-seleccion">{{ mensaje }}</app-banner>
      }
      @if (store.errorEnvio(); as error) {
        <app-banner variante="error" testId="subida-error-envio">
          {{ error.mensaje }}
          <button banner-accion type="button" class="boton-enlace" data-testid="subida-reintentar" (click)="reintentar()">
            Reintentar
          </button>
        </app-banner>
      }

      <p class="bs-solo-lectores" role="status" data-testid="subida-anuncio">{{ store.resumen() }}</p>

      @if (store.hayResultados()) {
        <div class="resultados" data-testid="subida-resultados">
          <p class="resumen" data-testid="subida-resumen">{{ store.resumen() }}</p>
          <ul>
            @for (f of filas(); track $index) {
              <li class="resultado" [attr.data-testid]="'subida-resultado-' + $index" [attr.data-resultado]="f.resultado" [attr.data-motivo]="f.motivo">
                <span class="nombre">{{ f.nombre }}</span>
                <app-insignia [variante]="f.variante">{{ f.etiqueta }}</app-insignia>
                <span class="mensaje">{{ f.mensaje }}</span>
                @if (f.completarId; as id) {
                  @if (variante() === 'biblioteca') {
                    <a [routerLink]="['/panel/medios', id]" data-testid="subida-completar">Completar datos</a>
                  } @else {
                    <a [routerLink]="['/panel/medios', id]" target="_blank" rel="noopener" data-testid="subida-completar"
                      >Completar datos <span class="bs-solo-lectores">(se abre en otra pestaña)</span></a
                    >
                  }
                }
                @if (f.existenteId; as existente) {
                  @if (variante() === 'biblioteca') {
                    <a [routerLink]="['/panel/medios', existente]" data-testid="subida-usar-existente">Usar la existente</a>
                  } @else {
                    <button type="button" class="boton-enlace" data-testid="subida-usar-existente" (click)="usarExistente.emit(existente)">
                      Usar la existente
                    </button>
                  }
                }
              </li>
            }
          </ul>
          <button type="button" appBoton variante="secondary" tamano="sm" data-testid="subida-cerrar-resultados" (click)="store.cerrarResultados()">
            Cerrar resultados
          </button>
        </div>
      }
    </section>
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .subida {
      display: grid;
      gap: var(--bs-space-3);
    }
    .titulo {
      font-size: var(--bs-typography-h3-font-size);
    }
    .zona {
      display: grid;
      justify-items: start;
      gap: var(--bs-space-2);
      padding: var(--bs-space-5);
      border: var(--bs-border-width-strong) dashed var(--bs-color-border-control);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-bg-surface);
    }
    .arrastrando {
      border-color: var(--bs-color-border-brand);
      background: var(--bs-color-bg-brand-faint);
    }
    .oculto {
      display: none;
    }
    .progreso {
      display: grid;
      gap: var(--bs-space-1);
    }
    progress {
      width: 100%;
      height: 0.75rem;
      accent-color: var(--bs-color-action-primary-bg);
    }
    .resultados ul {
      display: grid;
      gap: var(--bs-space-2);
      margin: 0 0 var(--bs-space-3);
      padding: 0;
      list-style: none;
    }
    .resultados .resumen {
      font-weight: var(--bs-font-weight-semibold);
    }
    .resultado {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-2) var(--bs-space-3);
      padding: var(--bs-space-2) var(--bs-space-3);
      border: var(--bs-border-width-hairline) solid var(--bs-color-border-subtle);
      border-radius: var(--bs-radius-sm);
      background: var(--bs-color-bg-surface);
    }
    .nombre {
      font-weight: var(--bs-font-weight-semibold);
      overflow-wrap: anywhere;
    }
    .mensaje {
      flex: 1 1 12rem;
    }
  `,
})
export class SubidaMedios {
  protected readonly store = inject(SubidaMediosStore);
  protected readonly enLinea = inject(Conectividad).enLinea;

  readonly variante = input<VarianteSubida>('biblioteca');
  /** Prefijo de los id del DOM (único por instancia en la página). */
  readonly idBase = input('subida');
  /** Medios aceptados en una subida (PENDIENTE_METADATOS): quien lo usa recarga su listado. */
  readonly subidos = output<readonly Medio[]>();
  /** «Usar la existente» de un duplicado (solo en el selector). */
  readonly usarExistente = output<number>();

  private readonly entrada = viewChild.required<ElementRef<HTMLInputElement>>('entrada');

  protected readonly reglas = REGLAS_SUBIDA;
  protected readonly aceptar = ACEPTAR_ARCHIVOS;
  protected readonly filas = computed(() => this.store.resultados().map(fila));
  protected readonly arrastrando = signal(false);
  protected readonly bloqueado = computed(() => this.store.subiendo() || !this.enLinea());

  protected abrirSelector(): void {
    if (this.bloqueado()) return;
    this.entrada().nativeElement.click();
  }

  protected async alElegir(evento: Event): Promise<void> {
    const control = evento.target as HTMLInputElement;
    const archivos = Array.from(control.files ?? []);
    // Permite volver a elegir el mismo archivo (si no, el navegador no emite `change`).
    control.value = '';
    await this.subir(archivos);
  }

  protected alArrastrar(evento: DragEvent): void {
    evento.preventDefault();
    if (!this.bloqueado()) this.arrastrando.set(true);
  }

  protected async alSoltar(evento: DragEvent): Promise<void> {
    evento.preventDefault();
    this.arrastrando.set(false);
    await this.subir(Array.from(evento.dataTransfer?.files ?? []));
  }

  protected async reintentar(): Promise<void> {
    const error = await this.store.reintentar();
    this.notificar(error === null);
  }

  private async subir(archivos: readonly File[]): Promise<void> {
    if (this.bloqueado() || archivos.length === 0) return;
    const error = await this.store.seleccionar(archivos);
    this.notificar(error === null);
  }

  private notificar(exito: boolean): void {
    const aceptados = this.store.aceptados();
    if (exito && aceptados.length > 0) this.subidos.emit(aceptados);
  }
}
