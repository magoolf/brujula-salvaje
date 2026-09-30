import { Dialog } from '@angular/cdk/dialog';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Compartir } from '../../../core/layout/compartir';
import { estaGuardado } from '../../../core/layout/guardados/elemento-guardado.model';
import { GuardadosStore } from '../../../core/layout/guardados/guardados.store';
import { JsonLd } from '../../../core/seo/datos-estructurados';
import { Seo } from '../../../core/seo/seo';
import { NOMBRE_MARCA } from '../../../core/seo/marca';
import { PaginaContenidoRetirado } from '../../../core/layout/paginas/pagina-contenido-retirado/pagina-contenido-retirado';
import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { BotonCompartir } from '../../../shared/ui/boton-compartir/boton-compartir';
import { BotonGuardar } from '../../../shared/ui/boton-guardar/boton-guardar';
import { Banner } from '../../../shared/ui/banner/banner';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MedidorPresupuesto } from '../../../shared/ui/medidor-presupuesto/medidor-presupuesto';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { formatoDuracion, formatoFechaEsCo, nombreMes, tieneItinerariosPropios } from '../domain/destino';
import { formatoCoordenadas } from '../domain/mapa';
import { DestinoDetalleStore } from '../state/destino-detalle.store';
import { VisorGaleria } from './visor-galeria';

/** SCR-004 Ficha de destino (FEAT-006..015). */
@Component({
  selector: 'app-pagina-destino',
  imports: [
    RouterLink,
    MigasDePan,
    BotonGuardar,
    BotonCompartir,
    ImagenResponsiva,
    MedidorDificultad,
    MedidorPresupuesto,
    TarjetaContenido,
    Banner,
    EstadoCargando,
    EstadoError,
    PaginaNoEncontrada,
    PaginaContenidoRetirado,
  ],
  // Instancia propia por activación de ruta: ver el porqué en destino-detalle.store.ts.
  providers: [DestinoDetalleStore],
  templateUrl: './pagina-destino.html',
  styleUrl: './pagina-destino.css',
})
export class PaginaDestino {
  protected readonly store = inject(DestinoDetalleStore);
  protected readonly guardados = inject(GuardadosStore);
  private readonly compartirServicio = inject(Compartir);
  private readonly dialogo = inject(Dialog);
  private readonly seo = inject(Seo);

  protected readonly marca = NOMBRE_MARCA;
  protected readonly compartiendo = signal(false);
  protected readonly mensajeCompartir = signal<string | null>(null);

  protected readonly migas = computed<readonly Miga[]>(() => {
    const destino = this.store.destino();
    return [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Destinos', ruta: '/destinos' },
      { etiqueta: destino?.titulo ?? '' },
    ];
  });

  protected readonly tieneItinerariosPropios = computed(() => {
    const destino = this.store.destino();
    return destino !== null && tieneItinerariosPropios(destino);
  });

  protected readonly duracionTexto = computed(() => {
    const destino = this.store.destino();
    return destino ? formatoDuracion(destino.duracionMinDias, destino.duracionMaxDias) : '';
  });

  protected readonly coordenadasTexto = computed(() => {
    const destino = this.store.destino();
    return destino ? formatoCoordenadas(destino.latitud, destino.longitud) : '';
  });

  protected readonly meses = Array.from({ length: 12 }, (_, i) => i + 1);

  protected readonly fechaRevisionTexto = computed(() => {
    const destino = this.store.destino();
    return destino ? formatoFechaEsCo(destino.fechaUltimaRevision) : '';
  });

  constructor() {
    // FEAT-027/CON-007: los metadatos se recalculan cada vez que llega un destino nuevo (incluida
    // la navegación entre fichas vía "Sigue explorando", que reutiliza este mismo componente).
    effect(() => {
      const destino = this.store.destino();
      if (destino === null) return;
      const datosEstructurados: JsonLd = {
        '@context': 'https://schema.org',
        '@type': 'TouristAttraction',
        name: destino.titulo,
        description: destino.resumen,
        latitude: destino.latitud,
        longitude: destino.longitud,
        ...(destino.portada ? { image: destino.portada.src } : {}),
      };
      this.seo.establecer({
        titulo: destino.titulo,
        descripcion: destino.resumen,
        imagen: destino.portada ? { url: destino.portada.src, alt: destino.portada.alt } : undefined,
        tipoOg: 'article',
        datosEstructurados,
      });
    });
  }

  protected estaGuardado(): boolean {
    const destino = this.store.destino();
    return destino !== null && estaGuardado(this.guardados.elementos(), 'DESTINO', destino.slug);
  }

  protected alternarGuardado(): void {
    const destino = this.store.destino();
    if (destino === null) return;
    if (this.estaGuardado()) {
      this.guardados.quitar('DESTINO', destino.slug);
    } else {
      this.guardados.guardar({
        tipo: 'DESTINO',
        slug: destino.slug,
        titulo: destino.titulo,
        pais: destino.pais.nombre,
      });
    }
  }

  protected async compartir(): Promise<void> {
    const destino = this.store.destino();
    if (destino === null || this.compartiendo()) return;
    this.compartiendo.set(true);
    this.mensajeCompartir.set(null);
    try {
      const resultado = await this.compartirServicio.compartir({
        titulo: destino.titulo,
        texto: destino.resumen,
        url:
          typeof window !== 'undefined' ? window.location.href : `https://brujulasalvaje.com/destinos/${destino.slug}`,
      });
      if (resultado.via === 'portapapeles') this.mensajeCompartir.set('Copiamos el enlace al portapapeles.');
      else if (resultado.error) this.mensajeCompartir.set(resultado.error.mensaje);
    } finally {
      this.compartiendo.set(false);
    }
  }

  protected abrirGaleria(indice: number): void {
    const destino = this.store.destino();
    if (destino === null || destino.galeria.length === 0) return;
    this.dialogo.open(VisorGaleria, {
      data: { imagenes: destino.galeria, indiceInicial: indice, tituloDestino: destino.titulo },
      backdropClass: 'bs-fondo-dialogo',
      panelClass: 'bs-panel-dialogo-completo',
      autoFocus: 'first-tabbable',
    });
  }

  protected esMesRecomendado(mes: number): boolean {
    return this.store.destino()?.mesesMejorEpoca.includes(mes) ?? false;
  }

  protected abreviaturaMes(mes: number): string {
    return (nombreMes(mes) ?? '').slice(0, 3);
  }
}
