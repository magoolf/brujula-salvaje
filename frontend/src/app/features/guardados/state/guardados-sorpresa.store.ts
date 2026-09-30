import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { from } from 'rxjs';

import { ejecutar } from '../../../core/http/ejecutar';
import { ErrorApi } from '../../../core/http/error-api.model';
import { GuardadosRepositorio } from '../data/guardados.repositorio';

/** STATE: comando «Sorpréndeme» (GI-08) ofrecido desde el estado vacío de SCR-019. */
@Injectable({ providedIn: 'root' })
export class GuardadosSorpresaStore {
  private readonly repo = inject(GuardadosRepositorio);
  private readonly router = inject(Router);

  async sorprenderme(): Promise<ErrorApi | null> {
    return ejecutar(from(this.repo.destinoAleatorio()), (slug) => {
      void this.router.navigate(['/destinos', slug]);
    });
  }
}
