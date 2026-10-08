/**
 * Dominio de los contenidos editoriales del panel (MOD-010, TKT-023): los 7 tipos, sus rutas,
 * etiquetas y capacidades, las acciones permitidas por estado (STATE-001) y los filtros del Listado
 * (SCR-035). Puro: sin Angular ni RxJS (Skill_Frontend Regla 08).
 */
import { EntidadTransitada, RequisitosPublicacion } from './ciclo-editorial';
import { FormularioContenido, RefContenido } from './formulario-contenido';
import { EstadoEditorial, RolPanel, TipoContenido } from './modelos';

/** Contenido cargado en el editor (SCR-036): metadatos del servidor + valores del formulario. */
export interface ContenidoEditable {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly estado: EstadoEditorial;
  /** Bloqueo optimista (ALT-016, AC-110). */
  readonly version: number;
  /** RULE-008: el slug no cambia tras la primera publicación. */
  readonly slugBloqueado: boolean;
  readonly nuncaPublicado: boolean;
  readonly urlPublica: string | null;
  readonly actualizadoEn: Date;
  readonly actualizadoPor: string;
  readonly motivoRetiro: string | null;
  /** Páginas legales: solo Administrador (RULE-014). */
  readonly soloAdministrador: boolean;
  /** Término del glosario: contenidos que lo vinculan (solo lectura). */
  readonly vinculadoEn: readonly RefContenido[];
  readonly requisitos: RequisitosPublicacion;
  readonly formulario: FormularioContenido;
  /** Tipos co-publicados o retirados en cascada al «Actualizar publicación» (CHG-API-005). */
  readonly entidadesAfectadas: readonly EntidadTransitada[];
}

/** Segmento de la URL de cada tipo (igual que el `TipoContenidoRuta` del contrato). */
export type RutaTipo =
  | 'destinos'
  | 'itinerarios'
  | 'guias'
  | 'tipos-aventura'
  | 'colecciones'
  | 'glosario'
  | 'paginas';

export const RUTA_CONTENIDO = '/panel/contenido';

interface DefinicionTipo {
  readonly ruta: RutaTipo;
  readonly plural: string;
  readonly singular: string;
  /** Artículo para «Nuevo destino» / «Nueva guía». */
  readonly femenino: boolean;
  /** Prefijo público del slug (Slug: «/destinos/»). */
  readonly prefijoPublico: string;
}

export const DEFINICION_TIPO: Readonly<Record<TipoContenido, DefinicionTipo>> = {
  DESTINO: { ruta: 'destinos', plural: 'Destinos', singular: 'destino', femenino: false, prefijoPublico: '/destinos/' },
  ITINERARIO: { ruta: 'itinerarios', plural: 'Itinerarios', singular: 'itinerario', femenino: false, prefijoPublico: '/itinerarios/' },
  GUIA: { ruta: 'guias', plural: 'Guías', singular: 'guía', femenino: true, prefijoPublico: '/guias/' },
  TIPO: { ruta: 'tipos-aventura', plural: 'Tipos de aventura', singular: 'tipo de aventura', femenino: false, prefijoPublico: '/tipos-de-aventura/' },
  COLECCION: { ruta: 'colecciones', plural: 'Colecciones', singular: 'colección', femenino: true, prefijoPublico: '/colecciones/' },
  TERMINO: { ruta: 'glosario', plural: 'Glosario', singular: 'término', femenino: false, prefijoPublico: '/glosario#' },
  PAGINA: { ruta: 'paginas', plural: 'Páginas institucionales', singular: 'página', femenino: true, prefijoPublico: '/' },
};

export const TIPOS_CONTENIDO: readonly TipoContenido[] = [
  'DESTINO',
  'ITINERARIO',
  'GUIA',
  'TIPO',
  'COLECCION',
  'TERMINO',
  'PAGINA',
];

export function tipoDeRuta(ruta: string | null | undefined): TipoContenido | null {
  return TIPOS_CONTENIDO.find((t) => DEFINICION_TIPO[t].ruta === ruta) ?? null;
}

export function rutaDeTipo(tipo: TipoContenido): RutaTipo {
  return DEFINICION_TIPO[tipo].ruta;
}

export function rutaListado(tipo: TipoContenido): string {
  return `${RUTA_CONTENIDO}/${rutaDeTipo(tipo)}`;
}

/** Ruta del editor: `/nuevo` para el alta (id null). */
export function rutaEditor(tipo: TipoContenido, id: number | null): string {
  return `${rutaListado(tipo)}/${id === null ? 'nuevo' : id}`;
}

/** SCR-037: también de contenido nuevo, desde el formulario en memoria (DEC-AUTO-120). */
export function rutaVistaPrevia(tipo: TipoContenido, id: number | null): string {
  return `${rutaEditor(tipo, id)}/vista-previa`;
}

function mayuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** «Nuevo destino», «Nueva guía». */
export function textoNuevo(tipo: TipoContenido): string {
  const def = DEFINICION_TIPO[tipo];
  return `${def.femenino ? 'Nueva' : 'Nuevo'} ${def.singular}`;
}

/** h1 del editor: «Nuevo destino» / «Editar destino: {título}». */
export function tituloEditor(tipo: TipoContenido, titulo: string | null): string {
  if (titulo === null) return textoNuevo(tipo);
  return `Editar ${DEFINICION_TIPO[tipo].singular}: ${titulo.trim() || 'sin título'}`;
}

export function etiquetaSingular(tipo: TipoContenido): string {
  return mayuscula(DEFINICION_TIPO[tipo].singular);
}

/** «Aún no hay destinos». */
export function textoListadoVacio(tipo: TipoContenido): string {
  return `Aún no hay ${DEFINICION_TIPO[tipo].plural.toLowerCase()}`;
}

/** Las páginas institucionales siempre existen: no se crean, eliminan ni retiran (AC-033). */
export function puedeCrear(tipo: TipoContenido): boolean {
  return tipo !== 'PAGINA';
}

/** El glosario no tiene vista previa en el contrato (no tiene plantilla pública propia). */
export function tieneVistaPrevia(tipo: TipoContenido): boolean {
  return tipo !== 'TERMINO';
}

/** Ciclo BORRADOR/PUBLICADO/RETIRADO completo (las páginas se guardan publicadas, AC-033). */
export function tieneCicloEditorial(tipo: TipoContenido): boolean {
  return tipo !== 'PAGINA';
}

/**
 * Páginas legales (todas menos «Acerca de»): solo las edita el Administrador (RULE-014). El
 * listado no trae la clave, pero los slugs de las 4 páginas son fijos (selectors.SLUG_PAGINA).
 */
export const SLUG_ACERCA_DE = 'acerca-de';

export function paginaSoloAdministrador(slug: string | null): boolean {
  return slug !== SLUG_ACERCA_DE;
}

export function puedeEditarPagina(rol: RolPanel | null, soloAdministrador: boolean): boolean {
  return !soloAdministrador || rol === 'ADMINISTRADOR';
}

// ---------------------------------------------------------------------------------------------
// STATE-001: acciones del editor según el estado (StatusBar del HANDOFF)
// ---------------------------------------------------------------------------------------------
export type AccionPrincipal = 'PUBLICAR' | 'ACTUALIZAR' | 'REACTIVAR' | 'GUARDAR_PAGINA';

export interface AccionesEditor {
  readonly principal: AccionPrincipal | null;
  readonly guardarBorrador: boolean;
  readonly vistaPrevia: boolean;
  readonly retirar: boolean;
  /** Solo un borrador que nunca se publicó (DEC-AUTO-045). */
  readonly eliminar: boolean;
  /** RETIRADO: campos en solo lectura hasta reactivar. */
  readonly soloLectura: boolean;
}

export interface EstadoContenidoEditor {
  readonly tipo: TipoContenido;
  /** null en el alta (aún no existe). */
  readonly estado: EstadoEditorial | null;
  readonly nuncaPublicado: boolean;
}

export function accionesEditor(contenido: EstadoContenidoEditor): AccionesEditor {
  const { tipo, estado } = contenido;
  const vistaPrevia = tieneVistaPrevia(tipo) && estado !== 'RETIRADO';
  if (!tieneCicloEditorial(tipo)) {
    return {
      principal: 'GUARDAR_PAGINA',
      guardarBorrador: false,
      vistaPrevia,
      retirar: false,
      eliminar: false,
      soloLectura: false,
    };
  }
  switch (estado) {
    case null:
      // Alta: primero se guarda el borrador; publicar exige que exista (FLOW-011 pasos 3-5).
      return { principal: null, guardarBorrador: true, vistaPrevia, retirar: false, eliminar: false, soloLectura: false };
    case 'BORRADOR':
      return {
        principal: 'PUBLICAR',
        guardarBorrador: true,
        vistaPrevia,
        retirar: false,
        eliminar: contenido.nuncaPublicado,
        soloLectura: false,
      };
    case 'PUBLICADO':
      return { principal: 'ACTUALIZAR', guardarBorrador: false, vistaPrevia, retirar: true, eliminar: false, soloLectura: false };
    case 'RETIRADO':
      return { principal: 'REACTIVAR', guardarBorrador: false, vistaPrevia: false, retirar: false, eliminar: false, soloLectura: true };
  }
}

export const ETIQUETA_ACCION: Readonly<Record<AccionPrincipal, string>> = {
  PUBLICAR: 'Publicar',
  ACTUALIZAR: 'Actualizar publicación',
  REACTIVAR: 'Reactivar como borrador',
  GUARDAR_PAGINA: 'Guardar cambios',
};

// ---------------------------------------------------------------------------------------------
// SCR-035 Listado
// ---------------------------------------------------------------------------------------------
export interface ContenidoResumen {
  readonly id: number;
  readonly tipo: TipoContenido;
  readonly titulo: string;
  readonly slug: string | null;
  readonly estado: EstadoEditorial;
  readonly fechaRevision: string | null;
  readonly actualizadoEn: Date;
  readonly actualizadoPor: string;
  readonly publicado: boolean;
  /** Ruta pública si está publicado («Ver en el sitio»). */
  readonly urlPublica: string | null;
}

export interface PaginaContenidos {
  readonly contenidos: readonly ContenidoResumen[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
}

export interface FiltrosContenidos {
  readonly estado: EstadoEditorial | null;
  readonly q: string;
  readonly pagina: number;
}

export const FILTROS_CONTENIDOS_VACIOS: FiltrosContenidos = { estado: null, q: '', pagina: 1 };

const ESTADOS: readonly EstadoEditorial[] = ['BORRADOR', 'PUBLICADO', 'RETIRADO'];
/** Longitud máxima del filtro de texto (igual que el resto de buscadores del panel). */
export const LONGITUD_MAXIMA_Q = 100;

/** Parámetros inválidos de la URL se ignoran (FLOW-002: «parámetro inválido → se ignora»). */
export function filtrosContenidosDesdeQuery(
  query: Readonly<Record<string, string | null | undefined>>,
): FiltrosContenidos {
  const estado = ESTADOS.find((e) => e === query['estado']) ?? null;
  const q = (query['q'] ?? '').trim().slice(0, LONGITUD_MAXIMA_Q);
  const paginaTexto = query['pagina'] ?? '';
  const pagina = /^[1-9]\d{0,5}$/.test(paginaTexto) ? Number(paginaTexto) : 1;
  return { estado, q, pagina };
}

export function queryDesdeFiltrosContenidos(
  filtros: FiltrosContenidos,
): Record<string, string | null> {
  return {
    estado: filtros.estado,
    q: filtros.q === '' ? null : filtros.q,
    pagina: filtros.pagina > 1 ? String(filtros.pagina) : null,
  };
}

export function hayFiltrosContenidos(filtros: FiltrosContenidos): boolean {
  return filtros.estado !== null || filtros.q !== '';
}

/** Las páginas institucionales no admiten filtros (el contrato solo acepta `pagina`). */
export function admiteFiltros(tipo: TipoContenido): boolean {
  return tipo !== 'PAGINA';
}

export function textoRecuento(total: number, tipo: TipoContenido): string {
  const def = DEFINICION_TIPO[tipo];
  if (total === 1) return `1 ${def.singular}`;
  return `${total} ${def.plural.toLowerCase()}`;
}

/** «Destinos, ordenados por última modificación» (caption de la tabla). */
export function textoCaption(tipo: TipoContenido): string {
  return `${DEFINICION_TIPO[tipo].plural}, ordenados por última modificación`;
}
