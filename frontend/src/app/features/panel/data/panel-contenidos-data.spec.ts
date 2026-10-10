import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { ContenidoPanelMeta } from '../../../api/models/contenido-panel-meta';
import { DestinoPanel } from '../../../api/models/destino-panel';
import { VistaPrevia } from '../../../api/models/vista-previa';
import { FILTROS_CONTENIDOS_VACIOS } from '../domain/contenidos';
import { FormularioContenido, formularioVacio } from '../domain/formulario-contenido';
import { TipoContenido } from '../domain/modelos';
import {
  ContenidoPanelDto,
  campoFormulario,
  cuerpoDesdeFormulario,
  erroresDeFormulario,
  leerBloqueosCascada,
  leerEntidadesEnConflicto,
  leerErroresPorEntidad,
  leerImpactoCascada,
  leerUsos,
  mapAnalisis,
  mapContenido,
  mapImpacto,
  mapPaginaContenidos,
  mapResultado,
  mapRevisiones,
} from './contenidos.mapper';
import { PanelContenidosRepositorio } from './panel-contenidos.repositorio';
import { mapVistaPrevia } from './vista-previa.mapper';

const BASE = '/api/v1/panel/contenidos';

function meta(tipo: TipoContenido, extra: Partial<ContenidoPanelMeta> = {}): ContenidoPanelMeta {
  return {
    id: 11,
    tipo,
    estado_editorial: 'BORRADOR',
    version: 3,
    slug_bloqueado: false,
    creado_en: '2026-10-01T10:00:00Z',
    actualizado_en: '2026-10-02T10:00:00Z',
    creado_por: { id: 1, etiqueta: 'Ana' },
    actualizado_por: { id: 2, etiqueta: 'Luis' },
    requisitos_publicacion: {
      cumple: false,
      pendientes: [
        { campo: 'galeria_ids', code: 'galeria_minima', mensaje: 'Faltan imágenes.' },
        { campo: 'tipos_ids', code: 'tipo_retirado', mensaje: 'Reactiva primero el tipo Kayak', referencias: [{ id: 4, tipo: 'TIPO', titulo: 'Kayak', estado_editorial: 'RETIRADO' }] },
      ],
    },
    referencias: {
      medios: [{ id: 5, estado: 'DISPONIBLE', url_miniatura: '/m/5.webp', texto_alternativo: 'Lago' }],
      contenidos: [
        { id: 20, tipo: 'DESTINO', titulo: 'Torres', estado_editorial: 'PUBLICADO' },
        { id: 21, tipo: 'ITINERARIO', titulo: 'Circuito W', estado_editorial: 'PUBLICADO' },
      ],
      terminos: [{ id: 30, termino: 'Refugio' }],
    },
    ...extra,
  };
}

const DESTINO: DestinoPanel = {
  ...meta('DESTINO'),
  titulo: 'Torres del Paine',
  slug: 'torres-del-paine',
  fecha_ultima_revision: '2026-09-01',
  seo_titulo: 'Torres',
  seo_descripcion: 'SEO',
  fuentes: [{ titulo: 'CONAF', url: 'https://conaf.cl', entidad_editora: null, fecha_consulta: '2026-08-01' }],
  relaciones: [{ tipo: 'ITINERARIO', id: 21 }, { tipo: 'GUIA', id: 99 }],
  terminos_ids: [30, 31],
  pais_id: 3,
  resumen: 'Resumen',
  descripcion_experta: '<p>Texto</p>',
  tipos_ids: [4, 6],
  tipo_principal_id: 6,
  dificultad: 3,
  meses_mejor_epoca: [1, 2],
  duracion_min_dias: 3,
  duracion_max_dias: 7,
  nivel_presupuesto: 2,
  clima: 'Ventoso',
  altitud_max_m: 3050,
  como_llegar: '<p>Avión</p>',
  seguridad_riesgos: '<p>Viento</p>',
  sostenibilidad: '<p>Basura</p>',
  latitud: -50.94,
  longitud: -73.4,
  portada_id: 5,
  galeria_ids: [5, 6],
};

function rellenado(tipo: TipoContenido, extra: Partial<FormularioContenido> = {}): FormularioContenido {
  return { ...formularioVacio(tipo), titulo: 'T', ...extra };
}

describe('contenidos.mapper (contrato ↔ dominio, TKT-023)', () => {
  it('AC_TKT023_03 destino: DTO → formulario con datos de visualización de las referencias', () => {
    const c = mapContenido(DESTINO);
    expect(c).toMatchObject({
      id: 11,
      tipo: 'DESTINO',
      estado: 'BORRADOR',
      version: 3,
      slugBloqueado: false,
      nuncaPublicado: true,
      actualizadoPor: 'Luis',
      soloAdministrador: false,
      nombrePagina: null,
    });
    expect(c.requisitos.pendientes[0]).toMatchObject({ campo: 'galeria', codigo: 'galeria_minima' });
    expect(c.requisitos.pendientes[1].referencias).toEqual([{ id: 4, tipo: 'TIPO', titulo: 'Kayak', estado: 'RETIRADO' }]);
    const f = c.formulario;
    expect(f).toMatchObject({
      titulo: 'Torres del Paine',
      slug: 'torres-del-paine',
      pais: '3',
      tipos: [4, 6],
      tipoPrincipal: '6',
      dificultad: '3',
      duracionMin: '3',
      latitud: '-50.94',
      descripcion: '<p>Texto</p>',
      comoLlegar: '<p>Avión</p>',
    });
    expect(f.portada).toEqual({ id: 5, estado: 'DISPONIBLE', miniatura: '/m/5.webp', textoAlternativo: 'Lago' });
    expect(f.galeria[1]).toEqual({ id: 6, estado: null, miniatura: null, textoAlternativo: null });
    expect(f.relaciones.map((r) => r.titulo)).toEqual(['Circuito W', 'Contenido #99']);
    expect(f.terminos.map((t) => t.nombre)).toEqual(['Refugio', 'Término #31']);
    expect(f.fuentes[0]).toMatchObject({ titulo: 'CONAF', url: 'https://conaf.cl', entidadEditora: '', fechaConsulta: '2026-08-01' });
  });

  it('AC_TKT023_03 destino: formulario → cuerpo del contrato (ida y vuelta)', () => {
    const cuerpo = cuerpoDesdeFormulario(mapContenido(DESTINO).formulario);
    expect(cuerpo).toEqual({
      titulo: 'Torres del Paine',
      slug: 'torres-del-paine',
      fecha_ultima_revision: '2026-09-01',
      seo_titulo: 'Torres',
      seo_descripcion: 'SEO',
      relaciones: [{ tipo: 'ITINERARIO', id: 21 }, { tipo: 'GUIA', id: 99 }],
      terminos_ids: [30, 31],
      fuentes: [{ titulo: 'CONAF', url: 'https://conaf.cl', entidad_editora: null, fecha_consulta: '2026-08-01' }],
      pais_id: 3,
      resumen: 'Resumen',
      descripcion_experta: '<p>Texto</p>',
      tipos_ids: [4, 6],
      tipo_principal_id: 6,
      dificultad: 3,
      meses_mejor_epoca: [1, 2],
      duracion_min_dias: 3,
      duracion_max_dias: 7,
      nivel_presupuesto: 2,
      clima: 'Ventoso',
      altitud_max_m: 3050,
      como_llegar: '<p>Avión</p>',
      seguridad_riesgos: '<p>Viento</p>',
      sostenibilidad: '<p>Basura</p>',
      latitud: -50.94,
      longitud: -73.4,
      portada_id: 5,
      galeria_ids: [5, 6],
    });
    // Vacíos → null; coordenadas a 6 decimales; HTML vacío → null.
    const vacio = cuerpoDesdeFormulario(
      rellenado('DESTINO', { slug: ' ', descripcion: '<p><br></p>', latitud: '-33,1234567', dificultad: 'x' }),
    );
    expect(vacio).toMatchObject({ slug: null, descripcion_experta: null, latitud: -33.123457, dificultad: null, pais_id: null });
  });

  it('AC_TKT023_03 itinerario (días numerados), guía, tipo (checklist), colección, término y página', () => {
    const itinerario = mapContenido({
      ...meta('ITINERARIO'),
      titulo: 'Circuito',
      destino_id: 20,
      duracion_dias: 2,
      dias: [
        { numero_dia: 2, titulo: 'B', actividades: '<p>b</p>', distancia_km: 12.5 },
        { numero_dia: 1, titulo: 'A', actividades: '<p>a</p>', consejos: '<p>c</p>' },
      ],
      riesgos_seguridad: '<p>r</p>',
    } as ContenidoPanelDto);
    expect(itinerario.formulario.destino).toEqual({ id: 20, tipo: 'DESTINO', titulo: 'Torres', estado: 'PUBLICADO' });
    expect(itinerario.formulario.dias.map((d) => d.titulo)).toEqual(['A', 'B']);
    const cuerpoIt = cuerpoDesdeFormulario(itinerario.formulario);
    expect(cuerpoIt['dias']).toEqual([
      { numero_dia: 1, titulo: 'A', actividades: '<p>a</p>', distancia_km: null, desnivel_positivo_m: null, desnivel_negativo_m: null, alojamiento_orientativo: null, consejos: '<p>c</p>' },
      { numero_dia: 2, titulo: 'B', actividades: '<p>b</p>', distancia_km: 12.5, desnivel_positivo_m: null, desnivel_negativo_m: null, alojamiento_orientativo: null, consejos: null },
    ]);
    expect(cuerpoIt).toMatchObject({ destino_id: 20, duracion_dias: 2, riesgos_seguridad: '<p>r</p>' });

    const guia = mapContenido({ ...meta('GUIA'), titulo: 'G', categoria_id: 2, cuerpo: '<p>x</p>', destinos_ids: [20], remite_a_metodologia: true } as ContenidoPanelDto);
    expect(guia.formulario).toMatchObject({ categoria: '2', descripcion: '<p>x</p>', remiteMetodologia: true });
    expect(cuerpoDesdeFormulario(guia.formulario)).toMatchObject({ categoria_id: 2, cuerpo: '<p>x</p>', destinos_ids: [20], remite_a_metodologia: true });

    const tipo = mapContenido({
      ...meta('TIPO'),
      titulo: 'Trekking',
      nivel_exigencia: 4,
      orden: 2,
      descripcion: '<p>d</p>',
      checklist: [
        { texto: 'Botas', esencial: true, orden: 1 },
        { texto: 'Agua', grupo: 'Básico', esencial: false, orden: 0 },
      ],
    } as ContenidoPanelDto);
    expect(tipo.formulario.checklist.map((c) => c.texto)).toEqual(['Agua', 'Botas']);
    expect(cuerpoDesdeFormulario(tipo.formulario)).toMatchObject({
      nivel_exigencia: 4,
      orden: 2,
      descripcion: '<p>d</p>',
      checklist: [
        { texto: 'Agua', grupo: 'Básico', esencial: false, orden: 0 },
        { texto: 'Botas', grupo: null, esencial: true, orden: 1 },
      ],
    });

    const coleccion = mapContenido({
      ...meta('COLECCION'),
      titulo: 'Top',
      elementos: [{ tipo_contenido: 'ITINERARIO', contenido_id: 21, orden: 0, nota_editorial: 'Imperdible' }],
    } as ContenidoPanelDto);
    expect(coleccion.formulario.elementos[0]).toMatchObject({ nota: 'Imperdible', contenido: { titulo: 'Circuito W' } });
    expect(cuerpoDesdeFormulario(coleccion.formulario)['elementos']).toEqual([
      { tipo_contenido: 'ITINERARIO', contenido_id: 21, orden: 0, nota_editorial: 'Imperdible' },
    ]);

    const termino = mapContenido({
      ...meta('TERMINO'),
      titulo: 'Refugio',
      definicion: 'Casa',
      vinculado_en: [{ id: 20, tipo: 'DESTINO', titulo: 'Torres', estado_editorial: 'PUBLICADO' }],
    } as ContenidoPanelDto);
    expect(termino.vinculadoEn).toHaveLength(1);
    expect(cuerpoDesdeFormulario(termino.formulario)).toEqual({ titulo: 'Refugio', slug: null, definicion: 'Casa', fecha_ultima_revision: null });

    const pagina = mapContenido({
      ...meta('PAGINA', { estado_editorial: 'PUBLICADO', primera_publicacion_en: '2026-01-01T00:00:00Z' }),
      titulo: 'Aviso legal',
      cuerpo: '<p>x</p>',
      version_documento: '1.0',
      vigente_desde: '2026-01-01',
      clave: 'AVISO_LEGAL',
      solo_administrador: true,
    } as ContenidoPanelDto);
    expect(pagina).toMatchObject({ soloAdministrador: true, nombrePagina: 'Aviso legal', nuncaPublicado: false });
    expect(cuerpoDesdeFormulario(pagina.formulario)).toEqual({
      titulo: 'Aviso legal',
      cuerpo: '<p>x</p>',
      version_documento: '1.0',
      vigente_desde: '2026-01-01',
      fecha_ultima_revision: null,
      seo_titulo: null,
      seo_descripcion: null,
    });
  });

  it('AC_TKT023_02 errores del contrato → claves del formulario (incluidos campos anidados)', () => {
    expect(campoFormulario('descripcion_experta')).toBe('descripcion');
    expect(campoFormulario('dias.2.titulo')).toBe('dias.2.titulo');
    expect(campoFormulario('dias.0.desnivel_positivo_m')).toBe('dias.0.desnivelPositivo');
    expect(campoFormulario('fuentes.1')).toBe('fuentes.1');
    expect(campoFormulario('fuentes.x')).toBe('fuentes');
    expect(campoFormulario('desconocido')).toBe('_general');
    expect(
      erroresDeFormulario({
        slug: ['En uso.'],
        'copublicar_tipos.4.resumen': ['No va al formulario.'],
        resumen: ['Uno.', 'Dos.'],
        cuerpo: [],
        descripcion: ['A.'],
        descripcion_experta: ['B.'],
      }),
    ).toEqual({ slug: 'En uso.', resumen: 'Uno.', descripcion: 'A. B.' });
  });

  it('AC_TKT023_07..10 análisis, impacto, resultado, revisiones y miembros de extensión', () => {
    const ref = { id: 4, tipo: 'TIPO' as const, titulo: 'Kayak', estado_editorial: 'BORRADOR' as const };
    const validacion = { ...ref, cumple: true, pendientes: [], rol: 'COPUBLICACION' as const, version: 2 };
    const analisis = mapAnalisis({
      operacion: 'PUBLICAR',
      confirmable: true,
      entidad: { ...validacion, id: 11, tipo: 'DESTINO', rol: 'PRINCIPAL' },
      copublicacion: [validacion],
      copublicar_tipos: [{ id: 4, version: 2 }],
      tipos_en_cascada: [],
      bloqueos_cascada: [{ tipo_aventura: ref, itinerarios: [{ ...ref, id: 9, tipo: 'ITINERARIO' }], total_itinerarios: 3 }],
    });
    expect(analisis.copublicarTipos).toEqual([{ id: 4, version: 2 }]);
    expect(analisis.copublicacion[0]).toMatchObject({ id: 4, estado: 'BORRADOR', rol: 'COPUBLICACION' });
    expect(analisis.bloqueosCascada[0]).toMatchObject({ totalItinerarios: 3, tipoAventura: { titulo: 'Kayak' } });

    const impacto = mapImpacto({
      retirable: false,
      bloqueos: [{ id: 1, tipo_entidad: 'DESTINO', titulo: 'X' }],
      bloqueos_cascada: [],
      colecciones: [ref],
      destacados: ['DESTINOS'],
      enlaces_entrantes: 2,
      itinerarios_en_cascada: [],
      tipos_en_cascada: [ref],
    });
    expect(impacto).toMatchObject({ retirable: false, destacados: ['DESTINOS'], enlacesEntrantes: 2 });
    expect(impacto.bloqueos[0]).toEqual({ id: 1, tipoEntidad: 'DESTINO', titulo: 'X', estado: null });

    const resultado = mapResultado({
      id: 11,
      tipo: 'DESTINO',
      estado_editorial: 'PUBLICADO',
      version: 4,
      url_publica: '/destinos/torres',
      afectados: [],
      entidades: [{ ...ref, version: 3, origen: 'COPUBLICACION' }],
    });
    expect(resultado).toMatchObject({ estado: 'PUBLICADO', urlPublica: '/destinos/torres' });
    expect(resultado.entidades[0]).toMatchObject({ origen: 'COPUBLICACION', urlPublica: null });

    const revisiones = mapRevisiones({
      resultados: [{ numero_revision: 2, creado_en: '2026-10-01T00:00:00Z', creado_por: { id: 1, etiqueta: 'Ana' }, motivo: 'PUBLICACION' }],
      pagina: 1,
      total_paginas: 1,
      total: 1,
      tamano_pagina: 50,
      anterior: null,
      siguiente: null,
    });
    expect(revisiones.revisiones[0]).toMatchObject({ numero: 2, creadaPor: 'Ana', motivo: 'PUBLICACION' });

    const extra = {
      errores_por_entidad: [
        { id: 11, tipo: 'DESTINO', titulo: 'Torres', rol: 'PRINCIPAL', estado_editorial: 'BORRADOR', errores: [{ campo: 'resumen', code: 'requerido', mensaje: 'Falta.' }] },
        { id: 'x', tipo: 'TIPO' },
        'basura',
      ],
      impacto_cascada: { itinerarios_en_cascada: [{ id: 9, tipo: 'ITINERARIO', titulo: 'It' }], tipos_en_cascada: [], bloqueos_cascada: [{ tipo_aventura: { id: 4, tipo: 'TIPO' }, itinerarios: [] }, { tipo_aventura: null }] },
      bloqueos_cascada: [{ tipo_aventura: { id: 4, tipo: 'TIPO', titulo: 'Kayak' }, itinerarios: [{ id: 9, tipo: 'ITINERARIO', titulo: 'It' }], total_itinerarios: 1 }],
      usos: [{ id: 5, tipo_entidad: 'COLECCION', titulo: 'Top', estado_editorial: 'PUBLICADO' }, { id: null }],
      entidades_en_conflicto: [{ id: 4, tipo: 'TIPO', titulo: 'Kayak' }],
    };
    expect(leerErroresPorEntidad(extra)).toEqual([
      { id: 11, tipo: 'DESTINO', titulo: 'Torres', rol: 'PRINCIPAL', errores: [{ campo: 'resumen', codigo: 'requerido', mensaje: 'Falta.', referencias: [] }] },
    ]);
    expect(leerImpactoCascada(extra)).toMatchObject({
      itinerariosEnCascada: [{ id: 9, titulo: 'It' }],
      bloqueosCascada: [{ tipoAventura: { id: 4, titulo: '#4' }, totalItinerarios: 0 }],
    });
    expect(leerImpactoCascada({})).toBeNull();
    expect(leerBloqueosCascada(extra)[0].itinerarios[0].titulo).toBe('It');
    expect(leerUsos(extra)).toEqual([{ id: 5, tipoEntidad: 'COLECCION', titulo: 'Top', estado: 'PUBLICADO' }]);
    expect(leerEntidadesEnConflicto(extra)[0]).toMatchObject({ id: 4, estado: null });
    expect(leerErroresPorEntidad({ errores_por_entidad: 'x' })).toEqual([]);
  });

  it('listado: página de resúmenes con «Ver en el sitio» solo si está publicado', () => {
    const pagina = mapPaginaContenidos({
      resultados: [
        { id: 1, tipo: 'DESTINO', titulo: 'A', estado_editorial: 'PUBLICADO', publicado: true, url_publica: '/destinos/a', actualizado_en: '2026-10-01T00:00:00Z', actualizado_por: { id: 1, etiqueta: 'Ana' }, version: 1, fecha_ultima_revision: '2026-09-01' },
        { id: 2, tipo: 'DESTINO', titulo: 'B', estado_editorial: 'BORRADOR', publicado: false, url_publica: '/destinos/b', actualizado_en: '2026-10-01T00:00:00Z', actualizado_por: { id: 1, etiqueta: 'Ana' }, version: 1 },
      ],
      pagina: 2,
      total_paginas: 3,
      total: 120,
      tamano_pagina: 50,
      anterior: null,
      siguiente: null,
    });
    expect(pagina).toMatchObject({ pagina: 2, totalPaginas: 3, total: 120 });
    expect(pagina.contenidos.map((c) => c.urlPublica)).toEqual(['/destinos/a', null]);
    expect(pagina.contenidos[1]).toMatchObject({ slug: null, fechaRevision: null });
  });
});

describe('vista-previa.mapper (SCR-037)', () => {
  const imagen = {
    texto_alternativo: 'Lago',
    autor_credito: 'Ana',
    licencia: { codigo: 'CC', nombre: 'CC' },
    derivados: [
      { formato: 'WEBP', ancho: 640, url: '/i/640.webp' },
      { formato: 'WEBP', ancho: 1280, url: '/i/1280.webp' },
      { formato: 'GIF', ancho: 10, url: '/x' },
    ],
  };
  const vista = (forma: VistaPrevia['forma'], datos: object): VistaPrevia => ({
    forma,
    datos,
    marca: 'VISTA PREVIA – NO PUBLICADO',
    requisitos_publicacion: { cumple: false, pendientes: [{ campo: 'resumen', code: 'r', mensaje: 'Falta' }] },
  });

  it('AC_TKT023_06 destino: datos clave, bloques, galería, fuentes seguras y enlaces públicos', () => {
    const v = mapVistaPrevia(
      vista('DestinoDetalle', {
        titulo: 'Torres',
        resumen: 'R',
        pais: { nombre: 'Chile' },
        tipo_principal: { nombre: 'Trekking' },
        tipos: [{ nombre: 'Trekking' }, { nombre: 'Kayak' }],
        dificultad: 3,
        duracion_min_dias: 3,
        duracion_max_dias: 5,
        meses_mejor_epoca: [1],
        altitud_max_m: 3000,
        latitud: -50,
        longitud: -73,
        descripcion_experta: '<p>d</p>',
        portada: imagen,
        galeria: [imagen, { derivados: [] }],
        fuentes: [{ titulo: 'A', url: 'javascript:x' }, { titulo: 'B', url: 'https://b.org', entidad_editora: 'E' }, { url: 'x' }],
        relacionados: [{ titulo: 'Guía', tipo: 'GUIA', slug: 'guia-x' }, { titulo: 'Mal', tipo: 'GUIA', slug: 'Mal Slug' }],
        metadatos: { fecha_ultima_revision: '2026-09-01' },
      }),
    );
    expect(v).toMatchObject({ tipo: 'DESTINO', titulo: 'Torres', antetitulo: 'Chile', revision: '2026-09-01' });
    expect(v.datos.map((d) => d.etiqueta)).toEqual(['Tipo principal', 'Tipos de aventura', 'Dificultad', 'Duración', 'Mejores meses', 'Altitud máxima', 'Coordenadas']);
    expect(v.portada).toMatchObject({ src: '/i/1280.webp', ancho: 1280, alto: 853, alt: 'Lago', credito: 'Ana' });
    expect(v.galeria).toHaveLength(1);
    expect(v.fuentes).toEqual([
      { titulo: 'A', url: null, entidad: null },
      { titulo: 'B', url: 'https://b.org', entidad: 'E' },
    ]);
    expect(v.enlaces).toEqual([{ titulo: 'Guía', ruta: '/guias/guia-x' }]);
    expect(v.requisitos.pendientes).toHaveLength(1);
  });

  it('AC_TKT023_06 itinerario, guía, tipo, colección y página; datos ausentes no rompen', () => {
    const it = mapVistaPrevia(
      vista('ItinerarioDetalle', {
        titulo: 'W',
        destino: { titulo: 'Torres', slug: 'torres' },
        dias: [{ numero_dia: 2, titulo: 'B', actividades: '<p>b</p>' }, { numero_dia: 1, titulo: 'A', alojamiento_orientativo: 'Refugio' }],
        duracion_dias: 2,
        distancia_total_km: 50,
        desnivel_acumulado_m: 900,
        riesgos_seguridad: '<p>r</p>',
      }),
    );
    expect(it.antetitulo).toBe('Torres');
    expect(it.listas[0].elementos.map((e) => e.titulo)).toEqual(['Día 1: A', 'Día 2: B']);
    expect(it.enlaces[0]).toEqual({ titulo: 'Torres', ruta: '/destinos/torres' });
    const guia = mapVistaPrevia(vista('GuiaDetalle', { titulo: 'G', categoria: { nombre: 'Seguridad' }, cuerpo: '<p>x</p>', destinos_relacionados: [{ titulo: 'D', slug: 'd' }] }));
    expect(guia).toMatchObject({ antetitulo: 'Seguridad', enlaces: [{ ruta: '/destinos/d' }] });
    const tipo = mapVistaPrevia(vista('TipoAventuraDetalle', { titulo: 'T', nivel_exigencia: 2, checklist: [{ texto: 'Agua', esencial: true, orden: 1 }, { orden: 0 }] }));
    expect(tipo.listas[0].elementos).toEqual([{ titulo: 'Agua', detalle: null, html: null, destacado: true }]);
    const col = mapVistaPrevia(
      vista('ColeccionDetalle', {
        titulo: 'C',
        elementos: [
          { tipo: 'ITINERARIO', orden: 1, itinerario: { titulo: 'W', slug: 'w' }, nota_editorial: 'Top' },
          { tipo: 'DESTINO', orden: 0, destino: { titulo: 'D' } },
          { tipo: 'DESTINO', orden: 2 },
        ],
      }),
    );
    expect(col.listas[0].elementos.map((e) => e.titulo)).toEqual(['D', 'W']);
    expect(col.enlaces).toEqual([{ titulo: 'W', ruta: '/itinerarios/w' }]);
    const pag = mapVistaPrevia(vista('PaginaInstitucionalPublica', { version_documento: '2', vigente_desde: '2026-01-01', cuerpo: '<p>x</p>' }));
    expect(pag).toMatchObject({ titulo: 'Sin título', datos: [{ etiqueta: 'Versión', valor: '2' }, { etiqueta: 'Vigente desde', valor: '2026-01-01' }] });
    expect(mapVistaPrevia({ ...vista('DestinoDetalle', {}), datos: [] as unknown as object }).titulo).toBe('Sin título');
  });
});

describe('PanelContenidosRepositorio (cliente generado, TKT-023)', () => {
  let repo: PanelContenidosRepositorio;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: ApiConfiguration, useValue: { rootUrl: '' } }],
    });
    repo = TestBed.inject(PanelContenidosRepositorio);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    http.verify();
    TestBed.resetTestingModule();
  });

  const paginaVacia = { resultados: [], pagina: 1, total_paginas: 1, total: 0, tamano_pagina: 50, anterior: null, siguiente: null };

  it('AC_TKT023_01 listar: endpoint por tipo y filtros solo cuando aplican', async () => {
    const tipos: [TipoContenido, string][] = [
      ['DESTINO', 'destinos'],
      ['ITINERARIO', 'itinerarios'],
      ['GUIA', 'guias'],
      ['TIPO', 'tipos-aventura'],
      ['COLECCION', 'colecciones'],
      ['TERMINO', 'glosario'],
      ['PAGINA', 'paginas'],
    ];
    for (const [tipo, ruta] of tipos) {
      const p = repo.listar(tipo, { estado: 'PUBLICADO', q: 'lago', pagina: 2 });
      const req = http.expectOne((r) => r.url === `${BASE}/${ruta}`);
      expect(req.request.params.get('pagina')).toBe('2');
      expect(req.request.params.get('q')).toBe(tipo === 'PAGINA' ? null : 'lago');
      req.flush(paginaVacia);
      expect((await p).total).toBe(0);
    }
    const sinFiltros = repo.listar('DESTINO', FILTROS_CONTENIDOS_VACIOS);
    const req = http.expectOne(`${BASE}/destinos`);
    expect(req.request.params.keys()).toEqual([]);
    req.flush(paginaVacia);
    await sinFiltros;
  });

  it('AC_TKT023_02 crear (Idempotency-Key), obtener, actualizar con co-publicación y eliminar con versión', async () => {
    const creado = repo.crear({ ...formularioVacio('DESTINO'), titulo: 'Nuevo' }, 'clave-1');
    const reqCrear = http.expectOne(`${BASE}/destinos`);
    expect(reqCrear.request.method).toBe('POST');
    expect(reqCrear.request.headers.get('Idempotency-Key')).toBe('clave-1');
    expect(reqCrear.request.body).toMatchObject({ titulo: 'Nuevo', slug: null });
    reqCrear.flush(DESTINO);
    expect((await creado).id).toBe(11);

    const obtenido = repo.obtener('GUIA', 4);
    http.expectOne(`${BASE}/guias/4`).flush({ ...meta('GUIA'), titulo: 'G' });
    expect((await obtenido).tipo).toBe('GUIA');

    const actualizado = repo.actualizar(11, mapContenido(DESTINO).formulario, 3, {
      copublicarTipos: [{ id: 4, version: 2 }],
      confirmarCascada: true,
      cascadaConfirmada: [{ id: 6, tipo: 'TIPO' }],
    });
    const reqPut = http.expectOne(`${BASE}/destinos/11`);
    expect(reqPut.request.method).toBe('PUT');
    expect(reqPut.request.body).toMatchObject({
      version: 3,
      copublicar_tipos: [{ id: 4, version: 2 }],
      confirmar_cascada: true,
      cascada_confirmada: [{ id: 6, tipo: 'TIPO' }],
    });
    reqPut.flush({ ...DESTINO, estado_editorial: 'PUBLICADO', entidades_afectadas: [{ id: 6, tipo: 'TIPO', titulo: 'T', estado_editorial: 'RETIRADO', version: 2, origen: 'CASCADA' }] });
    expect((await actualizado).entidadesAfectadas[0]).toMatchObject({ origen: 'CASCADA' });

    const borrado = repo.eliminar('COLECCION', 8, 2);
    const reqDel = http.expectOne((r) => r.url === `${BASE}/colecciones/8`);
    expect(reqDel.request.method).toBe('DELETE');
    expect(reqDel.request.params.get('version')).toBe('2');
    reqDel.flush(null, { status: 204, statusText: 'No Content' });
    await borrado;
  });

  it('AC_TKT023_03 actualizar y eliminar en cada tipo usan su endpoint', async () => {
    const rutas: [TipoContenido, string][] = [
      ['ITINERARIO', 'itinerarios'],
      ['GUIA', 'guias'],
      ['TIPO', 'tipos-aventura'],
      ['COLECCION', 'colecciones'],
      ['TERMINO', 'glosario'],
      ['PAGINA', 'paginas'],
    ];
    for (const [tipo, ruta] of rutas) {
      const p = repo.actualizar(5, { ...formularioVacio(tipo), titulo: 'X' }, 1);
      const req = http.expectOne(`${BASE}/${ruta}/5`);
      expect(req.request.body).toMatchObject({ titulo: 'X', version: 1 });
      req.flush({ ...meta(tipo), titulo: 'X' });
      await p;
      if (tipo !== 'PAGINA') {
        const c = repo.crear({ ...formularioVacio(tipo), titulo: 'X' }, 'k');
        http.expectOne(`${BASE}/${ruta}`).flush({ ...meta(tipo), titulo: 'X' });
        await c;
        const e = repo.eliminar(tipo, 5, 1);
        http.expectOne((r) => r.url === `${BASE}/${ruta}/5` && r.method === 'DELETE').flush(null, { status: 204, statusText: '' });
        await e;
        const o = repo.obtener(tipo, 5);
        http.expectOne(`${BASE}/${ruta}/5`).flush({ ...meta(tipo), titulo: 'X' });
        await o;
      }
    }
    await expect(repo.crear(formularioVacio('PAGINA'), 'k')).rejects.toThrow();
    await expect(repo.eliminar('PAGINA', 1, 1)).rejects.toThrow();
    await expect(repo.vistaPrevia(formularioVacio('TERMINO'), null)).rejects.toThrow();
  });

  it('AC_TKT023_06 vista previa sin persistir: con id (excluir de relacionados) y sin id (alta)', async () => {
    const rutas: [TipoContenido, string][] = [
      ['DESTINO', 'destinos'],
      ['ITINERARIO', 'itinerarios'],
      ['GUIA', 'guias'],
      ['TIPO', 'tipos-aventura'],
      ['COLECCION', 'colecciones'],
      ['PAGINA', 'paginas'],
    ];
    for (const [tipo, ruta] of rutas) {
      const p = repo.vistaPrevia({ ...formularioVacio(tipo), titulo: 'X' }, tipo === 'DESTINO' ? null : 3);
      const req = http.expectOne(`${BASE}/${ruta}/vista-previa`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body['id']).toBe(tipo === 'DESTINO' ? undefined : 3);
      req.flush({ forma: 'DestinoDetalle', datos: { titulo: 'X' }, marca: 'VISTA PREVIA – NO PUBLICADO', requisitos_publicacion: { cumple: true, pendientes: [] } });
      expect((await p).titulo).toBe('X');
    }
  });

  it('AC_TKT023_07..12 ciclo editorial: analizar, publicar, impacto, retirar, reactivar, revisiones y restaurar', async () => {
    const analisis = repo.analizar('DESTINO', 11, 3, { tipos: [4], principal: '4' });
    const reqA = http.expectOne(`${BASE}/destinos/11/analisis-publicacion`);
    expect(reqA.request.body).toEqual({ version: 3, tipos_ids: [4], tipo_principal_id: 4 });
    reqA.flush({
      operacion: 'ACTUALIZAR_PUBLICACION',
      confirmable: true,
      entidad: { id: 11, tipo: 'DESTINO', titulo: 'T', estado_editorial: 'PUBLICADO', version: 3, rol: 'PRINCIPAL', cumple: true, pendientes: [] },
      copublicacion: [],
      copublicar_tipos: [],
      tipos_en_cascada: [],
      bloqueos_cascada: [],
    });
    expect((await analisis).operacion).toBe('ACTUALIZAR_PUBLICACION');
    const sinTipos = repo.analizar('GUIA', 2, 1, null);
    const reqB = http.expectOne(`${BASE}/guias/2/analisis-publicacion`);
    expect(reqB.request.body).toEqual({ version: 1 });
    reqB.flush({ operacion: 'PUBLICAR', confirmable: false, entidad: { id: 2, tipo: 'GUIA', titulo: 'G', estado_editorial: 'BORRADOR', version: 1, rol: 'PRINCIPAL', cumple: false, pendientes: [] }, copublicacion: [], copublicar_tipos: [], tipos_en_cascada: [], bloqueos_cascada: [] });
    await sinTipos;

    const resultado = { id: 11, tipo: 'DESTINO', estado_editorial: 'PUBLICADO', version: 4, afectados: [], entidades: [] };
    const publicado = repo.publicar('DESTINO', 11, 3, [{ id: 4, version: 2 }], 'k1');
    const reqP = http.expectOne(`${BASE}/destinos/11/publicar`);
    expect(reqP.request.headers.get('Idempotency-Key')).toBe('k1');
    expect(reqP.request.body).toEqual({ version: 3, copublicar_tipos: [{ id: 4, version: 2 }] });
    reqP.flush(resultado);
    expect((await publicado).version).toBe(4);
    const publicadoGuia = repo.publicar('GUIA', 2, 1, [], 'k2');
    const reqPG = http.expectOne(`${BASE}/guias/2/publicar`);
    expect(reqPG.request.body).toEqual({ version: 1 });
    reqPG.flush({ ...resultado, tipo: 'GUIA' });
    await publicadoGuia;

    const impacto = repo.impactoRetiro('DESTINO', 11);
    http.expectOne(`${BASE}/destinos/11/impacto-retiro`).flush({ retirable: true, bloqueos: [], bloqueos_cascada: [], colecciones: [], destacados: [], enlaces_entrantes: 0, itinerarios_en_cascada: [], tipos_en_cascada: [] });
    expect((await impacto).retirable).toBe(true);

    const retirado = repo.retirar('DESTINO', 11, 4, '  Cierre  ', [{ id: 9, tipo: 'ITINERARIO' }], 'k3');
    const reqR = http.expectOne(`${BASE}/destinos/11/retirar`);
    expect(reqR.request.body).toEqual({ version: 4, motivo: 'Cierre', confirmar_cascada: true, cascada_confirmada: [{ id: 9, tipo: 'ITINERARIO' }] });
    reqR.flush({ ...resultado, estado_editorial: 'RETIRADO' });
    await retirado;
    const retiradoSinCascada = repo.retirar('GUIA', 2, 1, 'x', [], 'k4');
    const reqR2 = http.expectOne(`${BASE}/guias/2/retirar`);
    expect(reqR2.request.body).toMatchObject({ confirmar_cascada: false, cascada_confirmada: [] });
    reqR2.flush({ ...resultado, tipo: 'GUIA', estado_editorial: 'RETIRADO' });
    await retiradoSinCascada;

    const reactivado = repo.reactivar('TIPO', 4, 2, 'k5');
    const reqRe = http.expectOne(`${BASE}/tipos-aventura/4/reactivar`);
    expect(reqRe.request.body).toEqual({ version: 2 });
    reqRe.flush({ ...resultado, estado_editorial: 'BORRADOR' });
    await reactivado;

    const revisiones = repo.revisiones('DESTINO', 11, 2);
    const reqRev = http.expectOne((r) => r.url === `${BASE}/destinos/11/revisiones`);
    expect(reqRev.request.params.get('pagina')).toBe('2');
    reqRev.flush({ ...paginaVacia, pagina: 2 });
    expect((await revisiones).pagina).toBe(2);

    const restaurado = repo.restaurar('DESTINO', 11, 1);
    http.expectOne(`${BASE}/destinos/11/revisiones/1/restaurar`).flush({ numero_revision: 1, version_actual: 4, datos: { titulo: 'Antiguo', galeria_ids: [5] } });
    const r = await restaurado;
    expect(r).toMatchObject({ numero: 1, versionActual: 4 });
    expect(r.formulario).toMatchObject({ titulo: 'Antiguo', galeria: [{ id: 5, estado: null }] });
  });

  it('catálogos: países y categorías activos, escalas ordenadas, tipos de cualquier estado y búsqueda', async () => {
    const paises = repo.paises();
    http.expectOne('/api/v1/panel/taxonomias/paises').flush({ ...paginaVacia, total_paginas: 2, siguiente: '/x', resultados: [{ id: 2, nombre: 'Perú', activo: true }, { id: 3, nombre: 'Oculto', activo: false }] });
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne((r) => r.url === '/api/v1/panel/taxonomias/paises' && r.params.get('pagina') === '2').flush({ ...paginaVacia, pagina: 2, total_paginas: 2, resultados: [{ id: 1, nombre: 'Chile' }] });
    expect((await paises).map((p) => p.nombre)).toEqual(['Chile', 'Perú']);

    const categorias = repo.categoriasGuia();
    http.expectOne('/api/v1/panel/taxonomias/categorias-guia').flush({ ...paginaVacia, resultados: [{ id: 1, nombre: 'Seguridad' }, { id: 2 }] });
    expect((await categorias).map((c) => c.nombre)).toEqual(['Seguridad', 'Categoría #2']);

    const escalas = repo.escalas();
    http.expectOne('/api/v1/panel/taxonomias/escalas').flush({
      dificultad: [{ id: 2, nivel: 2, etiqueta: 'Media', descripcion: '', escala: 'DIFICULTAD' }, { id: 1, nivel: 1, etiqueta: 'Fácil', descripcion: 'x', escala: 'DIFICULTAD' }],
      presupuesto: [],
    });
    expect((await escalas).dificultad.map((n) => n.etiqueta)).toEqual(['Fácil', 'Media']);

    const tipos = repo.tiposAventura();
    http.expectOne(`${BASE}/tipos-aventura`).flush({ ...paginaVacia, resultados: [{ id: 4, tipo: 'TIPO', titulo: 'Kayak', estado_editorial: 'BORRADOR', publicado: false, actualizado_en: '2026-10-01T00:00:00Z', actualizado_por: { id: 1, etiqueta: 'A' }, version: 1 }] });
    expect(await tipos).toEqual([{ id: 4, nombre: 'Kayak', estado: 'BORRADOR' }]);

    const buscados = repo.buscar(['DESTINO', 'GUIA'], 'la', 'PUBLICADO');
    for (const ruta of ['destinos', 'guias']) {
      const req = http.expectOne((r) => r.url === `${BASE}/${ruta}`);
      expect(req.request.params.get('estado')).toBe('PUBLICADO');
      req.flush({ ...paginaVacia, resultados: [{ id: 1, tipo: ruta === 'guias' ? 'GUIA' : 'DESTINO', titulo: 'Lago', slug: 'lago', estado_editorial: 'PUBLICADO', publicado: true, actualizado_en: '2026-10-01T00:00:00Z', actualizado_por: { id: 1, etiqueta: 'A' }, version: 1 }] });
    }
    expect((await buscados).map((r) => `${r.tipo}:${r.slug}`)).toEqual(['DESTINO:lago', 'GUIA:lago']);
  });
});
