import { Meta } from '@angular/platform-browser';
import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { GuardadosStore } from '../../../core/layout/guardados/guardados.store';
import { estaGuardado } from '../../../core/layout/guardados/elemento-guardado.model';
import { Seo } from '../../../core/seo/seo';
import { BotonGuardar } from '../../../shared/ui/boton-guardar/boton-guardar';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { EstadoVacio } from '../../../shared/ui/estado-vacio/estado-vacio';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { MedidorPresupuesto } from '../../../shared/ui/medidor-presupuesto/medidor-presupuesto';
import { Paginacion } from '../../../shared/ui/paginacion/paginacion';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import {
  FiltroActivo,
  alternarDuracion,
  alternarMes,
  alternarPais,
  alternarPresupuesto,
  alternarRegion,
  alternarTipo,
  establecerOrden,
  establecerRangoDificultad,
  filtrosActivosComoLista,
  hayFiltrosActivos,
  limpiarFiltros,
} from '../domain/filtros';
import { nombreMes } from '../domain/destino';
import { OrdenDestinos } from '../domain/modelos';
import { DestinosListadoStore } from '../state/destinos-listado.store';

const ETIQUETAS_ORDEN: Record<OrdenDestinos, string> = {
  nombre: 'A-Z',
  dificultad_asc: 'Dificultad: de menor a mayor',
  dificultad_desc: 'Dificultad: de mayor a menor',
};

/**
 * SCR-002 Explorar destinos (FEAT-003/004, TPL-PUB-LIST). Todo el estado de filtros vive en la URL
 * (query params): cada opción es un enlace real con `queryParamsHandling="merge"`, funciona sin JS
 * y es compartible (RULE-019, DEC-AUTO-047). Simplificación documentada del ticket: la barra de
 * filtros se muestra siempre en `<aside>` (sidebar en escritorio, apilada arriba en móvil) en vez de
 * la hoja inferior modal del HANDOFF_UI_UX, para priorizar una funcionalidad de filtrado completa y
 * accesible dentro del alcance de este ticket.
 */
@Component({
  selector: 'app-pagina-destinos',
  imports: [
    RouterLink,
    TarjetaContenido,
    MedidorDificultad,
    MedidorPresupuesto,
    Paginacion,
    EstadoCargando,
    EstadoError,
    EstadoVacio,
    BotonGuardar,
    Boton,
  ],
  // Instancia propia por activación de ruta: ver el porqué en destino-detalle.store.ts.
  providers: [DestinosListadoStore],
  templateUrl: './pagina-destinos.html',
  styleUrl: './pagina-destinos.css',
})
export class PaginaDestinos {
  protected readonly store = inject(DestinosListadoStore);
  protected readonly guardados = inject(GuardadosStore);
  private readonly seo = inject(Seo);
  private readonly meta = inject(Meta);

  protected readonly etiquetasOrden = ETIQUETAS_ORDEN;
  protected readonly ordenesDisponibles: readonly OrdenDestinos[] = [
    'nombre',
    'dificultad_asc',
    'dificultad_desc',
  ];

  protected readonly filtros = this.store.filtros;
  protected readonly hayActivos = computed(() => hayFiltrosActivos(this.filtros()));

  protected readonly nombrePorSlug = computed(() => {
    const facetas = this.store.facetas();
    return (slug: string): string => {
      if (facetas === null) return slug;
      const mesNum = Number(slug);
      if (Number.isInteger(mesNum) && mesNum >= 1 && mesNum <= 12) {
        return nombreMes(mesNum) ?? slug;
      }
      const tipo = facetas.tipos.find((t) => t.slug === slug);
      if (tipo) return tipo.nombre;
      const region = facetas.regiones.find((r) => r.slug === slug);
      if (region) return region.nombre;
      for (const r of facetas.regiones) {
        const pais = r.paises.find((p) => p.slug === slug);
        if (pais) return pais.nombre;
      }
      return slug;
    };
  });

  private readonly etiquetaTramoDuracion = computed(() => {
    const facetas = this.store.facetas();
    return (codigo: string): string =>
      facetas?.tramosDuracion.find((t) => t.codigo === codigo)?.etiqueta ?? codigo;
  });

  private readonly etiquetaNivel = computed(() => {
    const facetas = this.store.facetas();
    return (escala: 'dificultad' | 'presupuesto', nivel: number): string => {
      const lista = escala === 'dificultad' ? facetas?.dificultad : facetas?.presupuesto;
      return lista?.find((n) => n.nivel === nivel)?.etiqueta ?? String(nivel);
    };
  });

  protected readonly filtrosActivos = computed<readonly FiltroActivo[]>(() =>
    filtrosActivosComoLista(
      this.filtros(),
      this.nombrePorSlug(),
      this.etiquetaTramoDuracion(),
      this.etiquetaNivel(),
    ),
  );

  protected readonly meses = Array.from({ length: 12 }, (_, i) => i + 1);
  protected readonly limpiarQueryParams = limpiarFiltros();

  constructor() {
    this.seo.establecer({
      titulo: 'Explorar destinos',
      descripcion:
        'Descubre destinos de aventura filtrando por tipo, región, dificultad, mes, duración y presupuesto.',
    });
    // DEC-AUTO-047: las URL filtradas quedan fuera del índice pero mantienen sus enlaces rastreables.
    if (hayFiltrosActivos(this.filtros()) || this.filtros().pagina > 1) {
      this.meta.updateTag({ name: 'robots', content: 'noindex, follow' });
    }
  }

  protected estaGuardado(slug: string): boolean {
    return estaGuardado(this.guardados.elementos(), 'DESTINO', slug);
  }

  protected alternarGuardado(slug: string, titulo: string, pais: string): void {
    if (this.estaGuardado(slug)) {
      this.guardados.quitar('DESTINO', slug);
    } else {
      this.guardados.guardar({ tipo: 'DESTINO', slug, titulo, pais });
    }
  }

  protected queryParamsTipo(slug: string) {
    return alternarTipo(this.filtros(), slug);
  }
  protected queryParamsRegion(slug: string) {
    return alternarRegion(this.filtros(), slug);
  }
  protected queryParamsPais(slug: string) {
    return alternarPais(this.filtros(), slug);
  }
  protected queryParamsMes(mes: number) {
    return alternarMes(this.filtros(), mes);
  }
  protected queryParamsDuracion(codigo: '1-3' | '4-7' | '8-14' | '15+') {
    return alternarDuracion(this.filtros(), codigo);
  }
  protected queryParamsPresupuesto(nivel: number) {
    return alternarPresupuesto(this.filtros(), nivel);
  }
  protected queryParamsOrden(orden: OrdenDestinos) {
    return establecerOrden(orden);
  }
  protected queryParamsDificultad(min: number | null, max: number | null) {
    return establecerRangoDificultad(min, max);
  }

  protected tiposTexto(tipos: readonly { nombre: string }[]): string {
    return tipos.map((t) => t.nombre).join(' · ');
  }

  protected abreviaturaMes(mes: number): string {
    return (nombreMes(mes) ?? '').slice(0, 3);
  }

  protected nombreCompletoMes(mes: number): string {
    return nombreMes(mes) ?? String(mes);
  }

  /** Campos ocultos del formulario "Dificultad" (form GET) para conservar el resto de filtros. */
  protected readonly camposOcultosDificultad = computed<readonly { nombre: string; valor: string }[]>(
    () => {
      const f = this.filtros();
      const campos: { nombre: string; valor: string }[] = [];
      for (const tipo of f.tipo) campos.push({ nombre: 'tipo', valor: tipo });
      if (f.region !== null) campos.push({ nombre: 'region', valor: f.region });
      if (f.pais !== null) campos.push({ nombre: 'pais', valor: f.pais });
      if (f.mes !== null) campos.push({ nombre: 'mes', valor: String(f.mes) });
      for (const codigo of f.duracion) campos.push({ nombre: 'duracion', valor: codigo });
      for (const nivel of f.presupuesto) campos.push({ nombre: 'presupuesto', valor: String(nivel) });
      if (f.orden !== 'nombre') campos.push({ nombre: 'orden', valor: f.orden });
      return campos;
    },
  );
}
