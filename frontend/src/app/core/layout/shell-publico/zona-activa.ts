import { Location } from '@angular/common';
import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import {
  NavigationCancel,
  NavigationEnd,
  NavigationError,
  NavigationSkipped,
  ResolveEnd,
  Router,
} from '@angular/router';

import { Zona, zonaDeEstado, zonaDeUrl } from './zona';

/**
 * Zona que App está pintando (ShellPublico o el armazón del panel) y zona de destino de la
 * navegación en curso (TKT-010, QA ciclo 2 HALLAZGO-ZONA).
 *
 * La zona NO cambia al empezar la navegación: la cambia ZonaOutlet en el instante en que el router
 * activa una ruta de la otra zona, así que la página saliente sigue en su armazón mientras se
 * comprueban guards, se resuelven datos y se descargan fragmentos, y el outlet de la zona entrante
 * nace con la ruta nueva ya registrada (no vuelve a montar la saliente).
 */
@Injectable({ providedIn: 'root' })
export class ZonaActiva {
  private readonly _zona = signal<Zona>(zonaDeUrl(inject(Location).path()));
  /** Zona de la navegación que ya pasó guards y resolvers (null fuera de una navegación). */
  private destino: Zona | null = null;

  readonly zona = this._zona.asReadonly();

  constructor() {
    const suscripcion = inject(Router).events.subscribe((evento) => {
      if (evento instanceof ResolveEnd) {
        this.destino = zonaDeEstado(evento.state.root);
      } else if (
        evento instanceof NavigationEnd ||
        evento instanceof NavigationCancel ||
        evento instanceof NavigationError ||
        evento instanceof NavigationSkipped
      ) {
        this.destino = null;
      }
    });
    inject(DestroyRef).onDestroy(() => suscripcion.unsubscribe());
  }

  /** La navegación que se está activando sale de `zona` hacia la otra. */
  saliendoDe(zona: Zona): boolean {
    return this.destino !== null && this.destino !== zona;
  }

  /** Lo llama ZonaOutlet cuando el router activa una ruta de la otra zona. */
  cambiarA(zona: Zona): void {
    this._zona.set(zona);
  }
}
