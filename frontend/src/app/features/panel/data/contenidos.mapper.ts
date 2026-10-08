/**
 * DATA: traducción entre el contrato de /api/v1/panel/contenidos/** (DTO generados) y el dominio
 * del editor de contenidos (TKT-023). Los DTO no salen de esta carpeta (Regla 04). También lee los
 * miembros de extensión de los Problem Details del ciclo editorial (`errores_por_entidad`,
 * `impacto_cascada`, `usos`…) que la normalización común deja en `ErrorApi.extra`.
 */
import { AnalisisPublicacion as AnalisisDto } from '../../../api/models/analisis-publicacion';
import { BloqueoCascada as BloqueoDto } from '../../../api/models/bloqueo-cascada';
import { ColeccionPanel } from '../../../api/models/coleccion-panel';
import { ContenidoComunCampos } from '../../../api/models/contenido-comun-campos';
import { ContenidoPanelMeta } from '../../../api/models/contenido-panel-meta';
import { ContenidoRefPanel } from '../../../api/models/contenido-ref-panel';
import { ContenidoResumenPanel } from '../../../api/models/contenido-resumen-panel';
import { DestinoCampos } from '../../../api/models/destino-campos';
import { DestinoPanel } from '../../../api/models/destino-panel';
import { EntidadTransitada as EntidadTransitadaDto } from '../../../api/models/entidad-transitada';
import { ErrorRegla } from '../../../api/models/error-regla';
import { GuiaCampos } from '../../../api/models/guia-campos';
import { GuiaPanel } from '../../../api/models/guia-panel';
import { ImpactoRetiro as ImpactoDto } from '../../../api/models/impacto-retiro';
import { ItinerarioCampos } from '../../../api/models/itinerario-campos';
import { ItinerarioPanel } from '../../../api/models/itinerario-panel';
import { PaginaContenidoResumen } from '../../../api/models/pagina-contenido-resumen';
import { PaginaInstitucionalCampos } from '../../../api/models/pagina-institucional-campos';
import { PaginaInstitucionalPanel } from '../../../api/models/pagina-institucional-panel';
import { PaginaRevisionResumen } from '../../../api/models/pagina-revision-resumen';
import { RequisitosPublicacion as RequisitosDto } from '../../../api/models/requisitos-publicacion';
import { ResultadoTransicion as ResultadoDto } from '../../../api/models/resultado-transicion';
import { TerminoGlosarioCampos } from '../../../api/models/termino-glosario-campos';
import { TerminoGlosarioPanel } from '../../../api/models/termino-glosario-panel';
import { TipoAventuraCampos } from '../../../api/models/tipo-aventura-campos';
import { TipoAventuraPanel } from '../../../api/models/tipo-aventura-panel';
import { ValidacionEntidad as ValidacionDto } from '../../../api/models/validacion-entidad';
import {
  AnalisisPublicacion,
  BloqueoCascada,
  EntidadTransitada,
  ErroresEntidad,
  ImpactoCascada,
  ImpactoRetiro,
  PaginaRevisiones,
  Requisito,
  RequisitosPublicacion,
  ResultadoTransicion,
  RolEntidad,
  SeccionDestacada,
  UsoBloqueante,
  ValidacionEntidad,
} from '../domain/ciclo-editorial';
import { ContenidoEditable, ContenidoResumen, PaginaContenidos } from '../domain/contenidos';
import {
  ChecklistItemForm,
  DiaForm,
  ElementoColeccionForm,
  FormularioContenido,
  FuenteForm,
  MedioRef,
  OpcionCatalogo,
  RefContenido,
  aDecimal,
  aEntero,
  aIdOpcional,
  formularioVacio,
  redondearCoordenada,
} from '../domain/formulario-contenido';
import { EstadoMedio } from '../domain/medios';
import { EstadoEditorial, TipoContenido } from '../domain/modelos';

/** Cualquier DTO de contenido del panel (respuesta de obtener/crear/actualizar). */
export type ContenidoPanelDto =
  | DestinoPanel
  | ItinerarioPanel
  | GuiaPanel
  | TipoAventuraPanel
  | ColeccionPanel
  | TerminoGlosarioPanel
  | PaginaInstitucionalPanel;

/** Campos que un DTO de contenido puede traer (unión de todos los `*Campos`). */
type CamposDto = ContenidoComunCampos &
  DestinoCampos &
  ItinerarioCampos &
  GuiaCampos &
  TipoAventuraCampos &
  Omit<TerminoGlosarioCampos, 'titulo' | 'slug' | 'fecha_ultima_revision'> &
  Omit<PaginaInstitucionalCampos, 'titulo' | 'fecha_ultima_revision' | 'seo_titulo' | 'seo_descripcion' | 'cuerpo'> & {
    cuerpo?: string | null;
    elementos?: ColeccionPanel['elementos'];
  };

type Referencias = ContenidoPanelMeta['referencias'];

const ESTADOS_EDITORIALES: readonly EstadoEditorial[] = ['BORRADOR', 'PUBLICADO', 'RETIRADO'];
const TIPOS: readonly TipoContenido[] = ['DESTINO', 'ITINERARIO', 'GUIA', 'TIPO', 'COLECCION', 'TERMINO', 'PAGINA'];
const ESTADOS_MEDIO: readonly EstadoMedio[] = ['PENDIENTE_METADATOS', 'DISPONIBLE', 'RETIRADO'];

// ---------------------------------------------------------------------------------------------
// Listado (SCR-035)
// ---------------------------------------------------------------------------------------------
export function mapResumen(dto: ContenidoResumenPanel): ContenidoResumen {
  return {
    id: dto.id,
    tipo: dto.tipo,
    titulo: dto.titulo,
    slug: dto.slug ?? null,
    estado: dto.estado_editorial,
    fechaRevision: dto.fecha_ultima_revision ?? null,
    actualizadoEn: new Date(dto.actualizado_en),
    actualizadoPor: dto.actualizado_por.etiqueta,
    publicado: dto.publicado,
    urlPublica: dto.publicado && dto.url_publica ? dto.url_publica : null,
  };
}

export function mapPaginaContenidos(dto: PaginaContenidoResumen): PaginaContenidos {
  return {
    contenidos: dto.resultados.map(mapResumen),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
    total: dto.total,
  };
}

// ---------------------------------------------------------------------------------------------
// Claves del contrato ↔ claves del formulario (errores y requisitos enlazables al campo)
// ---------------------------------------------------------------------------------------------
const CAMPO_API: Readonly<Record<string, string>> = {
  titulo: 'titulo',
  slug: 'slug',
  fecha_ultima_revision: 'fechaRevision',
  seo_titulo: 'seoTitulo',
  seo_descripcion: 'seoDescripcion',
  fuentes: 'fuentes',
  relaciones: 'relaciones',
  terminos_ids: 'terminos',
  resumen: 'resumen',
  descripcion_experta: 'descripcion',
  descripcion: 'descripcion',
  cuerpo: 'descripcion',
  definicion: 'definicion',
  pais_id: 'pais',
  tipos_ids: 'tipos',
  tipo_principal_id: 'tipoPrincipal',
  dificultad: 'dificultad',
  meses_mejor_epoca: 'meses',
  duracion_min_dias: 'duracionMin',
  duracion_max_dias: 'duracionMax',
  nivel_presupuesto: 'presupuesto',
  clima: 'clima',
  altitud_max_m: 'altitud',
  como_llegar: 'comoLlegar',
  seguridad_riesgos: 'seguridad',
  sostenibilidad: 'sostenibilidad',
  latitud: 'latitud',
  longitud: 'longitud',
  portada_id: 'portada',
  galeria_ids: 'galeria',
  destino_id: 'destino',
  duracion_dias: 'duracionDias',
  distancia_total_km: 'distanciaTotal',
  desnivel_acumulado_m: 'desnivelAcumulado',
  dias: 'dias',
  riesgos_seguridad: 'riesgos',
  categoria_id: 'categoria',
  destinos_ids: 'destinos',
  remite_a_metodologia: 'remiteMetodologia',
  nivel_exigencia: 'nivelExigencia',
  orden: 'orden',
  checklist: 'checklist',
  elementos: 'elementos',
  version_documento: 'versionDocumento',
  vigente_desde: 'vigenteDesde',
  _general: '_general',
};

const SUBCAMPO_API: Readonly<Record<string, string>> = {
  titulo: 'titulo',
  actividades: 'actividades',
  distancia_km: 'distanciaKm',
  desnivel_positivo_m: 'desnivelPositivo',
  desnivel_negativo_m: 'desnivelNegativo',
  alojamiento_orientativo: 'alojamiento',
  consejos: 'consejos',
  url: 'url',
  entidad_editora: 'entidadEditora',
  fecha_consulta: 'fechaConsulta',
  texto: 'texto',
  grupo: 'grupo',
  esencial: 'esencial',
  contenido_id: 'contenido',
  nota_editorial: 'nota',
  numero_dia: 'titulo',
};

/**
 * Clave del formulario para una clave del contrato ('dias.2.titulo' → 'dias.2.titulo',
 * 'descripcion_experta' → 'descripcion'). Las desconocidas van a '_general' (ErrorSummary).
 */
export function campoFormulario(campoApi: string): string {
  const [raiz, indice, sub] = campoApi.split('.');
  const campo = CAMPO_API[raiz];
  if (campo === undefined) return '_general';
  if (indice === undefined) return campo;
  if (!/^\d+$/.test(indice)) return campo;
  if (sub === undefined) return `${campo}.${indice}`;
  return `${campo}.${indice}.${SUBCAMPO_API[sub] ?? sub}`;
}

/** Errores por campo de un 400/422 (`ErrorApi.campos`) en claves del formulario. */
export function erroresDeFormulario(
  campos: Readonly<Record<string, readonly string[]>>,
): Readonly<Record<string, string>> {
  const errores: Record<string, string> = {};
  for (const [campoApi, mensajes] of Object.entries(campos)) {
    // Los errores de los tipos co-publicados (`copublicar_tipos.{id}.{campo}`) se muestran por
    // entidad en SCR-038, no en el formulario del destino.
    if (campoApi.startsWith('copublicar_tipos')) continue;
    const campo = campoFormulario(campoApi);
    if (mensajes.length === 0) continue;
    errores[campo] = errores[campo] ? `${errores[campo]} ${mensajes[0]}` : mensajes[0];
  }
  return errores;
}

// ---------------------------------------------------------------------------------------------
// Requisitos, análisis, impacto y transiciones (SCR-038)
// ---------------------------------------------------------------------------------------------
export function mapRef(dto: ContenidoRefPanel): RefContenido {
  return { id: dto.id, tipo: dto.tipo, titulo: dto.titulo, estado: dto.estado_editorial };
}

export function mapRequisito(dto: ErrorRegla): Requisito {
  return {
    campo: campoFormulario(dto.campo),
    codigo: dto.code,
    mensaje: dto.mensaje,
    referencias: (dto.referencias ?? []).map(mapRef),
  };
}

export function mapRequisitos(dto: RequisitosDto): RequisitosPublicacion {
  return { cumple: dto.cumple, pendientes: dto.pendientes.map(mapRequisito) };
}

function mapValidacion(dto: ValidacionDto): ValidacionEntidad {
  return {
    id: dto.id,
    tipo: dto.tipo,
    titulo: dto.titulo,
    estado: dto.estado_editorial,
    version: dto.version,
    rol: dto.rol,
    cumple: dto.cumple,
    pendientes: dto.pendientes.map(mapRequisito),
  };
}

function mapBloqueo(dto: BloqueoDto): BloqueoCascada {
  return {
    tipoAventura: mapRef(dto.tipo_aventura),
    itinerarios: dto.itinerarios.map(mapRef),
    totalItinerarios: dto.total_itinerarios,
  };
}

export function mapAnalisis(dto: AnalisisDto): AnalisisPublicacion {
  return {
    operacion: dto.operacion,
    confirmable: dto.confirmable,
    entidad: mapValidacion(dto.entidad),
    copublicacion: dto.copublicacion.map(mapValidacion),
    copublicarTipos: dto.copublicar_tipos.map((t) => ({ id: t.id, version: t.version })),
    tiposEnCascada: dto.tipos_en_cascada.map(mapRef),
    bloqueosCascada: dto.bloqueos_cascada.map(mapBloqueo),
  };
}

export function mapImpacto(dto: ImpactoDto): ImpactoRetiro {
  return {
    retirable: dto.retirable,
    bloqueos: dto.bloqueos.map((u) => ({
      id: u.id,
      tipoEntidad: u.tipo_entidad,
      titulo: u.titulo,
      estado: u.estado_editorial ?? null,
    })),
    bloqueosCascada: dto.bloqueos_cascada.map(mapBloqueo),
    itinerariosEnCascada: dto.itinerarios_en_cascada.map(mapRef),
    tiposEnCascada: dto.tipos_en_cascada.map(mapRef),
    colecciones: dto.colecciones.map(mapRef),
    destacados: dto.destacados,
    enlacesEntrantes: dto.enlaces_entrantes,
  };
}

function mapEntidadTransitada(dto: EntidadTransitadaDto): EntidadTransitada {
  return {
    id: dto.id,
    tipo: dto.tipo,
    titulo: dto.titulo,
    estado: dto.estado_editorial,
    version: dto.version,
    origen: dto.origen,
    urlPublica: dto.url_publica ?? null,
  };
}

export function mapResultado(dto: ResultadoDto): ResultadoTransicion {
  return {
    id: dto.id,
    estado: dto.estado_editorial,
    version: dto.version,
    urlPublica: dto.url_publica ?? null,
    entidades: dto.entidades.map(mapEntidadTransitada),
  };
}

export function mapRevisiones(dto: PaginaRevisionResumen): PaginaRevisiones {
  return {
    revisiones: dto.resultados.map((r) => ({
      numero: r.numero_revision,
      creadaEn: new Date(r.creado_en),
      creadaPor: r.creado_por.etiqueta,
      motivo: r.motivo,
    })),
    pagina: dto.pagina,
    totalPaginas: dto.total_paginas,
  };
}

// ---------------------------------------------------------------------------------------------
// Miembros de extensión de los Problem Details (ErrorApi.extra): lectura defensiva
// ---------------------------------------------------------------------------------------------
function esObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === 'object' && valor !== null && !Array.isArray(valor);
}

function lista(valor: unknown): readonly Record<string, unknown>[] {
  return Array.isArray(valor) ? valor.filter(esObjeto) : [];
}

function texto(valor: unknown): string | null {
  return typeof valor === 'string' ? valor : null;
}

function entero(valor: unknown): number | null {
  return typeof valor === 'number' && Number.isInteger(valor) ? valor : null;
}

function refDesde(valor: Record<string, unknown>): RefContenido | null {
  const id = entero(valor['id']);
  const tipo = TIPOS.find((t) => t === valor['tipo']) ?? null;
  if (id === null || tipo === null) return null;
  return {
    id,
    tipo,
    titulo: texto(valor['titulo']) ?? `#${id}`,
    estado: ESTADOS_EDITORIALES.find((e) => e === valor['estado_editorial']) ?? null,
  };
}

function refs(valor: unknown): readonly RefContenido[] {
  return lista(valor)
    .map(refDesde)
    .filter((r): r is RefContenido => r !== null);
}

function requisitoDesde(valor: Record<string, unknown>): Requisito {
  return {
    campo: campoFormulario(texto(valor['campo']) ?? '_general'),
    codigo: texto(valor['code']) ?? '',
    mensaje: texto(valor['mensaje']) ?? '',
    referencias: refs(valor['referencias']),
  };
}

const ROLES: readonly RolEntidad[] = ['PRINCIPAL', 'COPUBLICACION', 'CASCADA'];

/** `errores_por_entidad` de un 422 publicacion_invalida (FLOW-011 6a'). */
export function leerErroresPorEntidad(extra: Readonly<Record<string, unknown>>): readonly ErroresEntidad[] {
  return lista(extra['errores_por_entidad']).flatMap((e) => {
    const ref = refDesde(e);
    if (ref === null) return [];
    return [
      {
        id: ref.id,
        tipo: ref.tipo,
        titulo: ref.titulo,
        rol: ROLES.find((r) => r === e['rol']) ?? 'PRINCIPAL',
        errores: lista(e['errores']).map(requisitoDesde),
      },
    ];
  });
}

function bloqueosDesde(valor: unknown): readonly BloqueoCascada[] {
  return lista(valor).flatMap((b) => {
    const tipo = esObjeto(b['tipo_aventura']) ? refDesde(b['tipo_aventura']) : null;
    if (tipo === null) return [];
    const itinerarios = refs(b['itinerarios']);
    return [
      {
        tipoAventura: tipo,
        itinerarios,
        totalItinerarios: entero(b['total_itinerarios']) ?? itinerarios.length,
      },
    ];
  });
}

/** `impacto_cascada` de un 409 cascada_sin_confirmar / impacto_modificado. */
export function leerImpactoCascada(extra: Readonly<Record<string, unknown>>): ImpactoCascada | null {
  const impacto = extra['impacto_cascada'];
  if (!esObjeto(impacto)) return null;
  return {
    itinerariosEnCascada: refs(impacto['itinerarios_en_cascada']),
    tiposEnCascada: refs(impacto['tipos_en_cascada']),
    bloqueosCascada: bloqueosDesde(impacto['bloqueos_cascada']),
  };
}

/** `bloqueos_cascada` de un 409 cascada_bloqueada. */
export function leerBloqueosCascada(extra: Readonly<Record<string, unknown>>): readonly BloqueoCascada[] {
  return bloqueosDesde(extra['bloqueos_cascada']);
}

/** `usos` de un 409 dependencia_bloqueante / cascada_bloqueada (RULE-007). */
export function leerUsos(extra: Readonly<Record<string, unknown>>): readonly UsoBloqueante[] {
  return lista(extra['usos']).flatMap((u) => {
    const id = entero(u['id']);
    if (id === null) return [];
    return [
      {
        id,
        tipoEntidad: texto(u['tipo_entidad']) ?? '',
        titulo: texto(u['titulo']) ?? `#${id}`,
        estado: ESTADOS_EDITORIALES.find((e) => e === u['estado_editorial']) ?? null,
      },
    ];
  });
}

/** `entidades_en_conflicto` de un 409 conflicto_version multi-entidad. */
export function leerEntidadesEnConflicto(
  extra: Readonly<Record<string, unknown>>,
): readonly RefContenido[] {
  return refs(extra['entidades_en_conflicto']);
}

// ---------------------------------------------------------------------------------------------
// DTO de contenido → formulario
// ---------------------------------------------------------------------------------------------
let secuenciaClaves = 0;
/** Clave local estable de un elemento de lista (track), nunca enviada al servidor. */
export function nuevaClaveLista(prefijo: string): string {
  secuenciaClaves += 1;
  return `${prefijo}-${secuenciaClaves}`;
}

function textoDe(valor: string | null | undefined): string {
  return valor ?? '';
}

function numeroDe(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? '' : String(valor);
}

function medioRef(id: number, referencias: Referencias | null): MedioRef {
  const medio = referencias?.medios?.find((m) => m.id === id);
  return {
    id,
    estado: ESTADOS_MEDIO.find((e) => e === medio?.estado) ?? null,
    miniatura: medio?.url_miniatura ?? null,
    textoAlternativo: medio?.texto_alternativo ?? null,
  };
}

function refContenido(tipo: TipoContenido, id: number, referencias: Referencias | null): RefContenido {
  const ref = referencias?.contenidos?.find((c) => c.id === id && c.tipo === tipo);
  return ref ? mapRef(ref) : { id, tipo, titulo: `${tipo === 'DESTINO' ? 'Destino' : 'Contenido'} #${id}`, estado: null };
}

function opcionTermino(id: number, referencias: Referencias | null): OpcionCatalogo {
  const termino = referencias?.terminos?.find((t) => t.id === id);
  return { id, nombre: termino?.termino ?? `Término #${id}` };
}

/**
 * Valores del formulario desde los campos de un contenido. `referencias` aporta los datos de
 * visualización (miniaturas, títulos); en una revisión restaurada se usan los del contenido actual.
 */
export function formularioDesdeCampos(
  tipo: TipoContenido,
  campos: CamposDto,
  referencias: Referencias | null,
): FormularioContenido {
  const vacio = formularioVacio(tipo);
  const descripcion =
    tipo === 'DESTINO' ? campos.descripcion_experta : tipo === 'GUIA' || tipo === 'PAGINA' ? campos.cuerpo : campos.descripcion;
  return {
    ...vacio,
    titulo: textoDe(campos.titulo),
    slug: textoDe(campos.slug),
    fechaRevision: textoDe(campos.fecha_ultima_revision),
    seoTitulo: textoDe(campos.seo_titulo),
    seoDescripcion: textoDe(campos.seo_descripcion),
    fuentes: (campos.fuentes ?? []).map(
      (f): FuenteForm => ({
        clave: nuevaClaveLista('fuente'),
        titulo: f.titulo,
        url: textoDe(f.url),
        entidadEditora: textoDe(f.entidad_editora),
        fechaConsulta: textoDe(f.fecha_consulta),
      }),
    ),
    relaciones: (campos.relaciones ?? []).map((r) => refContenido(r.tipo, r.id, referencias)),
    terminos: (campos.terminos_ids ?? []).map((id) => opcionTermino(id, referencias)),
    resumen: textoDe(campos.resumen),
    descripcion: textoDe(descripcion),
    portada: campos.portada_id ? medioRef(campos.portada_id, referencias) : null,
    galeria: (campos.galeria_ids ?? []).map((id) => medioRef(id, referencias)),
    tipos: [...(campos.tipos_ids ?? [])],
    dificultad: numeroDe(campos.dificultad),
    pais: numeroDe(campos.pais_id),
    tipoPrincipal: numeroDe(campos.tipo_principal_id),
    meses: [...(campos.meses_mejor_epoca ?? [])],
    duracionMin: numeroDe(campos.duracion_min_dias),
    duracionMax: numeroDe(campos.duracion_max_dias),
    presupuesto: numeroDe(campos.nivel_presupuesto),
    clima: textoDe(campos.clima),
    altitud: numeroDe(campos.altitud_max_m),
    comoLlegar: textoDe(campos.como_llegar),
    seguridad: textoDe(campos.seguridad_riesgos),
    sostenibilidad: textoDe(campos.sostenibilidad),
    latitud: numeroDe(campos.latitud),
    longitud: numeroDe(campos.longitud),
    destino: campos.destino_id ? refContenido('DESTINO', campos.destino_id, referencias) : null,
    duracionDias: numeroDe(campos.duracion_dias),
    distanciaTotal: numeroDe(campos.distancia_total_km),
    desnivelAcumulado: numeroDe(campos.desnivel_acumulado_m),
    dias: [...(campos.dias ?? [])]
      .sort((a, b) => a.numero_dia - b.numero_dia)
      .map(
        (d): DiaForm => ({
          clave: nuevaClaveLista('dia'),
          titulo: d.titulo,
          actividades: d.actividades,
          distanciaKm: numeroDe(d.distancia_km),
          desnivelPositivo: numeroDe(d.desnivel_positivo_m),
          desnivelNegativo: numeroDe(d.desnivel_negativo_m),
          alojamiento: textoDe(d.alojamiento_orientativo),
          consejos: textoDe(d.consejos),
        }),
      ),
    riesgos: textoDe(campos.riesgos_seguridad),
    categoria: numeroDe(campos.categoria_id),
    destinos: (campos.destinos_ids ?? []).map((id) => refContenido('DESTINO', id, referencias)),
    remiteMetodologia: campos.remite_a_metodologia ?? false,
    nivelExigencia: numeroDe(campos.nivel_exigencia),
    orden: numeroDe(campos.orden ?? 0),
    checklist: [...(campos.checklist ?? [])]
      .sort((a, b) => a.orden - b.orden)
      .map(
        (c): ChecklistItemForm => ({
          clave: nuevaClaveLista('item'),
          texto: c.texto,
          grupo: textoDe(c.grupo),
          esencial: c.esencial,
        }),
      ),
    elementos: [...(campos.elementos ?? [])]
      .sort((a, b) => a.orden - b.orden)
      .map(
        (e): ElementoColeccionForm => ({
          clave: nuevaClaveLista('elemento'),
          contenido: refContenido(e.tipo_contenido, e.contenido_id, referencias),
          nota: textoDe(e.nota_editorial),
        }),
      ),
    definicion: textoDe(campos.definicion),
    versionDocumento: textoDe(campos.version_documento),
    vigenteDesde: textoDe(campos.vigente_desde),
  };
}

export function mapContenido(dto: ContenidoPanelDto, entidadesAfectadas: readonly EntidadTransitadaDto[] = []): ContenidoEditable {
  const campos = dto as unknown as CamposDto;
  const pagina = dto.tipo === 'PAGINA' ? (dto as PaginaInstitucionalPanel) : null;
  const termino = dto.tipo === 'TERMINO' ? (dto as TerminoGlosarioPanel) : null;
  return {
    id: dto.id,
    tipo: dto.tipo,
    estado: dto.estado_editorial,
    version: dto.version,
    slugBloqueado: dto.slug_bloqueado,
    nuncaPublicado: !dto.primera_publicacion_en,
    urlPublica: dto.url_publica ?? null,
    actualizadoEn: new Date(dto.actualizado_en),
    actualizadoPor: dto.actualizado_por.etiqueta,
    motivoRetiro: dto.motivo_retiro ?? null,
    soloAdministrador: pagina?.solo_administrador ?? false,
    vinculadoEn: (termino?.vinculado_en ?? []).map(mapRef),
    requisitos: mapRequisitos(dto.requisitos_publicacion),
    formulario: formularioDesdeCampos(dto.tipo, campos, dto.referencias),
    entidadesAfectadas: entidadesAfectadas.map(mapEntidadTransitada),
  };
}

// ---------------------------------------------------------------------------------------------
// Formulario → cuerpo de la petición (solo los campos del tipo: unevaluatedProperties false)
// ---------------------------------------------------------------------------------------------
function nulo(valor: string): string | null {
  const limpio = valor.trim();
  return limpio === '' ? null : limpio;
}

/** HTML vacío ('' o un párrafo vacío del editor) se envía como null. */
function htmlONulo(valor: string): string | null {
  const limpio = valor.trim();
  return limpio === '' || /^<p>(\s|<br\s*\/?>)*<\/p>$/i.test(limpio) ? null : limpio;
}

function enteroONulo(valor: string): number | null {
  const n = aEntero(valor);
  return n === null || Number.isNaN(n) ? null : n;
}

function decimalONulo(valor: string): number | null {
  const n = aDecimal(valor);
  return n === null || Number.isNaN(n) ? null : n;
}

function coordenada(valor: string): number | null {
  const n = decimalONulo(valor);
  return n === null ? null : redondearCoordenada(n);
}

type Cuerpo = Record<string, unknown>;

/** Cuerpo de una petición de contenido: siempre lleva el título (requerido por el contrato). */
export interface CuerpoContenido {
  readonly titulo: string;
  readonly [campo: string]: unknown;
}

function comunes(f: FormularioContenido): CuerpoContenido {
  return {
    titulo: f.titulo.trim(),
    slug: nulo(f.slug),
    fecha_ultima_revision: nulo(f.fechaRevision),
    seo_titulo: nulo(f.seoTitulo),
    seo_descripcion: nulo(f.seoDescripcion),
    relaciones: f.relaciones.map((r) => ({ tipo: r.tipo, id: r.id })),
    terminos_ids: f.terminos.map((t) => t.id),
    fuentes: f.fuentes.map((fuente) => ({
      titulo: fuente.titulo.trim(),
      url: nulo(fuente.url),
      entidad_editora: nulo(fuente.entidadEditora),
      fecha_consulta: nulo(fuente.fechaConsulta),
    })),
  };
}

function camposDestino(f: FormularioContenido): Cuerpo {
  return {
    pais_id: aIdOpcional(f.pais),
    resumen: nulo(f.resumen),
    descripcion_experta: htmlONulo(f.descripcion),
    tipos_ids: [...f.tipos],
    tipo_principal_id: aIdOpcional(f.tipoPrincipal),
    dificultad: enteroONulo(f.dificultad),
    meses_mejor_epoca: [...f.meses],
    duracion_min_dias: enteroONulo(f.duracionMin),
    duracion_max_dias: enteroONulo(f.duracionMax),
    nivel_presupuesto: enteroONulo(f.presupuesto),
    clima: nulo(f.clima),
    altitud_max_m: enteroONulo(f.altitud),
    como_llegar: htmlONulo(f.comoLlegar),
    seguridad_riesgos: htmlONulo(f.seguridad),
    sostenibilidad: htmlONulo(f.sostenibilidad),
    latitud: coordenada(f.latitud),
    longitud: coordenada(f.longitud),
    portada_id: f.portada?.id ?? null,
    galeria_ids: f.galeria.map((m) => m.id),
  };
}

function camposItinerario(f: FormularioContenido): Cuerpo {
  return {
    destino_id: f.destino?.id ?? null,
    resumen: nulo(f.resumen),
    duracion_dias: enteroONulo(f.duracionDias),
    dificultad: enteroONulo(f.dificultad),
    tipos_ids: [...f.tipos],
    distancia_total_km: decimalONulo(f.distanciaTotal),
    desnivel_acumulado_m: enteroONulo(f.desnivelAcumulado),
    riesgos_seguridad: htmlONulo(f.riesgos),
    portada_id: f.portada?.id ?? null,
    galeria_ids: f.galeria.map((m) => m.id),
    dias: f.dias.map((d, i) => ({
      numero_dia: i + 1,
      titulo: d.titulo.trim(),
      actividades: d.actividades.trim(),
      distancia_km: decimalONulo(d.distanciaKm),
      desnivel_positivo_m: enteroONulo(d.desnivelPositivo),
      desnivel_negativo_m: enteroONulo(d.desnivelNegativo),
      alojamiento_orientativo: nulo(d.alojamiento),
      consejos: htmlONulo(d.consejos),
    })),
  };
}

function camposGuia(f: FormularioContenido): Cuerpo {
  return {
    categoria_id: aIdOpcional(f.categoria),
    resumen: nulo(f.resumen),
    cuerpo: htmlONulo(f.descripcion),
    destinos_ids: f.destinos.map((d) => d.id),
    tipos_ids: [...f.tipos],
    remite_a_metodologia: f.remiteMetodologia,
    portada_id: f.portada?.id ?? null,
  };
}

function camposTipo(f: FormularioContenido): Cuerpo {
  return {
    resumen: nulo(f.resumen),
    descripcion: htmlONulo(f.descripcion),
    nivel_exigencia: enteroONulo(f.nivelExigencia),
    portada_id: f.portada?.id ?? null,
    orden: enteroONulo(f.orden) ?? 0,
    checklist: f.checklist.map((c, i) => ({
      texto: c.texto.trim(),
      grupo: nulo(c.grupo),
      esencial: c.esencial,
      orden: i,
    })),
  };
}

function camposColeccion(f: FormularioContenido): Cuerpo {
  return {
    resumen: nulo(f.resumen),
    descripcion: htmlONulo(f.descripcion),
    portada_id: f.portada?.id ?? null,
    elementos: f.elementos.map((e, i) => ({
      tipo_contenido: e.contenido.tipo,
      contenido_id: e.contenido.id,
      orden: i,
      nota_editorial: nulo(e.nota),
    })),
  };
}

/**
 * Cuerpo de crear / vista previa / actualizar (sin `version`) para el tipo del formulario.
 * El término y la página no usan los campos comunes (sus esquemas no los incluyen).
 */
export function cuerpoDesdeFormulario(f: FormularioContenido): CuerpoContenido {
  switch (f.tipo) {
    case 'TERMINO':
      return {
        titulo: f.titulo.trim(),
        slug: nulo(f.slug),
        definicion: nulo(f.definicion),
        fecha_ultima_revision: nulo(f.fechaRevision),
      };
    case 'PAGINA':
      return {
        titulo: f.titulo.trim(),
        cuerpo: f.descripcion.trim(),
        version_documento: f.versionDocumento.trim(),
        vigente_desde: f.vigenteDesde,
        fecha_ultima_revision: nulo(f.fechaRevision),
        seo_titulo: nulo(f.seoTitulo),
        seo_descripcion: nulo(f.seoDescripcion),
      };
    case 'DESTINO':
      return { ...comunes(f), ...camposDestino(f) };
    case 'ITINERARIO':
      return { ...comunes(f), ...camposItinerario(f) };
    case 'GUIA':
      return { ...comunes(f), ...camposGuia(f) };
    case 'TIPO':
      return { ...comunes(f), ...camposTipo(f) };
    case 'COLECCION':
      return { ...comunes(f), ...camposColeccion(f) };
  }
}

/** `datos` de una revisión restaurada (forma `{Tipo}Actualizacion` sin `version`). */
export function formularioDesdeRestauracion(
  tipo: TipoContenido,
  datos: object,
  referencias: Referencias | null,
): FormularioContenido {
  return formularioDesdeCampos(tipo, datos as CamposDto, referencias);
}
