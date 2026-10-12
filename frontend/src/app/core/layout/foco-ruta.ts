import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import {
  AfterRenderRef,
  DestroyRef,
  Injectable,
  Injector,
  PLATFORM_ID,
  afterEveryRender,
  afterNextRender,
  inject,
} from '@angular/core';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { filter } from 'rxjs';

import { ID_CONTENIDO_PRINCIPAL } from './navegacion';

/**
 * Tiempo máximo que se espera a que aparezca el destino de un fragmento cuyos datos llegan tras la
 * navegación (p. ej. `/glosario#termino`, que se pinta cuando responde la API). Pasado este tiempo
 * se abandona la espera: el visitante se queda en la vista ya anunciada.
 */
export const ESPERA_MAXIMA_FRAGMENTO_MS = 10_000;

/**
 * Interacciones que cancelan la espera de un fragmento: si el visitante ya está desplazándose,
 * leyendo o tecleando, llevarle de golpe al destino cuando lleguen los datos le desorientaría.
 */
const EVENTOS_INTERACCION = ['pointerdown', 'keydown', 'wheel', 'touchstart'] as const;

/**
 * Lleva la vista y el foco al destino de un ancla (TKT-042): desplaza el elemento al inicio del
 * viewport (respeta `scroll-margin-top` bajo la cabecera fija) y le da el foco (tabindex=-1 si no
 * es enfocable) para que el lector de pantalla lo anuncie y el Tab continúe desde ahí. Si el foco
 * ya está dentro del destino (lo movió la propia vista) no se le quita. `enfocar=false` solo
 * desplaza (carga inicial: el navegador ya fijó el punto de partida de la navegación secuencial).
 * Devuelve `false` si el destino no existe.
 */
export function irAAncla(documento: Document, id: string, enfocar = true): boolean {
  const destino = id === '' ? null : documento.getElementById(id);
  if (destino === null) return false;
  if (enfocar && !destino.contains(documento.activeElement)) {
    if (!destino.hasAttribute('tabindex')) destino.setAttribute('tabindex', '-1');
    destino.focus({ preventScroll: true });
  }
  destino.scrollIntoView({ block: 'start' });
  return true;
}

/**
 * Gestión del foco al cambiar de ruta (ACCESSIBILITY_SPEC.Focus_Management): tras cada navegación
 * interna (no en la carga inicial) el foco va al h1 de la vista (tabindex=-1), de modo que el lector
 * de pantalla anuncia el nuevo título; si no hay h1, al contenido principal.
 *
 * Navegaciones con fragmento (TKT-042, QA TKT-019 OBS-02): `anchorScrolling` del Router actúa en
 * cuanto termina la navegación, cuando la vista aún no tiene sus datos y el destino no existe. Por
 * eso, si el destino ya está en el DOM se va directamente a él; si no, se anuncia la vista (h1) y
 * se espera a que el destino aparezca en un render posterior para llevar allí la vista y el foco.
 * La espera se cancela con la siguiente navegación, con cualquier interacción del visitante o a
 * los ESPERA_MAXIMA_FRAGMENTO_MS. En la carga inicial (SSR) el navegador ya desplaza al fragmento;
 * solo si el destino llega después se desplaza, sin mover el foco.
 */
@Injectable({
  providedIn: 'root',
})
export class FocoRuta {
  private readonly router = inject(Router);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly destroyRef = inject(DestroyRef);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));
  private iniciado = false;
  private cancelarEsperaActual: (() => void) | null = null;

  iniciar(): void {
    if (!this.esNavegador || this.iniciado) return;
    this.iniciado = true;
    let primera = true;
    const suscripcion = this.router.events
      .pipe(filter((e) => e instanceof NavigationStart || e instanceof NavigationEnd))
      .subscribe((evento) => {
        this.cancelarEspera();
        if (!(evento instanceof NavigationEnd)) return;
        const fragmento = this.router.parseUrl(evento.urlAfterRedirects).fragment ?? '';
        const esPrimera = primera;
        primera = false;
        if (esPrimera) {
          if (fragmento !== '') this.esperarDestino(fragmento, false);
          return;
        }
        afterNextRender(() => this.trasNavegar(fragmento), { injector: this.injector });
      });
    this.destroyRef.onDestroy(() => {
      suscripcion.unsubscribe();
      this.cancelarEspera();
    });
  }

  enfocarVista(): void {
    const principal = this.documento.getElementById(ID_CONTENIDO_PRINCIPAL);
    if (principal === null) return;
    const destino = principal.querySelector<HTMLElement>('h1') ?? principal;
    if (!destino.hasAttribute('tabindex')) destino.setAttribute('tabindex', '-1');
    destino.focus({ preventScroll: false });
  }

  /**
   * Salto a un ancla de la propia página sin pasar por el Router (índices internos): una navegación
   * solo de fragmento no cambia la vista y no debe re-anunciarla. Devuelve `false` si el destino no
   * existe (el enlace sigue su curso normal).
   */
  irAAncla(id: string): boolean {
    if (!this.esNavegador) return false;
    this.cancelarEspera();
    return irAAncla(this.documento, id);
  }

  private trasNavegar(fragmento: string): void {
    if (fragmento !== '' && irAAncla(this.documento, fragmento)) return;
    this.enfocarVista();
    if (fragmento !== '') this.esperarDestino(fragmento, true);
  }

  /** Espera (render a render) a que exista el destino del fragmento; ver la doc. de la clase. */
  private esperarDestino(fragmento: string, enfocar: boolean): void {
    if (this.documento.getElementById(fragmento) !== null) return;
    const ventana = this.documento.defaultView;
    let render: AfterRenderRef | null = null;
    const cancelar = (): void => {
      render?.destroy();
      render = null;
      ventana?.clearTimeout(temporizador);
      for (const tipo of EVENTOS_INTERACCION) {
        this.documento.removeEventListener(tipo, cancelar, true);
      }
      if (this.cancelarEsperaActual === cancelar) this.cancelarEsperaActual = null;
    };
    const temporizador = ventana?.setTimeout(cancelar, ESPERA_MAXIMA_FRAGMENTO_MS);
    for (const tipo of EVENTOS_INTERACCION) {
      this.documento.addEventListener(tipo, cancelar, { capture: true, passive: true });
    }
    render = afterEveryRender(
      () => {
        if (irAAncla(this.documento, fragmento, enfocar)) cancelar();
      },
      { injector: this.injector },
    );
    this.cancelarEsperaActual = cancelar;
  }

  private cancelarEspera(): void {
    this.cancelarEsperaActual?.();
  }
}
