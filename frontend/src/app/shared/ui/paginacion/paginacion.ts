import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icono } from '../icono/icono';
import { calcularPaginas, normalizarPagina, normalizarTotal } from './paginas';

/**
 * Pagination (HANDOFF_UI_UX): enlaces reales con `?pagina=` (funcionan sin JS y con SSR),
 * conservando el resto de parámetros de la URL (filtros, RULE-019). La página 1 no lleva parámetro.
 * < sm: solo «Anterior · Página X de Y · Siguiente».
 */
@Component({
  selector: 'app-paginacion',
  imports: [RouterLink, Icono],
  template: `
    @if (total() > 1) {
      <nav aria-label="Paginación" class="paginacion" data-testid="paginacion">
        @if (actual() > 1) {
          <a class="control" [routerLink]="[]" [queryParams]="parametros(actual() - 1)" queryParamsHandling="merge"
             rel="prev" data-testid="paginacion-anterior">
            <app-icono nombre="chevron-left" [tamano]="16" /><span>Anterior</span>
          </a>
        } @else {
          <span class="control control--inactivo" aria-disabled="true">
            <app-icono nombre="chevron-left" [tamano]="16" /><span>Anterior</span>
          </span>
        }

        <ol class="numeros">
          @for (el of elementos(); track el.tipo === 'pagina' ? el.numero : el.clave) {
            <li>
              @if (el.tipo === 'pagina') {
                @if (el.numero === actual()) {
                  <a class="numero numero--actual" aria-current="page" [routerLink]="[]"
                     [queryParams]="parametros(el.numero)" queryParamsHandling="merge"
                     [attr.aria-label]="'Página ' + el.numero">{{ el.numero }}</a>
                } @else {
                  <a class="numero" [routerLink]="[]" [queryParams]="parametros(el.numero)" queryParamsHandling="merge"
                     [attr.aria-label]="'Página ' + el.numero">{{ el.numero }}</a>
                }
              } @else {
                <span class="elipsis" aria-hidden="true">…</span>
              }
            </li>
          }
        </ol>
        <span class="resumen">Página {{ actual() }} de {{ total() }}</span>

        @if (actual() < total()) {
          <a class="control" [routerLink]="[]" [queryParams]="parametros(actual() + 1)" queryParamsHandling="merge"
             rel="next" data-testid="paginacion-siguiente">
            <span>Siguiente</span><app-icono nombre="chevron-right" [tamano]="16" />
          </a>
        } @else {
          <span class="control control--inactivo" aria-disabled="true">
            <span>Siguiente</span><app-icono nombre="chevron-right" [tamano]="16" />
          </span>
        }
      </nav>
    }
  `,
  styles: `
    .paginacion {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: var(--bs-space-2);
    }
    .numeros {
      display: none;
      gap: var(--bs-space-1);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .control,
    .numero,
    .elipsis {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: var(--bs-space-1);
      min-width: var(--bs-size-target);
      min-height: var(--bs-size-target);
      padding-inline: var(--bs-space-2);
      box-sizing: border-box;
      border-radius: var(--bs-radius-md);
      font-variant-numeric: tabular-nums;
    }
    .numero--actual {
      background: var(--bs-color-action-primary-bg);
      color: var(--bs-color-action-primary-fg);
      text-decoration: none;
      font-weight: var(--bs-font-weight-bold);
    }
    .control--inactivo {
      color: var(--bs-color-text-disabled);
    }
    .resumen {
      font-variant-numeric: tabular-nums;
    }
    @media (min-width: 30rem) {
      .numeros { display: flex; }
      .resumen { display: none; }
    }
  `,
})
export class Paginacion {
  readonly paginaActual = input.required<number>();
  readonly totalPaginas = input.required<number>();

  protected readonly total = computed(() => normalizarTotal(this.totalPaginas()));
  protected readonly actual = computed(() => normalizarPagina(this.paginaActual(), this.total()));
  protected readonly elementos = computed(() => calcularPaginas(this.actual(), this.total()));

  protected parametros(numero: number): Record<string, number | null> {
    return { pagina: numero === 1 ? null : numero };
  }
}
