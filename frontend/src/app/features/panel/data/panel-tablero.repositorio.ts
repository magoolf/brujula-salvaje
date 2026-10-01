/**
 * DATA: Tablero del panel (SCR-034, GET /api/v1/panel/tablero).
 */
import { Injectable, inject } from '@angular/core';

import { PanelTableroService } from '../../../api/services/panel-tablero.service';
import { TableroPanel } from '../domain/modelos';
import { mapTablero } from './panel.mapper';

@Injectable({ providedIn: 'root' })
export class PanelTableroRepositorio {
  private readonly api = inject(PanelTableroService);

  async tablero(): Promise<TableroPanel> {
    return mapTablero(await this.api.panelObtenerTablero());
  }
}
