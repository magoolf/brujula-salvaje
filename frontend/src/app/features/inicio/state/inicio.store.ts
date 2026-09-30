import { Injectable, computed, inject, resource } from '@angular/core';
import { Router } from '@angular/router';
import { from } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { normalizarError } from '../../../core/http/normalizar-error';
import { InicioRepositorio } from '../data/inicio.repositorio';

/** STATE de Inicio (SCR-001, FEAT-001). Un único recurso de lectura. */
@Injectable({ providedIn: 'root' })
export class InicioStore {
  private readonly repo = inject(InicioRepositorio);
  private readonly router = inject(Router);

  private readonly recurso = resource({ loader: () => this.repo.obtener() });

  // `hasValue()` evita que `.value()` lance al leerlo mientras el recurso está en error.
  readonly inicio = computed(() => (this.recurso.hasValue() ? this.recurso.value() : null));
  readonly cargando = computed(() => this.recurso.isLoading());
  readonly error = computed<ErrorApi | null>(() => {
    const error = this.recurso.error();
    return error ? normalizarError(error) : null;
  });

  recargar(): void {
    this.recurso.reload();
  }

  /**
   * FEAT-051/GI-08 «Sorpréndeme»: lectura disparada por una acción del usuario (comando, Regla
   * 11/12), no un recurso pasivo de la vista.
   */
  async sorprenderme(): Promise<ErrorApi | null> {
    return ejecutar(from(this.repo.destinoAleatorio()), (slug) => {
      void this.router.navigate(['/destinos', slug]);
    });
  }
}
