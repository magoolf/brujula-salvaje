/**
 * Catálogo de secciones del panel (DEC-ESTRUCTURA-03, BLUEPRINT §10 y §17, RULE-030).
 *
 * Fuente única de la navegación lateral (TPL-PANEL-SHELL), de los accesos rápidos del Tablero
 * (SCR-034) y del control de rol de las rutas (SCR-048). Solo contiene secciones YA implementadas:
 * cada ticket del panel (TKT-022 medios, TKT-023 contenidos, TKT-024 inicio, taxonomías,
 * configuración, cuentas y auditoría) añade su entrada aquí y su ruta en ui/panel.routes.ts, sin
 * tocar el armazón. Así nunca hay enlaces a pantallas inexistentes (Cero huérfanos, CLAUDE.md §5.3).
 */
import { RolPanel } from './modelos';

export interface AccesoRapido {
  readonly id: string;
  readonly etiqueta: string;
  readonly ruta: string;
}

export interface SeccionPanel {
  /** Identificador estable (data-testid). */
  readonly id: string;
  readonly etiqueta: string;
  /** Ruta absoluta de la sección bajo /panel. */
  readonly ruta: string;
  /** Rol mínimo (los accesos de Administrador se ocultan al Editor, AC-105). */
  readonly rolMinimo: RolPanel;
  /** Accesos rápidos que la sección ofrece en el Tablero (SCR-034: «nuevo destino», etc.). */
  readonly accesosRapidos: readonly AccesoRapido[];
}

export const RUTA_TABLERO = '/panel';
/** SCR-039 Biblioteca de medios (MOD-011, TKT-022). */
export const RUTA_MEDIOS = '/panel/medios';
/** SCR-035 Listados de contenidos por tipo (MOD-010, TKT-023). */
export const RUTA_CONTENIDO = '/panel/contenido';
/** MOD-012 (TKT-024): SCR-042 Destacados, SCR-043 Taxonomías y SCR-047 Configuración [Admin]. */
export const RUTA_DESTACADOS = '/panel/inicio';
export const RUTA_TAXONOMIAS = '/panel/taxonomias';
export const RUTA_CONFIGURACION = '/panel/configuracion';
/** MOD-013 (TKT-024): SCR-044/045 Cuentas del equipo y SCR-046 Auditoría [Admin]. */
export const RUTA_USUARIOS = '/panel/usuarios';
export const RUTA_AUDITORIA = '/panel/auditoria';

const contenido = (id: string, etiqueta: string, ruta: string): SeccionPanel => ({
  id: `contenido-${id}`,
  etiqueta,
  ruta: `${RUTA_CONTENIDO}/${ruta}`,
  rolMinimo: 'EDITOR',
  accesosRapidos: [],
});

export const SECCIONES_PANEL: readonly SeccionPanel[] = [
  { id: 'tablero', etiqueta: 'Tablero', ruta: RUTA_TABLERO, rolMinimo: 'EDITOR', accesosRapidos: [] },
  {
    ...contenido('destinos', 'Destinos', 'destinos'),
    accesosRapidos: [
      { id: 'nuevo-destino', etiqueta: 'Nuevo destino', ruta: `${RUTA_CONTENIDO}/destinos/nuevo` },
    ],
  },
  contenido('itinerarios', 'Itinerarios', 'itinerarios'),
  contenido('guias', 'Guías', 'guias'),
  contenido('tipos-aventura', 'Tipos de aventura', 'tipos-aventura'),
  contenido('colecciones', 'Colecciones', 'colecciones'),
  contenido('glosario', 'Glosario', 'glosario'),
  contenido('paginas', 'Páginas institucionales', 'paginas'),
  {
    id: 'medios',
    etiqueta: 'Medios',
    ruta: RUTA_MEDIOS,
    rolMinimo: 'EDITOR',
    accesosRapidos: [{ id: 'subir-medios', etiqueta: 'Subir medios', ruta: RUTA_MEDIOS }],
  },
  // MOD-012 y MOD-013 (TKT-024).
  { id: 'inicio', etiqueta: 'Destacados de inicio', ruta: RUTA_DESTACADOS, rolMinimo: 'EDITOR', accesosRapidos: [] },
  { id: 'taxonomias', etiqueta: 'Taxonomías', ruta: RUTA_TAXONOMIAS, rolMinimo: 'EDITOR', accesosRapidos: [] },
  {
    id: 'usuarios',
    etiqueta: 'Cuentas del equipo',
    ruta: RUTA_USUARIOS,
    rolMinimo: 'ADMINISTRADOR',
    accesosRapidos: [{ id: 'nueva-cuenta', etiqueta: 'Nueva cuenta', ruta: `${RUTA_USUARIOS}/nuevo` }],
  },
  { id: 'auditoria', etiqueta: 'Auditoría', ruta: RUTA_AUDITORIA, rolMinimo: 'ADMINISTRADOR', accesosRapidos: [] },
  {
    id: 'configuracion',
    etiqueta: 'Configuración del sitio',
    ruta: RUTA_CONFIGURACION,
    rolMinimo: 'ADMINISTRADOR',
    accesosRapidos: [],
  },
  { id: 'cuenta', etiqueta: 'Mi cuenta', ruta: '/panel/cuenta', rolMinimo: 'EDITOR', accesosRapidos: [] },
];

export const ETIQUETA_ROL: Readonly<Record<RolPanel, string>> = {
  EDITOR: 'Editor',
  ADMINISTRADOR: 'Administrador',
};

/** El Tablero solo está activo en su ruta exacta (no en todo /panel/**). */
export function activoSoloExacto(seccion: SeccionPanel): boolean {
  return seccion.ruta === RUTA_TABLERO;
}

const JERARQUIA: Readonly<Record<RolPanel, number>> = { EDITOR: 1, ADMINISTRADOR: 2 };

/** Deny-by-default en la UI: el rol nunca sale de la entrada del usuario, sino de la sesión. */
export function puedeAcceder(rol: RolPanel | null | undefined, rolMinimo: RolPanel): boolean {
  return rol !== null && rol !== undefined && JERARQUIA[rol] >= JERARQUIA[rolMinimo];
}

export function seccionesVisibles(
  rol: RolPanel,
  catalogo: readonly SeccionPanel[] = SECCIONES_PANEL,
): readonly SeccionPanel[] {
  return catalogo.filter((s) => puedeAcceder(rol, s.rolMinimo));
}

export function accesosRapidos(
  rol: RolPanel,
  catalogo: readonly SeccionPanel[] = SECCIONES_PANEL,
): readonly AccesoRapido[] {
  return seccionesVisibles(rol, catalogo).flatMap((s) => s.accesosRapidos);
}

function rutaSinConsulta(url: string): string {
  return url.split(/[?#]/)[0].replace(/\/+$/, '') || '/';
}

/**
 * Sección a la que pertenece una URL del panel (prefijo más largo). El Tablero (`/panel`) solo
 * coincide exactamente, para no capturar rutas de secciones aún no implementadas.
 */
export function seccionDeRuta(
  url: string,
  catalogo: readonly SeccionPanel[] = SECCIONES_PANEL,
): SeccionPanel | null {
  const ruta = rutaSinConsulta(url);
  let mejor: SeccionPanel | null = null;
  for (const seccion of catalogo) {
    const coincide =
      seccion.ruta === RUTA_TABLERO
        ? ruta === RUTA_TABLERO
        : ruta === seccion.ruta || ruta.startsWith(`${seccion.ruta}/`);
    if (coincide && (mejor === null || seccion.ruta.length > mejor.ruta.length)) mejor = seccion;
  }
  return mejor;
}

/** Un enlace del servidor (p. ej. de una alerta del Tablero) solo se muestra si su sección existe. */
export function enlaceDisponible(
  enlace: string | null,
  rol: RolPanel,
  catalogo: readonly SeccionPanel[] = SECCIONES_PANEL,
): string | null {
  if (enlace === null) return null;
  const seccion = seccionDeRuta(enlace, catalogo);
  return seccion !== null && puedeAcceder(rol, seccion.rolMinimo) ? enlace : null;
}
