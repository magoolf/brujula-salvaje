import { Component, computed, effect, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { GuardadosStore } from '../../../core/layout/guardados/guardados.store';
import { estaGuardado } from '../../../core/layout/guardados/elemento-guardado.model';
import { PaginaNoEncontrada } from '../../../core/layout/paginas/pagina-no-encontrada/pagina-no-encontrada';
import { Seo } from '../../../core/seo/seo';
import { BotonGuardar } from '../../../shared/ui/boton-guardar/boton-guardar';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MigasDePan, Miga } from '../../../shared/ui/migas-de-pan/migas-de-pan';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { mesAdyacente, nombreMes } from '../domain/destino';
import { DestinosDelMesStore } from '../state/meses.store';

/** SCR-016 Destinos del mes (FEAT-018). Mes inválido → 404 (ST-NOTFOUND). */
@Component({
  selector: 'app-pagina-destinos-del-mes',
  imports: [
    RouterLink,
    MigasDePan,
    TarjetaContenido,
    MedidorDificultad,
    BotonGuardar,
    EstadoCargando,
    EstadoError,
    EstadoVacio,
    PaginaNoEncontrada,
  ],
  // Instancia propia por activación de ruta: ver el porqué en destino-detalle.store.ts.
  providers: [DestinosDelMesStore],
  templateUrl: './pagina-destinos-del-mes.html',
  styleUrl: './pagina-destinos-del-mes.css',
})
export class PaginaDestinosDelMes {
  protected readonly store = inject(DestinosDelMesStore);
  protected readonly guardados = inject(GuardadosStore);
  private readonly seo = inject(Seo);

  protected readonly nombreMesActual = computed(() => {
    const mes = this.store.mes();
    return mes !== null ? (nombreMes(mes) ?? '') : '';
  });

  protected readonly mesAnterior = computed(() => {
    const mes = this.store.mes();
    return mes !== null ? mesAdyacente(mes, -1) : null;
  });

  protected readonly mesSiguiente = computed(() => {
    const mes = this.store.mes();
    return mes !== null ? mesAdyacente(mes, 1) : null;
  });

  protected readonly migas = computed<readonly Miga[]>(() => [
    { etiqueta: 'Inicio', ruta: '/' },
    { etiqueta: 'Cuándo ir', ruta: '/cuando-ir' },
    { etiqueta: this.nombreMesActual() },
  ]);

  constructor() {
    effect(() => {
      const nombre = this.nombreMesActual();
      if (nombre === '') return;
      this.seo.establecer({
        titulo: `Dónde ir en ${nombre}`,
        descripcion: `Destinos recomendados para viajar en ${nombre}.`,
      });
    });
  }

  protected nombreDeMes(mes: number): string {
    return nombreMes(mes) ?? String(mes);
  }

  protected estaGuardado(slug: string): boolean {
    return estaGuardado(this.guardados.elementos(), 'DESTINO', slug);
  }

  protected alternarGuardado(slug: string, titulo: string, pais: string): void {
    if (this.estaGuardado(slug)) this.guardados.quitar('DESTINO', slug);
    else this.guardados.guardar({ tipo: 'DESTINO', slug, titulo, pais });
  }
}
