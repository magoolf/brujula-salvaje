import { Component, computed, effect, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PaginaContenidoRetirado } from '../../../core/layout/paginas/pagina-contenido-retirado/pagina-contenido-retirado';
import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { JsonLd } from '../../../core/seo/datos-estructurados';
import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { ColeccionDetalleStore } from '../state/coleccion-detalle.store';

/** SCR-014 Detalle de colección (FEAT-017, TPL-PUB-DETAIL, SHOULD). */
@Component({
  selector: 'app-pagina-coleccion',
  imports: [
    RouterLink,
    MigasDePan,
    ImagenResponsiva,
    MedidorDificultad,
    TarjetaContenido,
    EstadoCargando,
    EstadoError,
    PaginaNoEncontrada,
    PaginaContenidoRetirado,
  ],
  providers: [ColeccionDetalleStore],
  templateUrl: './pagina-coleccion.html',
  styleUrl: './pagina-coleccion.css',
})
export class PaginaColeccion {
  protected readonly store = inject(ColeccionDetalleStore);
  private readonly seo = inject(Seo);

  protected readonly migas = computed<readonly Miga[]>(() => {
    const c = this.store.coleccion();
    return [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Colecciones', ruta: '/colecciones' },
      { etiqueta: c?.titulo ?? '' },
    ];
  });

  constructor() {
    effect(() => {
      const c = this.store.coleccion();
      if (c === null) return;
      const datosEstructurados: JsonLd = {
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        name: c.titulo,
        description: c.resumen,
      };
      this.seo.establecer({
        titulo: c.titulo,
        descripcion: c.resumen,
        imagen: c.portada ? { url: c.portada.src, alt: c.portada.alt } : undefined,
        tipoOg: 'website',
        datosEstructurados,
      });
    });
  }
}
