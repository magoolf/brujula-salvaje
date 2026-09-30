import { Component, computed, effect, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { CampoBusqueda } from '../../../shared/ui/campo-busqueda/campo-busqueda';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { etiquetaGrupo } from '../domain/filtros';
import { GrupoResultado } from '../domain/modelos';
import { BusquedaStore } from '../state/busqueda.store';

const GRUPOS: readonly GrupoResultado[] = ['destinos', 'itinerarios', 'guias', 'tipos'];

/** SCR-017 Resultados de búsqueda (FEAT-016, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-busqueda',
  imports: [RouterLink, CampoBusqueda, TarjetaContenido, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [BusquedaStore],
  templateUrl: './pagina-busqueda.html',
  styleUrl: './pagina-busqueda.css',
})
export class PaginaBusqueda {
  protected readonly store = inject(BusquedaStore);
  private readonly seo = inject(Seo);

  protected readonly grupos = GRUPOS;
  protected readonly filtros = this.store.filtros;

  protected readonly totalTexto = computed(() => {
    const total = this.store.filtros().tipo === null ? this.store.agrupada()?.total : this.store.grupo()?.total;
    if (total === undefined) return '';
    return total === 1 ? '1 resultado' : `${total} resultados`;
  });

  constructor() {
    // AC-020/THREAT-020: `q` se muestra siempre como texto (nunca HTML) y nunca se registra.
    effect(() => {
      const q = this.filtros().q;
      this.seo.establecer({
        titulo: q === '' ? 'Buscar' : `Resultados para «${q}»`,
        indexable: false,
      });
    });
  }

  protected etiqueta(grupo: GrupoResultado): string {
    return etiquetaGrupo(grupo);
  }

  protected queryParamsGrupo(grupo: GrupoResultado): Record<string, string> {
    return { q: this.filtros().q, tipo: grupo };
  }

  protected readonly queryParamsTodos = computed<Record<string, string>>(() => ({ q: this.filtros().q }));
}
