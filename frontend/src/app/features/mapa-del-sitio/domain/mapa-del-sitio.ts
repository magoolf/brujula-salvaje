/**
 * DOMAIN: reglas del Mapa del sitio (SCR-022, FEAT-025, RULE-030, AC-025). Funciones puras: a
 * partir de lo publicado (índice público, meses y glosario) construyen las secciones agrupadas.
 * Solo se enlaza lo que existe: RULE-001 garantiza que el índice público no contiene borradores ni
 * retirados, y aquí se descarta además cualquier entrada cuya ruta no exista en el sitio (p. ej.
 * una página institucional desconocida), para no publicar enlaces rotos.
 */
import {
  Agrupacion,
  DatosMapaDelSitio,
  EnlaceMapa,
  EntradaIndiceVista,
  GrupoMapa,
  MesVista,
  SeccionMapa,
  TerminoVista,
  TipoEntradaIndice,
} from './modelos';

/** Páginas institucionales con ruta propia en el sitio (contrato: enum de /publico/paginas/{slug}). */
export const SLUGS_PAGINAS_INSTITUCIONALES: readonly string[] = [
  'acerca-de',
  'politica-de-tratamiento-de-datos',
  'politica-de-cookies',
  'aviso-legal',
];

const PREFIJO_POR_TIPO: Readonly<Record<Exclude<TipoEntradaIndice, 'PAGINA'>, string>> = {
  DESTINO: '/destinos',
  ITINERARIO: '/itinerarios',
  TIPO: '/tipos-de-aventura',
  GUIA: '/guias',
  CATEGORIA_GUIA: '/guias/categoria',
  COLECCION: '/colecciones',
};

const ID_SIN_GRUPO = 'otros';

/** Ruta pública de una entrada del índice; `null` si el sitio no tiene página para ella. */
export function rutaDeEntrada(entrada: Pick<EntradaIndiceVista, 'tipo' | 'slug'>): string | null {
  if (entrada.slug.trim() === '') return null;
  if (entrada.tipo === 'PAGINA') {
    return SLUGS_PAGINAS_INSTITUCIONALES.includes(entrada.slug) ? `/${entrada.slug}` : null;
  }
  const prefijo = PREFIJO_POR_TIPO[entrada.tipo] as string | undefined;
  return prefijo === undefined ? null : `${prefijo}/${entrada.slug}`;
}

/** Comparación alfabética en español (ignora mayúsculas y tildes). */
export function compararTexto(a: string, b: string): number {
  return a.localeCompare(b, 'es', { sensitivity: 'base' });
}

function enlaceDe(entrada: EntradaIndiceVista): EnlaceMapa | null {
  const ruta = rutaDeEntrada(entrada);
  return ruta === null ? null : { etiqueta: entrada.titulo, ruta };
}

/** Enlaces de un tipo, ordenados alfabéticamente y sin rutas duplicadas. */
function enlacesDeTipo(
  entradas: readonly EntradaIndiceVista[],
  tipo: TipoEntradaIndice,
): EnlaceMapa[] {
  return ordenarEnlaces(entradas.filter((e) => e.tipo === tipo));
}

function ordenarEnlaces(entradas: readonly EntradaIndiceVista[]): EnlaceMapa[] {
  const vistos = new Set<string>();
  const enlaces: EnlaceMapa[] = [];
  for (const entrada of entradas) {
    const enlace = enlaceDe(entrada);
    if (enlace === null || vistos.has(enlace.ruta)) continue;
    vistos.add(enlace.ruta);
    enlaces.push(enlace);
  }
  return enlaces.sort((a, b) => compararTexto(a.etiqueta, b.etiqueta));
}

function grupoUnico(id: string, enlaces: readonly EnlaceMapa[]): GrupoMapa[] {
  return enlaces.length === 0 ? [] : [{ id, titulo: null, ruta: null, enlaces }];
}

/**
 * Agrupa entradas por su `agrupacion` (región o categoría). El orden de los grupos lo da
 * `ordenGrupos` (si se conoce) y, después, el alfabético; las entradas sin agrupación van al final
 * en un grupo «Otros…».
 */
export function agruparPor(
  entradas: readonly EntradaIndiceVista[],
  prefijoId: string,
  tituloSinGrupo: string,
  ordenGrupos: readonly Agrupacion[] = [],
  rutaGrupo: (agrupacion: Agrupacion) => string | null = () => null,
): GrupoMapa[] {
  const porSlug = new Map<string, { agrupacion: Agrupacion; entradas: EntradaIndiceVista[] }>();
  const sinGrupo: EntradaIndiceVista[] = [];
  for (const entrada of entradas) {
    const agrupacion = entrada.agrupacion;
    if (agrupacion === null) {
      sinGrupo.push(entrada);
      continue;
    }
    const grupo = porSlug.get(agrupacion.slug) ?? { agrupacion, entradas: [] };
    grupo.entradas.push(entrada);
    porSlug.set(agrupacion.slug, grupo);
  }

  const posicion = new Map(ordenGrupos.map((g, i) => [g.slug, i]));
  const ordenados = [...porSlug.values()].sort((a, b) => {
    const pa = posicion.get(a.agrupacion.slug) ?? Number.MAX_SAFE_INTEGER;
    const pb = posicion.get(b.agrupacion.slug) ?? Number.MAX_SAFE_INTEGER;
    return pa !== pb ? pa - pb : compararTexto(a.agrupacion.nombre, b.agrupacion.nombre);
  });

  const grupos: GrupoMapa[] = [];
  for (const { agrupacion, entradas: delGrupo } of ordenados) {
    const enlaces = ordenarEnlaces(delGrupo);
    if (enlaces.length === 0) continue;
    grupos.push({
      id: `${prefijoId}-${agrupacion.slug}`,
      titulo: agrupacion.nombre,
      ruta: rutaGrupo(agrupacion),
      enlaces,
    });
  }
  const restantes = ordenarEnlaces(sinGrupo);
  if (restantes.length > 0) {
    grupos.push({
      id: `${prefijoId}-${ID_SIN_GRUPO}`,
      titulo: tituloSinGrupo,
      ruta: null,
      enlaces: restantes,
    });
  }
  return grupos;
}

function etiquetaMes(mes: MesVista): string {
  const n = mes.numeroDestinos;
  return `${mes.nombre} (${n} ${n === 1 ? 'destino' : 'destinos'})`;
}

function enlaceTermino(termino: TerminoVista): EnlaceMapa {
  return termino.pagina > 1
    ? {
        etiqueta: termino.termino,
        ruta: '/glosario',
        queryParams: { pagina: String(termino.pagina) },
        fragmento: termino.slug,
      }
    : { etiqueta: termino.termino, ruta: '/glosario', fragmento: termino.slug };
}

/**
 * SCR-022: secciones del mapa del sitio en el orden de HANDOFF_UI_UX (Destinos por región,
 * Itinerarios, Tipos de aventura, Guías por categoría, Colecciones, Meses, Glosario,
 * Institucional), precedidas de las páginas generales. Cada sección enlaza siempre su listado.
 */
export function construirSecciones(datos: DatosMapaDelSitio): readonly SeccionMapa[] {
  const { entradas } = datos;
  const categorias: Agrupacion[] = entradas
    .filter((e) => e.tipo === 'CATEGORIA_GUIA' && rutaDeEntrada(e) !== null)
    .map((e) => ({ slug: e.slug, nombre: e.titulo }));
  const slugsCategorias = new Set(categorias.map((c) => c.slug));

  const guias = entradas.filter((e) => e.tipo === 'GUIA');
  const gruposGuias = agruparPor(guias, 'guias', 'Otras guías', categorias, (c) =>
    slugsCategorias.has(c.slug) ? `/guias/categoria/${c.slug}` : null,
  );

  const terminos = [...datos.terminos]
    .filter((t) => t.slug.trim() !== '')
    .sort((a, b) => compararTexto(a.termino, b.termino))
    .map(enlaceTermino);

  return [
    {
      id: 'general',
      titulo: 'General',
      enlacesSeccion: [
        { etiqueta: 'Inicio', ruta: '/' },
        { etiqueta: 'Mis aventuras guardadas', ruta: '/guardados' },
      ],
      grupos: [],
    },
    {
      id: 'destinos',
      titulo: 'Destinos',
      enlacesSeccion: [
        { etiqueta: 'Explorar destinos', ruta: '/destinos' },
        { etiqueta: 'Mapa de destinos', ruta: '/destinos/mapa' },
      ],
      grupos: agruparPor(
        entradas.filter((e) => e.tipo === 'DESTINO'),
        'destinos',
        'Otros destinos',
      ),
    },
    {
      id: 'itinerarios',
      titulo: 'Itinerarios',
      enlacesSeccion: [{ etiqueta: 'Todos los itinerarios', ruta: '/itinerarios' }],
      grupos: grupoUnico('itinerarios-todos', enlacesDeTipo(entradas, 'ITINERARIO')),
    },
    {
      id: 'tipos-de-aventura',
      titulo: 'Tipos de aventura',
      enlacesSeccion: [{ etiqueta: 'Todos los tipos de aventura', ruta: '/tipos-de-aventura' }],
      grupos: grupoUnico('tipos-todos', enlacesDeTipo(entradas, 'TIPO')),
    },
    {
      id: 'guias',
      titulo: 'Guías',
      enlacesSeccion: [{ etiqueta: 'Todas las guías', ruta: '/guias' }],
      grupos: gruposGuias,
    },
    {
      id: 'colecciones',
      titulo: 'Colecciones',
      enlacesSeccion: [{ etiqueta: 'Todas las colecciones', ruta: '/colecciones' }],
      grupos: grupoUnico('colecciones-todas', enlacesDeTipo(entradas, 'COLECCION')),
    },
    {
      id: 'cuando-ir',
      titulo: '¿Dónde ir cada mes?',
      enlacesSeccion: [{ etiqueta: 'Calendario de destinos', ruta: '/cuando-ir' }],
      grupos: grupoUnico(
        'meses-todos',
        datos.meses
          .filter((m) => Number.isInteger(m.numero) && m.numero >= 1 && m.numero <= 12)
          .map((m) => ({ etiqueta: etiquetaMes(m), ruta: `/cuando-ir/${m.numero}` })),
      ),
    },
    {
      id: 'glosario',
      titulo: 'Glosario',
      enlacesSeccion: [{ etiqueta: 'Glosario completo', ruta: '/glosario' }],
      grupos: grupoUnico('glosario-terminos', terminos),
    },
    {
      id: 'institucional',
      titulo: 'Institucional',
      enlacesSeccion: [],
      grupos: grupoUnico('institucional-todas', [
        ...enlacesDeTipo(entradas, 'PAGINA'),
        { etiqueta: 'Créditos de imágenes', ruta: '/creditos' },
      ]),
    },
  ];
}

/** Total de enlaces a páginas publicadas (sin contar los listados de sección). */
export function totalEnlaces(secciones: readonly SeccionMapa[]): number {
  return secciones.reduce(
    (total, s) => total + s.grupos.reduce((n, g) => n + g.enlaces.length, 0),
    0,
  );
}
