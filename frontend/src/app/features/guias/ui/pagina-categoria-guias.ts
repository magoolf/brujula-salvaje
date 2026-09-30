import { Component, computed, effect, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { textoMinutosLectura, textoRevisado } from '../domain/guia';
import { GuiasCategoriaStore } from '../state/guias-categoria.store';

/** SCR-011 Categoría de guías (FEAT-012, TPL-PUB-LIST). */
@Component({
  selector: 'app-pagina-categoria-guias',
  imports: [RouterLink, MigasDePan, TarjetaContenido, Paginacion, EstadoCargando, EstadoError, PaginaNoEncontrada],
  providers: [GuiasCategoriaStore],
  templateUrl: './pagina-categoria-guias.html',
  styleUrl: './pagina-categoria-guias.css',
})
export class PaginaCategoriaGuias {
  protected readonly store = inject(GuiasCategoriaStore);
  private readonly seo = inject(Seo);

  protected readonly migas = computed<readonly Miga[]>(() => {
    const categoria = this.store.categoria();
    return [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Guías', ruta: '/guias' },
      { etiqueta: categoria?.nombre ?? '' },
    ];
  });

  constructor() {
    effect(() => {
      const categoria = this.store.categoria();
      if (categoria === null) return;
      this.seo.establecer({ titulo: categoria.nombre, descripcion: categoria.descripcion });
    });
  }

  protected minutosLectura(minutos: number | null): string | null {
    return textoMinutosLectura(minutos);
  }

  protected revisado(iso: string): string {
    return textoRevisado(iso);
  }
}
