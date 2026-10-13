import {
  AnalisisPublicacion,
  ImpactoRetiro,
  ResultadoTransicion,
  cascadaConfirmada,
  conCascada,
  entidadesAdicionales,
  hayCascada,
  motivoValido,
  pendientesAnalisis,
  textoCompletitud,
  textoRequisito,
  tituloResumenErrores,
} from './ciclo-editorial';
import {
  TIPOS_CONTENIDO,
  accionesEditor,
  admiteFiltros,
  etiquetaSingular,
  filtrosContenidosDesdeQuery,
  hayFiltrosContenidos,
  nivelesPorDefecto,
  paginaSoloAdministrador,
  puedeCrear,
  puedeEditarPagina,
  queryDesdeFiltrosContenidos,
  rutaEditor,
  rutaListado,
  rutaVistaPrevia,
  textoCaption,
  textoListadoVacio,
  textoNuevo,
  textoRecuento,
  tieneCicloEditorial,
  tieneVistaPrevia,
  tipoDeRuta,
  tituloEditor,
} from './contenidos';
import {
  rutaPublica,
  textoDuracion,
  textoEscala,
  textoMeses,
  tituloDocumentoVistaPrevia,
} from './vista-previa';

describe('contenidos (dominio, TKT-023)', () => {
  it('AC_TKT023_01 rutas por tipo: listado, editor (alta y edición) y vista previa', () => {
    expect(TIPOS_CONTENIDO.map((t) => tipoDeRuta(rutaListado(t).split('/').pop()))).toEqual(TIPOS_CONTENIDO);
    expect(tipoDeRuta('nada')).toBeNull();
    expect(tipoDeRuta(null)).toBeNull();
    expect(rutaListado('TIPO')).toBe('/panel/contenido/tipos-aventura');
    expect(rutaEditor('DESTINO', null)).toBe('/panel/contenido/destinos/nuevo');
    expect(rutaEditor('GUIA', 4)).toBe('/panel/contenido/guias/4');
    expect(rutaVistaPrevia('COLECCION', null)).toBe('/panel/contenido/colecciones/nuevo/vista-previa');
    expect(rutaVistaPrevia('ITINERARIO', 9)).toBe('/panel/contenido/itinerarios/9/vista-previa');
  });

  it('AC_TKT023_01 textos del listado y del editor según el género del tipo', () => {
    expect(textoNuevo('DESTINO')).toBe('Nuevo destino');
    expect(textoNuevo('GUIA')).toBe('Nueva guía');
    expect(tituloEditor('COLECCION', null)).toBe('Nueva colección');
    expect(tituloEditor('DESTINO', 'Torres del Paine')).toBe('Editar destino: Torres del Paine');
    expect(tituloEditor('DESTINO', '  ')).toBe('Editar destino: sin título');
    expect(etiquetaSingular('TIPO')).toBe('Tipo de aventura');
    expect(textoListadoVacio('ITINERARIO')).toBe('Aún no hay itinerarios');
    expect(textoRecuento(1, 'DESTINO')).toBe('1 destino');
    expect(textoRecuento(3, 'GUIA')).toBe('3 guías');
    expect(textoCaption('DESTINO')).toBe('Destinos, ordenados por última modificación');
  });

  it('AC_TKT023_01 filtros de la URL: valores inválidos se ignoran; la página 1 no va en la URL', () => {
    expect(filtrosContenidosDesdeQuery({ estado: 'PUBLICADO', q: '  lago ', pagina: '3' })).toEqual({
      estado: 'PUBLICADO',
      q: 'lago',
      pagina: 3,
    });
    expect(filtrosContenidosDesdeQuery({ estado: 'X', pagina: '0' })).toEqual({ estado: null, q: '', pagina: 1 });
    expect(filtrosContenidosDesdeQuery({ q: 'a'.repeat(150), pagina: 'abc' }).q).toHaveLength(100);
    expect(queryDesdeFiltrosContenidos({ estado: null, q: '', pagina: 1 })).toEqual({ estado: null, q: null, pagina: null });
    expect(queryDesdeFiltrosContenidos({ estado: 'BORRADOR', q: 'x', pagina: 2 })).toEqual({
      estado: 'BORRADOR',
      q: 'x',
      pagina: '2',
    });
    expect(hayFiltrosContenidos({ estado: null, q: '', pagina: 4 })).toBe(false);
    expect(hayFiltrosContenidos({ estado: 'RETIRADO', q: '', pagina: 1 })).toBe(true);
  });

  it('AC_TKT023_01 capacidades por tipo: páginas sin alta, filtros ni ciclo; glosario sin vista previa', () => {
    expect(puedeCrear('PAGINA')).toBe(false);
    expect(puedeCrear('TERMINO')).toBe(true);
    expect(admiteFiltros('PAGINA')).toBe(false);
    expect(tieneVistaPrevia('TERMINO')).toBe(false);
    expect(tieneVistaPrevia('PAGINA')).toBe(true);
    expect(tieneCicloEditorial('PAGINA')).toBe(false);
    expect(paginaSoloAdministrador('acerca-de')).toBe(false);
    expect(paginaSoloAdministrador('aviso-legal')).toBe(true);
    expect(paginaSoloAdministrador(null)).toBe(true);
    expect(puedeEditarPagina('EDITOR', true)).toBe(false);
    expect(puedeEditarPagina('ADMINISTRADOR', true)).toBe(true);
    expect(puedeEditarPagina('EDITOR', false)).toBe(true);
    expect(nivelesPorDefecto(4).map((n) => n.nivel)).toEqual([1, 2, 3, 4]);
  });

  it('AC_TKT023_11 STATE-001: acciones de la barra según el estado', () => {
    expect(accionesEditor({ tipo: 'DESTINO', estado: null, nuncaPublicado: true })).toMatchObject({
      principal: null,
      guardarBorrador: true,
      vistaPrevia: true,
      eliminar: false,
    });
    expect(accionesEditor({ tipo: 'DESTINO', estado: 'BORRADOR', nuncaPublicado: true })).toMatchObject({
      principal: 'PUBLICAR',
      eliminar: true,
      retirar: false,
    });
    expect(accionesEditor({ tipo: 'DESTINO', estado: 'BORRADOR', nuncaPublicado: false }).eliminar).toBe(false);
    expect(accionesEditor({ tipo: 'GUIA', estado: 'PUBLICADO', nuncaPublicado: false })).toMatchObject({
      principal: 'ACTUALIZAR',
      guardarBorrador: false,
      retirar: true,
    });
    expect(accionesEditor({ tipo: 'GUIA', estado: 'RETIRADO', nuncaPublicado: false })).toMatchObject({
      principal: 'REACTIVAR',
      vistaPrevia: false,
      soloLectura: true,
    });
    expect(accionesEditor({ tipo: 'PAGINA', estado: 'PUBLICADO', nuncaPublicado: false })).toMatchObject({
      principal: 'GUARDAR_PAGINA',
      retirar: false,
      eliminar: false,
      vistaPrevia: true,
    });
    expect(accionesEditor({ tipo: 'TERMINO', estado: 'BORRADOR', nuncaPublicado: true }).vistaPrevia).toBe(false);
  });
});

describe('ciclo editorial (dominio)', () => {
  const ref = (id: number, tipo: 'ITINERARIO' | 'TIPO' | 'COLECCION' = 'TIPO') => ({
    id,
    tipo,
    titulo: `R${id}`,
    estado: 'PUBLICADO' as const,
  });
  const impacto: ImpactoRetiro = {
    retirable: true,
    bloqueos: [],
    bloqueosCascada: [],
    itinerariosEnCascada: [ref(5, 'ITINERARIO')],
    tiposEnCascada: [ref(8)],
    colecciones: [],
    destacados: [],
    enlacesEntrantes: 0,
  };

  it('AC_TKT023_10 cascada confirmada = itinerarios + tipos que el editor vio', () => {
    expect(cascadaConfirmada(impacto)).toEqual([
      { id: 5, tipo: 'ITINERARIO' },
      { id: 8, tipo: 'TIPO' },
    ]);
    expect(hayCascada(impacto)).toBe(true);
    expect(hayCascada({ itinerariosEnCascada: [], tiposEnCascada: [] })).toBe(false);
  });

  it('AC_TKT023_10 impacto_modificado: se sustituye la cascada y un bloqueo la vuelve no retirable', () => {
    const nuevo = conCascada(impacto, { itinerariosEnCascada: [], tiposEnCascada: [ref(9)], bloqueosCascada: [] });
    expect(nuevo.tiposEnCascada.map((t) => t.id)).toEqual([9]);
    expect(nuevo.retirable).toBe(true);
    const bloqueado = conCascada(impacto, {
      itinerariosEnCascada: [],
      tiposEnCascada: [ref(9)],
      bloqueosCascada: [{ tipoAventura: ref(9), itinerarios: [ref(3, 'ITINERARIO')], totalItinerarios: 1 }],
    });
    expect(bloqueado.retirable).toBe(false);
  });

  it('AC_TKT023_10 el motivo del retiro es obligatorio y acotado', () => {
    expect(motivoValido('  ')).toBe(false);
    expect(motivoValido('Cierre del parque')).toBe(true);
    expect(motivoValido('x'.repeat(501))).toBe(false);
  });

  it('AC_TKT023_07 textos del ErrorSummary, completitud y requisitos', () => {
    expect(tituloResumenErrores('publicar', 1)).toBe('No se puede publicar todavía. Corrige 1 problema:');
    expect(tituloResumenErrores('guardar', 3)).toBe('No se puede guardar todavía. Corrige 3 problemas:');
    expect(textoCompletitud({ cumple: true, pendientes: [] })).toBe('Listo para publicar');
    const req = { campo: 'galeria', codigo: 'x', mensaje: 'Faltan imágenes.', referencias: [] };
    expect(textoCompletitud({ cumple: false, pendientes: [req] })).toBe('Falta 1 requisito para publicar');
    expect(textoCompletitud({ cumple: false, pendientes: [req, req] })).toBe('Faltan 2 requisitos para publicar');
    expect(textoRequisito(req)).toBe('Galería: Faltan imágenes.');
    expect(textoRequisito({ ...req, campo: '_general' })).toBe('Faltan imágenes.');
  });

  it('AC_TKT023_08 pendientes de un análisis multi-entidad y entidades adicionales de un resultado', () => {
    const validacion = {
      id: 1,
      tipo: 'DESTINO' as const,
      titulo: 'D',
      estado: 'BORRADOR' as const,
      version: 1,
      rol: 'PRINCIPAL' as const,
      cumple: false,
      pendientes: [{ campo: 'resumen', codigo: 'x', mensaje: 'm', referencias: [] }],
    };
    const analisis: AnalisisPublicacion = {
      operacion: 'PUBLICAR',
      confirmable: false,
      entidad: validacion,
      copublicacion: [{ ...validacion, id: 2, tipo: 'TIPO', rol: 'COPUBLICACION' }],
      copublicarTipos: [{ id: 2, version: 1 }],
      tiposEnCascada: [],
      bloqueosCascada: [],
    };
    expect(pendientesAnalisis(analisis)).toBe(2);
    const resultado: ResultadoTransicion = {
      id: 1,
      estado: 'PUBLICADO',
      version: 2,
      urlPublica: '/destinos/d',
      entidades: [
        { id: 1, tipo: 'DESTINO', titulo: 'D', estado: 'PUBLICADO', version: 2, origen: 'PRINCIPAL', urlPublica: null },
        { id: 2, tipo: 'TIPO', titulo: 'T', estado: 'PUBLICADO', version: 2, origen: 'COPUBLICACION', urlPublica: null },
      ],
    };
    expect(entidadesAdicionales(resultado).map((e) => e.id)).toEqual([2]);
  });
});

describe('vista previa (dominio)', () => {
  it('AC_TKT023_06 enlaces a versiones públicas, escalas, meses y duración legibles', () => {
    expect(rutaPublica('DESTINO', 'torres')).toBe('/destinos/torres');
    expect(rutaPublica('TIPO', 'trekking')).toBe('/tipos-de-aventura/trekking');
    expect(rutaPublica('TERMINO', 'x')).toBeNull();
    expect(rutaPublica('DESTINO', 'javascript:alert(1)')).toBeNull();
    expect(rutaPublica('DESTINO', null)).toBeNull();
    expect(textoEscala(3, 5)).toBe('3 de 5');
    expect(textoEscala(9, 5)).toBeNull();
    expect(textoEscala(null, 5)).toBeNull();
    expect(textoMeses([1, 12, 13])).toBe('enero, diciembre');
    expect(textoMeses([])).toBeNull();
    expect(textoDuracion(3, 5)).toBe('3 a 5 días');
    expect(textoDuracion(1, null)).toBe('1 día');
    expect(textoDuracion(4, 4)).toBe('4 días');
    expect(textoDuracion(null, null)).toBeNull();
    expect(tituloDocumentoVistaPrevia('Lago')).toBe('Vista previa (no publicado) — Lago');
    expect(tituloDocumentoVistaPrevia('')).toBe('Vista previa (no publicado) — sin título');
  });
});
