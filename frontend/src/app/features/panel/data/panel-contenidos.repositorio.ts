/**
 * DATA: única puerta HTTP de los contenidos del panel (MOD-010, /api/v1/panel/contenidos/** y los
 * catálogos que usa el editor). Usa el cliente generado desde el contrato (Skill_Frontend §27.3):
 * aquí viven las URL y los DTO; hacia arriba solo salen modelos de dominio.
 */
import { Injectable, inject } from '@angular/core';

import { ColeccionActualizacion } from '../../../api/models/coleccion-actualizacion';
import { ColeccionEntrada } from '../../../api/models/coleccion-entrada';
import { ColeccionVistaPrevia } from '../../../api/models/coleccion-vista-previa';
import { DestinoActualizacion } from '../../../api/models/destino-actualizacion';
import { DestinoEntrada } from '../../../api/models/destino-entrada';
import { DestinoVistaPrevia } from '../../../api/models/destino-vista-previa';
import { GuiaActualizacion } from '../../../api/models/guia-actualizacion';
import { GuiaEntrada } from '../../../api/models/guia-entrada';
import { GuiaVistaPrevia } from '../../../api/models/guia-vista-previa';
import { ItinerarioActualizacion } from '../../../api/models/itinerario-actualizacion';
import { ItinerarioEntrada } from '../../../api/models/itinerario-entrada';
import { ItinerarioVistaPrevia } from '../../../api/models/itinerario-vista-previa';
import { PaginaContenidoResumen } from '../../../api/models/pagina-contenido-resumen';
import { PaginaInstitucionalActualizacion } from '../../../api/models/pagina-institucional-actualizacion';
import { PaginaInstitucionalVistaPrevia } from '../../../api/models/pagina-institucional-vista-previa';
import { TerminoGlosarioActualizacion } from '../../../api/models/termino-glosario-actualizacion';
import { TerminoGlosarioEntrada } from '../../../api/models/termino-glosario-entrada';
import { TipoAventuraActualizacion } from '../../../api/models/tipo-aventura-actualizacion';
import { TipoAventuraEntrada } from '../../../api/models/tipo-aventura-entrada';
import { TipoAventuraVistaPrevia } from '../../../api/models/tipo-aventura-vista-previa';
import { VistaPrevia } from '../../../api/models/vista-previa';
import { PanelCicloEditorialService } from '../../../api/services/panel-ciclo-editorial.service';
import { PanelConfiguracionService } from '../../../api/services/panel-configuracion.service';
import { PanelContenidosService } from '../../../api/services/panel-contenidos.service';
import {
  AnalisisPublicacion,
  EntidadVersionada,
  ImpactoRetiro,
  PaginaRevisiones,
  ResultadoTransicion,
} from '../domain/ciclo-editorial';
import {
  ContenidoEditable,
  ContenidoResumen,
  FiltrosContenidos,
  PaginaContenidos,
  rutaDeTipo,
} from '../domain/contenidos';
import { FormularioContenido, OpcionCatalogo, RefContenido, aIdOpcional } from '../domain/formulario-contenido';
import { EstadoEditorial, TipoContenido } from '../domain/modelos';
import { VistaPreviaContenido } from '../domain/vista-previa';
import {
  ContenidoPanelDto,
  cuerpoDesdeFormulario,
  formularioDesdeRestauracion,
  mapAnalisis,
  mapContenido,
  mapImpacto,
  mapPaginaContenidos,
  mapResultado,
  mapRevisiones,
} from './contenidos.mapper';
import { mapVistaPrevia } from './vista-previa.mapper';

/** Páginas máximas que se leen de un catálogo (100 por página en taxonomías, 50 en contenidos). */
const PAGINAS_CATALOGO = 20;

/** Opciones de «Actualizar publicación» de un destino (co-publicación y cascada, CHG-API-005). */
export interface OpcionesActualizacion {
  readonly copublicarTipos: readonly EntidadVersionada[];
  readonly confirmarCascada: boolean;
  readonly cascadaConfirmada: readonly { readonly id: number; readonly tipo: TipoContenido }[];
}

/** Revisión restaurada en el formulario (FEAT-050): no persiste nada (AC-121). */
export interface RevisionRestaurada {
  readonly numero: number;
  readonly versionActual: number;
  readonly formulario: FormularioContenido;
}

interface ParamsListado {
  estado?: EstadoEditorial;
  q?: string;
  pagina?: number;
}

@Injectable({ providedIn: 'root' })
export class PanelContenidosRepositorio {
  private readonly api = inject(PanelContenidosService);
  private readonly ciclo = inject(PanelCicloEditorialService);
  private readonly configuracion = inject(PanelConfiguracionService);

  // -------------------------------------------------------------------------------- listado
  async listar(tipo: TipoContenido, filtros: FiltrosContenidos): Promise<PaginaContenidos> {
    const params: ParamsListado = {};
    if (filtros.estado !== null) params.estado = filtros.estado;
    if (filtros.q !== '') params.q = filtros.q;
    if (filtros.pagina > 1) params.pagina = filtros.pagina;
    return mapPaginaContenidos(await this.paginaListado(tipo, params));
  }

  private paginaListado(tipo: TipoContenido, params: ParamsListado): Promise<PaginaContenidoResumen> {
    switch (tipo) {
      case 'DESTINO':
        return this.api.panelListarDestinos(params);
      case 'ITINERARIO':
        return this.api.panelListarItinerarios(params);
      case 'GUIA':
        return this.api.panelListarGuias(params);
      case 'TIPO':
        return this.api.panelListarTiposAventura(params);
      case 'COLECCION':
        return this.api.panelListarColecciones(params);
      case 'TERMINO':
        return this.api.panelListarTerminosGlosario(params);
      case 'PAGINA':
        return this.api.panelListarPaginasInstitucionales(params.pagina ? { pagina: params.pagina } : {});
    }
  }

  // -------------------------------------------------------------------------------- CRUD
  async obtener(tipo: TipoContenido, id: number): Promise<ContenidoEditable> {
    return mapContenido(await this.dtoObtener(tipo, id));
  }

  private dtoObtener(tipo: TipoContenido, id: number): Promise<ContenidoPanelDto> {
    switch (tipo) {
      case 'DESTINO':
        return this.api.panelObtenerDestino({ id });
      case 'ITINERARIO':
        return this.api.panelObtenerItinerario({ id });
      case 'GUIA':
        return this.api.panelObtenerGuia({ id });
      case 'TIPO':
        return this.api.panelObtenerTipoAventura({ id });
      case 'COLECCION':
        return this.api.panelObtenerColeccion({ id });
      case 'TERMINO':
        return this.api.panelObtenerTerminoGlosario({ id });
      case 'PAGINA':
        return this.api.panelObtenerPaginaInstitucional({ id });
    }
  }

  /** Alta en BORRADOR (FLOW-011 paso 3). Las páginas institucionales no se crean (AC-033). */
  async crear(formulario: FormularioContenido, clave: string): Promise<ContenidoEditable> {
    const cuerpo = cuerpoDesdeFormulario(formulario);
    const p = { 'Idempotency-Key': clave };
    switch (formulario.tipo) {
      case 'DESTINO':
        return mapContenido(await this.api.panelCrearDestino({ ...p, body: cuerpo as DestinoEntrada }));
      case 'ITINERARIO':
        return mapContenido(await this.api.panelCrearItinerario({ ...p, body: cuerpo as ItinerarioEntrada }));
      case 'GUIA':
        return mapContenido(await this.api.panelCrearGuia({ ...p, body: cuerpo as GuiaEntrada }));
      case 'TIPO':
        return mapContenido(await this.api.panelCrearTipoAventura({ ...p, body: cuerpo as TipoAventuraEntrada }));
      case 'COLECCION':
        return mapContenido(await this.api.panelCrearColeccion({ ...p, body: cuerpo as ColeccionEntrada }));
      case 'TERMINO':
        return mapContenido(
          await this.api.panelCrearTerminoGlosario({ ...p, body: cuerpo as TerminoGlosarioEntrada }),
        );
      case 'PAGINA':
        throw new Error('Las páginas institucionales no se crean.');
    }
  }

  /**
   * Guardar borrador / Actualizar publicación (PUT con `version`, bloqueo optimista ALT-016). En un
   * destino PUBLICADO, `opciones` lleva la co-publicación y la confirmación de la cascada.
   */
  async actualizar(
    id: number,
    formulario: FormularioContenido,
    version: number,
    opciones: OpcionesActualizacion | null = null,
  ): Promise<ContenidoEditable> {
    const cuerpo = { ...cuerpoDesdeFormulario(formulario), version };
    switch (formulario.tipo) {
      case 'DESTINO': {
        const body: DestinoActualizacion = {
          ...(cuerpo as DestinoActualizacion),
          ...(opciones === null
            ? {}
            : {
                copublicar_tipos: opciones.copublicarTipos.map((t) => ({ id: t.id, version: t.version })),
                confirmar_cascada: opciones.confirmarCascada,
                cascada_confirmada: opciones.cascadaConfirmada.map((e) => ({ id: e.id, tipo: e.tipo })),
              }),
        };
        const dto = await this.api.panelActualizarDestino({ id, body });
        return mapContenido(dto, dto.entidades_afectadas);
      }
      case 'ITINERARIO':
        return mapContenido(await this.api.panelActualizarItinerario({ id, body: cuerpo as ItinerarioActualizacion }));
      case 'GUIA':
        return mapContenido(await this.api.panelActualizarGuia({ id, body: cuerpo as GuiaActualizacion }));
      case 'TIPO':
        return mapContenido(
          await this.api.panelActualizarTipoAventura({ id, body: cuerpo as TipoAventuraActualizacion }),
        );
      case 'COLECCION':
        return mapContenido(await this.api.panelActualizarColeccion({ id, body: cuerpo as ColeccionActualizacion }));
      case 'TERMINO':
        return mapContenido(
          await this.api.panelActualizarTerminoGlosario({ id, body: cuerpo as TerminoGlosarioActualizacion }),
        );
      case 'PAGINA':
        return mapContenido(
          await this.api.panelActualizarPaginaInstitucional({ id, body: cuerpo as PaginaInstitucionalActualizacion }),
        );
    }
  }

  /** Eliminar un borrador nunca publicado (DEC-AUTO-045, irreversible). */
  async eliminar(tipo: TipoContenido, id: number, version: number): Promise<void> {
    const p = { id, version };
    switch (tipo) {
      case 'DESTINO':
        return this.api.panelEliminarDestino(p);
      case 'ITINERARIO':
        return this.api.panelEliminarItinerario(p);
      case 'GUIA':
        return this.api.panelEliminarGuia(p);
      case 'TIPO':
        return this.api.panelEliminarTipoAventura(p);
      case 'COLECCION':
        return this.api.panelEliminarColeccion(p);
      case 'TERMINO':
        return this.api.panelEliminarTerminoGlosario(p);
      case 'PAGINA':
        throw new Error('Las páginas institucionales no se eliminan.');
    }
  }

  // -------------------------------------------------------------------------------- SCR-037
  /** Vista previa sin persistir (FEAT-035). `id` null: contenido nuevo (DEC-AUTO-120). */
  async vistaPrevia(formulario: FormularioContenido, id: number | null): Promise<VistaPreviaContenido> {
    return mapVistaPrevia(await this.dtoVistaPrevia(formulario, id));
  }

  private dtoVistaPrevia(formulario: FormularioContenido, id: number | null): Promise<VistaPrevia> {
    const cuerpo = { ...cuerpoDesdeFormulario(formulario), ...(id === null ? {} : { id }) };
    switch (formulario.tipo) {
      case 'DESTINO':
        return this.api.panelVistaPreviaDestino({ body: cuerpo as DestinoVistaPrevia });
      case 'ITINERARIO':
        return this.api.panelVistaPreviaItinerario({ body: cuerpo as ItinerarioVistaPrevia });
      case 'GUIA':
        return this.api.panelVistaPreviaGuia({ body: cuerpo as GuiaVistaPrevia });
      case 'TIPO':
        return this.api.panelVistaPreviaTipoAventura({ body: cuerpo as TipoAventuraVistaPrevia });
      case 'COLECCION':
        return this.api.panelVistaPreviaColeccion({ body: cuerpo as ColeccionVistaPrevia });
      case 'PAGINA':
        return this.api.panelVistaPreviaPaginaInstitucional({ body: cuerpo as PaginaInstitucionalVistaPrevia });
      case 'TERMINO':
        throw new Error('El glosario no tiene vista previa.');
    }
  }

  // -------------------------------------------------------------------------------- SCR-038
  /**
   * Análisis sin efectos (CHG-API-005). En un destino PUBLICADO se envían los tipos del formulario
   * (sin guardar) para calcular co-publicación y cascada.
   */
  async analizar(
    tipo: TipoContenido,
    id: number,
    version: number,
    tiposPropuestos: { readonly tipos: readonly number[]; readonly principal: string } | null,
  ): Promise<AnalisisPublicacion> {
    const body =
      tiposPropuestos === null
        ? { version }
        : {
            version,
            tipos_ids: [...tiposPropuestos.tipos],
            tipo_principal_id: aIdOpcional(tiposPropuestos.principal),
          };
    return mapAnalisis(await this.ciclo.panelAnalizarPublicacion({ tipo: rutaDeTipo(tipo), id, body }));
  }

  async publicar(
    tipo: TipoContenido,
    id: number,
    version: number,
    copublicarTipos: readonly EntidadVersionada[],
    clave: string,
  ): Promise<ResultadoTransicion> {
    const body =
      tipo === 'DESTINO'
        ? { version, copublicar_tipos: copublicarTipos.map((t) => ({ id: t.id, version: t.version })) }
        : { version };
    return mapResultado(
      await this.ciclo.panelPublicarContenido({ tipo: rutaDeTipo(tipo), id, 'Idempotency-Key': clave, body }),
    );
  }

  async impactoRetiro(tipo: TipoContenido, id: number): Promise<ImpactoRetiro> {
    return mapImpacto(await this.ciclo.panelObtenerImpactoRetiro({ tipo: rutaDeTipo(tipo), id }));
  }

  async retirar(
    tipo: TipoContenido,
    id: number,
    version: number,
    motivo: string,
    cascada: readonly { readonly id: number; readonly tipo: TipoContenido }[],
    clave: string,
  ): Promise<ResultadoTransicion> {
    const body = {
      version,
      motivo: motivo.trim(),
      confirmar_cascada: cascada.length > 0,
      cascada_confirmada: cascada.map((e) => ({ id: e.id, tipo: e.tipo })),
    };
    return mapResultado(
      await this.ciclo.panelRetirarContenido({ tipo: rutaDeTipo(tipo), id, 'Idempotency-Key': clave, body }),
    );
  }

  async reactivar(tipo: TipoContenido, id: number, version: number, clave: string): Promise<ResultadoTransicion> {
    return mapResultado(
      await this.ciclo.panelReactivarContenido({
        tipo: rutaDeTipo(tipo),
        id,
        'Idempotency-Key': clave,
        body: { version },
      }),
    );
  }

  // -------------------------------------------------------------------------------- revisiones
  async revisiones(tipo: TipoContenido, id: number, pagina = 1): Promise<PaginaRevisiones> {
    return mapRevisiones(
      await this.ciclo.panelListarRevisiones({ tipo: rutaDeTipo(tipo), id, ...(pagina > 1 ? { pagina } : {}) }),
    );
  }

  /** Carga una revisión en el formulario (audita RESTAURAR_REVISION; no cambia nada público). */
  async restaurar(tipo: TipoContenido, id: number, numero: number): Promise<RevisionRestaurada> {
    const dto = await this.ciclo.panelRestaurarRevision({ tipo: rutaDeTipo(tipo), id, numero });
    return {
      numero: dto.numero_revision,
      versionActual: dto.version_actual,
      formulario: formularioDesdeRestauracion(tipo, dto.datos, null),
    };
  }

  // -------------------------------------------------------------------------------- catálogos
  async paises(): Promise<readonly OpcionCatalogo[]> {
    const todas: OpcionCatalogo[] = [];
    for (let pagina = 1; pagina <= PAGINAS_CATALOGO; pagina++) {
      const dto = await this.configuracion.panelListarPaises(pagina > 1 ? { pagina } : {});
      todas.push(
        ...dto.resultados
          .filter((p) => p.activo !== false)
          .map((p) => ({ id: p.id, nombre: p.nombre ?? `País #${p.id}` })),
      );
      if (dto.siguiente === null || pagina >= dto.total_paginas) break;
    }
    return todas.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  }

  async categoriasGuia(): Promise<readonly OpcionCatalogo[]> {
    const todas: OpcionCatalogo[] = [];
    for (let pagina = 1; pagina <= PAGINAS_CATALOGO; pagina++) {
      const dto = await this.configuracion.panelListarCategoriasGuia(pagina > 1 ? { pagina } : {});
      todas.push(
        ...dto.resultados
          .filter((c) => c.activo !== false)
          .map((c) => ({ id: c.id, nombre: c.nombre ?? `Categoría #${c.id}` })),
      );
      if (dto.siguiente === null || pagina >= dto.total_paginas) break;
    }
    return todas;
  }

  /** Todos los tipos de aventura (cualquier estado: los BORRADOR se co-publican, RULE-025). */
  async tiposAventura(): Promise<readonly OpcionCatalogo[]> {
    const todos: OpcionCatalogo[] = [];
    for (let pagina = 1; pagina <= PAGINAS_CATALOGO; pagina++) {
      const dto = await this.api.panelListarTiposAventura(pagina > 1 ? { pagina } : {});
      todos.push(...dto.resultados.map((t) => ({ id: t.id, nombre: t.titulo, estado: t.estado_editorial })));
      if (dto.siguiente === null || pagina >= dto.total_paginas) break;
    }
    return todos.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  }

  /** Búsqueda para los combobox (relacionados, destino, elementos, términos): primera página. */
  async buscar(
    tipos: readonly TipoContenido[],
    q: string,
    estado: EstadoEditorial | null,
  ): Promise<readonly RefContenido[]> {
    const filtros: FiltrosContenidos = { estado, q, pagina: 1 };
    const paginas = await Promise.all(tipos.map((t) => this.listar(t, filtros)));
    return paginas
      .flatMap((p) => p.contenidos)
      .map((c: ContenidoResumen) => ({ id: c.id, tipo: c.tipo, titulo: c.titulo, estado: c.estado }));
  }
}
