import { Injectable } from '@angular/core';

import { FormularioContenido } from '../domain/formulario-contenido';
import { TipoContenido } from '../domain/modelos';

/** Formulario en memoria de un editor abierto (sin persistir). */
export interface BorradorEnMemoria {
  readonly formulario: FormularioContenido;
  /** Versión del servidor sobre la que se editaba (null en el alta). */
  readonly version: number | null;
}

/**
 * STATE: formulario sin guardar del editor mientras el usuario está en la Vista previa (SCR-037,
 * DEC-AUTO-120: también de contenido nuevo). Solo vive en memoria de la pestaña (nunca en
 * localStorage: puede contener texto aún no publicado); al volver al editor se recupera y se
 * descarta. Sin señales públicas escribibles (Regla 03).
 */
@Injectable({ providedIn: 'root' })
export class MemoriaEditor {
  private readonly borradores = new Map<string, BorradorEnMemoria>();
  private aviso: string | null = null;

  /** Mensaje para la pantalla siguiente (p. ej. «Borrador guardado» tras el alta). */
  dejarAviso(aviso: string): void {
    this.aviso = aviso;
  }

  tomarAviso(): string | null {
    const aviso = this.aviso;
    this.aviso = null;
    return aviso;
  }

  static clave(tipo: TipoContenido, id: number | null): string {
    return `${tipo}:${id ?? 'nuevo'}`;
  }

  guardar(tipo: TipoContenido, id: number | null, borrador: BorradorEnMemoria): void {
    this.borradores.set(MemoriaEditor.clave(tipo, id), borrador);
  }

  leer(tipo: TipoContenido, id: number | null): BorradorEnMemoria | null {
    return this.borradores.get(MemoriaEditor.clave(tipo, id)) ?? null;
  }

  /** Lee y descarta (el editor lo recupera una sola vez). */
  tomar(tipo: TipoContenido, id: number | null): BorradorEnMemoria | null {
    const borrador = this.leer(tipo, id);
    this.borradores.delete(MemoriaEditor.clave(tipo, id));
    return borrador;
  }

  olvidar(tipo: TipoContenido, id: number | null): void {
    this.borradores.delete(MemoriaEditor.clave(tipo, id));
  }
}
