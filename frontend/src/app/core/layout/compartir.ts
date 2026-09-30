import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject } from '@angular/core';

import { ErrorApi } from '../http/error-api.model';

export interface DatosCompartir {
  readonly titulo: string;
  readonly texto?: string;
  readonly url: string;
}

/** Resultado de un intento de compartir (Regla 12 adaptada: además de `error`, indica la vía usada
 * porque la UI muestra un mensaje distinto según compartió con la app nativa o copió el enlace). */
export interface ResultadoCompartir {
  readonly error: ErrorApi | null;
  readonly via: 'nativo' | 'portapapeles' | 'cancelado';
}

const ERROR_SIN_VIA: ErrorApi = {
  tipo: 'compartir_no_disponible',
  categoria: 'desconocido',
  codigo: null,
  mensaje: 'No pudimos compartir ni copiar el enlace. Selecciónalo manualmente.',
  campos: {},
  traceId: null,
  extra: {},
};

/**
 * Compartir (GI-06, FEAT-021): función nativa del dispositivo (Web Share API) con respaldo a copiar
 * la URL canónica al portapapeles (DEC-AUTO-078 no aplica: esto no es un enlace externo, es la
 * propia página). Vive en `core/layout` porque, como Guardar (GI-07), es una interacción global
 * usada por varias features.
 */
@Injectable({ providedIn: 'root' })
export class Compartir {
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly documento = inject(DOCUMENT);

  soportaNativo(): boolean {
    return (
      this.esNavegador && typeof this.documento.defaultView?.navigator.share === 'function'
    );
  }

  async compartir(datos: DatosCompartir): Promise<ResultadoCompartir> {
    const ventana = this.documento.defaultView;
    if (this.soportaNativo() && ventana) {
      try {
        await ventana.navigator.share({ title: datos.titulo, text: datos.texto, url: datos.url });
        return { error: null, via: 'nativo' };
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return { error: null, via: 'cancelado' };
        }
        // Cualquier otro fallo del share sheet sigue al respaldo de copiar.
      }
    }
    if (ventana?.navigator.clipboard) {
      try {
        await ventana.navigator.clipboard.writeText(datos.url);
        return { error: null, via: 'portapapeles' };
      } catch {
        return { error: ERROR_SIN_VIA, via: 'cancelado' };
      }
    }
    return { error: ERROR_SIN_VIA, via: 'cancelado' };
  }
}
