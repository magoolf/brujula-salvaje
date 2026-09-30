import { isPlatformBrowser } from '@angular/common';
import { Component, PLATFORM_ID, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import {
  ElementoGuardado,
  rutaElemento,
} from '../../../core/layout/guardados/elemento-guardado.model';
import { GuardadosStore } from '../../../core/layout/guardados/guardados.store';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { GuardadosSorpresaStore } from '../state/guardados-sorpresa.store';

/**
 * SCR-019 Mis aventuras guardadas (FEAT-020, RULE-013). 100 % cliente: se renderiza desde
 * `GuardadosStore` (localStorage), sin llamada al servidor. Los datos ya llegan validados/saneados
 * por `core/layout/guardados` (THREAT-026); aquí solo se construyen rutas internas con
 * `rutaElemento` (tipo+slug), nunca HTML ni URLs externas.
 */
@Component({
  selector: 'app-pagina-guardados',
  imports: [RouterLink, Banner, Boton, EstadoCargando, EstadoVacio],
  templateUrl: './pagina-guardados.html',
  styleUrl: './pagina-guardados.css',
})
export class PaginaGuardados {
  protected readonly guardados = inject(GuardadosStore);
  private readonly sorpresa = inject(GuardadosSorpresaStore);
  private readonly seo = inject(Seo);

  /** El HTML inicial no conoce el localStorage (SSR): se muestra un esqueleto hasta hidratar. */
  protected readonly hidratado = signal(isPlatformBrowser(inject(PLATFORM_ID)));

  protected readonly confirmandoVaciar = signal(false);
  protected readonly ultimoQuitado = signal<{ elemento: ElementoGuardado; indice: number } | null>(
    null,
  );
  protected readonly buscandoSorpresa = signal(false);

  protected readonly elementos = computed(() => this.guardados.elementos());

  constructor() {
    this.seo.establecer({
      titulo: 'Mis aventuras guardadas',
      descripcion: 'Tus destinos e itinerarios guardados en este navegador.',
      indexable: false,
    });
  }

  protected rutaDe(elemento: ElementoGuardado): string {
    return rutaElemento(elemento);
  }

  protected quitar(elemento: ElementoGuardado): void {
    const indice = this.elementos().findIndex(
      (e) => e.tipo === elemento.tipo && e.slug === elemento.slug,
    );
    this.guardados.quitar(elemento.tipo, elemento.slug);
    this.ultimoQuitado.set({ elemento, indice });
    this.confirmandoVaciar.set(false);
  }

  protected deshacerQuitar(): void {
    const ultimo = this.ultimoQuitado();
    if (ultimo === null) return;
    this.guardados.guardar(ultimo.elemento);
    this.ultimoQuitado.set(null);
  }

  protected pedirConfirmacionVaciar(): void {
    this.confirmandoVaciar.set(true);
    this.ultimoQuitado.set(null);
  }

  protected cancelarVaciar(): void {
    this.confirmandoVaciar.set(false);
  }

  protected confirmarVaciar(): void {
    this.guardados.vaciar();
    this.confirmandoVaciar.set(false);
  }

  protected async sorprenderme(): Promise<void> {
    this.buscandoSorpresa.set(true);
    try {
      await this.sorpresa.sorprenderme();
    } finally {
      this.buscandoSorpresa.set(false);
    }
  }
}
