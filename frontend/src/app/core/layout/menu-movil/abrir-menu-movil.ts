import { Dialog, DialogRef } from '@angular/cdk/dialog';
import { Overlay } from '@angular/cdk/overlay';
import { Injector } from '@angular/core';

import { MenuMovil } from './menu-movil';

/**
 * Abre el cajón de navegación móvil (GI-01) sobre CDK Dialog. Vive en su propio módulo para que la
 * cabecera lo cargue bajo demanda (TKT-056): CDK Dialog + Overlay + el cajón suman ~87 kB sin
 * comprimir que antes iban en el bundle inicial de TODAS las rutas y solo se usan al pulsar Menú.
 */
export function abrirMenuMovil(injector: Injector, restaurarFoco: HTMLElement): DialogRef<unknown, MenuMovil> {
  const overlay = injector.get(Overlay);
  return injector.get(Dialog).open(MenuMovil, {
    ariaLabelledBy: 'menu-movil-titulo',
    backdropClass: 'bs-fondo-dialogo',
    positionStrategy: overlay.position().global().left('0').top('0'),
    autoFocus: 'first-tabbable',
    restoreFocus: restaurarFoco,
  });
}
