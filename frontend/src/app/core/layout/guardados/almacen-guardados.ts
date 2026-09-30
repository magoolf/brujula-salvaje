import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject } from '@angular/core';

import { ElementoGuardado, validarElementoGuardado } from './elemento-guardado.model';

const CLAVE_ALMACEN = 'bs-guardados-v1';
const CLAVE_PRUEBA = '__bs_prueba__';

/**
 * Adaptador de `localStorage` para los guardados (RULE-013, INT-001). Es la única pieza de la
 * aplicación que toca `window.localStorage`: aísla su disponibilidad (modo privado, cuota agotada,
 * SSR) y su formato de serialización. Los datos leídos se tratan como no confiables (THREAT-026):
 * pasan siempre por `validarElementoGuardado` antes de exponerse.
 */
@Injectable({ providedIn: 'root' })
export class AlmacenGuardados {
  private readonly storage: Storage | null;

  constructor() {
    this.storage = this.detectarStorage();
  }

  /** ALT-011: `false` cuando el almacenamiento local no existe o no se puede escribir. */
  estaDisponible(): boolean {
    return this.storage !== null;
  }

  leer(): readonly ElementoGuardado[] {
    if (this.storage === null) return [];
    try {
      const crudo = this.storage.getItem(CLAVE_ALMACEN);
      if (crudo === null) return [];
      const datos: unknown = JSON.parse(crudo);
      if (!Array.isArray(datos)) return [];
      return datos
        .map((valor) => validarElementoGuardado(valor))
        .filter((elemento): elemento is ElementoGuardado => elemento !== null);
    } catch {
      return [];
    }
  }

  /** @returns `true` si se pudo persistir. */
  escribir(lista: readonly ElementoGuardado[]): boolean {
    if (this.storage === null) return false;
    try {
      this.storage.setItem(CLAVE_ALMACEN, JSON.stringify(lista));
      return true;
    } catch {
      return false;
    }
  }

  private detectarStorage(): Storage | null {
    if (!isPlatformBrowser(inject(PLATFORM_ID))) return null;
    try {
      const ventana = inject(DOCUMENT).defaultView;
      const storage = ventana?.localStorage ?? null;
      if (storage === null) return null;
      // Safari en modo privado expone localStorage pero lanza al escribir: se comprueba en frío.
      storage.setItem(CLAVE_PRUEBA, '1');
      storage.removeItem(CLAVE_PRUEBA);
      return storage;
    } catch {
      return null;
    }
  }
}
