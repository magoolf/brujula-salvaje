import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { GrupoCreditos, agruparCreditosPorContenido } from '../domain/institucional';
import { CreditosStore } from '../state/creditos.store';

/** SCR-021 Créditos de imágenes (FEAT-024, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-creditos',
  imports: [RouterLink, ImagenResponsiva, Paginacion, EstadoCargando, EstadoError, EstadoVacio],
  providers: [CreditosStore],
  templateUrl: './pagina-creditos.html',
  styleUrl: './pagina-creditos.css',
})
export class PaginaCreditos {
  protected readonly store = inject(CreditosStore);
  private readonly seo = inject(Seo);

  protected readonly grupos = computed<readonly GrupoCreditos[]>(() => {
    const p = this.store.pagina();
    return p ? agruparCreditosPorContenido(p.resultados) : [];
  });

  constructor() {
    this.seo.establecer({
      titulo: 'Créditos de imágenes',
      descripcion: 'Autoría, licencia y fuente de todos los medios usados en el contenido publicado.',
    });
  }
}
