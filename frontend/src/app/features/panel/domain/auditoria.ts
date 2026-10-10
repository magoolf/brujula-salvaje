/**
 * Registro de auditoría (SCR-046, FEAT-046, FLOW-016, AC-030, THREAT-013, TKT-024): consulta de
 * solo lectura, filtrada por fechas, actor, acción y tipo de entidad, en orden descendente. Los
 * filtros viven en la URL (`?desde=&hasta=&actor=&accion=&tipo=&pagina=`). Las fechas se muestran
 * absolutas en es-CO con la zona America/Bogota (HANDOFF SCR-046). Puro (Regla 08).
 */
import { LOCALE } from '../../../core/seo/marca';
import { rutaEditor } from './contenidos';
import { TipoContenido } from './modelos';

export type AccionAuditoria =
  | 'LOGIN_OK'
  | 'LOGIN_FALLIDO'
  | 'BLOQUEO'
  | 'LOGOUT'
  | 'AUTORIZACION_ACEPTADA'
  | 'CAMBIO_CREDENCIAL'
  | 'MFA_ACTIVAR'
  | 'MFA_DESACTIVAR'
  | 'CREAR'
  | 'EDITAR'
  | 'PUBLICAR'
  | 'ACTUALIZAR_PUBLICACION'
  | 'RETIRAR'
  | 'REACTIVAR'
  | 'ELIMINAR_BORRADOR'
  | 'RESTAURAR_REVISION'
  | 'SUBIR_MEDIO'
  | 'EDITAR_MEDIO'
  | 'RETIRAR_MEDIO'
  | 'CONFIG_INICIO'
  | 'CONFIG_SITIO'
  | 'TAXONOMIA'
  | 'CUENTA_CREAR'
  | 'CUENTA_ROL'
  | 'CUENTA_RESTABLECER'
  | 'CUENTA_DESACTIVAR'
  | 'CUENTA_REACTIVAR'
  | 'CUENTA_ANONIMIZAR';

export const ETIQUETA_ACCION: Readonly<Record<AccionAuditoria, string>> = {
  LOGIN_OK: 'Inicio de sesión',
  LOGIN_FALLIDO: 'Inicio de sesión fallido',
  BLOQUEO: 'Bloqueo de la cuenta',
  LOGOUT: 'Cierre de sesión',
  AUTORIZACION_ACEPTADA: 'Autorización de tratamiento',
  CAMBIO_CREDENCIAL: 'Cambio de contraseña',
  MFA_ACTIVAR: 'Activación de la verificación en dos pasos',
  MFA_DESACTIVAR: 'Desactivación de la verificación en dos pasos',
  CREAR: 'Creación',
  EDITAR: 'Edición',
  PUBLICAR: 'Publicación',
  ACTUALIZAR_PUBLICACION: 'Actualización de la publicación',
  RETIRAR: 'Retiro',
  REACTIVAR: 'Reactivación',
  ELIMINAR_BORRADOR: 'Eliminación de borrador',
  RESTAURAR_REVISION: 'Restauración de revisión',
  SUBIR_MEDIO: 'Subida de imagen',
  EDITAR_MEDIO: 'Edición de imagen',
  RETIRAR_MEDIO: 'Retiro de imagen',
  CONFIG_INICIO: 'Destacados de inicio',
  CONFIG_SITIO: 'Configuración del sitio',
  TAXONOMIA: 'Taxonomías y catálogos',
  CUENTA_CREAR: 'Alta de cuenta',
  CUENTA_ROL: 'Cambio de cuenta o rol',
  CUENTA_RESTABLECER: 'Restablecimiento de cuenta',
  CUENTA_DESACTIVAR: 'Desactivación de cuenta',
  CUENTA_REACTIVAR: 'Reactivación de cuenta',
  CUENTA_ANONIMIZAR: 'Anonimización de cuenta',
};

export const ACCIONES_AUDITORIA = Object.keys(ETIQUETA_ACCION) as readonly AccionAuditoria[];

/** Tipos de entidad que registra el backend (tipo_entidad, ^[A-Z_]+$). */
export const ETIQUETA_TIPO_ENTIDAD: Readonly<Record<string, string>> = {
  DESTINO: 'Destino',
  ITINERARIO: 'Itinerario',
  GUIA: 'Guía',
  TIPO: 'Tipo de aventura',
  COLECCION: 'Colección',
  TERMINO: 'Término del glosario',
  PAGINA: 'Página institucional',
  MEDIO: 'Imagen',
  REGION: 'Región',
  PAIS: 'País',
  CATEGORIA_GUIA: 'Categoría de guía',
  LICENCIA: 'Licencia',
  NIVEL_ESCALA: 'Nivel de escala',
  CONFIG_INICIO: 'Destacados de inicio',
  CONFIG_SITIO: 'Configuración del sitio',
  CUENTA: 'Cuenta',
};

export const TIPOS_ENTIDAD = Object.keys(ETIQUETA_TIPO_ENTIDAD);

export type ResultadoAuditoria = 'EXITO' | 'FALLO';

export const ETIQUETA_RESULTADO: Readonly<Record<ResultadoAuditoria, string>> = {
  EXITO: 'Correcto',
  FALLO: 'Fallido',
};

export interface EventoAuditoria {
  readonly id: number;
  readonly ocurridoEn: Date;
  readonly actor: string;
  readonly actorId: number | null;
  readonly accion: AccionAuditoria;
  readonly resultado: ResultadoAuditoria;
  readonly tipoEntidad: string | null;
  readonly entidadId: number | null;
  readonly entidadTitulo: string | null;
  readonly camposCambiados: readonly string[];
  readonly ipTruncada: string | null;
}

export interface PaginaAuditoria {
  readonly eventos: readonly EventoAuditoria[];
  readonly pagina: number;
  readonly totalPaginas: number;
  readonly total: number;
}

/** Actor elegible en el filtro (cuentas del equipo). */
export interface OpcionActor {
  readonly id: number;
  readonly etiqueta: string;
}

export interface FiltrosAuditoria {
  /** AAAA-MM-DD o '' (fecha local de Bogotá). */
  readonly desde: string;
  readonly hasta: string;
  readonly actor: number | null;
  readonly accion: AccionAuditoria | null;
  readonly tipo: string | null;
  readonly pagina: number;
}

export const FILTROS_AUDITORIA_VACIOS: FiltrosAuditoria = {
  desde: '',
  hasta: '',
  actor: null,
  accion: null,
  tipo: null,
  pagina: 1,
};

const PATRON_FECHA = /^\d{4}-\d{2}-\d{2}$/;

function fechaValida(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || !PATRON_FECHA.test(valor)) return '';
  const fecha = new Date(`${valor}T12:00:00Z`);
  return !Number.isNaN(fecha.getTime()) && fecha.toISOString().startsWith(valor) ? valor : '';
}

function entero(valor: string | null | undefined): number | null {
  return valor !== null && valor !== undefined && /^[1-9]\d{0,17}$/.test(valor) && Number.isSafeInteger(Number(valor))
    ? Number(valor)
    : null;
}

/** Filtros desde la URL: los valores no válidos se ignoran (deny-by-default, nunca se reenvían). */
export function filtrosAuditoriaDesdeQuery(query: Readonly<Record<string, string | null>>): FiltrosAuditoria {
  const accion = query['accion'];
  const tipo = query['tipo'];
  return {
    desde: fechaValida(query['desde']),
    hasta: fechaValida(query['hasta']),
    actor: entero(query['actor']),
    accion: ACCIONES_AUDITORIA.find((a) => a === accion) ?? null,
    tipo: TIPOS_ENTIDAD.find((t) => t === tipo) ?? null,
    pagina: entero(query['pagina']) ?? 1,
  };
}

/** Query de la URL (los vacíos y la página 1 se omiten). */
export function queryDesdeFiltrosAuditoria(f: FiltrosAuditoria): Record<string, string | null> {
  return {
    desde: f.desde === '' ? null : f.desde,
    hasta: f.hasta === '' ? null : f.hasta,
    actor: f.actor === null ? null : String(f.actor),
    accion: f.accion,
    tipo: f.tipo,
    pagina: f.pagina > 1 ? String(f.pagina) : null,
  };
}

export function hayFiltrosAuditoria(f: FiltrosAuditoria): boolean {
  return f.desde !== '' || f.hasta !== '' || f.actor !== null || f.accion !== null || f.tipo !== null;
}

/** «Desde» posterior a «Hasta»: no se consulta (error en línea). */
export function errorRangoFechas(desde: string, hasta: string): string | null {
  return desde !== '' && hasta !== '' && desde > hasta ? 'La fecha «Desde» no puede ser posterior a «Hasta».' : null;
}

/** Bogotá no tiene horario de verano: UTC−5 todo el año. */
const DESFASE_BOGOTA = '-05:00';

/** Límites date-time del contrato para un día local de Bogotá (inicio y fin del día). */
export function limitesFechas(f: FiltrosAuditoria): { desde: string | null; hasta: string | null } {
  return {
    desde: f.desde === '' ? null : `${f.desde}T00:00:00${DESFASE_BOGOTA}`,
    hasta: f.hasta === '' ? null : `${f.hasta}T23:59:59.999${DESFASE_BOGOTA}`,
  };
}

const FECHA_ZONA = new Intl.DateTimeFormat(LOCALE, {
  dateStyle: 'medium',
  timeStyle: 'medium',
  timeZone: 'America/Bogota',
});

/** Fecha absoluta en es-CO con la zona indicada («10 oct 2026, 3:05:00 p. m. (hora de Bogotá)»). */
export function formatearFechaBogota(fecha: Date): string {
  return `${FECHA_ZONA.format(fecha)} (hora de Bogotá)`;
}

const RUTA_CATALOGO: Readonly<Record<string, string>> = {
  REGION: 'regiones',
  PAIS: 'paises',
  CATEGORIA_GUIA: 'categorias',
  LICENCIA: 'licencias',
  NIVEL_ESCALA: 'escalas',
};

const TIPOS_CONTENIDO: readonly TipoContenido[] = ['DESTINO', 'ITINERARIO', 'GUIA', 'TIPO', 'COLECCION', 'TERMINO', 'PAGINA'];

/**
 * Pantalla del panel donde se abre la entidad del evento (FLOW-016 «abre la entidad»), o null si
 * no tiene (p. ej. eventos de sesión). Las cuentas anonimizadas no se enlazan (sin datos).
 */
export function rutaEntidad(evento: EventoAuditoria): { ruta: string; query: Record<string, string> | null } | null {
  const tipo = evento.tipoEntidad;
  if (tipo === null) return null;
  if (tipo === 'CONFIG_INICIO') return { ruta: '/panel/inicio', query: null };
  if (tipo === 'CONFIG_SITIO') return { ruta: '/panel/configuracion', query: null };
  const catalogo = RUTA_CATALOGO[tipo];
  if (catalogo !== undefined) return { ruta: '/panel/taxonomias', query: { catalogo } };
  if (evento.entidadId === null) return null;
  if (tipo === 'MEDIO') return { ruta: `/panel/medios/${evento.entidadId}`, query: null };
  if (tipo === 'CUENTA') {
    return evento.accion === 'CUENTA_ANONIMIZAR' ? null : { ruta: `/panel/usuarios/${evento.entidadId}`, query: null };
  }
  const contenido = TIPOS_CONTENIDO.find((t) => t === tipo);
  return contenido === undefined ? null : { ruta: rutaEditor(contenido, evento.entidadId), query: null };
}

/** Texto de la entidad: «Destino · Volcán Cotopaxi» (o solo el tipo). */
export function textoEntidad(evento: EventoAuditoria): string {
  if (evento.tipoEntidad === null) return '—';
  const tipo = ETIQUETA_TIPO_ENTIDAD[evento.tipoEntidad] ?? evento.tipoEntidad;
  const titulo = evento.entidadTitulo ?? (evento.entidadId === null ? null : `#${evento.entidadId}`);
  return titulo === null ? tipo : `${tipo} · ${titulo}`;
}

export function varianteResultado(resultado: ResultadoAuditoria): 'publicado' | 'rechazado' {
  return resultado === 'EXITO' ? 'publicado' : 'rechazado';
}

/** El evento tiene detalle que desplegar («Ver cambios»): campos cambiados u origen truncado. */
export function tieneDetalle(evento: EventoAuditoria): boolean {
  return evento.camposCambiados.length > 0 || evento.ipTruncada !== null;
}

export function textoRecuentoAuditoria(total: number): string {
  return total === 1 ? '1 evento' : `${total.toLocaleString(LOCALE)} eventos`;
}
