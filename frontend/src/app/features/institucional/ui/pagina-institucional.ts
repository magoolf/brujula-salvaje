import { Component, computed, effect, inject } from '@angular/core';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MedidorPresupuesto } from '../../../shared/ui/medidor-presupuesto/medidor-presupuesto';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { MARCADOR_RESPONSABLE_PENDIENTE, formatoFechaEsCo } from '../domain/institucional';
import { PaginaInstitucionalStore } from '../state/pagina-institucional.store';

/** SCR-020 Página institucional, plantilla reutilizada por las 4 rutas legales/informativas (FEAT-023). */
@Component({
  selector: 'app-pagina-institucional',
  imports: [MigasDePan, MedidorDificultad, MedidorPresupuesto, EstadoCargando, EstadoError],
  providers: [PaginaInstitucionalStore],
  templateUrl: './pagina-institucional.html',
  styleUrl: './pagina-institucional.css',
})
export class PaginaInstitucional {
  protected readonly store = inject(PaginaInstitucionalStore);
  private readonly seo = inject(Seo);

  protected readonly marcadorPendiente = MARCADOR_RESPONSABLE_PENDIENTE;

  protected readonly esAcercaDe = computed(() => this.store.pagina()?.slug === 'acerca-de');
  protected readonly esTratamientoDatos = computed(
    () => this.store.pagina()?.slug === 'politica-de-tratamiento-de-datos',
  );
  /** Páginas legales (todas salvo /acerca-de, que es informativa): muestran versión y vigencia. */
  protected readonly esLegal = computed(() => this.store.pagina()?.slug !== 'acerca-de');

  protected readonly migas = computed<readonly Miga[]>(() => [
    { etiqueta: 'Inicio', ruta: '/' },
    { etiqueta: this.store.pagina()?.titulo ?? '' },
  ]);

  protected readonly vigenteDesdeTexto = computed(() => {
    const p = this.store.pagina();
    return p ? formatoFechaEsCo(p.vigenteDesde) : '';
  });

  constructor() {
    effect(() => {
      const p = this.store.pagina();
      if (p === null) return;
      this.seo.establecer({ titulo: p.titulo });
    });
  }
}
