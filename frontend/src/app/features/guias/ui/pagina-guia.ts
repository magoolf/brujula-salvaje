import { Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Compartir } from '../../../core/layout/compartir';
import { PaginaContenidoRetirado } from '../../../core/layout/paginas/pagina-contenido-retirado/pagina-contenido-retirado';
import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { JsonLd } from '../../../core/seo/datos-estructurados';
import { Seo } from '../../../core/seo/seo';
import { BotonCompartir } from '../../../shared/ui/boton-compartir/boton-compartir';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { formatoFechaEsCo, textoMinutosLectura } from '../domain/guia';
import { GuiaDetalleStore } from '../state/guia-detalle.store';

/** SCR-012 Detalle de guía (FEAT-012/013/014/015/052, TPL-PUB-ARTICLE). */
@Component({
  selector: 'app-pagina-guia',
  imports: [
    RouterLink,
    MigasDePan,
    BotonCompartir,
    ImagenResponsiva,
    MedidorDificultad,
    TarjetaContenido,
    EstadoCargando,
    EstadoError,
    PaginaNoEncontrada,
    PaginaContenidoRetirado,
  ],
  providers: [GuiaDetalleStore],
  templateUrl: './pagina-guia.html',
  styleUrl: './pagina-guia.css',
})
export class PaginaGuia {
  protected readonly store = inject(GuiaDetalleStore);
  private readonly compartirServicio = inject(Compartir);
  private readonly seo = inject(Seo);

  protected readonly compartiendo = signal(false);
  protected readonly mensajeCompartir = signal<string | null>(null);

  protected readonly migas = computed<readonly Miga[]>(() => {
    const guia = this.store.guia();
    if (guia === null) return [{ etiqueta: 'Inicio', ruta: '/' }, { etiqueta: 'Guías', ruta: '/guias' }];
    return [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Guías', ruta: '/guias' },
      { etiqueta: guia.categoria.nombre, ruta: `/guias/categoria/${guia.categoria.slug}` },
      { etiqueta: guia.titulo },
    ];
  });

  protected readonly lecturaTexto = computed(() => {
    const guia = this.store.guia();
    return guia ? textoMinutosLectura(guia.minutosLectura) : null;
  });

  protected readonly fechaRevisionTexto = computed(() => {
    const guia = this.store.guia();
    return guia ? formatoFechaEsCo(guia.fechaUltimaRevision) : '';
  });

  constructor() {
    effect(() => {
      const guia = this.store.guia();
      if (guia === null) return;
      const datosEstructurados: JsonLd = {
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: guia.titulo,
        description: guia.resumen,
        ...(guia.portada ? { image: guia.portada.src } : {}),
      };
      this.seo.establecer({
        titulo: guia.titulo,
        descripcion: guia.resumen,
        imagen: guia.portada ? { url: guia.portada.src, alt: guia.portada.alt } : undefined,
        tipoOg: 'article',
        datosEstructurados,
      });
    });
  }

  protected async compartir(): Promise<void> {
    const guia = this.store.guia();
    if (guia === null || this.compartiendo()) return;
    this.compartiendo.set(true);
    this.mensajeCompartir.set(null);
    try {
      const resultado = await this.compartirServicio.compartir({
        titulo: guia.titulo,
        texto: guia.resumen,
        url:
          typeof window !== 'undefined' ? window.location.href : `https://brujulasalvaje.com/guias/${guia.slug}`,
      });
      if (resultado.via === 'portapapeles') this.mensajeCompartir.set('Copiamos el enlace al portapapeles.');
      else if (resultado.error) this.mensajeCompartir.set(resultado.error.mensaje);
    } finally {
      this.compartiendo.set(false);
    }
  }
}
