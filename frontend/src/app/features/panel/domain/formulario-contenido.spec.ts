import {
  FormularioContenido,
  MENSAJES,
  aDecimal,
  aEntero,
  aIdOpcional,
  alternarNumero,
  anadirSinDuplicados,
  anuncioMovido,
  contarPalabras,
  enriquecerReferencias,
  esEnlaceExterno,
  esHrefPermitido,
  esSlugValido,
  esUrlHttp,
  etiquetaCampo,
  fechaLocal,
  formularioVacio,
  hayCambios,
  idCampo,
  idDestinoCampo,
  indicadorDias,
  moverEn,
  nuevaClaveLista,
  proponerSlug,
  quitarEn,
  redondearCoordenada,
  reemplazarEn,
  seccionDeCampo,
  seccionesDe,
  textoContadorPalabras,
  textoMinimo,
  textoPlano,
  validarFormato,
} from './formulario-contenido';
import { TipoContenido } from './modelos';

const HOY = '2026-10-08';

function con(tipo: TipoContenido, cambios: Partial<FormularioContenido> = {}): FormularioContenido {
  return { ...formularioVacio(tipo), titulo: 'Título', ...cambios };
}

function dia(cambios: Partial<FormularioContenido['dias'][number]> = {}): FormularioContenido['dias'][number] {
  return {
    clave: nuevaClaveLista('dia'),
    titulo: 'Día',
    actividades: '<p>Caminar</p>',
    distanciaKm: '',
    desnivelPositivo: '',
    desnivelNegativo: '',
    alojamiento: '',
    consejos: '',
    ...cambios,
  };
}

describe('formulario de contenido (dominio, TKT-023)', () => {
  it('AC_TKT023_02 validación de formato: título obligatorio y límites del contrato', () => {
    expect(validarFormato(formularioVacio('DESTINO'), HOY)).toEqual({ titulo: MENSAJES.obligatorio });
    const largo = validarFormato(
      con('DESTINO', {
        titulo: 'x'.repeat(151),
        resumen: 'x'.repeat(301),
        seoTitulo: 'x'.repeat(71),
        seoDescripcion: 'x'.repeat(161),
        clima: 'x'.repeat(5001),
      }),
      HOY,
    );
    expect(Object.keys(largo).sort()).toEqual(['clima', 'resumen', 'seoDescripcion', 'seoTitulo', 'titulo']);
    expect(validarFormato(con('GUIA'), HOY)).toEqual({});
  });

  it('AC_TKT023_04 slug: patrón [a-z0-9-] y propuesta desde el título (RULE-008)', () => {
    expect(validarFormato(con('DESTINO', { slug: 'Mal Slug' }), HOY)).toEqual({ slug: MENSAJES.slug });
    expect(validarFormato(con('DESTINO', { slug: 'bien-slug-2' }), HOY)).toEqual({});
    expect(validarFormato(con('DESTINO', { slug: 'a'.repeat(121) }), HOY)['slug']).toContain('120');
    expect(proponerSlug('  Torres del Paine: Circuito «W» ¡Ñandú!  ')).toBe('torres-del-paine-circuito-w-nandu');
    expect(proponerSlug('a'.repeat(130))).toHaveLength(120);
    expect(esSlugValido('trekking')).toBe(true);
    expect(esSlugValido('Mal')).toBe(false);
    expect(esSlugValido(null)).toBe(false);
  });

  it('AC_TKT023_02 RULE-009: la fecha de revisión no puede ser futura', () => {
    expect(validarFormato(con('GUIA', { fechaRevision: '2026-10-09' }), HOY)).toEqual({
      fechaRevision: MENSAJES.fechaFutura,
    });
    expect(validarFormato(con('GUIA', { fechaRevision: HOY }), HOY)).toEqual({});
    expect(fechaLocal(new Date(2026, 0, 5))).toBe('2026-01-05');
  });

  it('AC_TKT023_03 destino: rangos, duración mínima ≤ máxima, coordenadas y tipo principal', () => {
    const errores = validarFormato(
      con('DESTINO', {
        dificultad: '6',
        presupuesto: 'x',
        duracionMin: '10',
        duracionMax: '5',
        altitud: '9001',
        latitud: '91',
        longitud: 'abc',
        tipos: [1],
        tipoPrincipal: '2',
      }),
      HOY,
    );
    expect(errores).toEqual({
      dificultad: 'Escribe un valor entre 1 y 5.',
      presupuesto: MENSAJES.entero,
      duracionMax: MENSAJES.duracion,
      altitud: 'Escribe un valor entre -500 y 9000.',
      latitud: 'Escribe un valor entre -90 y 90.',
      longitud: MENSAJES.numero,
      tipoPrincipal: MENSAJES.principal,
    });
    expect(validarFormato(con('DESTINO', { duracionMin: '0', duracionMax: '3' }), HOY)).toEqual({
      duracionMin: 'Escribe un valor entre 1 y 90.',
    });
    expect(validarFormato(con('DESTINO', { latitud: '-33,123456', longitud: '-70.5', tipos: [2], tipoPrincipal: '2' }), HOY)).toEqual({});
  });

  it('AC_TKT023_03 itinerario: cada día necesita título y actividades (DiaEntrada) y números válidos', () => {
    const errores = validarFormato(
      con('ITINERARIO', {
        duracionDias: '61',
        distanciaTotal: '-1',
        desnivelAcumulado: '1.5',
        dias: [dia({ titulo: '', actividades: '<p> </p>', distanciaKm: 'x', desnivelPositivo: '20001', alojamiento: 'x'.repeat(301) }), dia()],
      }),
      HOY,
    );
    expect(errores).toEqual({
      duracionDias: 'Escribe un valor entre 1 y 60.',
      distanciaTotal: 'Escribe un valor entre 0 y 99999.9.',
      desnivelAcumulado: MENSAJES.entero,
      'dias.0.titulo': MENSAJES.obligatorio,
      'dias.0.actividades': MENSAJES.obligatorio,
      'dias.0.distanciaKm': MENSAJES.numero,
      'dias.0.desnivelPositivo': 'Escribe un valor entre 0 y 20000.',
      'dias.0.alojamiento': 'Escribe como máximo 300 caracteres.',
    });
  });

  it('AC_TKT023_03 tipo (checklist sin textos repetidos), colección, página, término y fuentes', () => {
    const item = (texto: string) => ({ clave: nuevaClaveLista('i'), texto, grupo: '', esencial: false });
    expect(
      validarFormato(con('TIPO', { nivelExigencia: '0', orden: '1001', checklist: [item('Agua'), item('agua'), item('')] }), HOY),
    ).toEqual({
      nivelExigencia: 'Escribe un valor entre 1 y 5.',
      orden: 'Escribe un valor entre 0 y 1000.',
      'checklist.1.texto': MENSAJES.duplicado,
      'checklist.2.texto': MENSAJES.obligatorio,
    });
    const ref = { id: 1, tipo: 'DESTINO' as const, titulo: 'D', estado: 'PUBLICADO' as const };
    expect(
      validarFormato(con('COLECCION', { elementos: [{ clave: 'e', contenido: ref, nota: 'x'.repeat(301) }] }), HOY),
    ).toEqual({ 'elementos.0.nota': 'Escribe como máximo 300 caracteres.' });
    expect(validarFormato(con('PAGINA'), HOY)).toEqual({
      versionDocumento: MENSAJES.obligatorio,
      vigenteDesde: MENSAJES.obligatorio,
    });
    expect(validarFormato(con('PAGINA', { versionDocumento: '1.0', vigenteDesde: HOY, slug: 'NO IMPORTA' }), HOY)).toEqual({});
    expect(validarFormato(con('TERMINO', { definicion: 'x'.repeat(601) }), HOY)).toEqual({
      definicion: 'Escribe como máximo 600 caracteres.',
    });
    const fuente = (titulo: string, url: string) => ({ clave: 'f', titulo, url, entidadEditora: '', fechaConsulta: '' });
    expect(
      validarFormato(con('GUIA', { fuentes: [fuente('', ''), fuente('Ok', 'javascript:alert(1)'), fuente('Ok', 'https://x.org')] }), HOY),
    ).toEqual({ 'fuentes.0.titulo': MENSAJES.obligatorio, 'fuentes.1.url': MENSAJES.url });
    expect(validarFormato(con('GUIA', { tipos: Array.from({ length: 13 }, (_, i) => i + 1) }), HOY)).toEqual({
      tipos: 'Como máximo 12 elementos.',
    });
  });

  it('AC_TKT023_14 RULE-021: enlaces solo http, https o rutas internas', () => {
    expect(esHrefPermitido('https://parques.cl')).toBe(true);
    expect(esHrefPermitido('/destinos/torres')).toBe(true);
    expect(esHrefPermitido('//evil.com')).toBe(false);
    expect(esHrefPermitido('/\\evil.com')).toBe(false);
    expect(esHrefPermitido('javascript:alert(1)')).toBe(false);
    expect(esHrefPermitido('data:text/html,x')).toBe(false);
    expect(esHrefPermitido('  ')).toBe(false);
    expect(esEnlaceExterno('https://x.org')).toBe(true);
    expect(esEnlaceExterno('/guias')).toBe(false);
    expect(esUrlHttp('ftp://x')).toBe(false);
  });

  it('AC_TKT023_03 conversiones, contadores, palabras e indicador de días (AC-118)', () => {
    expect(aEntero('')).toBeNull();
    expect(aEntero('12')).toBe(12);
    expect(aEntero('1.2')).toBeNaN();
    expect(aDecimal('3,5')).toBe(3.5);
    expect(aDecimal('x')).toBeNaN();
    expect(aDecimal(' ')).toBeNull();
    expect(aIdOpcional('7')).toBe(7);
    expect(aIdOpcional('0')).toBeNull();
    expect(aIdOpcional('')).toBeNull();
    expect(redondearCoordenada(-33.1234567)).toBe(-33.123457);
    expect(textoPlano('<p>Hola&nbsp;<strong>mundo</strong></p>')).toBe('Hola mundo');
    expect(contarPalabras('<p>uno dos</p><p>tres</p>')).toBe(3);
    expect(contarPalabras('')).toBe(0);
    expect(textoContadorPalabras(412, 600)).toBe('412 de 600 palabras mínimas');
    expect(textoMinimo(2, 3)).toBe('2 de 3 mínimo');
    expect(indicadorDias({ dias: [dia(), dia()], duracionDias: '2' })).toEqual({
      texto: 'Días: 2 de 2 según la duración',
      coincide: true,
    });
    expect(indicadorDias({ dias: [dia()], duracionDias: '3' }).coincide).toBe(false);
    expect(indicadorDias({ dias: [], duracionDias: '' }).texto).toContain('Indica la duración');
  });

  it('AC_TKT023_13 cambios sin guardar: compara los valores', () => {
    const base = con('DESTINO');
    expect(hayCambios(base, { ...base })).toBe(false);
    expect(hayCambios({ ...base, resumen: 'x' }, base)).toBe(true);
  });

  it('listas ordenables: mover, quitar, reemplazar, añadir sin duplicados y anuncio', () => {
    expect(moverEn([1, 2, 3], 0, 2)).toEqual([2, 3, 1]);
    const lista = [1, 2];
    expect(moverEn(lista, 0, 5)).toBe(lista);
    expect(moverEn(lista, 1, 1)).toBe(lista);
    expect(quitarEn([1, 2, 3], 1)).toEqual([1, 3]);
    expect(reemplazarEn([1, 2, 3], 1, 9)).toEqual([1, 9, 3]);
    const a = { id: 1, tipo: 'DESTINO' };
    const b = { id: 1, tipo: 'GUIA' };
    expect(anadirSinDuplicados([a], [a, b, { id: 2, tipo: 'GUIA' }], 2)).toEqual([a, b]);
    expect(anuncioMovido('Día 2', 3, 7)).toBe('Día 2 movido a la posición 3 de 7.');
    expect(alternarNumero([3, 1], 2)).toEqual([3, 1, 2].sort((x, y) => x - y));
    expect(alternarNumero([1, 2], 2)).toEqual([1]);
    expect(nuevaClaveLista('x')).not.toBe(nuevaClaveLista('x'));
  });

  it('secciones por tipo (BLUEPRINT §11.2), etiquetas e ids de los campos', () => {
    expect(seccionesDe('DESTINO').map((s) => s.id)).toEqual([
      'identidad',
      'datos',
      'contenido',
      'viaje',
      'seguridad',
      'ubicacion',
      'medios',
      'relacionados',
      'fuentes',
      'seo',
      'revision',
      'historial',
    ]);
    expect(seccionesDe('ITINERARIO').some((s) => s.id === 'dias')).toBe(true);
    expect(seccionesDe('TIPO').some((s) => s.id === 'checklist')).toBe(true);
    expect(seccionesDe('COLECCION').some((s) => s.id === 'elementos')).toBe(true);
    expect(seccionDeCampo('ITINERARIO', 'dias.2.titulo')?.titulo).toBe('Días');
    expect(seccionDeCampo('DESTINO', '_general')).toBeNull();
    expect(etiquetaCampo('dias.1.titulo')).toBe('Día 2: título');
    expect(etiquetaCampo('fuentes.0')).toBe('Fuente 1');
    expect(etiquetaCampo('descripcion')).toBe('Descripción');
    expect(etiquetaCampo('desconocido')).toBe('desconocido');
    expect(etiquetaCampo('otro.3.cosa')).toBe('otro 4: cosa');
    expect(idCampo('dias.2.titulo')).toBe('campo-dias-2-titulo');
    expect(idDestinoCampo('_general')).toBe('campo-titulo');
  });

  it('AC_TKT023_12 una revisión restaurada recupera miniaturas y títulos del formulario actual', () => {
    const medio = { id: 4, estado: 'DISPONIBLE' as const, miniatura: '/m/4.webp', textoAlternativo: 'Lago' };
    const ref = { id: 9, tipo: 'DESTINO' as const, titulo: 'Torres', estado: 'PUBLICADO' as const };
    const actual = con('COLECCION', {
      portada: medio,
      galeria: [medio],
      relaciones: [ref],
      destinos: [ref],
      destino: ref,
      elementos: [{ clave: 'e', contenido: ref, nota: '' }],
      terminos: [{ id: 3, nombre: 'Cumbre' }],
    });
    const sinDatos = { id: 4, estado: null, miniatura: null, textoAlternativo: null };
    const refSin = { id: 9, tipo: 'DESTINO' as const, titulo: 'Destino #9', estado: null };
    const restaurado = con('COLECCION', {
      portada: sinDatos,
      galeria: [sinDatos, { ...sinDatos, id: 5 }],
      relaciones: [refSin],
      destinos: [refSin],
      destino: refSin,
      elementos: [{ clave: 'x', contenido: refSin, nota: 'n' }],
      terminos: [{ id: 3, nombre: 'Término #3' }],
    });
    const enriquecido = enriquecerReferencias(restaurado, actual);
    expect(enriquecido.portada).toEqual(medio);
    expect(enriquecido.galeria.map((m) => m.miniatura)).toEqual(['/m/4.webp', null]);
    expect(enriquecido.relaciones[0].titulo).toBe('Torres');
    expect(enriquecido.destino?.titulo).toBe('Torres');
    expect(enriquecido.elementos[0]).toMatchObject({ nota: 'n', contenido: ref });
    expect(enriquecido.terminos[0].nombre).toBe('Cumbre');
    expect(enriquecerReferencias(con('COLECCION'), actual).portada).toBeNull();
  });
});
