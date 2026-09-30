import { Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Compartir } from '../../../core/layout/compartir';
import { PaginaContenidoRetirado } from '../../../core/layout/paginas/pagina-contenido-retirado/pagina-contenido-retirado';
import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { JsonLd } from '../../../core/seo/datos-estructurados';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { BotonCompartir } from '../../../shared/ui/boton-compartir/boton-compartir';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { formatoFechaEsCo, textoDesnivelDia, tieneMetricasRuta } from '../domain/itinerario';
import { ItinerarioDetalleStore } from '../state/itinerario-detalle.store';

/** SCR-007 Detalle de itinerario (FEAT-008/013/014/015). */
@Component({
  selector: 'app-pagina-itinerario',
  imports: [
    RouterLink,
    MigasDePan,
    BotonCompartir,
    ImagenResponsiva,
    MedidorDificultad,
    TarjetaContenido,
    Banner,
    EstadoCargando,
    EstadoError,
    PaginaNoEncontrada,
    PaginaContenidoRetirado,
  ],
  providers: [ItinerarioDetalleStore],
  templateUrl: './pagina-itinerario.html',
  styleUrl: './pagina-itinerario.css',
})
export class PaginaItinerario {
  protected readonly store = inject(ItinerarioDetalleStore);
  private readonly compartirServicio = inject(Compartir);
  private readonly seo = inject(Seo);

  protected readonly compartiendo = signal(false);
  protected readonly mensajeCompartir = signal<string | null>(null);

  protected readonly migas = computed<readonly Miga[]>(() => {
    const it = this.store.itinerario();
    if (it === null) {
      return [
        { etiqueta: 'Inicio', ruta: '/' },
        { etiqueta: 'Destinos', ruta: '/destinos' },
      ];
    }
    return [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Destinos', ruta: '/destinos' },
      { etiqueta: it.destino.titulo, ruta: `/destinos/${it.destino.slug}` },
      { etiqueta: it.titulo },
    ];
  });

  protected readonly tieneMetricas = computed(() => {
    const it = this.store.itinerario();
    return it !== null && tieneMetricasRuta(it);
  });

  protected readonly fechaRevisionTexto = computed(() => {
    const it = this.store.itinerario();
    return it ? formatoFechaEsCo(it.fechaUltimaRevision) : '';
  });

  constructor() {
    // FEAT-027/CON-007: recalcula los metadatos cada vez que llega un itinerario nuevo (incluye la
    // navegación vía "Sigue explorando", que reutiliza este mismo componente; mismo patrón que
    // PaginaDestino).
    effect(() => {
      const it = this.store.itinerario();
      if (it === null) return;
      const datosEstructurados: JsonLd = {
        '@context': 'https://schema.org',
        '@type': 'TouristTrip',
        name: it.titulo,
        description: it.resumen,
        ...(it.portada ? { image: it.portada.src } : {}),
      };
      this.seo.establecer({
        titulo: it.titulo,
        descripcion: it.resumen,
        imagen: it.portada ? { url: it.portada.src, alt: it.portada.alt } : undefined,
        tipoOg: 'article',
        datosEstructurados,
      });
    });
  }

  protected async compartir(): Promise<void> {
    const it = this.store.itinerario();
    if (it === null || this.compartiendo()) return;
    this.compartiendo.set(true);
    this.mensajeCompartir.set(null);
    try {
      const resultado = await this.compartirServicio.compartir({
        titulo: it.titulo,
        texto: it.resumen,
        url:
          typeof window !== 'undefined'
            ? window.location.href
            : `https://brujulasalvaje.com/itinerarios/${it.slug}`,
      });
      if (resultado.via === 'portapapeles') this.mensajeCompartir.set('Copiamos el enlace al portapapeles.');
      else if (resultado.error) this.mensajeCompartir.set(resultado.error.mensaje);
    } finally {
      this.compartiendo.set(false);
    }
  }

  protected textoDesnivel(positivoM: number | null, negativoM: number | null): string | null {
    return textoDesnivelDia(positivoM, negativoM);
  }
}
