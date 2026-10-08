import {
  DerivadoMedio,
  FILTROS_VACIOS,
  FormularioCatalogacion,
  LicenciaCatalogo,
  MENSAJE_DUPLICADA,
  MENSAJE_MOTIVO,
  MENSAJE_OBLIGATORIO_DISPONIBLE,
  MENSAJE_URL_FUENTE,
  Medio,
  ResultadoArchivo,
  TAMANO_MAXIMO_BYTES,
  alternarSeleccion,
  anuncioMovimiento,
  conFiltro,
  derivadoPara,
  descripcionMosaico,
  entradaDesdeFormulario,
  erroresCatalogacion,
  esSeleccionable,
  esUrlFuenteValida,
  excedeMaximo,
  filtrosDesdeQuery,
  formatearPeso,
  formularioDesdeMedio,
  hayFiltros,
  licenciasAsignables,
  mensajeResultado,
  mover,
  nombreMedio,
  porcentaje,
  puedeReactivar,
  puedeRetirar,
  queryDesdeFiltros,
  rechazoLocal,
  resumenSubida,
  srcsetDe,
  textoAnadir,
  textoRecuentoSeleccion,
  textoUsos,
  validarArchivo,
  validarCatalogacion,
  varianteEstadoMedio,
} from './medios';

export function medio(parcial: Partial<Medio> = {}): Medio {
  return {
    id: 7,
    estado: 'DISPONIBLE',
    tituloInterno: 'Cumbre al amanecer',
    textoAlternativo: 'Montaña nevada con el sol saliendo',
    pieDeFoto: null,
    autorCredito: 'Ana Pérez',
    fuenteUrl: null,
    licencia: { id: 1, codigo: 'CC-BY-4.0', nombre: 'CC BY 4.0', compatiblePublicacion: true },
    formatoOrigen: 'JPEG',
    anchoPx: 2400,
    altoPx: 1600,
    pesoBytes: 1_500_000,
    derivados: [
      { formato: 'AVIF', ancho: 320, alto: 213, url: '/a/320.avif' },
      { formato: 'WEBP', ancho: 960, alto: 640, url: '/w/960.webp' },
      { formato: 'WEBP', ancho: 320, alto: 213, url: '/w/320.webp' },
      { formato: 'JPEG', ancho: 320, alto: 213, url: '/j/320.jpg' },
    ],
    numeroUsos: 2,
    enUsoPublicado: false,
    subidoPor: '#3',
    subidoEn: new Date('2026-09-30T10:00:00Z'),
    actualizadoEn: new Date('2026-09-30T10:00:00Z'),
    pendientes: [],
    ...parcial,
  };
}

const FORMULARIO: FormularioCatalogacion = {
  tituloInterno: '',
  textoAlternativo: 'Un lago',
  pieDeFoto: '',
  autorCredito: 'Ana',
  fuenteUrl: '',
  licenciaId: '1',
};

describe('medios: presentación', () => {
  it('nombre, variante del estado, usos y descripción accesible del mosaico', () => {
    expect(nombreMedio(medio())).toBe('Cumbre al amanecer');
    expect(nombreMedio(medio({ tituloInterno: '  ', textoAlternativo: 'Lago' }))).toBe('Lago');
    expect(nombreMedio(medio({ tituloInterno: null, textoAlternativo: null }))).toBe('Imagen n.º 7');
    expect(varianteEstadoMedio('DISPONIBLE')).toBe('publicado');
    expect(varianteEstadoMedio('RETIRADO')).toBe('retirado');
    expect(varianteEstadoMedio('PENDIENTE_METADATOS')).toBe('pendiente');
    expect(textoUsos(0)).toBe('Sin usar');
    expect(textoUsos(3)).toBe('Usado en 3');
    expect(descripcionMosaico(medio())).toBe(
      'Cumbre al amanecer, Disponible, CC BY 4.0, usado en 2 contenidos',
    );
    expect(descripcionMosaico(medio({ licencia: null, numeroUsos: 1 }))).toBe(
      'Cumbre al amanecer, Disponible, sin licencia, usado en 1 contenido',
    );
  });

  it('peso legible en B, KB y MB', () => {
    expect(formatearPeso(512)).toBe('512 B');
    expect(formatearPeso(2048)).toBe('2 KB');
    expect(formatearPeso(1_572_864)).toBe('1,5 MB');
  });

  it('miniatura: WebP preferido, el menor ancho suficiente o el mayor disponible; srcset', () => {
    const derivados = medio().derivados;
    expect(derivadoPara(derivados, 300)?.url).toBe('/w/320.webp');
    expect(derivadoPara(derivados, 500)?.url).toBe('/w/960.webp');
    expect(derivadoPara(derivados, 4000)?.url).toBe('/w/960.webp');
    const soloJpeg: DerivadoMedio[] = [{ formato: 'JPEG', ancho: 640, alto: null, url: '/j.jpg' }];
    expect(derivadoPara(soloJpeg, 10)?.url).toBe('/j.jpg');
    expect(derivadoPara([], 10)).toBeNull();
    expect(srcsetDe(derivados)).toBe('/w/320.webp 320w, /w/960.webp 960w');
    expect(srcsetDe([])).toBe('');
  });
});

describe('medios: subida (FLOW-013, DEC-AUTO-044)', () => {
  it('AC_TKT022_01 validación previa: formato por tipo y extensión, tamaño y archivo vacío', () => {
    expect(validarArchivo({ nombre: 'a.JPG', tipo: 'image/jpeg', tamano: 100 })).toBeNull();
    expect(validarArchivo({ nombre: 'a.webp', tipo: '', tamano: 100 })).toBeNull();
    expect(validarArchivo({ nombre: 'a.gif', tipo: 'image/gif', tamano: 100 })).toBe('formato_no_permitido');
    expect(validarArchivo({ nombre: 'a.svg', tipo: 'image/png', tamano: 100 })).toBe('formato_no_permitido');
    expect(validarArchivo({ nombre: 'sin-extension', tipo: 'image/png', tamano: 100 })).toBe(
      'formato_no_permitido',
    );
    expect(validarArchivo({ nombre: 'a.png', tipo: 'image/png', tamano: TAMANO_MAXIMO_BYTES })).toBeNull();
    expect(validarArchivo({ nombre: 'a.png', tipo: 'image/png', tamano: TAMANO_MAXIMO_BYTES + 1 })).toBe(
      'tamano_excedido',
    );
    expect(validarArchivo({ nombre: 'a.png', tipo: 'image/png', tamano: 0 })).toBe('archivo_corrupto');
    expect(excedeMaximo(10)).toBe(false);
    expect(excedeMaximo(11)).toBe(true);
  });

  it('AC_TKT022_01 mensajes por resultado y resumen «n aceptadas, n rechazadas, n duplicadas»', () => {
    const local = rechazoLocal('x.gif', 'formato_no_permitido');
    expect(local).toEqual({
      nombreArchivo: 'x.gif',
      resultado: 'RECHAZADO',
      medio: null,
      medioExistenteId: null,
      motivo: 'formato_no_permitido',
      local: true,
    });
    const aceptado: ResultadoArchivo = { ...local, resultado: 'ACEPTADO', motivo: null, local: false };
    const duplicado: ResultadoArchivo = { ...aceptado, resultado: 'DUPLICADO', medioExistenteId: 4 };
    const sinMotivo: ResultadoArchivo = { ...aceptado, resultado: 'RECHAZADO' };
    expect(mensajeResultado(local)).toBe(MENSAJE_MOTIVO.formato_no_permitido);
    expect(mensajeResultado(aceptado)).toContain('Aceptada');
    expect(mensajeResultado(duplicado)).toBe(MENSAJE_DUPLICADA);
    expect(mensajeResultado(sinMotivo)).toBe(MENSAJE_MOTIVO.archivo_corrupto);
    expect(resumenSubida([aceptado])).toBe('1 aceptada');
    expect(resumenSubida([aceptado, aceptado, local, duplicado])).toBe(
      '2 aceptadas, 1 rechazada, 1 duplicada',
    );
    expect(resumenSubida([local, local, duplicado, duplicado])).toBe(
      '0 aceptadas, 2 rechazadas, 2 duplicadas',
    );
  });

  it('progreso en porcentaje acotado', () => {
    expect(porcentaje(50, 200)).toBe(25);
    expect(porcentaje(300, 200)).toBe(100);
    expect(porcentaje(10, null)).toBe(0);
    expect(porcentaje(10, 0)).toBe(0);
  });
});

describe('medios: catalogación (SCR-040, RULE-005, RULE-021)', () => {
  it('formulario desde el medio y entrada con null para los vacíos', () => {
    expect(formularioDesdeMedio(medio({ licencia: null, pieDeFoto: 'Pie' }))).toEqual({
      tituloInterno: 'Cumbre al amanecer',
      textoAlternativo: 'Montaña nevada con el sol saliendo',
      pieDeFoto: 'Pie',
      autorCredito: 'Ana Pérez',
      fuenteUrl: '',
      licenciaId: '',
    });
    expect(entradaDesdeFormulario({ ...FORMULARIO, fuenteUrl: ' https://x.org ', tituloInterno: '  ' })).toEqual({
      tituloInterno: null,
      textoAlternativo: 'Un lago',
      pieDeFoto: null,
      autorCredito: 'Ana',
      fuenteUrl: 'https://x.org',
      licenciaId: 1,
    });
    expect(entradaDesdeFormulario({ ...FORMULARIO, licenciaId: '' }).licenciaId).toBeNull();
    expect(entradaDesdeFormulario({ ...FORMULARIO, licenciaId: 'x' }).licenciaId).toBeNull();
  });

  it('AC_TKT022_03 DISPONIBLE exige alt, crédito y licencia; PENDIENTE admite datos parciales', () => {
    const vacio = { ...FORMULARIO, textoAlternativo: ' ', autorCredito: '', licenciaId: '' };
    expect(validarCatalogacion(vacio, 'DISPONIBLE')).toEqual({
      textoAlternativo: MENSAJE_OBLIGATORIO_DISPONIBLE,
      autorCredito: MENSAJE_OBLIGATORIO_DISPONIBLE,
      licenciaId: MENSAJE_OBLIGATORIO_DISPONIBLE,
    });
    expect(validarCatalogacion(vacio, 'PENDIENTE_METADATOS')).toEqual({});
    expect(validarCatalogacion(FORMULARIO, 'DISPONIBLE')).toEqual({});
  });

  it('AC_TKT022_03 longitudes máximas y URL de la fuente solo http/https (RULE-021)', () => {
    const largo = { ...FORMULARIO, textoAlternativo: 'a'.repeat(251), fuenteUrl: 'ftp://x.org' };
    expect(validarCatalogacion(largo, 'PENDIENTE_METADATOS')).toEqual({
      textoAlternativo: 'Máximo 250 caracteres.',
      fuenteUrl: MENSAJE_URL_FUENTE,
    });
    expect(validarCatalogacion({ ...FORMULARIO, fuenteUrl: `https://x.org/${'a'.repeat(500)}` }, 'DISPONIBLE')).toEqual({
      fuenteUrl: 'Máximo 500 caracteres.',
    });
    expect(esUrlFuenteValida('https://ejemplo.org/foto?x=1')).toBe(true);
    expect(esUrlFuenteValida('http://ejemplo.org')).toBe(true);
    expect(esUrlFuenteValida('javascript:alert(1)')).toBe(false);
    expect(esUrlFuenteValida('https://con espacio.org')).toBe(false);
    expect(esUrlFuenteValida(`https://x.org/${String.fromCharCode(1)}`)).toBe(false);
    expect(esUrlFuenteValida(`https://x.org/${String.fromCharCode(0x7f)}`)).toBe(false);
    expect(esUrlFuenteValida('https://')).toBe(false);
    expect(esUrlFuenteValida('https://[x')).toBe(false);
  });

  it('AC_TKT022_03 errores 400/422 por campo, con notación de puntos; el resto, generales', () => {
    expect(
      erroresCatalogacion(
        {
          licencia_id: ['Licencia incompatible: el medio está en uso por contenido publicado.'],
          'datos.fuente_url': ['URL no válida.', 'Otro'],
          autor_credito: [],
          otro: ['Error ajeno'],
        },
        'No se pudo guardar',
      ),
    ).toEqual({
      porCampo: {
        licenciaId: 'Licencia incompatible: el medio está en uso por contenido publicado.',
        fuenteUrl: 'URL no válida.',
      },
      generales: ['Error ajeno'],
    });
    expect(erroresCatalogacion({ texto_alternativo: ['a'], 'texto_alternativo.0': ['b'] }, 'x')).toEqual({
      porCampo: { textoAlternativo: 'a' },
      generales: [],
    });
    expect(erroresCatalogacion({}, 'Conflicto')).toEqual({ porCampo: {}, generales: ['Conflicto'] });
  });

  it('licencias asignables: activas y la actual aunque esté inactiva o fuera del catálogo', () => {
    const catalogo: LicenciaCatalogo[] = [
      { id: 1, codigo: 'A', nombre: 'A', compatiblePublicacion: true, activa: true },
      { id: 2, codigo: 'B', nombre: 'B', compatiblePublicacion: true, activa: false },
    ];
    expect(licenciasAsignables(catalogo, null).map((l) => l.id)).toEqual([1]);
    expect(licenciasAsignables(catalogo, catalogo[1]).map((l) => l.id)).toEqual([1, 2]);
    const fuera = { id: 9, codigo: 'Z', nombre: 'Z', compatiblePublicacion: false };
    expect(licenciasAsignables(catalogo, fuera)).toEqual([catalogo[0], { ...fuera, activa: false }]);
  });

  it('AC_TKT022_03 retirar solo si no está retirado ni en uso publicado (AC-117); reactivar si retirado', () => {
    expect(puedeRetirar(medio())).toBe(true);
    expect(puedeRetirar(medio({ enUsoPublicado: true }))).toBe(false);
    expect(puedeRetirar(medio({ estado: 'RETIRADO' }))).toBe(false);
    expect(puedeReactivar(medio({ estado: 'RETIRADO' }))).toBe(true);
    expect(puedeReactivar(medio())).toBe(false);
  });
});

describe('medios: filtros de la biblioteca en la URL (SCR-039)', () => {
  it('AC_TKT022_02 lee la URL descartando valores fuera del contrato', () => {
    expect(
      filtrosDesdeQuery({ estado: 'RETIRADO', licencia: 'CC-BY-4.0', en_uso: 'true', q: ' lago ', pagina: '3' }),
    ).toEqual({ estado: 'RETIRADO', licencia: 'CC-BY-4.0', enUso: true, q: 'lago', pagina: 3 });
    expect(
      filtrosDesdeQuery({ estado: 'OTRO', licencia: 'mal código!', en_uso: 'quizá', q: null, pagina: '0' }),
    ).toEqual(FILTROS_VACIOS);
    expect(filtrosDesdeQuery({ en_uso: 'false', pagina: '1.5' })).toEqual({ ...FILTROS_VACIOS, enUso: false });
    expect(filtrosDesdeQuery({ q: `a${String.fromCharCode(0)}b${'c'.repeat(200)}` }).q).toHaveLength(100);
    expect(filtrosDesdeQuery({ pagina: '10001' }).pagina).toBe(1);
  });

  it('AC_TKT022_02 escribe la URL omitiendo vacíos y la página 1; cambiar un filtro vuelve a la 1', () => {
    expect(queryDesdeFiltros(FILTROS_VACIOS)).toEqual({
      estado: null,
      licencia: null,
      en_uso: null,
      q: null,
      pagina: null,
    });
    const filtros = { estado: 'DISPONIBLE', licencia: 'CC0-1.0', enUso: false, q: 'río', pagina: 4 } as const;
    expect(queryDesdeFiltros(filtros)).toEqual({
      estado: 'DISPONIBLE',
      licencia: 'CC0-1.0',
      en_uso: 'false',
      q: 'río',
      pagina: '4',
    });
    expect(conFiltro(filtros, { q: 'lago' })).toEqual({ ...filtros, q: 'lago', pagina: 1 });
    expect(conFiltro(filtros, { pagina: 2 }).pagina).toBe(2);
    expect(hayFiltros(FILTROS_VACIOS)).toBe(false);
    expect(hayFiltros({ ...FILTROS_VACIOS, q: 'x' })).toBe(true);
    expect(hayFiltros({ ...FILTROS_VACIOS, estado: 'RETIRADO' })).toBe(true);
    expect(hayFiltros({ ...FILTROS_VACIOS, licencia: 'A' })).toBe(true);
    expect(hayFiltros({ ...FILTROS_VACIOS, enUso: true })).toBe(true);
  });
});

describe('medios: selector (SCR-041)', () => {
  const a = medio({ id: 1 });
  const b = medio({ id: 2 });
  const c = medio({ id: 3 });

  it('AC_TKT022_04 solo DISPONIBLES (RULE-005); pendientes si se permite; nunca retirados', () => {
    expect(esSeleccionable(a, false)).toBe(true);
    expect(esSeleccionable(medio({ estado: 'PENDIENTE_METADATOS' }), false)).toBe(false);
    expect(esSeleccionable(medio({ estado: 'PENDIENTE_METADATOS' }), true)).toBe(true);
    expect(esSeleccionable(medio({ estado: 'RETIRADO' }), true)).toBe(false);
  });

  it('AC_TKT022_04 alternar en modo uno y varios, con máximo', () => {
    expect(alternarSeleccion([], a, 'uno')).toEqual([a]);
    expect(alternarSeleccion([a], b, 'uno')).toEqual([b]);
    expect(alternarSeleccion([a], a, 'uno')).toEqual([]);
    expect(alternarSeleccion([a], b, 'varios')).toEqual([a, b]);
    expect(alternarSeleccion([a, b], a, 'varios')).toEqual([b]);
    expect(alternarSeleccion([a, b], c, 'varios', 2)).toEqual([a, b]);
  });

  it('AC_TKT022_04 reordenar la bandeja y anunciarlo', () => {
    expect(mover([a, b, c], 0, 2)).toEqual([b, c, a]);
    expect(mover([a, b, c], 2, -5)).toEqual([c, a, b]);
    expect(mover([a, b, c], 1, 1)).toEqual([a, b, c]);
    expect(mover([a, b, c], 5, 0)).toEqual([a, b, c]);
    expect(anuncioMovimiento('Lago', 2, 3)).toBe('Lago movida a la posición 2 de 3.');
  });

  it('textos del botón principal y del recuento', () => {
    expect(textoAnadir(0, 'varios')).toBe('Añadir imágenes');
    expect(textoAnadir(1, 'varios')).toBe('Añadir 1 imagen');
    expect(textoAnadir(4, 'varios')).toBe('Añadir 4 imágenes');
    expect(textoAnadir(1, 'uno')).toBe('Elegir imagen');
    expect(textoRecuentoSeleccion(0)).toBe('Ninguna imagen seleccionada');
    expect(textoRecuentoSeleccion(1)).toBe('1 seleccionada');
    expect(textoRecuentoSeleccion(5)).toBe('5 seleccionadas');
  });
});
