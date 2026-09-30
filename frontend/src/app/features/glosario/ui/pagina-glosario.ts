import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

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
}
