import { inject } from '@angular/core';
import {
  CanActivateChildFn,
  CanActivateFn,
  CanMatchFn,
  RedirectCommand,
  Router,
} from '@angular/router';

import {
  RUTA_ACCESO_PANEL,
  destinoTrasAcceso,
  esDestinoSeguro,
} from '../../../core/auth/destino-seguro';
import { RUTA_ACCESO_DENEGADO, esPasoDeCuentaObligatorio, rutaParaPaso } from '../domain/acceso';
import { PasoPendiente, RolPanel } from '../domain/modelos';
import { puedeAcceder } from '../domain/secciones';
import { CargaPanelStore } from '../state/carga-panel.store';
import { SesionPanelStore } from '../state/sesion-panel.store';

/**
 * Guards de navegación del panel (Skill_Frontend §5.1: los guards pertenecen a UI). El servidor es
 * la autoridad (deny-by-default, THREAT-004): estos guards solo evitan mostrar pantallas que la API
 * rechazaría y llevan a la pantalla correcta del FLOW-010.
 */

/** Clave de `data` con el rol mínimo de una ruta del panel (TKT-022/023/024 la usan). */
export const DATO_ROL_MINIMO = 'rolMinimo';

/**
 * Carga completa de una URL del panel con la sesión aún sin leer (QA TKT-010 OBS-C3-01): la ruta de
 * carga (CargaPanel, sin guards) coincide al instante, recuerda la URL y muestra el armazón mínimo
 * mientras se resuelve la sesión. Síncrono: nunca espera a la API.
 */
export const sesionSinResolverMatch: CanMatchFn = () => {
  const carga = inject(CargaPanelStore);
  if (!carga.necesitaCarga()) return false;
  carga.recordarDestino();
  return true;
};

/**
 * Armazón del panel (TPL-PANEL-SHELL): exige sesión completa. Sin sesión → SCR-030 con un
 * `siguiente` seguro (ST-UNAUTHORIZED, AC-115); con un paso pendiente → la pantalla de ese paso.
 */
export const sesionCompletaGuard: CanActivateFn = async (_ruta, estado) => {
  const store = inject(SesionPanelStore);
  const router = inject(Router);
  const sesion = await store.asegurar();
  if (sesion === null) {
    const queryParams = esDestinoSeguro(estado.url) ? { siguiente: estado.url } : {};
    return router.createUrlTree([RUTA_ACCESO_PANEL], { queryParams });
  }
  if (sesion.pasoPendiente !== 'NINGUNO') {
    return router.parseUrl(rutaParaPaso(sesion.pasoPendiente, sesion.redireccion));
  }
  return true;
};

/**
 * Rol de cada ruta hija (`data.rolMinimo`). Sin permiso → SCR-048 conservando en la barra de
 * direcciones la URL que se intentó abrir (ST-FORBIDDEN, AC-105; `browserUrl`).
 */
export const rolGuard: CanActivateChildFn = (ruta, estado) => {
  const rolMinimo = ruta.data[DATO_ROL_MINIMO] as RolPanel | undefined;
  if (rolMinimo === undefined) return true;
  const store = inject(SesionPanelStore);
  if (puedeAcceder(store.rol(), rolMinimo)) return true;
  const router = inject(Router);
  return new RedirectCommand(router.parseUrl(RUTA_ACCESO_DENEGADO), { browserUrl: estado.url });
};

/**
 * SCR-030: siempre relee la sesión (puede venir de un cierre o de una expiración). Con la sesión
 * completa no tiene sentido volver a entrar: va al destino seguro o al Tablero.
 */
export const accesoGuard: CanActivateFn = async (ruta) => {
  // inject() antes de cualquier await: después se pierde el contexto de inyección.
  const store = inject(SesionPanelStore);
  const router = inject(Router);
  const sesion = await store.cargar();
  if (sesion?.pasoPendiente === 'NINGUNO') {
    return router.parseUrl(destinoTrasAcceso(ruta.queryParamMap.get('siguiente')));
  }
  return true;
};

/**
 * El armazón de acceso solo atiende rutas con segmentos (acceso, verificación, autorización,
 * cuenta): con /panel a secas el router debe pasar al armazón del panel (Tablero). Sin esta guarda,
 * un padre con path '' y sin hijo coincidente se activaría vacío.
 */
export const conSegmentosMatch: CanMatchFn = (_ruta, segmentos) => segmentos.length > 0;

/** Pantallas de un paso del FLOW-010 (SCR-031, SCR-033): solo con ese paso pendiente. */
export function pasoGuard(paso: PasoPendiente): CanActivateFn {
  return async () => {
    const store = inject(SesionPanelStore);
    const router = inject(Router);
    const sesion = await store.asegurar();
    if (sesion === null) return router.parseUrl(RUTA_ACCESO_PANEL);
    if (sesion.pasoPendiente !== paso) {
      return router.parseUrl(rutaParaPaso(sesion.pasoPendiente, sesion.redireccion));
    }
    return true;
  };
}

/**
 * SCR-032 en modo obligatorio (cambio de contraseña o configurar MFA): se monta en el armazón de
 * acceso, sin navegación. Si no aplica, la ruta /panel/cuenta del armazón normal la atiende.
 */
export const cuentaObligatoriaMatch: CanMatchFn = async () => {
  const sesion = await inject(SesionPanelStore).asegurar();
  return sesion !== null && esPasoDeCuentaObligatorio(sesion.pasoPendiente);
};
