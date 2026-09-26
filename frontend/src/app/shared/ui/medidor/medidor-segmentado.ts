import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { normalizarNivel, segmentos, textoAccesible } from './medidor';

/**
 * Medidor segmentado accesible (base de DifficultyMeter y BudgetMeter, DEC-AUTO-063).
 * Los segmentos son decorativos (aria-hidden); el texto «N de M: etiqueta» es el equivalente
 * accesible y visible. Segmentos llenos con action.primary-bg; vacíos con border.control (≥3:1).
 */
@Component({
  selector: 'app-medidor-segmentado',
  imports: [RouterLink],
  template: `
    <span class="medidor" [class.medidor--compacto]="compacto()" [attr.data-testid]="testId()">
      <span class="segmentos" aria-hidden="true">
        @for (s of segmentos(); track s.indice) {
          <span class="segmento" [class.segmento--lleno]="s.lleno"></span>
        }
      </span>
      <span class="bs-solo-lectores">{{ textoAccesible() }}</span>
      <span class="valor" aria-hidden="true">
        {{ nivel() === null ? '—' : nivel() + '/' + maximo() }}
        @if (!compacto() && etiqueta()) {
          <span class="etiqueta">{{ etiqueta() }}</span>
        }
      </span>
      @if (!compacto() && enlaceEscala()) {
        <a class="explicacion" [routerLink]="rutaEscala()" [fragment]="fragmentoEscala()">¿Qué significa?</a>
      }
    </span>
  `,
  styles: `
    .medidor {
      display: inline-flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-2);
      font-size: var(--bs-typography-body-sm-font-size);
      line-height: var(--bs-typography-body-sm-line-height);
    }
    .segmentos {
      display: inline-flex;
      gap: 0.1875rem;
    }
    .segmento {
      width: 0.75rem;
      height: 0.5rem;
      border-radius: 2px;
      border: 1px solid var(--bs-color-border-control);
      background: transparent;
    }
    .segmento--lleno {
      border-color: var(--bs-color-action-primary-bg);
      background: var(--bs-color-action-primary-bg);
    }
    .valor {
      font-weight: var(--bs-font-weight-semibold);
      font-variant-numeric: tabular-nums;
    }
    .etiqueta {
      font-weight: var(--bs-font-weight-regular);
      margin-inline-start: var(--bs-space-1);
    }
    .explicacion {
      display: inline-flex;
      align-items: center;
      min-height: var(--bs-size-target-min);
    }
    @media (forced-colors: active) {
      .segmento--lleno { background: CanvasText; }
    }
  `,
})
export class MedidorSegmentado {
  readonly concepto = input.required<string>();
  readonly maximo = input.required<number>();
  readonly valor = input<number | null>(null);
  /** Etiqueta del nivel según la escala (DATA-020), p. ej. «Exigente». */
  readonly etiqueta = input<string | null>(null);
  readonly compacto = input(false);
  /** Ancla de la escala en /acerca-de (p. ej. `escala-de-dificultad`); vacío = sin enlace. */
  readonly enlaceEscala = input<string | null>(null);
  readonly testId = input('medidor');

  protected readonly nivel = computed(() => normalizarNivel(this.valor(), this.maximo()));
  protected readonly segmentos = computed(() => segmentos(this.nivel(), this.maximo()));
  protected readonly textoAccesible = computed(() =>
    textoAccesible(this.concepto(), this.nivel(), this.maximo(), this.etiqueta()),
  );
  protected readonly rutaEscala = computed(() => '/acerca-de');
  protected readonly fragmentoEscala = computed(() => this.enlaceEscala() ?? undefined);
}
