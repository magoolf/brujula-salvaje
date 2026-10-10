/**
 * DATA: única puerta HTTP de la configuración editorial del panel (MOD-012, TKT-024):
 * /api/v1/panel/inicio, /api/v1/panel/configuracion y /api/v1/panel/taxonomias/**. Usa el cliente
 * generado desde el contrato (Skill_Frontend §27.3); hacia arriba solo salen modelos de dominio.
 */
import { Injectable, inject } from '@angular/core';

import { PanelConfiguracionService } from '../../../api/services/panel-configuracion.service';
import { ConfiguracionSitio, EntradaConfiguracion } from '../domain/configuracion-sitio';
import { ConfigInicio, EntradaDestacados } from '../domain/destacados';
import {
  Catalogo,
  ElementoCatalogo,
  EntradaCatalogo,
  EntradaNivelEscala,
  EscalasPanel,
  NivelEscalaPanel,
} from '../domain/taxonomias';
import {
  aConfigInicioDto,
  aConfiguracionDto,
  aCategoriaDto,
  aLicenciaDto,
  aPaisDto,
  aRegionDto,
  mapCategoria,
  mapConfigInicio,
  mapConfiguracion,
  mapEscalas,
  mapLicenciaCatalogo,
  mapNivel,
  mapPais,
  mapRegion,
} from './configuracion.mapper';

/** Páginas máximas que se leen de un catálogo (100 por página, contrato). */
const PAGINAS_CATALOGO = 20;

interface PaginaDto<T> {
  readonly resultados: readonly T[];
  readonly siguiente?: string | null;
  readonly total_paginas: number;
}

async function leerTodo<T, R>(
  pedir: (pagina: number) => Promise<PaginaDto<T>>,
  mapear: (dto: T) => R,
): Promise<readonly R[]> {
  const todos: R[] = [];
  for (let pagina = 1; pagina <= PAGINAS_CATALOGO; pagina++) {
    const dto = await pedir(pagina);
    todos.push(...dto.resultados.map(mapear));
    if (dto.siguiente === null || dto.siguiente === undefined || pagina >= dto.total_paginas) break;
  }
  return todos;
}

@Injectable({ providedIn: 'root' })
export class PanelConfiguracionRepositorio {
  private readonly api = inject(PanelConfiguracionService);

  // ---------------------------------------------------------------- destacados (SCR-042)
  async inicio(): Promise<ConfigInicio> {
    return mapConfigInicio(await this.api.panelObtenerConfigInicio());
  }

  async guardarInicio(entrada: EntradaDestacados): Promise<ConfigInicio> {
    return mapConfigInicio(await this.api.panelActualizarConfigInicio({ body: aConfigInicioDto(entrada) }));
  }

  // ---------------------------------------------------------------- configuración (SCR-047)
  async configuracion(): Promise<ConfiguracionSitio> {
    return mapConfiguracion(await this.api.panelObtenerConfiguracionSitio());
  }

  async guardarConfiguracion(entrada: EntradaConfiguracion): Promise<ConfiguracionSitio> {
    return mapConfiguracion(await this.api.panelActualizarConfiguracionSitio({ body: aConfiguracionDto(entrada) }));
  }

  // ---------------------------------------------------------------- taxonomías (SCR-043)
  /** Todos los elementos de un catálogo (activos e inactivos). */
  listar(catalogo: Exclude<Catalogo, 'escalas'>): Promise<readonly ElementoCatalogo[]> {
    const params = (pagina: number) => (pagina > 1 ? { pagina } : {});
    switch (catalogo) {
      case 'regiones':
        return leerTodo((p) => this.api.panelListarRegiones(params(p)), mapRegion);
      case 'paises':
        return leerTodo((p) => this.api.panelListarPaises(params(p)), mapPais);
      case 'categorias':
        return leerTodo((p) => this.api.panelListarCategoriasGuia(params(p)), mapCategoria);
      case 'licencias':
        return leerTodo((p) => this.api.panelListarLicencias(params(p)), mapLicenciaCatalogo);
    }
  }

  async crear(entrada: EntradaCatalogo): Promise<ElementoCatalogo> {
    switch (entrada.catalogo) {
      case 'regiones':
        return mapRegion(await this.api.panelCrearRegion({ body: aRegionDto(entrada) }));
      case 'paises':
        return mapPais(await this.api.panelCrearPais({ body: aPaisDto(entrada) }));
      case 'categorias':
        return mapCategoria(await this.api.panelCrearCategoriaGuia({ body: aCategoriaDto(entrada) }));
      case 'licencias':
        return mapLicenciaCatalogo(await this.api.panelCrearLicencia({ body: aLicenciaDto(entrada) }));
    }
  }

  async actualizar(id: number, entrada: EntradaCatalogo): Promise<ElementoCatalogo> {
    switch (entrada.catalogo) {
      case 'regiones':
        return mapRegion(await this.api.panelActualizarRegion({ id, body: aRegionDto(entrada) }));
      case 'paises':
        return mapPais(await this.api.panelActualizarPais({ id, body: aPaisDto(entrada) }));
      case 'categorias':
        return mapCategoria(await this.api.panelActualizarCategoriaGuia({ id, body: aCategoriaDto(entrada) }));
      case 'licencias':
        return mapLicenciaCatalogo(await this.api.panelActualizarLicencia({ id, body: aLicenciaDto(entrada) }));
    }
  }

  async escalas(): Promise<EscalasPanel> {
    return mapEscalas(await this.api.panelObtenerEscalas());
  }

  async actualizarNivel(id: number, entrada: EntradaNivelEscala): Promise<NivelEscalaPanel> {
    return mapNivel(
      await this.api.panelActualizarNivelEscala({
        id,
        body: { etiqueta: entrada.etiqueta, descripcion: entrada.descripcion },
      }),
    );
  }
}
