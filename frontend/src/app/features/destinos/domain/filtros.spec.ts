import {
  FILTROS_VACIOS,
  alternarDuracion,
  alternarMes,
  alternarPais,
  alternarPresupuesto,
  alternarRegion,
  alternarTipo,
  establecerOrden,
  establecerRangoDificultad,
  filtrosActivosComoLista,
  filtrosDesdeQueryParams,
  hayFiltrosActivos,
  limpiarFiltros,
  normalizarRangoDificultad,
} from './filtros';

describe('normalizarRangoDificultad', () => {
  it('intercambia el rango cuando desde > hasta (DEC-AUTO-067)', () => {
    expect(normalizarRangoDificultad(4, 2)).toEqual({ min: 2, max: 4 });
  });

  it('conserva un rango válido o parcial', () => {
    expect(normalizarRangoDificultad(2, 4)).toEqual({ min: 2, max: 4 });
    expect(normalizarRangoDificultad(null, 4)).toEqual({ min: null, max: 4 });
    expect(normalizarRangoDificultad(null, null)).toEqual({ min: null, max: null });
  });
});

describe('filtrosDesdeQueryParams', () => {
  it('produce los filtros vacíos cuando no hay parámetros', () => {
    expect(filtrosDesdeQueryParams({})).toEqual(FILTROS_VACIOS);
  });

  it('lee tipo (repetible), región, país, mes, duración, presupuesto, orden y página', () => {
    const filtros = filtrosDesdeQueryParams({
      tipo: ['senderismo', 'buceo'],
      region: 'suramerica',
      pais: 'colombia',
      mes: '7',
      duracion: ['1-3', '4-7'],
      presupuesto: ['1', '3'],
      orden: 'dificultad_asc',
      pagina: '2',
    });
    expect(filtros).toEqual({
      tipo: ['senderismo', 'buceo'],
      region: 'suramerica',
      pais: 'colombia',
      dificultadMin: null,
      dificultadMax: null,
      mes: 7,
      duracion: ['1-3', '4-7'],
      presupuesto: [1, 3],
      orden: 'dificultad_asc',
      pagina: 2,
    });
  });

  it('ignora en silencio valores fuera de dominio (AC-113): slug inválido, orden desconocido, mes fuera de 1-12', () => {
    const filtros = filtrosDesdeQueryParams({
      tipo: ['Mayúscula Inválida', 'valido-ok'],
      region: 'CON ESPACIO',
      orden: 'aleatorio',
      mes: '13',
      pagina: 'no-es-numero',
    });
    expect(filtros.tipo).toEqual(['valido-ok']);
    expect(filtros.region).toBeNull();
    expect(filtros.orden).toBe('nombre');
    expect(filtros.mes).toBeNull();
    expect(filtros.pagina).toBe(1);
  });

  it('intercambia dificultad_min/dificultad_max si vienen invertidos', () => {
    const filtros = filtrosDesdeQueryParams({ dificultad_min: '5', dificultad_max: '2' });
    expect(filtros.dificultadMin).toBe(2);
    expect(filtros.dificultadMax).toBe(5);
  });
});

describe('hayFiltrosActivos', () => {
  it('es falso para los filtros vacíos y verdadero si cualquier faceta está activa', () => {
    expect(hayFiltrosActivos(FILTROS_VACIOS)).toBe(false);
    expect(hayFiltrosActivos({ ...FILTROS_VACIOS, tipo: ['buceo'] })).toBe(true);
    expect(hayFiltrosActivos({ ...FILTROS_VACIOS, mes: 3 })).toBe(true);
    expect(hayFiltrosActivos({ ...FILTROS_VACIOS, presupuesto: [2] })).toBe(true);
  });
});

describe('alternarTipo', () => {
  it('añade el tipo si no estaba y lo quita si ya estaba, reiniciando la página', () => {
    expect(alternarTipo(FILTROS_VACIOS, 'buceo')).toEqual({ tipo: ['buceo'], pagina: null });
    const conBuceo = { ...FILTROS_VACIOS, tipo: ['buceo'] };
    expect(alternarTipo(conBuceo, 'buceo')).toEqual({ tipo: null, pagina: null });
  });
});

describe('alternarRegion', () => {
  it('al quitar la región también quita el país dependiente', () => {
    const filtros = { ...FILTROS_VACIOS, region: 'suramerica', pais: 'colombia' };
    expect(alternarRegion(filtros, 'suramerica')).toEqual({ region: null, pais: null, pagina: null });
  });

  it('al elegir otra región reemplaza y también limpia el país', () => {
    const filtros = { ...FILTROS_VACIOS, region: 'suramerica', pais: 'colombia' };
    expect(alternarRegion(filtros, 'europa')).toEqual({ region: 'europa', pais: null, pagina: null });
  });
});

describe('alternarPais / alternarMes / alternarDuracion / alternarPresupuesto', () => {
  it('cada faceta alterna su propio valor', () => {
    expect(alternarPais(FILTROS_VACIOS, 'colombia')).toEqual({ pais: 'colombia', pagina: null });
    expect(alternarPais({ ...FILTROS_VACIOS, pais: 'colombia' }, 'colombia')).toEqual({
      pais: null,
      pagina: null,
    });
    expect(alternarMes(FILTROS_VACIOS, 7)).toEqual({ mes: '7', pagina: null });
    expect(alternarMes({ ...FILTROS_VACIOS, mes: 7 }, 7)).toEqual({ mes: null, pagina: null });
    expect(alternarDuracion(FILTROS_VACIOS, '4-7')).toEqual({ duracion: ['4-7'], pagina: null });
    expect(alternarPresupuesto(FILTROS_VACIOS, 2)).toEqual({ presupuesto: ['2'], pagina: null });
  });
});

describe('establecerRangoDificultad / establecerOrden / limpiarFiltros', () => {
  it('construye los query params correspondientes', () => {
    expect(establecerRangoDificultad(2, 4)).toEqual({ dificultad_min: '2', dificultad_max: '4', pagina: null });
    expect(establecerRangoDificultad(null, null)).toEqual({
      dificultad_min: null,
      dificultad_max: null,
      pagina: null,
    });
    expect(establecerOrden('dificultad_desc')).toEqual({ orden: 'dificultad_desc', pagina: null });
    expect(establecerOrden('nombre')).toEqual({ orden: null, pagina: null });
    expect(limpiarFiltros()).toMatchObject({ tipo: null, region: null, pagina: null });
  });
});

describe('filtrosActivosComoLista', () => {
  const nombrePorSlug = (slug: string) => (slug === 'buceo' ? 'Buceo' : slug);
  const etiquetaTramo = () => '4 a 7 días';
  const etiquetaNivel = (escala: 'dificultad' | 'presupuesto', nivel: number) =>
    `${escala}-${nivel}`;

  it('produce una ficha por cada faceta activa, con la etiqueta legible', () => {
    const filtros = {
      ...FILTROS_VACIOS,
      tipo: ['buceo'],
      dificultadMin: 2,
      dificultadMax: 4,
      duracion: ['4-7'] as const,
      presupuesto: [3],
    };
    const activos = filtrosActivosComoLista(filtros, nombrePorSlug, etiquetaTramo, etiquetaNivel);
    expect(activos.map((a) => a.etiqueta)).toEqual([
      'Tipo: Buceo',
      'Dificultad: dificultad-2 a dificultad-4',
      'Duración: 4 a 7 días',
      'Presupuesto: presupuesto-3',
    ]);
  });

  it('sin filtros activos devuelve una lista vacía', () => {
    expect(filtrosActivosComoLista(FILTROS_VACIOS, nombrePorSlug, etiquetaTramo, etiquetaNivel)).toEqual([]);
  });
});
