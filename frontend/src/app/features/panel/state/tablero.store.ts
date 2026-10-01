import { Injectable, computed, inject, resource } from '@angular/core';

import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { PanelTableroRepositorio } from '../data/panel-tablero.repositorio';
import { AlertaTablero } from '../domain/modelos';
import { accesosRapidos, enlaceDisponible } from '../domain/secciones';
import { esTableroVacio, hayAvisosDeSalud } from '../domain/tablero';
import { SesionPanelStore } from './sesion-panel.store';

/** STATE del Tablero (SCR-034, FEAT-033/049, AC_TKT010_09). */
@Injectable()
export class TableroStore {
  private readonly repo = inject(PanelTableroRepositorio);
  private readonly sesion = inject(SesionPanelStore);

  private readonly recurso = resource({ loader: () => this.repo.tablero() });

  readonly tablero = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });
  /** 403 en la feature → SCR-048 (Skill_Frontend §12). */
  readonly accesoDenegado = computed(() => this.error()?.categoria === 'permiso_denegado');
  readonly vacio = computed(() => {
    const tablero = this.tablero();
    return tablero !== null && esTableroVacio(tablero);
  });
  readonly mostrarSalud = computed(() => {
    const tablero = this.tablero();
    return tablero !== null && hayAvisosDeSalud(tablero);
  });
  /** Las alertas solo enlazan a secciones implementadas y permitidas al rol (RULE-030). */
  readonly alertas = computed<readonly AlertaTablero[]>(() => {
    const tablero = this.tablero();
    const rol = this.sesion.rol();
    if (tablero === null || rol === null) return [];
    return tablero.alertas.map((a) => ({ ...a, enlace: enlaceDisponible(a.enlace, rol) }));
  });
  readonly accesosRapidos = computed(() => {
    const rol = this.sesion.rol();
    return rol === null ? [] : accesosRapidos(rol);
  });
  readonly nombreVisible = computed(() => this.sesion.sesion()?.nombreVisible ?? '');

  recargar(): void {
    this.recurso.reload();
  }
}
