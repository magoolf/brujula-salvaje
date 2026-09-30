import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JsonLd, sitioWebJsonLd } from '../../../core/seo/datos-estructurados';
import { IDIOMA, NOMBRE_MARCA } from '../../../core/seo/marca';
import { Seo } from '../../../core/seo/seo';
import { Boton } from '../../../shared/ui/boton/boton';
import { CampoBusqueda } from '../../../shared/ui/campo-busqueda/campo-busqueda';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { MedidorDificultad } from '../../../shared/ui/medidor-dificultad/medidor-dificultad';
import { TarjetaContenido } from '../../../shared/ui/tarjeta-contenido/tarjeta-contenido';
import { AccesoMosaico, ACCESOS_MOSAICO, esInicioVacio } from '../domain/inicio';
import { InicioStore } from '../state/inicio.store';

/**
 * TKT-009 (QA ciclo 1/3, RULE-030): Colecciones ya existe (MOD-005) pero `ACCESOS_MOSAICO` vive en
 * `domain/inicio.ts`, fuera de `archivos_permitidos` de este ticket (solo se amplió con
 * `core/layout/navegacion.ts` y este componente). Se añade aquí, en la capa UI, en vez de tocar el
 * dominio de la feature `inicio`. Sigue el orden de SCR-001/HANDOFF_UI_UX: «Mapa* · Cuándo ir* ·
 * Colecciones* · Sorpréndeme*» (línea 66 y BLUEPRINT §10 línea 244).
 */
const ACCESO_COLECCIONES: AccesoMosaico = {
  id: 'colecciones',
  etiqueta: 'Colecciones',
  descripcion: 'Selecciones curadas de destinos e itinerarios por nuestro equipo editorial.',
  ruta: '/colecciones',
};

/** SCR-001 Inicio (FEAT-001/002/025/028/051, TPL-PUB-HOME). */
@Component({
  selector: 'app-pagina-inicio',
  imports: [
    RouterLink,
    Boton,
    CampoBusqueda,
    EstadoError,
    MedidorDificultad,
    TarjetaContenido,
  ],
  templateUrl: './pagina-inicio.html',
  styleUrl: './pagina-inicio.css',
})
export class PaginaInicio {
  protected readonly store = inject(InicioStore);
  private readonly seo = inject(Seo);

  protected readonly marca = NOMBRE_MARCA;
  protected readonly accesosMosaico: readonly AccesoMosaico[] = [...ACCESOS_MOSAICO, ACCESO_COLECCIONES];
  protected readonly buscandoSorpresa = signal(false);

  protected readonly vacio = computed(() => {
    const inicio = this.store.inicio();
    return inicio !== null && esInicioVacio(inicio);
  });

  constructor() {
    const datosEstructurados: JsonLd = sitioWebJsonLd(this.seo.origen(), NOMBRE_MARCA, IDIOMA);
    this.seo.establecer({
      titulo: '',
      descripcion:
        'Guías de aventura honestas: destinos, itinerarios día a día y consejos de seguridad, sin publicidad engañosa.',
      rutaCanonica: '/',
      datosEstructurados,
    });
  }

  protected async sorprenderme(): Promise<void> {
    if (this.buscandoSorpresa()) return;
    this.buscandoSorpresa.set(true);
    try {
      await this.store.sorprenderme();
    } finally {
      this.buscandoSorpresa.set(false);
    }
  }
}
