/**
 * Taxonomías y catálogos (SCR-043, FEAT-044, RULE-007, RULE-014, AC-105, TKT-024): regiones,
 * países y categorías de guía (Editor y Administrador); licencias y escalas (solo Administrador;
 * el Editor las ve en solo lectura). Retirar = guardar con `activo=false`; si el elemento está en
 * uso por contenido publicado, el servidor responde 409 `dependencia_bloqueante` con los usos.
 * Puro: sin Angular ni RxJS (Regla 08).
 */
import { ErroresTraducidos, longitudTexto } from './errores-formulario';
import { PATRON_SLUG, proponerSlug } from './formulario-contenido';
import { EstadoEditorial, RolPanel } from './modelos';
import { puedeAcceder } from './secciones';

export type Catalogo = 'regiones' | 'paises' | 'categorias' | 'licencias' | 'escalas';

export const CATALOGOS: readonly Catalogo[] = ['regiones', 'paises', 'categorias', 'licencias', 'escalas'];

export interface DefinicionCatalogo {
  readonly etiqueta: string;
  /** Sustantivo en singular para botones y diálogos («Nueva región»). */
  readonly nuevo: string;
  readonly singular: string;
  /** «Aún no hay {elementos}». */
  readonly plural: string;
  readonly rolEdicion: RolPanel;
  /** Las escalas son fijas: solo se editan, no se crean ni se retiran. */
  readonly admiteAltas: boolean;
}

export const DEFINICION_CATALOGO: Readonly<Record<Catalogo, DefinicionCatalogo>> = {
  regiones: { etiqueta: 'Regiones', nuevo: 'Nueva región', singular: 'región', plural: 'regiones', rolEdicion: 'EDITOR', admiteAltas: true },
  paises: { etiqueta: 'Países', nuevo: 'Nuevo país', singular: 'país', plural: 'países', rolEdicion: 'EDITOR', admiteAltas: true },
  categorias: {
    etiqueta: 'Categorías de guía',
    nuevo: 'Nueva categoría',
    singular: 'categoría',
    plural: 'categorías de guía',
    rolEdicion: 'EDITOR',
    admiteAltas: true,
  },
  licencias: {
    etiqueta: 'Licencias',
    nuevo: 'Nueva licencia',
    singular: 'licencia',
    plural: 'licencias',
    rolEdicion: 'ADMINISTRADOR',
    admiteAltas: true,
  },
  escalas: {
    etiqueta: 'Escalas',
    nuevo: '',
    singular: 'nivel',
    plural: 'niveles',
    rolEdicion: 'ADMINISTRADOR',
    admiteAltas: false,
  },
};

export const AVISO_SOLO_ADMIN = 'Solo un administrador puede modificar las licencias y las escalas.';

/** Pestaña activa desde la URL (`?catalogo=`); por defecto, Regiones. */
export function catalogoDesdeQuery(valor: string | null | undefined): Catalogo {
  return CATALOGOS.find((c) => c === valor) ?? 'regiones';
}

/** RULE-014: licencias y escalas solo las edita el Administrador. */
export function puedeEditarCatalogo(rol: RolPanel | null, catalogo: Catalogo): boolean {
  return puedeAcceder(rol, DEFINICION_CATALOGO[catalogo].rolEdicion);
}

// ---------------------------------------------------------------------------------------------
// Modelos
// ---------------------------------------------------------------------------------------------
export type Continente = 'AMERICA' | 'EUROPA' | 'AFRICA' | 'ASIA' | 'OCEANIA' | 'ANTARTIDA';

export const CONTINENTES: readonly Continente[] = ['AMERICA', 'EUROPA', 'AFRICA', 'ASIA', 'OCEANIA', 'ANTARTIDA'];

export const ETIQUETA_CONTINENTE: Readonly<Record<Continente, string>> = {
  AMERICA: 'América',
  EUROPA: 'Europa',
  AFRICA: 'África',
  ASIA: 'Asia',
  OCEANIA: 'Oceanía',
  ANTARTIDA: 'Antártida',
};

export interface Region {
  readonly catalogo: 'regiones';
  readonly id: number;
  readonly nombre: string;
  readonly slug: string;
  readonly continente: Continente;
  readonly orden: number;
  readonly activo: boolean;
}

export interface Pais {
  readonly catalogo: 'paises';
  readonly id: number;
  readonly nombre: string;
  readonly slug: string;
  readonly codigoIso2: string;
  readonly regionId: number;
  readonly activo: boolean;
}

export interface CategoriaGuia {
  readonly catalogo: 'categorias';
  readonly id: number;
  readonly nombre: string;
  readonly slug: string;
  readonly descripcion: string;
  readonly orden: number;
  readonly activo: boolean;
}

export interface Licencia {
  readonly catalogo: 'licencias';
  readonly id: number;
  readonly codigo: string;
  readonly nombre: string;
  readonly urlTextoLegal: string | null;
  readonly requiereAtribucion: boolean;
  readonly compatiblePublicacion: boolean;
  readonly activo: boolean;
}

export type ElementoCatalogo = Region | Pais | CategoriaGuia | Licencia;

export type Escala = 'DIFICULTAD' | 'PRESUPUESTO';

export interface NivelEscalaPanel {
  readonly id: number;
  readonly escala: Escala;
  readonly nivel: number;
  readonly etiqueta: string;
  readonly descripcion: string;
}

export interface EscalasPanel {
  readonly dificultad: readonly NivelEscalaPanel[];
  readonly presupuesto: readonly NivelEscalaPanel[];
}

export const ETIQUETA_ESCALA: Readonly<Record<Escala, string>> = {
  DIFICULTAD: 'Dificultad',
  PRESUPUESTO: 'Presupuesto',
};

/** Nombre visible de un elemento (las licencias muestran también su código). */
export function nombreElemento(elemento: ElementoCatalogo): string {
  return elemento.catalogo === 'licencias' ? `${elemento.nombre} (${elemento.codigo})` : elemento.nombre;
}

// ---------------------------------------------------------------------------------------------
// Formulario (diálogo de alta y edición)
// ---------------------------------------------------------------------------------------------
export interface FormularioCatalogo {
  readonly nombre: string;
  readonly slug: string;
  readonly continente: string;
  readonly orden: string;
  readonly codigoIso2: string;
  readonly regionId: string;
  readonly descripcion: string;
  readonly codigo: string;
  readonly urlTextoLegal: string;
  readonly etiqueta: string;
  readonly requiereAtribucion: boolean;
  readonly compatiblePublicacion: boolean;
}

export type CampoTextoCatalogo = Exclude<keyof FormularioCatalogo, 'requiereAtribucion' | 'compatiblePublicacion'>;

export const FORMULARIO_CATALOGO_VACIO: FormularioCatalogo = {
  nombre: '',
  slug: '',
  continente: '',
  orden: '0',
  codigoIso2: '',
  regionId: '',
  descripcion: '',
  codigo: '',
  urlTextoLegal: '',
  etiqueta: '',
  requiereAtribucion: true,
  compatiblePublicacion: true,
};

/** Campos de texto de cada catálogo, en orden de pantalla. */
export const CAMPOS_CATALOGO: Readonly<Record<Catalogo, readonly CampoTextoCatalogo[]>> = {
  regiones: ['nombre', 'slug', 'continente', 'orden'],
  paises: ['nombre', 'slug', 'codigoIso2', 'regionId'],
  categorias: ['nombre', 'slug', 'descripcion', 'orden'],
  licencias: ['codigo', 'nombre', 'urlTextoLegal'],
  escalas: ['etiqueta', 'descripcion'],
};

/** Campo del contrato de cada campo del formulario (errores 400 por campo). */
export const CAMPO_API_CATALOGO: Readonly<Record<CampoTextoCatalogo, string>> = {
  nombre: 'nombre',
  slug: 'slug',
  continente: 'continente',
  orden: 'orden',
  codigoIso2: 'codigo_iso2',
  regionId: 'region_id',
  descripcion: 'descripcion',
  codigo: 'codigo',
  urlTextoLegal: 'url_texto_legal',
  etiqueta: 'etiqueta',
};

const MAXIMOS: Readonly<Record<Catalogo, Partial<Record<CampoTextoCatalogo, number>>>> = {
  regiones: { nombre: 60, slug: 60 },
  paises: { nombre: 80, slug: 80 },
  categorias: { nombre: 80, slug: 80, descripcion: 400 },
  licencias: { codigo: 40, nombre: 120, urlTextoLegal: 500 },
  escalas: { etiqueta: 40, descripcion: 400 },
};

export function maximoCampo(catalogo: Catalogo, campo: CampoTextoCatalogo): number | null {
  return MAXIMOS[catalogo][campo] ?? null;
}

export function formularioDesdeElemento(elemento: ElementoCatalogo): FormularioCatalogo {
  switch (elemento.catalogo) {
    case 'regiones':
      return {
        ...FORMULARIO_CATALOGO_VACIO,
        nombre: elemento.nombre,
        slug: elemento.slug,
        continente: elemento.continente,
        orden: String(elemento.orden),
      };
    case 'paises':
      return {
        ...FORMULARIO_CATALOGO_VACIO,
        nombre: elemento.nombre,
        slug: elemento.slug,
        codigoIso2: elemento.codigoIso2,
        regionId: String(elemento.regionId),
      };
    case 'categorias':
      return {
        ...FORMULARIO_CATALOGO_VACIO,
        nombre: elemento.nombre,
        slug: elemento.slug,
        descripcion: elemento.descripcion,
        orden: String(elemento.orden),
      };
    case 'licencias':
      return {
        ...FORMULARIO_CATALOGO_VACIO,
        codigo: elemento.codigo,
        nombre: elemento.nombre,
        urlTextoLegal: elemento.urlTextoLegal ?? '',
        requiereAtribucion: elemento.requiereAtribucion,
        compatiblePublicacion: elemento.compatiblePublicacion,
      };
  }
}

export function formularioDesdeNivel(nivel: NivelEscalaPanel): FormularioCatalogo {
  return { ...FORMULARIO_CATALOGO_VACIO, etiqueta: nivel.etiqueta, descripcion: nivel.descripcion };
}

/** Slug propuesto desde el nombre (RULE-008), recortado a la longitud del catálogo. */
export function proponerSlugCatalogo(catalogo: Catalogo, nombre: string): string {
  const maximo = maximoCampo(catalogo, 'slug') ?? 80;
  return proponerSlug(nombre).slice(0, maximo).replace(/-+$/g, '');
}

const OBLIGATORIO = 'Este campo es obligatorio.';

function errorCampo(catalogo: Catalogo, campo: CampoTextoCatalogo, valor: string): string | null {
  const texto = valor.trim();
  const opcional = campo === 'urlTextoLegal';
  if (texto === '') return opcional ? null : OBLIGATORIO;
  const maximo = maximoCampo(catalogo, campo);
  if (maximo !== null && longitudTexto(texto) > maximo) return `Usa como máximo ${maximo} caracteres.`;
  switch (campo) {
    case 'slug':
      return PATRON_SLUG.test(texto) ? null : 'Usa solo minúsculas sin tildes, números y guiones (sin guion al principio ni al final).';
    case 'orden':
      return /^\d{1,4}$/.test(texto) && Number(texto) <= 1000 ? null : 'Escribe un número entero entre 0 y 1000.';
    case 'codigoIso2':
      return /^[A-Za-z]{2}$/.test(texto) ? null : 'Escribe el código ISO de 2 letras (p. ej. CO).';
    case 'codigo':
      return /^[A-Za-z0-9.-]+$/.test(texto) ? null : 'Usa solo letras, números, puntos y guiones (p. ej. CC-BY-4.0).';
    case 'urlTextoLegal':
      return /^https?:\/\/\S+$/i.test(texto) ? null : 'Escribe una dirección completa que empiece por http:// o https://.';
    case 'continente':
      return CONTINENTES.includes(texto as Continente) ? null : 'Elige un continente.';
    default:
      return null;
  }
}

export function validarCatalogo(
  catalogo: Catalogo,
  f: FormularioCatalogo,
): Partial<Record<CampoTextoCatalogo, string>> {
  const errores: Partial<Record<CampoTextoCatalogo, string>> = {};
  for (const campo of CAMPOS_CATALOGO[catalogo]) {
    const error = errorCampo(catalogo, campo, f[campo]);
    if (error !== null) errores[campo] = error;
  }
  return errores;
}

// ---------------------------------------------------------------------------------------------
// Entradas de escritura (el estado `activo` se conserva al editar y se cambia al retirar/reactivar)
// ---------------------------------------------------------------------------------------------
export type EntradaCatalogo =
  | Omit<Region, 'id'>
  | Omit<Pais, 'id'>
  | Omit<CategoriaGuia, 'id'>
  | Omit<Licencia, 'id'>;

export interface EntradaNivelEscala {
  readonly etiqueta: string;
  readonly descripcion: string;
}

export function entradaCatalogo(
  catalogo: Exclude<Catalogo, 'escalas'>,
  f: FormularioCatalogo,
  activo: boolean,
): EntradaCatalogo {
  switch (catalogo) {
    case 'regiones':
      return {
        catalogo,
        nombre: f.nombre.trim(),
        slug: f.slug.trim(),
        continente: f.continente as Continente,
        orden: Number(f.orden.trim()),
        activo,
      };
    case 'paises':
      return {
        catalogo,
        nombre: f.nombre.trim(),
        slug: f.slug.trim(),
        codigoIso2: f.codigoIso2.trim().toUpperCase(),
        regionId: Number(f.regionId),
        activo,
      };
    case 'categorias':
      return {
        catalogo,
        nombre: f.nombre.trim(),
        slug: f.slug.trim(),
        descripcion: f.descripcion.trim(),
        orden: Number(f.orden.trim()),
        activo,
      };
    case 'licencias': {
      const url = f.urlTextoLegal.trim();
      return {
        catalogo,
        codigo: f.codigo.trim().toUpperCase(),
        nombre: f.nombre.trim(),
        urlTextoLegal: url === '' ? null : url,
        requiereAtribucion: f.requiereAtribucion,
        compatiblePublicacion: f.compatiblePublicacion,
        activo,
      };
    }
  }
}

/** La misma entrada del elemento con otro estado (Retirar / Reactivar). */
export function entradaConEstado(elemento: ElementoCatalogo, activo: boolean): EntradaCatalogo {
  const { id: _id, ...resto } = elemento;
  return { ...resto, activo };
}

export function entradaNivel(f: FormularioCatalogo): EntradaNivelEscala {
  return { etiqueta: f.etiqueta.trim(), descripcion: f.descripcion.trim() };
}

export function erroresCatalogo(
  campos: Readonly<Record<string, readonly string[]>>,
  mensaje: string,
  catalogo: Catalogo,
): ErroresTraducidos<CampoTextoCatalogo> {
  const visibles = new Set(CAMPOS_CATALOGO[catalogo]);
  const porCampo: Partial<Record<CampoTextoCatalogo, string>> = {};
  const generales: string[] = [];
  for (const [clave, mensajes] of Object.entries(campos)) {
    const campo = (Object.keys(CAMPO_API_CATALOGO) as CampoTextoCatalogo[]).find(
      (c) => CAMPO_API_CATALOGO[c] === clave,
    );
    if (campo !== undefined && visibles.has(campo) && mensajes.length > 0) porCampo[campo] = mensajes[0];
    else generales.push(...mensajes);
  }
  if (Object.keys(porCampo).length === 0 && generales.length === 0) generales.push(mensaje);
  return { porCampo, generales };
}

// ---------------------------------------------------------------------------------------------
// Usos que bloquean un retiro (RULE-007, 409 dependencia_bloqueante con `usos`)
// ---------------------------------------------------------------------------------------------
export interface UsoBloqueante {
  readonly tipo: string;
  readonly id: number;
  readonly titulo: string;
  readonly estado: EstadoEditorial | null;
}

export interface Bloqueo {
  readonly mensaje: string;
  readonly usos: readonly UsoBloqueante[];
  readonly total: number;
}

const ESTADOS: readonly string[] = ['BORRADOR', 'PUBLICADO', 'RETIRADO'];

function aUso(valor: unknown): UsoBloqueante | null {
  if (typeof valor !== 'object' || valor === null) return null;
  const v = valor as Record<string, unknown>;
  if (typeof v['id'] !== 'number' || typeof v['titulo'] !== 'string') return null;
  const estado = v['estado_editorial'];
  return {
    tipo: typeof v['tipo_entidad'] === 'string' ? v['tipo_entidad'] : '',
    id: v['id'],
    titulo: v['titulo'],
    estado: typeof estado === 'string' && ESTADOS.includes(estado) ? (estado as EstadoEditorial) : null,
  };
}

/** «Lo usa 1 contenido publicado:» / «Lo usan 3 contenidos publicados:». */
export function textoUsosBloqueo(total: number): string {
  return total === 1 ? 'Lo usa 1 contenido publicado:' : `Lo usan ${total} contenidos publicados:`;
}

/** Lee los usos del miembro de extensión del Problem Details (ErrorApi.extra). */
export function bloqueoDesdeError(mensaje: string, extra: Readonly<Record<string, unknown>>): Bloqueo {
  const lista = Array.isArray(extra['usos']) ? extra['usos'] : [];
  const usos = lista.map(aUso).filter((u): u is UsoBloqueante => u !== null);
  const total = typeof extra['total_usos'] === 'number' ? extra['total_usos'] : usos.length;
  return { mensaje, usos, total };
}
