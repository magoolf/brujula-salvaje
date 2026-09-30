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
import { ACCESOS_MOSAICO, esInicioVacio } from '../domain/inicio';
import { InicioStore } from '../state/inicio.store';

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
  protected readonly accesosMosaico = ACCESOS_MOSAICO;
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
