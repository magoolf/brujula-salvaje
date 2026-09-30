import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { Banner } from '../../../shared/ui/banner/banner';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { agruparMarcadores, ClusterMapa, ElementoMapa, MarcadorIndividual } from '../domain/mapa';
import { PuntoMapa, RefTaxonomiaVista } from '../domain/modelos';
import { MapaStore } from '../state/mapa.store';

interface GrupoRegion {
  readonly region: RefTaxonomiaVista;
  readonly destinos: readonly PuntoMapa[];
}

/**
 * SCR-003 Mapa de destinos (FEAT-005, SHOULD). DEC-AUTO-TKT008-01 (ver `domain/mapa.ts`): fondo
 * cartográfico decorativo simplificado en vez del SVG real de Natural Earth. La lista agrupada por
 * región es la alternativa equivalente exigida por accesibilidad (1.1.1/2.1.1): siempre presente en
 * el HTML, no depende del mapa.
 */
@Component({
  selector: 'app-pagina-mapa-destinos',
  imports: [RouterLink, EstadoCargando, EstadoVacio, Banner, MedidorDificultad],
  templateUrl: './pagina-mapa-destinos.html',
  styleUrl: './pagina-mapa-destinos.css',
})
export class PaginaMapaDestinos {
  protected readonly store = inject(MapaStore);
  private readonly seo = inject(Seo);

  protected readonly regionActiva = signal<string | null>(null);
  protected readonly marcadorActivo = signal<string | null>(null);

  protected readonly regionesDisponibles = computed<readonly RefTaxonomiaVista[]>(() => {
    const vistos = new Map<string, RefTaxonomiaVista>();
    for (const punto of this.store.puntos()) {
      if (!vistos.has(punto.region.slug)) vistos.set(punto.region.slug, punto.region);
    }
    return [...vistos.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  protected readonly puntosVisibles = computed(() => {
    const region = this.regionActiva();
    const todos = this.store.puntos();
    return region === null ? todos : todos.filter((p) => p.region.slug === region);
  });

  protected readonly elementos = computed<readonly ElementoMapa[]>(() =>
    agruparMarcadores(this.puntosVisibles()),
  );

  protected readonly gruposPorRegion = computed<readonly GrupoRegion[]>(() => {
    const mapa = new Map<string, GrupoRegion>();
    for (const punto of this.store.puntos()) {
      const existente = mapa.get(punto.region.slug);
      if (existente) (existente.destinos as PuntoMapa[]).push(punto);
      else mapa.set(punto.region.slug, { region: punto.region, destinos: [punto] });
    }
    return [...mapa.values()].sort((a, b) => a.region.nombre.localeCompare(b.region.nombre, 'es'));
  });

  protected readonly puntoActivo = computed<PuntoMapa | null>(() => {
    const slug = this.marcadorActivo();
    if (slug === null) return null;
    return this.store.puntos().find((p) => p.slug === slug) ?? null;
  });

  constructor() {
    this.seo.establecer({
      titulo: 'Mapa de destinos',
      descripcion: 'Explora todos los destinos publicados en un mapa del mundo, por región.',
    });
  }

  protected elegirRegion(slug: string | null): void {
    this.regionActiva.set(slug);
    this.marcadorActivo.set(null);
  }

  protected alternarMarcador(slug: string): void {
    this.marcadorActivo.set(this.marcadorActivo() === slug ? null : slug);
  }

  protected cerrarMinitarjeta(): void {
    this.marcadorActivo.set(null);
  }

  protected esCluster(elemento: ElementoMapa): elemento is ClusterMapa {
    return elemento.tipo === 'cluster';
  }

  protected comoMarcador(elemento: ElementoMapa): MarcadorIndividual {
    return elemento as MarcadorIndividual;
  }
}
