import { DOCUMENT, ViewportScroller, isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject } from '@angular/core';

/** Borde del viewport que tapa un elemento fijo/sticky del panel. */
export type BordeReserva = 'arriba' | 'abajo';

/**
 * Borde en el que un elemento sticky/fixed se queda pegado según su estilo calculado (`top` o
 * `bottom` distinto de `auto`); null si no está fijado.
 */
export function bordeFijado(elemento: HTMLElement): BordeReserva | null {
  const estilo = elemento.ownerDocument.defaultView?.getComputedStyle(elemento);
  if (estilo === undefined || (estilo.position !== 'sticky' && estilo.position !== 'fixed')) return null;
  if (fijado(estilo.top)) return 'arriba';
  if (fijado(estilo.bottom)) return 'abajo';
  return null;
}

function fijado(valor: string): boolean {
  return valor !== '' && valor !== 'auto';
}

/**
 * Separación extra entre el borde de la barra y el destino: deja a la vista el anillo de foco
 * (3 px + 2 px de separación, ACCESSIBILITY_SPEC.Focus_Management) y algo de aire.
 */
export const HOLGURA_FOCO_PX = 8;

/** Prefijo de la custom property con la altura medida de cada barra (`--panel-alto-<clave>`). */
const PREFIJO_VARIABLE = '--panel-alto-';

interface Reserva {
  readonly borde: BordeReserva;
  readonly alto: number;
}

/**
 * Reserva de desplazamiento del panel (TKT-070, WCAG 2.4.11 Foco no oculto).
 *
 * La barra superior del panel (sticky) mide más que los 80 px que reserva `html` para la cabecera
 * pública (crece al envolver su contenido en móvil) y la barra de estado del editor es sticky inferior
 * < lg: un ancla, un `scrollIntoView` o el desplazamiento al tabular dejaban el destino debajo de
 * ellas. Cada barra se registra aquí con su borde; se mide con `ResizeObserver` y la suma por borde se
 * aplica al contenedor de desplazamiento (el documento):
 * - `scroll-padding-top|bottom` en `html`: lo respetan `scrollIntoView`, los saltos a anclas del
 *   navegador y el desplazamiento al mover el foco (Tab);
 * - el offset del `ViewportScroller`: el `anchorScrolling` del Router desplaza con `window.scrollTo`
 *   y no atiende a `scroll-padding`;
 * - `--panel-alto-<clave>` en `html`: para que otros elementos sticky se coloquen bajo la barra.
 * Al dejar de haber reservas (se sale del panel) se retiran: el sitio público vuelve a su base.css.
 */
@Injectable({
  providedIn: 'root',
})
export class ReservaDesplazamiento {
  private readonly documento = inject(DOCUMENT);
  private readonly scroller = inject(ViewportScroller);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly reservas = new Map<string, Reserva>();

  /**
   * Observa `elemento` y reserva su altura en el borde que indique `borde()` (null: no tapa nada, p.
   * ej. porque en ese punto de corte no es sticky o va en otra columna). Devuelve la función que
   * cancela la observación y retira la reserva.
   */
  observar(clave: string, elemento: HTMLElement, borde: () => BordeReserva | null): () => void {
    if (!this.esNavegador) return () => undefined;
    const ventana = this.documento.defaultView;
    const medir = (): void => {
      const lado = borde();
      const alto = Math.ceil(elemento.getBoundingClientRect().height);
      if (lado === null || alto <= 0) this.retirar(clave);
      else this.reservar(clave, lado, alto);
    };
    medir();
    const observador = typeof ResizeObserver === 'function' ? new ResizeObserver(medir) : null;
    observador?.observe(elemento);
    // Un cambio de punto de corte puede cambiar el borde sin cambiar el tamaño.
    ventana?.addEventListener('resize', medir, { passive: true });
    return () => {
      observador?.disconnect();
      ventana?.removeEventListener('resize', medir);
      this.retirar(clave);
    };
  }

  /** Suma de las reservas de un borde, sin holgura (px). */
  total(borde: BordeReserva): number {
    let suma = 0;
    for (const r of this.reservas.values()) if (r.borde === borde) suma += r.alto;
    return suma;
  }

  reservar(clave: string, borde: BordeReserva, alto: number): void {
    const previa = this.reservas.get(clave);
    if (previa?.borde === borde && previa.alto === alto) return;
    this.reservas.set(clave, { borde, alto });
    this.aplicar(clave);
  }

  retirar(clave: string): void {
    if (!this.reservas.delete(clave)) return;
    this.aplicar(clave);
  }

  private aplicar(clave: string): void {
    const estilo = this.documento.documentElement.style;
    const reserva = this.reservas.get(clave);
    if (reserva === undefined) estilo.removeProperty(PREFIJO_VARIABLE + clave);
    else estilo.setProperty(PREFIJO_VARIABLE + clave, `${reserva.alto}px`);

    const arriba = this.margenSuperior();
    const abajo = this.total('abajo');
    if (arriba > 0) estilo.setProperty('scroll-padding-top', `${arriba}px`);
    else estilo.removeProperty('scroll-padding-top');
    if (abajo > 0) estilo.setProperty('scroll-padding-bottom', `${abajo + HOLGURA_FOCO_PX}px`);
    else estilo.removeProperty('scroll-padding-bottom');

    if (this.reservas.size === 0) this.scroller.setOffset([0, 0]);
    else this.scroller.setOffset(() => [0, this.margenSuperior()]);
  }

  /** Lo que el Router debe dejar libre arriba al saltar a un ancla (px). */
  private margenSuperior(): number {
    const arriba = this.total('arriba');
    return arriba > 0 ? arriba + HOLGURA_FOCO_PX : 0;
  }
}
