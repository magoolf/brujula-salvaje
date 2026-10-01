import { Component, computed, input } from '@angular/core';
import { encode } from 'uqr';

/** Margen de módulos claros alrededor del código (zona silenciosa de la norma ISO/IEC 18004). */
const ZONA_SILENCIOSA = 4;

/**
 * Código QR generado en el navegador, sin terceros ni red (HANDOFF SCR-032, CON-003): la URI
 * otpauth nunca sale del cliente. Se dibuja como un SVG en línea (un único `path`, sin innerHTML),
 * con nombre accesible equivalente al alt de la especificación. Biblioteca: uqr (MIT).
 */
@Component({
  selector: 'app-codigo-qr',
  template: `
    <svg
      class="qr"
      role="img"
      [attr.aria-label]="textoAlternativo()"
      [attr.viewBox]="caja()"
      shape-rendering="crispEdges"
      data-testid="codigo-qr"
    >
      <rect [attr.width]="modulos().tamano" [attr.height]="modulos().tamano" fill="#ffffff" />
      <path [attr.d]="modulos().ruta" fill="#000000" />
    </svg>
  `,
  styles: `
    .qr {
      width: 12.5rem;
      height: 12.5rem;
      forced-color-adjust: none;
    }
  `,
})
export class CodigoQr {
  readonly contenido = input.required<string>();
  readonly textoAlternativo = input('Código QR para configurar tu aplicación autenticadora');

  protected readonly modulos = computed(() => {
    const qr = encode(this.contenido(), { ecc: 'M', border: ZONA_SILENCIOSA });
    const tramos: string[] = [];
    qr.data.forEach((fila, y) =>
      fila.forEach((oscuro, x) => {
        if (oscuro) tramos.push(`M${x} ${y}h1v1h-1z`);
      }),
    );
    return { tamano: qr.size, ruta: tramos.join('') };
  });
  protected readonly caja = computed(() => `0 0 ${this.modulos().tamano} ${this.modulos().tamano}`);
}
