import { Component, computed, effect, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PaginaContenidoRetirado } from '../../../core/layout/paginas/pagina-contenido-retirado/pagina-contenido-retirado';
import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { JsonLd } from '../../../core/seo/datos-estructurados';
import { Seo } from '../../../core/seo/seo';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { ImagenResponsiva } from '../../../shared/ui/imagen-responsiva/imagen-responsiva';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { GrupoChecklist, agruparChecklist, formatoFechaEsCo, tieneChecklist } from '../domain/tipo-aventura';
import { TipoDetalleStore } from '../state/tipo-detalle.store';

/** SCR-009 Detalle de tipo de aventura (FEAT-010/011/013/014/015). */
@Component({
  selector: 'app-pagina-tipo-aventura',
  imports: [
    RouterLink,
    MigasDePan,
    ImagenResponsiva,
    MedidorDificultad,
    Insignia,
    TarjetaContenido,
    EstadoCargando,
    EstadoError,
    PaginaNoEncontrada,
    PaginaContenidoRetirado,
  ],
  providers: [TipoDetalleStore],
  templateUrl: './pagina-tipo-aventura.html',
  styleUrl: './pagina-tipo-aventura.css',
})
export class PaginaTipoAventura {
  protected readonly store = inject(TipoDetalleStore);
  private readonly seo = inject(Seo);

  protected readonly migas = computed<readonly Miga[]>(() => {
    const tipo = this.store.tipo();
    return [
      { etiqueta: 'Inicio', ruta: '/' },
      { etiqueta: 'Tipos de aventura', ruta: '/tipos-de-aventura' },
      { etiqueta: tipo?.titulo ?? '' },
    ];
  });

  protected readonly grupos = computed<readonly GrupoChecklist[]>(() => {
    const tipo = this.store.tipo();
    return tipo ? agruparChecklist(tipo.checklist) : [];
  });

  protected readonly mostrarChecklist = computed(() => {
    const tipo = this.store.tipo();
    return tipo !== null && tieneChecklist(tipo.checklist);
  });

  protected readonly fechaRevisionTexto = computed(() => {
    const tipo = this.store.tipo();
    return tipo ? formatoFechaEsCo(tipo.fechaUltimaRevision) : '';
  });

  constructor() {
    effect(() => {
      const tipo = this.store.tipo();
      if (tipo === null) return;
      const datosEstructurados: JsonLd = {
        '@context': 'https://schema.org',
        '@type': 'Article',
        headline: tipo.titulo,
        description: tipo.resumen,
        ...(tipo.portada ? { image: tipo.portada.src } : {}),
      };
      this.seo.establecer({
        titulo: tipo.titulo,
        descripcion: tipo.resumen,
        imagen: tipo.portada ? { url: tipo.portada.src, alt: tipo.portada.alt } : undefined,
        tipoOg: 'article',
        datosEstructurados,
      });
    });
  }

  protected conteo(n: number): string {
    return n === 1 ? '1 destino' : `${n} destinos`;
  }
}
