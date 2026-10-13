import { Location } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { FocoRuta } from '../../../core/layout/foco-ruta';
import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { ALFABETO, GrupoLetra, agruparPorLetra } from '../domain/glosario';
import { GlosarioStore } from '../state/glosario.store';

/** SCR-018 Glosario (FEAT-019, COULD, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-glosario',
  imports: [RouterLink, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [GlosarioStore],
  templateUrl: './pagina-glosario.html',
  styleUrl: './pagina-glosario.css',
})
export class PaginaGlosario {
  protected readonly store = inject(GlosarioStore);
  private readonly seo = inject(Seo);
  private readonly location = inject(Location);
  private readonly focoRuta = inject(FocoRuta);

  protected readonly alfabeto = ALFABETO;

  protected readonly grupos = computed<readonly GrupoLetra[]>(() => {
    const p = this.store.pagina();
    return p ? agruparPorLetra(p.resultados) : [];
  });

  protected readonly letrasDisponibles = computed(() => new Set(this.grupos().map((g) => g.letra)));

  constructor() {
    this.seo.establecer({
      titulo: 'Glosario',
      descripcion: 'Vocabulario experto de viajes de aventura, explicado en español sencillo.',
    });
  }

  /**
   * Href completo del índice alfabético (TKT-042, QA TKT-019 OBS-01): con `<base href="/">` un
   * `#letra-x` relativo resolvería a `/#letra-x` (Inicio). Conserva la ruta y la query actuales
   * (`?pagina=2`); sin JS (SSR sin hidratar) el navegador hace la navegación de fragmento.
   */
  protected hrefAncla(id: string): string {
    return `${this.location.path()}#${id}`;
  }

  /**
   * Salto dentro de la página sin pasar por el Router (no re-anuncia la vista): lleva la vista y el
   * foco a la sección y deja el fragmento en la URL para que sea compartible. Los clics con
   * modificador (nueva pestaña) siguen su curso.
   */
  protected irAAncla(evento: MouseEvent, id: string): void {
    if (evento.button !== 0 || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) {
      return;
    }
    if (!this.focoRuta.irAAncla(id)) return;
    evento.preventDefault();
    this.location.replaceState(this.hrefAncla(id));
  }
}
