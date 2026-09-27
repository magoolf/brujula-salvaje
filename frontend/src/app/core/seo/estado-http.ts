import { Injectable, RESPONSE_INIT, inject } from '@angular/core';

/**
 * Fija el código HTTP real de la respuesta del SSR (BLUEPRINT §37: "el HTTP real debe coincidir,
 * no solo la vista"): 404 en SCR-023, 410 en SCR-024 y 500 en SCR-025.
 * En el navegador `RESPONSE_INIT` no existe y la llamada no tiene efecto.
 */
@Injectable({
  providedIn: 'root',
})
export class EstadoHttp {
  private readonly respuesta = inject(RESPONSE_INIT, { optional: true });

  establecer(estado: 404 | 410 | 500 | 503): void {
    if (this.respuesta !== null) {
      this.respuesta.status = estado;
    }
  }
}
