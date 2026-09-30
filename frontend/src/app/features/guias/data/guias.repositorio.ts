/**
 * DATA: única puerta de entrada HTTP de la feature Guías (Regla 01/02).
 */
import { Injectable, inject } from '@angular/core';

import { PublicoGeneralService } from '../../../api/services/publico-general.service';
import { PublicoGuiasService } from '../../../api/services/publico-guias.service';
import { RefTaxonomiaVista, PaginaCategorias, PaginaGuias, GuiaDetalle } from '../domain/modelos';
import { mapCategoria, mapGuiaDetalle, mapPaginaCategorias, mapPaginaGuias } from './guias.mapper';

@Injectable({ providedIn: 'root' })
export class GuiasRepositorio {
  private readonly guias = inject(PublicoGuiasService);
  private readonly general = inject(PublicoGeneralService);

  async listarCategorias(pagina: number): Promise<PaginaCategorias> {
    const dto = await this.guias.publicoListarCategoriasGuia({ pagina: pagina > 1 ? pagina : undefined });
    return mapPaginaCategorias(dto);
  }

  async categoria(slug: string): Promise<RefTaxonomiaVista & { readonly descripcion: string }> {
    const dto = await this.guias.publicoObtenerCategoriaGuia({ slug });
    return mapCategoria(dto);
  }

  async listarGuias(categoria: string | null, pagina: number): Promise<PaginaGuias> {
    const dto = await this.guias.publicoListarGuias({
      categoria: categoria ?? undefined,
      pagina: pagina > 1 ? pagina : undefined,
    });
    return mapPaginaGuias(dto);
  }

  async detalle(slug: string): Promise<GuiaDetalle> {
    const dto = await this.guias.publicoObtenerGuia({ slug });
    return mapGuiaDetalle(dto);
  }

  /** RULE-010: texto del descargo de responsabilidad. */
  async textoDescargo(): Promise<string> {
    const dto = await this.general.publicoObtenerConfiguracion();
    return dto.texto_descargo;
  }
}
