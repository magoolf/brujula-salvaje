import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { MesesIndiceStore } from '../state/meses.store';

/** SCR-015 «¿Dónde ir cada mes?» (FEAT-018, SHOULD). */
@Component({
  selector: 'app-pagina-cuando-ir',
  imports: [RouterLink, EstadoCargando, EstadoError, ImagenResponsiva],
  templateUrl: './pagina-cuando-ir.html',
  styleUrl: './pagina-cuando-ir.css',
})
export class PaginaCuandoIr {
  protected readonly store = inject(MesesIndiceStore);
  private readonly seo = inject(Seo);

  constructor() {
    this.seo.establecer({
      titulo: '¿Dónde ir cada mes?',
      descripcion: 'Encuentra el destino ideal según el mes en el que planeas viajar.',
    });
  }
}
