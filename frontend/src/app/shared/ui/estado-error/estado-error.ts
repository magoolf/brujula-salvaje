import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Boton } from '../boton/boton';
import { Icono } from '../icono/icono';

/**
 * ErrorState (ST-ERROR, HANDOFF_UI_UX): mensaje comprensible, «Reintentar» y enlace a Inicio
 * (panel: Tablero). Nunca trazas ni códigos técnicos. role=alert solo si aparece como resultado
 * de una acción del usuario (`anunciar`).
 */
@Component({
  selector: 'app-estado-error',
  imports: [RouterLink, Boton, Icono],
  template: `
    <div class="error" [attr.role]="anunciar() ? 'alert' : null" [attr.data-testid]="testId()">
      <app-icono nombre="circle-alert" [tamano]="24" />
      <div class="cuerpo">
        <p class="titulo">{{ titulo() }}</p>
        <p>{{ mensaje() }}</p>
        <div class="acciones">
          <button type="button" appBoton variante="secondary" [cargando]="reintentando()"
                  data-testid="estado-error-reintentar" (click)="reintentar.emit()">
            <app-icono nombre="refresh-cw" [tamano]="20" />
            {{ reintentando() ? 'Reintentando…' : 'Reintentar' }}
          </button>
          <a [routerLink]="rutaSalida()">{{ etiquetaSalida() }}</a>
        </div>
      </div>
    </div>
  `,
  styles: `
    .error {
      display: flex;
      gap: var(--bs-space-3);
      padding: var(--bs-space-4);
      border-radius: var(--bs-radius-md);
      background: var(--bs-color-status-error-bg);
      color: var(--bs-color-status-error-fg);
    }
    .cuerpo {
      display: grid;
      gap: var(--bs-space-2);
      color: var(--bs-color-text-default);
    }
    .titulo {
      font-weight: var(--bs-font-weight-bold);
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--bs-space-4);
    }
  `,
})
export class EstadoError {
  readonly titulo = input('No pudimos cargar esta sección');
  readonly mensaje = input('Vuelve a intentarlo en unos segundos.');
  readonly reintentando = input(false);
  readonly anunciar = input(false);
  readonly rutaSalida = input('/');
  readonly etiquetaSalida = input('Ir al inicio');
  readonly testId = input('estado-error');
  readonly reintentar = output<void>();
}
