import {
  ETIQUETA_TIPO_ENTIDAD,
  EventoAuditoria,
  FILTROS_AUDITORIA_VACIOS,
  errorRangoFechas,
  filtrosAuditoriaDesdeQuery,
  formatearFechaBogota,
  hayFiltrosAuditoria,
  limitesFechas,
  queryDesdeFiltrosAuditoria,
  rutaEntidad,
  textoEntidad,
  textoRecuentoAuditoria,
  tieneDetalle,
  varianteResultado,
} from './auditoria';
import {
  AVISO_RESPONSABLE_VACIO,
  ConfiguracionSitio,
  FormularioConfiguracion,
  entradaDesdeFormulario as entradaConfiguracion,
  erroresConfiguracion,
  formularioDesdeConfiguracion,
  hayCambiosConfiguracion,
  responsableIncompleto,
  validarConfiguracion,
} from './configuracion-sitio';
import {
  CuentaEquipo,
  DEFINICION_ACCION,
  MENSAJE_PROPIA_DESACTIVAR,
  MENSAJE_PROPIA_RESTABLECER,
  MENSAJE_PROPIO_ROL,
  MENSAJE_ULTIMO_ADMIN,
  disponibilidadAccion,
  entradaAlta,
  entradaCambio,
  erroresCuenta,
  esAnonimizada,
  esUltimoAdmin,
  formularioDesdeCuenta,
  idCuentaDeRuta,
  mensajeConflictoCuenta,
  motivoRolBloqueado,
  paginaDesdeQuery,
  validarCuenta,
  varianteEstadoCuenta,
} from './cuentas';
import {
  ConfigInicio,
  FormularioDestacados,
  entradaDesdeFormulario as entradaDestacados,
  erroresDestacados,
  formularioDesdeConfig,
  hayCambiosDestacados,
  listaLlena,
  motivoListaLlena,
  noPublicados,
  textoContadorLista,
  validarDestacados,
} from './destacados';
import { erroresPorCampo, longitudTexto, sinError } from './errores-formulario';
import { RefContenido } from './formulario-contenido';
import {
  CategoriaGuia,
  FORMULARIO_CATALOGO_VACIO,
  Licencia,
  Pais,
  Region,
  bloqueoDesdeError,
  catalogoDesdeQuery,
  entradaCatalogo,
  entradaConEstado,
  entradaNivel,
  erroresCatalogo,
  formularioDesdeElemento,
  formularioDesdeNivel,
  maximoCampo,
  nombreElemento,
  proponerSlugCatalogo,
  puedeEditarCatalogo,
  textoUsosBloqueo,
  validarCatalogo,
} from './taxonomias';

// ------------------------------------------------------------------------------------ apoyo
function ref(id: number, tipo: RefContenido['tipo'] = 'DESTINO', estado: RefContenido['estado'] = 'PUBLICADO'): RefContenido {
  return { id, tipo, titulo: `${tipo} ${id}`, estado };
}

function refs(n: number, tipo: RefContenido['tipo']): readonly RefContenido[] {
  return Array.from({ length: n }, (_, i) => ref(i + 1, tipo));
}

function destacadosValidos(): FormularioDestacados {
  return {
    titular: 'Aventura',
    subtitulo: 'Lugares salvajes',
    medio: { id: 9, estado: 'DISPONIBLE', miniatura: '/m.webp', textoAlternativo: 'Montaña' },
    destinos: refs(6, 'DESTINO'),
    itinerarios: refs(3, 'ITINERARIO'),
    guias: refs(3, 'GUIA'),
  };
}

function configuracion(parcial: Partial<ConfiguracionSitio> = {}): ConfiguracionSitio {
  return {
    nombreMarca: 'Brújula Salvaje',
    lema: null,
    textoDescargo: 'Viaja con cuidado.',
    responsableNombre: 'Brújula SAS',
    responsableIdentificacion: '900.1',
    responsableDomicilio: 'Bogotá',
    responsableCanalAtencion: 'datos@example.com',
    actualizadoEn: new Date('2026-10-01T10:00:00Z'),
    ...parcial,
  };
}

function cuenta(parcial: Partial<CuentaEquipo> = {}): CuentaEquipo {
  return {
    id: 5,
    usuario: 'ana',
    nombreVisible: 'Ana',
    etiqueta: 'ana',
    rol: 'EDITOR',
    estado: 'ACTIVA',
    mfaActivo: true,
    debeCambiarCredencial: false,
    ultimoAccesoEn: null,
    creadoEn: new Date('2026-09-01T10:00:00Z'),
    desactivadoEn: null,
    ...parcial,
  };
}

function evento(parcial: Partial<EventoAuditoria> = {}): EventoAuditoria {
  return {
    id: 1,
    ocurridoEn: new Date('2026-10-10T20:05:00Z'),
    actor: 'ana',
    actorId: 5,
    accion: 'EDITAR',
    resultado: 'EXITO',
    tipoEntidad: 'DESTINO',
    entidadId: 7,
    entidadTitulo: 'Cotopaxi',
    camposCambiados: [],
    ipTruncada: null,
    ...parcial,
  };
}

describe('errores de formulario (TKT-024)', () => {
  it('traduce errores por campo, deja los desconocidos en el resumen y usa el mensaje si no hay ninguno', () => {
    const mapa = { nombre: 'nombre_api' } as const;
    expect(erroresPorCampo(mapa, { nombre_api: ['Mal'], otro: ['Otro'] }, 'X')).toEqual({
      porCampo: { nombre: 'Mal' },
      generales: ['Otro'],
    });
    expect(erroresPorCampo(mapa, { nombre_api: [] }, 'Genérico')).toEqual({ porCampo: {}, generales: ['Genérico'] });
    expect(sinError<'a' | 'b'>({ a: 'x', b: 'y' }, 'a')).toEqual({ b: 'y' });
    const sin = { b: 'y' };
    expect(sinError<'a' | 'b'>(sin, 'a')).toBe(sin);
    expect(longitudTexto('ñandú')).toBe(5);
  });
});

describe('configuración del sitio (SCR-047, AC-070)', () => {
  const formulario = (): FormularioConfiguracion => formularioDesdeConfiguracion(configuracion());

  it('AC_TKT024_10 valida obligatorios y longitudes; convierte vacíos opcionales en null', () => {
    expect(validarConfiguracion(formulario())).toEqual({});
    const errores = validarConfiguracion({ ...formulario(), nombreMarca: ' ', textoDescargo: '', lema: 'x'.repeat(121) });
    expect(errores).toEqual({
      nombreMarca: 'Este campo es obligatorio.',
      textoDescargo: 'Este campo es obligatorio.',
      lema: 'Usa como máximo 120 caracteres.',
    });
    const entrada = entradaConfiguracion({ ...formulario(), lema: '  ', nombreMarca: ' Marca ' });
    expect(entrada.lema).toBeNull();
    expect(entrada.nombreMarca).toBe('Marca');
    expect(formularioDesdeConfiguracion(configuracion({ responsableNombre: null })).responsableNombre).toBe('');
  });

  it('AC_TKT024_10 detecta el Responsable incompleto (marcador [RESPONSABLE POR DEFINIR])', () => {
    expect(responsableIncompleto(formulario())).toBe(false);
    expect(responsableIncompleto({ ...formulario(), responsableDomicilio: ' ' })).toBe(true);
    expect(AVISO_RESPONSABLE_VACIO).toContain('[RESPONSABLE POR DEFINIR]');
  });

  it('cambios sin guardar y errores de la API', () => {
    expect(hayCambiosConfiguracion(formulario(), null)).toBe(false);
    expect(hayCambiosConfiguracion(formulario(), formulario())).toBe(false);
    expect(hayCambiosConfiguracion({ ...formulario(), lema: 'Nuevo' }, formulario())).toBe(true);
    expect(erroresConfiguracion({ texto_descargo: ['Vacío'] }, 'x').porCampo).toEqual({ textoDescargo: 'Vacío' });
  });
});

describe('destacados de inicio (SCR-042, FLOW-014, RULE-016, AC-011)', () => {
  it('AC_TKT024_02 contadores, máximos y motivo de «Añadir» deshabilitado', () => {
    expect(textoContadorLista('destinos', 4)).toBe('4 de 6 mínimo · máximo 12');
    expect(listaLlena('itinerarios', 6)).toBe(true);
    expect(listaLlena('guias', 5)).toBe(false);
    expect(motivoListaLlena('guias')).toBe('Ya hay 6 guías, el máximo. Quita uno para añadir otro.');
  });

  it('AC_TKT024_02 valida mínimos, máximos, estado publicado, imagen y textos', () => {
    expect(validarDestacados(destacadosValidos())).toEqual({});
    const errores = validarDestacados({
      titular: '',
      subtitulo: '',
      medio: null,
      destinos: refs(4, 'DESTINO'),
      itinerarios: refs(7, 'ITINERARIO'),
      guias: [...refs(2, 'GUIA'), ref(9, 'GUIA', 'RETIRADO')],
    });
    expect(errores).toEqual({
      titular: 'Escribe el titular.',
      subtitulo: 'Escribe el subtítulo.',
      medio: 'Elige la imagen del bloque principal.',
      destinos: 'Elige al menos 6 destinos (ahora hay 4).',
      itinerarios: 'Elige como máximo 6 itinerarios (ahora hay 7).',
      guias: 'Quita lo que ya no está publicado: GUIA 9.',
    });
    const largos = validarDestacados({
      ...destacadosValidos(),
      titular: 'x'.repeat(81),
      subtitulo: 'y'.repeat(161),
      medio: { id: 1, estado: 'PENDIENTE_METADATOS', miniatura: null, textoAlternativo: null },
    });
    expect(largos.titular).toBe('Usa como máximo 80 caracteres.');
    expect(largos.subtitulo).toBe('Usa como máximo 160 caracteres.');
    expect(largos.medio).toContain('disponible');
    expect(validarDestacados({ ...destacadosValidos(), medio: { id: 1, estado: null, miniatura: null, textoAlternativo: null } }).medio).toBeUndefined();
    expect(noPublicados([ref(1), ref(2, 'DESTINO', null)])).toHaveLength(1);
  });

  it('entrada, cambios y errores de la API', () => {
    const f = destacadosValidos();
    expect(entradaDestacados({ ...f, titular: ' T ' })).toMatchObject({ titular: 'T', medioId: 9, destinosIds: [1, 2, 3, 4, 5, 6] });
    expect(entradaDestacados({ ...f, medio: null }).medioId).toBe(0);
    expect(hayCambiosDestacados(f, null)).toBe(false);
    expect(hayCambiosDestacados(f, f)).toBe(false);
    expect(hayCambiosDestacados({ ...f, guias: [...f.guias].reverse() }, f)).toBe(true);
    expect(hayCambiosDestacados({ ...f, medio: null }, f)).toBe(true);
    expect(hayCambiosDestacados({ ...f, subtitulo: 'otro' }, f)).toBe(true);
    const config: ConfigInicio = { ...f, actualizadoEn: new Date(), actualizadoPor: 'ana' };
    expect(formularioDesdeConfig(config)).toEqual(f);
    expect(erroresDestacados({ 'destinos_ids.2': ['No publicado'], destinos_ids: ['Otro'], hero_titular: ['Largo'], x: ['General'] }, 'M')).toEqual({
      porCampo: { destinos: 'No publicado', titular: 'Largo' },
      generales: ['General'],
    });
    expect(erroresDestacados({}, 'Mensaje')).toEqual({ porCampo: {}, generales: ['Mensaje'] });
  });
});

describe('taxonomías y catálogos (SCR-043, RULE-007, RULE-014)', () => {
  const region: Region = { catalogo: 'regiones', id: 1, nombre: 'Andes', slug: 'andes', continente: 'AMERICA', orden: 2, activo: true };
  const pais: Pais = { catalogo: 'paises', id: 2, nombre: 'Colombia', slug: 'colombia', codigoIso2: 'CO', regionId: 1, activo: true };
  const categoria: CategoriaGuia = { catalogo: 'categorias', id: 3, nombre: 'Seguridad', slug: 'seguridad', descripcion: 'Desc', orden: 1, activo: false };
  const licencia: Licencia = {
    catalogo: 'licencias',
    id: 4,
    codigo: 'CC-BY-4.0',
    nombre: 'CC BY',
    urlTextoLegal: null,
    requiereAtribucion: true,
    compatiblePublicacion: true,
    activo: true,
  };

  it('AC_TKT024_04 pestaña desde la URL y permisos por rol (licencias y escalas solo Administrador)', () => {
    expect(catalogoDesdeQuery('licencias')).toBe('licencias');
    expect(catalogoDesdeQuery('otra')).toBe('regiones');
    expect(catalogoDesdeQuery(null)).toBe('regiones');
    expect(puedeEditarCatalogo('EDITOR', 'paises')).toBe(true);
    expect(puedeEditarCatalogo('EDITOR', 'licencias')).toBe(false);
    expect(puedeEditarCatalogo('EDITOR', 'escalas')).toBe(false);
    expect(puedeEditarCatalogo('ADMINISTRADOR', 'escalas')).toBe(true);
    expect(puedeEditarCatalogo(null, 'regiones')).toBe(false);
  });

  it('formularios desde elementos y niveles, y nombre visible', () => {
    expect(formularioDesdeElemento(region)).toMatchObject({ nombre: 'Andes', continente: 'AMERICA', orden: '2' });
    expect(formularioDesdeElemento(pais)).toMatchObject({ codigoIso2: 'CO', regionId: '1' });
    expect(formularioDesdeElemento(categoria)).toMatchObject({ descripcion: 'Desc', orden: '1' });
    expect(formularioDesdeElemento(licencia)).toMatchObject({ codigo: 'CC-BY-4.0', urlTextoLegal: '' });
    expect(formularioDesdeElemento({ ...licencia, urlTextoLegal: 'https://x' }).urlTextoLegal).toBe('https://x');
    expect(formularioDesdeNivel({ id: 1, escala: 'DIFICULTAD', nivel: 1, etiqueta: 'Fácil', descripcion: 'D' })).toMatchObject({ etiqueta: 'Fácil', descripcion: 'D' });
    expect(nombreElemento(licencia)).toBe('CC BY (CC-BY-4.0)');
    expect(nombreElemento(region)).toBe('Andes');
    expect(maximoCampo('regiones', 'slug')).toBe(60);
    expect(maximoCampo('regiones', 'descripcion')).toBeNull();
    expect(proponerSlugCatalogo('regiones', 'Ándes del Sur ')).toBe('andes-del-sur');
    expect(proponerSlugCatalogo('escalas', 'x'.repeat(90))).toHaveLength(80);
  });

  it('AC_TKT024_04 validación por catálogo', () => {
    const vacio = FORMULARIO_CATALOGO_VACIO;
    expect(validarCatalogo('regiones', vacio)).toEqual({
      nombre: 'Este campo es obligatorio.',
      slug: 'Este campo es obligatorio.',
      continente: 'Este campo es obligatorio.',
    });
    expect(validarCatalogo('regiones', { ...vacio, nombre: 'A', slug: 'Mal Slug', continente: 'MARTE', orden: '1001' })).toEqual({
      slug: expect.stringContaining('minúsculas'),
      continente: 'Elige un continente.',
      orden: 'Escribe un número entero entre 0 y 1000.',
    });
    expect(validarCatalogo('paises', { ...vacio, nombre: 'x'.repeat(81), slug: 'ok', codigoIso2: 'COL', regionId: '1' })).toEqual({
      nombre: 'Usa como máximo 80 caracteres.',
      codigoIso2: expect.stringContaining('ISO'),
    });
    expect(validarCatalogo('licencias', { ...vacio, codigo: 'CC BY', nombre: 'n', urlTextoLegal: 'ftp://x' })).toEqual({
      codigo: expect.stringContaining('letras'),
      urlTextoLegal: expect.stringContaining('http'),
    });
    expect(validarCatalogo('licencias', { ...vacio, codigo: 'CC0', nombre: 'n' })).toEqual({});
    expect(validarCatalogo('escalas', { ...vacio, etiqueta: 'Fácil', descripcion: 'd' })).toEqual({});
    expect(validarCatalogo('categorias', { ...vacio, nombre: 'n', slug: 's', descripcion: 'd', orden: '5' })).toEqual({});
  });

  it('AC_TKT024_04 entradas de escritura (alta, edición y cambio de estado)', () => {
    const f = { ...FORMULARIO_CATALOGO_VACIO, nombre: ' Andes ', slug: 'andes', continente: 'AMERICA', orden: '3', codigoIso2: 'co', regionId: '1', descripcion: ' D ', codigo: 'cc0', urlTextoLegal: ' ' };
    expect(entradaCatalogo('regiones', f, true)).toEqual({ catalogo: 'regiones', nombre: 'Andes', slug: 'andes', continente: 'AMERICA', orden: 3, activo: true });
    expect(entradaCatalogo('paises', f, false)).toEqual({ catalogo: 'paises', nombre: 'Andes', slug: 'andes', codigoIso2: 'CO', regionId: 1, activo: false });
    expect(entradaCatalogo('categorias', f, true)).toMatchObject({ descripcion: 'D', orden: 3 });
    expect(entradaCatalogo('licencias', f, true)).toMatchObject({ codigo: 'CC0', urlTextoLegal: null, requiereAtribucion: true });
    expect(entradaCatalogo('licencias', { ...f, urlTextoLegal: 'https://l' }, true)).toMatchObject({ urlTextoLegal: 'https://l' });
    expect(entradaConEstado(pais, false)).toEqual({ catalogo: 'paises', nombre: 'Colombia', slug: 'colombia', codigoIso2: 'CO', regionId: 1, activo: false });
    expect(entradaNivel({ ...f, etiqueta: ' Fácil ', descripcion: ' D ' })).toEqual({ etiqueta: 'Fácil', descripcion: 'D' });
  });

  it('AC_TKT024_05 errores de la API y bloqueo de retiro con los usos (RULE-007)', () => {
    expect(erroresCatalogo({ slug: ['En uso'], codigo_iso2: ['X'], otro: ['G'] }, 'M', 'regiones')).toEqual({
      porCampo: { slug: 'En uso' },
      generales: ['X', 'G'],
    });
    expect(erroresCatalogo({}, 'M', 'paises')).toEqual({ porCampo: {}, generales: ['M'] });
    const bloqueo = bloqueoDesdeError('En uso', {
      usos: [
        { tipo_entidad: 'DESTINO', id: 8, titulo: 'Cocora', estado_editorial: 'PUBLICADO' },
        { tipo_entidad: 3, id: 9, titulo: 'Sin tipo', estado_editorial: 'RARO' },
        { id: 'x', titulo: 'malo' },
        null,
      ],
      total_usos: 12,
    });
    expect(bloqueo).toEqual({
      mensaje: 'En uso',
      total: 12,
      usos: [
        { tipo: 'DESTINO', id: 8, titulo: 'Cocora', estado: 'PUBLICADO' },
        { tipo: '', id: 9, titulo: 'Sin tipo', estado: null },
      ],
    });
    expect(bloqueoDesdeError('M', {})).toEqual({ mensaje: 'M', usos: [], total: 0 });
    expect(textoUsosBloqueo(1)).toBe('Lo usa 1 contenido publicado:');
    expect(textoUsosBloqueo(3)).toBe('Lo usan 3 contenidos publicados:');
  });
});

describe('cuentas del equipo (SCR-044/045, FLOW-015, RULE-015)', () => {
  const ajena = { esPropia: false, adminsActivos: 3 };

  it('estados legibles y variantes del Badge', () => {
    expect(varianteEstadoCuenta('ACTIVA')).toBe('publicado');
    expect(varianteEstadoCuenta('PENDIENTE_ACTIVACION')).toBe('pendiente');
    expect(varianteEstadoCuenta('BLOQUEADA_TEMPORAL')).toBe('rechazado');
    expect(varianteEstadoCuenta('DESACTIVADA')).toBe('retirado');
    expect(varianteEstadoCuenta('ANONIMIZADA')).toBe('neutral');
    expect(esAnonimizada(cuenta({ estado: 'ANONIMIZADA' }))).toBe(true);
    expect(DEFINICION_ACCION.desactivar.efecto).toContain('Se cerrarán todas sus sesiones de inmediato');
  });

  it('AC_TKT024_08 RULE-015: no se ofrece desactivar ni degradar al último Administrador activo ni a uno mismo', () => {
    const admin = cuenta({ rol: 'ADMINISTRADOR' });
    expect(esUltimoAdmin(admin, 1)).toBe(true);
    expect(esUltimoAdmin(admin, 2)).toBe(false);
    expect(esUltimoAdmin(admin, null)).toBe(false);
    expect(esUltimoAdmin(cuenta(), 1)).toBe(false);
    expect(disponibilidadAccion('desactivar', admin, { esPropia: false, adminsActivos: 1 })).toEqual({ visible: true, motivo: MENSAJE_ULTIMO_ADMIN });
    expect(disponibilidadAccion('desactivar', admin, { esPropia: true, adminsActivos: 1 })).toEqual({ visible: true, motivo: MENSAJE_PROPIA_DESACTIVAR });
    expect(disponibilidadAccion('desactivar', cuenta(), ajena)).toEqual({ visible: true, motivo: null });
    expect(motivoRolBloqueado(admin, { esPropia: false, adminsActivos: 1 })).toBe(MENSAJE_ULTIMO_ADMIN);
    expect(motivoRolBloqueado(admin, { esPropia: true, adminsActivos: 4 })).toBe(MENSAJE_PROPIO_ROL);
    expect(motivoRolBloqueado(cuenta({ estado: 'DESACTIVADA' }), ajena)).toContain('desactivada');
    expect(motivoRolBloqueado(cuenta(), ajena)).toBeNull();
  });

  it('AC_TKT024_07 acciones visibles según el estado (Reactivar y Anonimizar solo DESACTIVADA)', () => {
    const viva = cuenta();
    expect(disponibilidadAccion('restablecerContrasena', viva, ajena)).toEqual({ visible: true, motivo: null });
    expect(disponibilidadAccion('restablecerContrasena', viva, { ...ajena, esPropia: true }).motivo).toBe(MENSAJE_PROPIA_RESTABLECER);
    expect(disponibilidadAccion('restablecerMfa', viva, ajena).visible).toBe(true);
    expect(disponibilidadAccion('restablecerMfa', cuenta({ mfaActivo: false }), ajena).visible).toBe(false);
    expect(disponibilidadAccion('restablecerMfa', viva, { ...ajena, esPropia: true }).motivo).toBe(MENSAJE_PROPIA_RESTABLECER);
    expect(disponibilidadAccion('reactivar', viva, ajena).visible).toBe(false);
    const baja = cuenta({ estado: 'DESACTIVADA' });
    expect(disponibilidadAccion('reactivar', baja, ajena).visible).toBe(true);
    expect(disponibilidadAccion('anonimizar', baja, ajena).visible).toBe(true);
    expect(disponibilidadAccion('desactivar', baja, ajena).visible).toBe(false);
  });

  it('mensajes de los 409 de cuenta', () => {
    expect(mensajeConflictoCuenta('ultimo_administrador', 'x', 'desactivar')).toBe(MENSAJE_ULTIMO_ADMIN);
    expect(mensajeConflictoCuenta('operacion_sobre_si_mismo', 'x', 'rol')).toBe(MENSAJE_PROPIO_ROL);
    expect(mensajeConflictoCuenta('operacion_sobre_si_mismo', 'x', 'desactivar')).toBe(MENSAJE_PROPIA_DESACTIVAR);
    expect(mensajeConflictoCuenta('transicion_invalida', 'Del servidor', 'anonimizar')).toBe('Del servidor');
  });

  it('AC_TKT024_06 formulario: validación del alta y de la edición, entradas y errores', () => {
    expect(validarCuenta({ usuario: '', nombreVisible: '', rol: '' }, true)).toEqual({
      usuario: 'Escribe el usuario.',
      nombreVisible: 'Escribe el nombre visible.',
      rol: 'Elige un rol.',
    });
    expect(validarCuenta({ usuario: 'Ana Mayúscula', nombreVisible: 'x'.repeat(101), rol: 'EDITOR' }, true)).toEqual({
      usuario: expect.stringContaining('Entre 3 y 40'),
      nombreVisible: 'Usa como máximo 100 caracteres.',
    });
    expect(validarCuenta({ usuario: '', nombreVisible: 'Ana', rol: 'EDITOR' }, false)).toEqual({});
    expect(entradaAlta({ usuario: ' ana ', nombreVisible: ' Ana ', rol: 'ADMINISTRADOR' })).toEqual({ usuario: 'ana', nombreVisible: 'Ana', rol: 'ADMINISTRADOR' });
    expect(entradaAlta({ usuario: 'a', nombreVisible: 'A', rol: '' }).rol).toBe('EDITOR');
    const c = cuenta();
    expect(entradaCambio(formularioDesdeCuenta(c), c)).toBeNull();
    expect(entradaCambio({ usuario: 'ana', nombreVisible: 'Ana B', rol: 'ADMINISTRADOR' }, c)).toEqual({ nombreVisible: 'Ana B', rol: 'ADMINISTRADOR' });
    expect(entradaCambio({ usuario: 'ana', nombreVisible: 'Ana', rol: '' }, c)).toBeNull();
    expect(formularioDesdeCuenta(cuenta({ usuario: null, nombreVisible: null }))).toEqual({ usuario: '', nombreVisible: '', rol: 'EDITOR' });
    expect(erroresCuenta({ nombre_visible: ['Mal'] }, 'x').porCampo).toEqual({ nombreVisible: 'Mal' });
  });

  it('id de la ruta y página de la URL', () => {
    expect(idCuentaDeRuta('nuevo')).toBe('nuevo');
    expect(idCuentaDeRuta('12')).toBe(12);
    expect(idCuentaDeRuta('0')).toBeNull();
    expect(idCuentaDeRuta(null)).toBeNull();
    expect(idCuentaDeRuta('99999999999999999')).toBeNull();
    expect(paginaDesdeQuery('3')).toBe(3);
    expect(paginaDesdeQuery('x')).toBe(1);
    expect(paginaDesdeQuery(null)).toBe(1);
    expect(paginaDesdeQuery(undefined)).toBe(1);
  });
});

describe('registro de auditoría (SCR-046, FLOW-016, AC-030)', () => {
  it('AC_TKT024_09 filtros desde la URL: los valores no válidos se ignoran', () => {
    expect(
      filtrosAuditoriaDesdeQuery({ desde: '2026-10-01', hasta: '2026-02-30', actor: '5', accion: 'EDITAR', tipo: 'DESTINO', pagina: '2' }),
    ).toEqual({ desde: '2026-10-01', hasta: '', actor: 5, accion: 'EDITAR', tipo: 'DESTINO', pagina: 2 });
    expect(filtrosAuditoriaDesdeQuery({ desde: 'ayer', actor: '-1', accion: 'BORRAR', tipo: '<x>', pagina: '0' })).toEqual(FILTROS_AUDITORIA_VACIOS);
    expect(filtrosAuditoriaDesdeQuery({})).toEqual(FILTROS_AUDITORIA_VACIOS);
  });

  it('AC_TKT024_09 query de la URL, rango de fechas y límites en hora de Bogotá', () => {
    const f = { desde: '2026-10-01', hasta: '2026-10-10', actor: 5, accion: 'EDITAR' as const, tipo: 'MEDIO', pagina: 3 };
    expect(queryDesdeFiltrosAuditoria(f)).toEqual({ desde: '2026-10-01', hasta: '2026-10-10', actor: '5', accion: 'EDITAR', tipo: 'MEDIO', pagina: '3' });
    expect(queryDesdeFiltrosAuditoria(FILTROS_AUDITORIA_VACIOS)).toEqual({ desde: null, hasta: null, actor: null, accion: null, tipo: null, pagina: null });
    expect(hayFiltrosAuditoria(FILTROS_AUDITORIA_VACIOS)).toBe(false);
    expect(hayFiltrosAuditoria({ ...FILTROS_AUDITORIA_VACIOS, tipo: 'MEDIO' })).toBe(true);
    expect(hayFiltrosAuditoria({ ...FILTROS_AUDITORIA_VACIOS, hasta: '2026-10-01' })).toBe(true);
    expect(errorRangoFechas('2026-10-10', '2026-10-01')).toContain('posterior');
    expect(errorRangoFechas('2026-10-01', '2026-10-10')).toBeNull();
    expect(errorRangoFechas('', '2026-10-10')).toBeNull();
    expect(limitesFechas(f)).toEqual({ desde: '2026-10-01T00:00:00-05:00', hasta: '2026-10-10T23:59:59.999-05:00' });
    expect(limitesFechas(FILTROS_AUDITORIA_VACIOS)).toEqual({ desde: null, hasta: null });
  });

  it('AC_TKT024_09 fecha absoluta en hora de Bogotá, entidad enlazada y textos', () => {
    // 20:05 UTC = 15:05 en Bogotá (UTC−5).
    expect(formatearFechaBogota(new Date('2026-10-10T20:05:00Z'))).toMatch(/3:05:00.*p.*m.*\(hora de Bogotá\)/);
    expect(rutaEntidad(evento())).toEqual({ ruta: '/panel/contenido/destinos/7', query: null });
    expect(rutaEntidad(evento({ tipoEntidad: null }))).toBeNull();
    expect(rutaEntidad(evento({ tipoEntidad: 'CONFIG_INICIO', entidadId: null }))).toEqual({ ruta: '/panel/inicio', query: null });
    expect(rutaEntidad(evento({ tipoEntidad: 'CONFIG_SITIO' }))).toEqual({ ruta: '/panel/configuracion', query: null });
    expect(rutaEntidad(evento({ tipoEntidad: 'LICENCIA' }))).toEqual({ ruta: '/panel/taxonomias', query: { catalogo: 'licencias' } });
    expect(rutaEntidad(evento({ tipoEntidad: 'MEDIO', entidadId: 3 }))).toEqual({ ruta: '/panel/medios/3', query: null });
    expect(rutaEntidad(evento({ tipoEntidad: 'CUENTA', entidadId: 4, accion: 'CUENTA_ROL' }))).toEqual({ ruta: '/panel/usuarios/4', query: null });
    expect(rutaEntidad(evento({ tipoEntidad: 'CUENTA', entidadId: 4, accion: 'CUENTA_ANONIMIZAR' }))).toBeNull();
    expect(rutaEntidad(evento({ tipoEntidad: 'DESTINO', entidadId: null }))).toBeNull();
    expect(rutaEntidad(evento({ tipoEntidad: 'DESCONOCIDO' }))).toBeNull();
    expect(textoEntidad(evento())).toBe('Destino · Cotopaxi');
    expect(textoEntidad(evento({ entidadTitulo: null }))).toBe('Destino · #7');
    expect(textoEntidad(evento({ entidadTitulo: null, entidadId: null, tipoEntidad: 'CONFIG_SITIO' }))).toBe('Configuración del sitio');
    expect(textoEntidad(evento({ tipoEntidad: null }))).toBe('—');
    expect(textoEntidad(evento({ tipoEntidad: 'NUEVO', entidadTitulo: 'X' }))).toBe('NUEVO · X');
    expect(textoRecuentoAuditoria(1)).toBe('1 evento');
    expect(textoRecuentoAuditoria(1200)).toMatch(/^1.200 eventos$/);
    expect(varianteResultado('EXITO')).toBe('publicado');
    expect(varianteResultado('FALLO')).toBe('rechazado');
    expect(tieneDetalle(evento())).toBe(false);
    expect(tieneDetalle(evento({ camposCambiados: ['titulo'] }))).toBe(true);
    expect(tieneDetalle(evento({ ipTruncada: '10.0.0.0' }))).toBe(true);
    expect(ETIQUETA_TIPO_ENTIDAD['NIVEL_ESCALA']).toBe('Nivel de escala');
  });
});
