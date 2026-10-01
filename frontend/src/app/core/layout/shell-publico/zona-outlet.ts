import {
  ComponentRef,
  Directive,
  EnvironmentInjector,
  OnDestroy,
  ViewContainerRef,
  inject,
  input,
} from '@angular/core';
import { ActivatedRoute, RouterOutlet } from '@angular/router';

import { Zona, zonaDeRuta } from './zona';
import { ZonaActiva } from './zona-activa';

/**
 * router-outlet ligado a una zona (TKT-010, QA ciclo 2 HALLAZGO-ZONA). Se usa en lugar de
 * RouterOutlet en el contenedor de cada zona (ShellPublico, App en la zona del panel y los
 * armazones del panel) con `<router-outlet appZona="publico|panel" />`.
 *
 * Al cruzar de zona, en la misma activación síncrona del router:
 * - deactivate(): la página saliente NO se destruye; se queda montada en su armazón hasta que App
 *   retira la zona entera en el siguiente render (nunca hay un cuadro con el armazón vacío);
 * - activateWith() con una ruta de la otra zona: no crea el componente aquí (sería el armazón
 *   equivocado); cambia la zona y el router-outlet de la zona entrante, al nacer, activa esa ruta,
 *   que ya es la registrada en el contexto. La ruta saliente no se vuelve a montar ni repite sus
 *   peticiones, y nunca conviven dos armazones ni dos <main>.
 * Dentro de una misma zona se comporta exactamente como RouterOutlet.
 */
@Directive({
  selector: 'router-outlet[appZona]',
})
export class ZonaOutlet extends RouterOutlet implements OnDestroy {
  readonly zona = input.required<Zona>({ alias: 'appZona' });

  private readonly zonaActiva = inject(ZonaActiva);
  private readonly contenedor = inject(ViewContainerRef);
  /** Página saliente de un cruce de zona, visible hasta que se retire este outlet. */
  private saliente: ComponentRef<unknown> | null = null;

  override activateWith(ruta: ActivatedRoute, inyector: EnvironmentInjector): void {
    const zona = zonaDeRuta(ruta.snapshot);
    if (zona !== this.zona()) {
      this.zonaActiva.cambiarA(zona);
      return;
    }
    this.retirarSaliente();
    super.activateWith(ruta, inyector);
  }

  override deactivate(): void {
    if (!this.zonaActiva.saliendoDe(this.zona())) {
      this.retirarSaliente();
      super.deactivate();
      return;
    }
    // Una ruta sin componente (p. ej. `panel`, con loadChildren) comparte el contexto del outlet con
    // su hija, así que el router puede desactivar este outlet dos veces en el mismo cruce: la
    // segunda no debe retirar la página que se está conservando.
    if (!this.isActivated) return;
    const instancia = this.component;
    // detach() libera el outlet para el router; la vista se reinserta en el acto (sin pintar entre
    // medias) para que la página siga visible hasta que la zona entrante la sustituya.
    const ref = this.detach();
    this.contenedor.insert(ref.hostView);
    this.saliente = ref;
    this.deactivateEvents.emit(instancia);
  }

  override ngOnDestroy(): void {
    this.retirarSaliente();
    super.ngOnDestroy();
  }

  private retirarSaliente(): void {
    this.saliente?.destroy();
    this.saliente = null;
  }
}
