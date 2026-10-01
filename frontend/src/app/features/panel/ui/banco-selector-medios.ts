import { Component, computed, signal } from '@angular/core';

import { Boton } from '../../../shared/ui/boton/boton';
import { Medio, nombreMedio } from '../domain/medios';
import { SelectorMedios } from './selector-medios';

/**
 * Banco de pruebas del Selector de medios (SCR-041), SOLO en desarrollo (DEC-DEV-022-01): la ruta
 * se registra con `isDevMode()` en panel.routes.ts y no existe en producción. Sirve de documentación
 * viva de la API del componente (Skill_UI_UX §23) y de anfitrión para sus E2E de accesibilidad en
 * los 3 motores hasta que exista su pantalla real (SCR-036, TKT-023). Monta los dos modos.
 */
@Component({
  selector: 'app-banco-selector-medios',
  imports: [Boton, SelectorMedios],
  template: `
    <div class="pagina" data-testid="banco-selector">
      <h1 tabindex="-1">Banco de pruebas del selector de medios</h1>
      <p>Solo en desarrollo. Abre el selector en cada modo y comprueba la selección devuelta.</p>
      <div class="acciones">
        <button type="button" appBoton data-testid="banco-abrir-varios" (click)="abiertoVarios.set(true)">
          Elegir imágenes
        </button>
        <button type="button" appBoton variante="secondary" data-testid="banco-abrir-uno" (click)="abiertoUno.set(true)">
          Elegir portada
        </button>
      </div>
      <section aria-labelledby="banco-resultado-titulo">
        <h2 id="banco-resultado-titulo">Selección devuelta</h2>
        <p role="status" data-testid="banco-estado">{{ estado() }}</p>
        <ol data-testid="banco-resultado">
          @for (nombre of nombres(); track $index) {
            <li>{{ nombre }}</li>
          }
        </ol>
      </section>
    </div>
    <app-selector-medios
      [(abierto)]="abiertoVarios"
      modo="varios"
      titulo="Elegir imágenes"
      idBase="banco-varios"
      [seleccionInicial]="resultado()"
      (confirmar)="alConfirmar($event)"
      (cancelado)="estado.set('Selección cancelada.')"
    />
    <app-selector-medios
      [(abierto)]="abiertoUno"
      modo="uno"
      titulo="Elegir portada"
      idBase="banco-uno"
      (confirmar)="alConfirmar($event)"
      (cancelado)="estado.set('Selección cancelada.')"
    />
  `,
  styles: `
    .pagina {
      display: grid;
      gap: var(--bs-space-4);
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      gap: var(--bs-space-3);
    }
  `,
})
export class BancoSelectorMedios {
  protected readonly abiertoVarios = signal(false);
  protected readonly abiertoUno = signal(false);
  protected readonly resultado = signal<readonly Medio[]>([]);
  protected readonly estado = signal('Aún no se eligió nada.');
  protected readonly nombres = computed(() => this.resultado().map(nombreMedio));

  protected alConfirmar(medios: readonly Medio[]): void {
    this.resultado.set(medios);
    this.estado.set(medios.length === 1 ? 'Se eligió 1 imagen.' : `Se eligieron ${medios.length} imágenes.`);
  }
}
