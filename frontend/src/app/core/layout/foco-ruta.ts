import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { DestroyRef, Injectable, Injector, PLATFORM_ID, afterNextRender, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { ID_CONTENIDO_PRINCIPAL } from './navegacion';

/**
 * Gestión del foco al cambiar de ruta (ACCESSIBILITY_SPEC.Focus_Management): tras cada navegación
 * interna (no en la carga inicial) el foco va al h1 de la vista (tabindex=-1), de modo que el lector
 * de pantalla anuncia el nuevo título; si no hay h1, al contenido principal.
 */
@Injectable({
  providedIn: 'root',
})
export class FocoRuta {
  private readonly router = inject(Router);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly destroyRef = inject(DestroyRef);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));
  private iniciado = false;

  iniciar(): void {
    if (!this.esNavegador || this.iniciado) return;
    this.iniciado = true;
    let primera = true;
    const suscripcion = this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(() => {
        if (primera) {
          primera = false;
          return;
        }
        afterNextRender(() => this.enfocarVista(), { injector: this.injector });
      });
    this.destroyRef.onDestroy(() => suscripcion.unsubscribe());
  }

  enfocarVista(): void {
    const principal = this.documento.getElementById(ID_CONTENIDO_PRINCIPAL);
    if (principal === null) return;
    const destino = principal.querySelector<HTMLElement>('h1') ?? principal;
    if (!destino.hasAttribute('tabindex')) destino.setAttribute('tabindex', '-1');
    destino.focus({ preventScroll: false });
  }
}
