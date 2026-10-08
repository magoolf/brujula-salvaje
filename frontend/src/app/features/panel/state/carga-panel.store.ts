import { Injectable, inject } from '@angular/core';
import { Router, UrlTree } from '@angular/router';

import { SesionPanelStore } from './sesion-panel.store';

/**
 * STATE de la carga inicial del panel (QA TKT-010 OBS-C3-01, AC_TKT022_07). En la carga completa de
 * una URL /panel/** la sesión aún no se conoce y los guards tendrían que esperar a la API antes de
 * activar ninguna ruta: durante ese tiempo no habría armazón ni <main>. Mientras la sesión no está
 * resuelta, una ruta de carga (sin guards) muestra el armazón mínimo, resuelve la sesión y repite la
 * navegación a la URL original, que entonces pasa por los guards de siempre con la sesión conocida.
 */
@Injectable({ providedIn: 'root' })
export class CargaPanelStore {
  private readonly sesion = inject(SesionPanelStore);
  private readonly router = inject(Router);
  private destino: UrlTree | null = null;

  /** La ruta de carga solo atiende mientras la sesión no se ha leído nunca. */
  necesitaCarga(): boolean {
    return !this.sesion.cargada();
  }

  /** Recuerda la URL completa (con su consulta) de la navegación en curso. */
  recordarDestino(): void {
    this.destino = this.router.currentNavigation()?.extractedUrl ?? null;
  }

  /** Resuelve la sesión y repite la navegación original (sin añadir una entrada al historial). */
  async continuar(): Promise<boolean> {
    await this.sesion.asegurar();
    const destino = this.destino ?? this.router.parseUrl(this.router.url);
    this.destino = null;
    return this.router.navigateByUrl(destino, { replaceUrl: true, onSameUrlNavigation: 'reload' });
  }
}
