import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, ParamMap, convertToParamMap } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import { AnalisisPublicacion, ImpactoRetiro, ResultadoTransicion } from '../domain/ciclo-editorial';
import { ContenidoEditable, PaginaContenidos } from '../domain/contenidos';
import { FormularioContenido, formularioVacio } from '../domain/formulario-contenido';
import { SesionPanel, TipoContenido } from '../domain/modelos';
import { VistaPreviaContenido } from '../domain/vista-previa';
import { EditorContenidoStore, idDeSegmento } from './editor-contenido.store';
import { ListadoContenidosStore } from './listado-contenidos.store';
import { MemoriaEditor } from './memoria-editor';
import { PublicacionStore } from './publicacion.store';
import { SesionPanelStore } from './sesion-panel.store';
import { VistaPreviaStore } from './vista-previa.store';

function http(status: number, cuerpo: unknown = { code: 'x' }): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: cuerpo });
}

function formulario(tipo: TipoContenido = 'DESTINO', cambios: Partial<FormularioContenido> = {}): FormularioContenido {
  return { ...formularioVacio(tipo), titulo: 'Torres', ...cambios };
}

function contenido(cambios: Partial<ContenidoEditable> = {}): ContenidoEditable {
  return {
    id: 11,
    tipo: 'DESTINO',
    estado: 'BORRADOR',
    version: 3,
    slugBloqueado: false,
    nuncaPublicado: true,
    urlPublica: null,
    actualizadoEn: new Date('2026-10-01T00:00:00Z'),
    actualizadoPor: 'Ana',
    motivoRetiro: null,
    soloAdministrador: false,
    nombrePagina: null,
    vinculadoEn: [],
    requisitos: { cumple: false, pendientes: [{ campo: 'galeria', codigo: 'x', mensaje: 'Faltan imágenes.', referencias: [] }] },
    formulario: formulario(),
    entidadesAfectadas: [],
    ...cambios,
  };
}

const VISTA: VistaPreviaContenido = {
  tipo: 'DESTINO',
  marca: 'VISTA PREVIA – NO PUBLICADO',
  titulo: 'Torres',
  antetitulo: null,
  resumen: null,
  portada: null,
  datos: [],
  bloques: [],
  listas: [],
  galeria: [],
  fuentes: [],
  enlaces: [],
  revision: null,
  requisitos: { cumple: true, pendientes: [] },
};

function analisis(cambios: Partial<AnalisisPublicacion> = {}): AnalisisPublicacion {
  return {
    operacion: 'PUBLICAR',
    confirmable: true,
    entidad: { id: 11, tipo: 'DESTINO', titulo: 'Torres', estado: 'BORRADOR', version: 3, rol: 'PRINCIPAL', cumple: true, pendientes: [] },
    copublicacion: [],
    copublicarTipos: [],
    tiposEnCascada: [],
    bloqueosCascada: [],
    ...cambios,
  };
}

const RESULTADO: ResultadoTransicion = {
  id: 11,
  estado: 'PUBLICADO',
  version: 4,
  urlPublica: '/destinos/torres',
  entidades: [
    { id: 11, tipo: 'DESTINO', titulo: 'Torres', estado: 'PUBLICADO', version: 4, origen: 'PRINCIPAL', urlPublica: '/destinos/torres' },
    { id: 4, tipo: 'TIPO', titulo: 'Kayak', estado: 'PUBLICADO', version: 2, origen: 'COPUBLICACION', urlPublica: null },
  ],
};

const IMPACTO: ImpactoRetiro = {
  retirable: true,
  bloqueos: [],
  bloqueosCascada: [],
  itinerariosEnCascada: [{ id: 9, tipo: 'ITINERARIO', titulo: 'W', estado: 'PUBLICADO' }],
  tiposEnCascada: [],
  colecciones: [],
  destacados: [],
  enlacesEntrantes: 0,
};

type Repo = Record<keyof PanelContenidosRepositorio, ReturnType<typeof vi.fn>>;

function repo(): Repo {
  const pagina: PaginaContenidos = { contenidos: [], pagina: 1, totalPaginas: 1, total: 0 };
  return {
    listar: vi.fn().mockResolvedValue(pagina),
    obtener: vi.fn().mockResolvedValue(contenido()),
    crear: vi.fn().mockResolvedValue(contenido({ id: 12 })),
    actualizar: vi.fn().mockResolvedValue(contenido({ version: 4 })),
    eliminar: vi.fn().mockResolvedValue(undefined),
    vistaPrevia: vi.fn().mockResolvedValue(VISTA),
    analizar: vi.fn().mockResolvedValue(analisis()),
    publicar: vi.fn().mockResolvedValue(RESULTADO),
    impactoRetiro: vi.fn().mockResolvedValue(IMPACTO),
    retirar: vi.fn().mockResolvedValue({ ...RESULTADO, estado: 'RETIRADO' }),
    reactivar: vi.fn().mockResolvedValue({ ...RESULTADO, estado: 'BORRADOR' }),
    revisiones: vi.fn().mockResolvedValue({ revisiones: [], pagina: 1, totalPaginas: 3 }),
    restaurar: vi.fn().mockResolvedValue({ numero: 2, versionActual: 3, formulario: formulario('DESTINO', { titulo: 'Antiguo' }) }),
    paises: vi.fn().mockResolvedValue([{ id: 1, nombre: 'Chile' }]),
    categoriasGuia: vi.fn().mockResolvedValue([{ id: 2, nombre: 'Seguridad' }]),
    escalas: vi.fn().mockResolvedValue({ dificultad: [{ nivel: 1, etiqueta: 'Fácil', descripcion: '' }], presupuesto: [] }),
    tiposAventura: vi.fn().mockResolvedValue([{ id: 4, nombre: 'Kayak', estado: 'BORRADOR' }]),
    buscar: vi.fn().mockResolvedValue([
      { id: 1, tipo: 'DESTINO', titulo: 'A', estado: 'PUBLICADO' },
      { id: 2, tipo: 'DESTINO', titulo: 'B', estado: 'RETIRADO' },
    ]),
  };
}

function sesion(rol: 'EDITOR' | 'ADMINISTRADOR' = 'EDITOR'): SesionPanel {
  return {
    usuario: 'u',
    nombreVisible: 'U',
    rol,
    pasoPendiente: 'NINGUNO',
    mfaActivo: false,
    mfaObligatorio: false,
    expiraInactividadEn: new Date(Date.now() + 60_000),
    expiraAbsolutaEn: new Date(Date.now() + 60_000),
    redireccion: '/panel',
  };
}

interface Ruta {
  params: BehaviorSubject<ParamMap>;
  query: BehaviorSubject<ParamMap>;
}

function configurar(r: Repo, params: Record<string, string>, query: Record<string, string> = {}, rol: 'EDITOR' | 'ADMINISTRADOR' = 'EDITOR'): Ruta {
  const ruta: Ruta = {
    params: new BehaviorSubject(convertToParamMap(params)),
    query: new BehaviorSubject(convertToParamMap(query)),
  };
  TestBed.configureTestingModule({
    providers: [
      EditorContenidoStore,
      ListadoContenidosStore,
      PublicacionStore,
      VistaPreviaStore,
      { provide: PanelContenidosRepositorio, useValue: r },
      { provide: ActivatedRoute, useValue: { paramMap: ruta.params, queryParamMap: ruta.query } },
      { provide: SesionPanelStore, useValue: { rol: () => rol, sesion: () => sesion(rol) } },
    ],
  });
  return ruta;
}

async function estable(): Promise<void> {
  for (let i = 0; i < 3; i++) {
    TestBed.tick();
    await new Promise((r) => setTimeout(r, 0));
  }
}

describe('ListadoContenidosStore (SCR-035)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT023_01 lee tipo y filtros de la URL; vacío vs. sin coincidencias; 403 y página fuera de rango', async () => {
    const r = repo();
    const ruta = configurar(r, { tipo: 'destinos' }, { estado: 'BORRADOR', q: 'lago', pagina: '2' });
    const store = TestBed.inject(ListadoContenidosStore);
    await estable();
    expect(store.tipo()).toBe('DESTINO');
    expect(r.listar).toHaveBeenCalledWith('DESTINO', { estado: 'BORRADOR', q: 'lago', pagina: 2 });
    expect(store.sinCoincidencias()).toBe(true);
    expect(store.vacio()).toBe(false);
    ruta.query.next(convertToParamMap({}));
    await estable();
    expect(store.vacio()).toBe(true);
    // Páginas institucionales: sin filtros (el contrato solo admite `pagina`).
    ruta.params.next(convertToParamMap({ tipo: 'paginas' }));
    ruta.query.next(convertToParamMap({ q: 'x', estado: 'PUBLICADO' }));
    await estable();
    expect(r.listar).toHaveBeenLastCalledWith('PAGINA', { estado: null, q: '', pagina: 1 });
    r.listar.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    store.recargar();
    await estable();
    expect(store.accesoDenegado()).toBe(true);
    r.listar.mockRejectedValue(http(404, { code: 'pagina_fuera_de_rango' }));
    store.recargar();
    await estable();
    expect(store.paginaFueraDeRango()).toBe(true);
    ruta.params.next(convertToParamMap({ tipo: 'nada' }));
    await estable();
    expect(store.tipo()).toBeNull();
  });
});

describe('EditorContenidoStore (SCR-036)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('idDeSegmento: «nuevo», id válido o inválido', () => {
    expect(idDeSegmento('nuevo')).toBeNull();
    expect(idDeSegmento('12')).toBe(12);
    expect(idDeSegmento('0')).toBe('invalido');
    expect(idDeSegmento('abc')).toBe('invalido');
    expect(idDeSegmento(null)).toBe('invalido');
    expect(idDeSegmento('99999999999999999')).toBe('invalido');
  });

  it('AC_TKT023_02 alta: formulario vacío, catálogos del tipo y «Guardar borrador» crea con Idempotency-Key', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: 'nuevo' });
    const store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.esNuevo()).toBe(true);
    expect(store.formularioInicial()).toEqual(formularioVacio('DESTINO'));
    expect(store.acciones()).toMatchObject({ principal: null, guardarBorrador: true });
    expect(store.paises()).toEqual([{ id: 1, nombre: 'Chile' }]);
    expect(store.tiposAventura()).toHaveLength(1);
    expect(store.escalas().dificultad).toHaveLength(1);
    expect(r.categoriasGuia).not.toHaveBeenCalled();
    expect(await store.guardar(formulario())).toBeNull();
    expect(r.crear).toHaveBeenCalledWith(formulario(), expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(store.contenido()?.id).toBe(12);
    expect(store.guardadoEn()).not.toBeNull();
    expect(store.guardando()).toBe(false);
  });

  it('AC_TKT023_05 edición: guarda con la versión; 409 conflicto_version → aviso sin sobrescribir; Recargar', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: '11' });
    const store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.contenido()?.id).toBe(11);
    expect(store.acciones()).toMatchObject({ principal: 'PUBLICAR', eliminar: true });
    expect(store.requisitos()?.pendientes).toHaveLength(1);
    expect(await store.guardar(formulario())).toBeNull();
    expect(r.actualizar).toHaveBeenCalledWith(11, formulario(), 3);
    expect(store.contenido()?.version).toBe(4);
    r.actualizar.mockRejectedValueOnce(http(409, { code: 'conflicto_version' }));
    expect((await store.guardar(formulario()))?.codigo).toBe('conflicto_version');
    expect(store.conflicto()).toBe(true);
    expect(store.errorGuardado()).toBeNull();
    r.obtener.mockResolvedValueOnce(contenido({ version: 7 }));
    expect(await store.recargar()).toBeNull();
    expect(store.conflicto()).toBe(false);
    expect(store.contenido()?.version).toBe(7);
  });

  it('AC_TKT023_02 errores 400 por campo, error de red general y 401 sin banner', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: '11' });
    const store = TestBed.inject(EditorContenidoStore);
    await estable();
    r.actualizar.mockRejectedValueOnce(http(400, { code: 'validacion', errors: { slug: ['En uso.'], 'dias.0.titulo': ['Falta.'] } }));
    await store.guardar(formulario());
    expect(store.erroresServidor()).toEqual({ slug: 'En uso.', 'dias.0.titulo': 'Falta.' });
    store.limpiarErrorServidor('slug');
    store.limpiarErrorServidor('nada');
    expect(store.erroresServidor()).toEqual({ 'dias.0.titulo': 'Falta.' });
    r.actualizar.mockRejectedValueOnce(http(500, { code: 'error_interno' }));
    await store.guardar(formulario());
    expect(store.errorGuardado()?.categoria).toBe('servidor');
    r.actualizar.mockRejectedValueOnce(http(400, { code: 'validacion' }));
    await store.guardar(formulario());
    expect(store.errorGuardado()?.categoria).toBe('validacion');
    r.actualizar.mockRejectedValueOnce(http(401, { code: 'sesion_expirada' }));
    store.fijarAviso(null);
    await store.guardar(formulario());
    // El 401 lo trata el interceptor global (→ SCR-030); el formulario no muestra otro banner.
    expect(store.errorGuardado()).toBeNull();
  });

  it('AC_TKT023_11 eliminar borrador y reactivar (relee el contenido)', async () => {
    const r = repo();
    configurar(r, { tipo: 'guias', id: '11' });
    const store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(await store.eliminar()).toBeNull();
    expect(r.eliminar).toHaveBeenCalledWith('DESTINO', 11, 3);
    r.eliminar.mockRejectedValueOnce(http(409, { code: 'conflicto_version' }));
    expect((await store.eliminar())?.codigo).toBe('conflicto_version');
    expect(store.conflicto()).toBe(true);
    r.obtener.mockResolvedValue(contenido({ estado: 'BORRADOR', version: 5 }));
    expect(await store.reactivar()).toBeNull();
    expect(r.reactivar).toHaveBeenCalledWith('DESTINO', 11, 3, expect.any(String));
    expect(store.aviso()).toContain('Reactivaste');
    expect(store.contenido()?.version).toBe(5);
    r.reactivar.mockRejectedValueOnce(http(409, { code: 'transicion_invalida', title: 'No' }));
    expect((await store.reactivar())?.codigo).toBe('transicion_invalida');
    expect(store.errorGuardado()?.codigo).toBe('transicion_invalida');
  });

  it('AC_TKT023_12 revisiones paginadas y restauración en el formulario (sin persistir)', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: '11' });
    const store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.revisiones()?.totalPaginas).toBe(3);
    store.irAPaginaRevisiones(9);
    await estable();
    expect(r.revisiones).toHaveBeenLastCalledWith('DESTINO', 11, 3);
    store.irAPaginaRevisiones(0);
    await estable();
    expect(r.revisiones).toHaveBeenLastCalledWith('DESTINO', 11, 1);
    const actual = formulario('DESTINO', { portada: { id: 5, estado: 'DISPONIBLE', miniatura: '/m', textoAlternativo: 'L' } });
    r.restaurar.mockResolvedValueOnce({
      numero: 2,
      versionActual: 3,
      formulario: formulario('DESTINO', { titulo: 'Antiguo', portada: { id: 5, estado: null, miniatura: null, textoAlternativo: null } }),
    });
    expect(await store.restaurar(2, actual)).toBeNull();
    expect(store.restaurado()?.formulario.titulo).toBe('Antiguo');
    expect(store.restaurado()?.formulario.portada?.miniatura).toBe('/m');
    expect(store.conflicto()).toBe(false);
    expect(store.aviso()).toContain('revisión 2');
    store.restauracionAplicada();
    expect(store.restaurado()).toBeNull();
    // Si la versión vigente cambió mientras tanto, se avisa del conflicto.
    expect(await store.restaurar(2, actual)).toBeNull();
    r.revisiones.mockRejectedValueOnce(http(500));
    store.recargarRevisiones();
    await estable();
    expect(store.errorRevisiones()).toBe(true);
  });

  it('AC_TKT023_06 requisitos recalculados con la vista previa; el glosario no la tiene', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: '11' });
    const store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(await store.comprobarRequisitos(formulario())).toBeNull();
    expect(r.vistaPrevia).toHaveBeenCalledWith(formulario(), 11);
    expect(store.requisitos()).toEqual({ cumple: true, pendientes: [] });
    r.vistaPrevia.mockRejectedValueOnce(http(400, { code: 'validacion' }));
    expect((await store.comprobarRequisitos(formulario()))?.categoria).toBe('validacion');
    expect(store.requisitos()).toEqual({ cumple: true, pendientes: [] });
    TestBed.resetTestingModule();
    const r2 = repo();
    configurar(r2, { tipo: 'glosario', id: 'nuevo' });
    const glosario = TestBed.inject(EditorContenidoStore);
    expect(await glosario.comprobarRequisitos(formulario('TERMINO'))).toBeNull();
    expect(r2.vistaPrevia).not.toHaveBeenCalled();
    expect(r2.paises).not.toHaveBeenCalled();
  });

  it('búsqueda de los Combobox: sin retirados cuando se pide y error traducido', async () => {
    const r = repo();
    configurar(r, { tipo: 'itinerarios', id: 'nuevo' });
    const store = TestBed.inject(EditorContenidoStore);
    expect((await store.buscar(['DESTINO'], ' to ', null, true)).resultados.map((x) => x.id)).toEqual([1]);
    expect(r.buscar).toHaveBeenCalledWith(['DESTINO'], 'to', null);
    expect((await store.buscar(['DESTINO'], 'to', 'PUBLICADO')).resultados).toHaveLength(2);
    r.buscar.mockRejectedValueOnce(http(500));
    const fallo = await store.buscar(['DESTINO'], 'to', null);
    expect(fallo.resultados).toEqual([]);
    expect(fallo.error).toBeTruthy();
  });

  it('AC_TKT023_06 memoria del editor (vista previa y sesión expirada) y avisos entre pantallas', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: '11' });
    const store = TestBed.inject(EditorContenidoStore);
    const memoria = TestBed.inject(MemoriaEditor);
    await estable();
    store.guardarEnMemoria(formulario('DESTINO', { resumen: 'sin guardar' }));
    expect(memoria.leer('DESTINO', 11)).toEqual({ formulario: formulario('DESTINO', { resumen: 'sin guardar' }), version: 3 });
    expect(store.tomarDeMemoria()?.formulario.resumen).toBe('sin guardar');
    expect(store.tomarDeMemoria()).toBeNull();
    memoria.guardar('GUIA', null, { formulario: formulario('GUIA'), version: null });
    memoria.olvidar('GUIA', null);
    expect(memoria.leer('GUIA', null)).toBeNull();
    store.dejarAviso('Hola');
    expect(memoria.tomarAviso()).toBe('Hola');
    expect(memoria.tomarAviso()).toBeNull();
  });

  it('AC_TKT023_01 errores de carga: 404, 403, id inválido, alta de página y página legal para Editor', async () => {
    const r = repo();
    r.obtener.mockRejectedValue(http(404, { code: 'no_encontrado' }));
    configurar(r, { tipo: 'destinos', id: '11' });
    let store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.noEncontrado()).toBe(true);
    TestBed.resetTestingModule();
    const r2 = repo();
    r2.obtener.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    configurar(r2, { tipo: 'destinos', id: '11' });
    store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.accesoDenegado()).toBe(true);
    TestBed.resetTestingModule();
    configurar(repo(), { tipo: 'destinos', id: 'x' });
    expect(TestBed.inject(EditorContenidoStore).noEncontrado()).toBe(true);
    TestBed.resetTestingModule();
    configurar(repo(), { tipo: 'paginas', id: 'nuevo' });
    expect(TestBed.inject(EditorContenidoStore).noEncontrado()).toBe(true);
    TestBed.resetTestingModule();
    const r3 = repo();
    r3.obtener.mockResolvedValue(contenido({ tipo: 'PAGINA', soloAdministrador: true, estado: 'PUBLICADO' }));
    configurar(r3, { tipo: 'paginas', id: '2' });
    store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.accesoDenegado()).toBe(true);
    expect(store.acciones()?.principal).toBe('GUARDAR_PAGINA');
    TestBed.resetTestingModule();
    configurar(r3, { tipo: 'paginas', id: '2' }, {}, 'ADMINISTRADOR');
    store = TestBed.inject(EditorContenidoStore);
    await estable();
    expect(store.accesoDenegado()).toBe(false);
  });
});

describe('PublicacionStore (SCR-038)', () => {
  afterEach(() => TestBed.resetTestingModule());

  function crear(r: Repo): PublicacionStore {
    configurar(r, { tipo: 'destinos', id: '11' });
    return TestBed.inject(PublicacionStore);
  }

  it('AC_TKT023_07 publicar: análisis del guardado, confirmación con Idempotency-Key y éxito con «Ver en el sitio»', async () => {
    const r = repo();
    r.analizar.mockResolvedValue(analisis({ copublicacion: [{ ...analisis().entidad, id: 4, tipo: 'TIPO', titulo: 'Kayak', rol: 'COPUBLICACION' }], copublicarTipos: [{ id: 4, version: 1 }] }));
    const store = crear(r);
    expect(await store.analizar(contenido(), formulario())).toBeNull();
    expect(r.analizar).toHaveBeenCalledWith('DESTINO', 11, 3, null);
    expect(r.vistaPrevia).not.toHaveBeenCalled();
    expect(store.fase()).toBe('lista');
    expect(store.confirmable()).toBe(true);
    expect(store.totalPendientes()).toBe(0);
    const { error, contenido: actualizado } = await store.confirmar(contenido(), formulario());
    expect(error).toBeNull();
    expect(actualizado).toBeNull();
    expect(r.publicar).toHaveBeenCalledWith('DESTINO', 11, 3, [{ id: 4, version: 1 }], expect.stringMatching(/^[0-9a-f-]{36}$/));
    expect(store.fase()).toBe('hecha');
    expect(store.exito()).toEqual({ titulo: 'Torres', urlPublica: '/destinos/torres', adicionales: [{ id: 4, tipo: 'TIPO', titulo: 'Kayak', estado: 'PUBLICADO' }] });
    store.limpiarExito();
    expect(store.exito()).toBeNull();
  });

  it('AC_TKT023_07 / AC_TKT023_08 análisis con pendientes: lista enlazable por entidad y no confirmable', async () => {
    const r = repo();
    const pendiente = { campo: 'tipos', codigo: 'tipo_retirado', mensaje: 'Reactiva primero el tipo Kayak', referencias: [{ id: 4, tipo: 'TIPO' as const, titulo: 'Kayak', estado: 'RETIRADO' as const }] };
    r.analizar.mockResolvedValue(
      analisis({
        confirmable: false,
        entidad: { ...analisis().entidad, cumple: false, pendientes: [pendiente] },
        copublicacion: [{ ...analisis().entidad, id: 5, tipo: 'TIPO', titulo: 'Rafting', rol: 'COPUBLICACION', cumple: false, pendientes: [{ ...pendiente, campo: 'checklist', codigo: 'x', mensaje: 'Faltan 8', referencias: [] }] }],
      }),
    );
    const store = crear(r);
    await store.analizar(contenido(), formulario());
    expect(store.pendientesPrincipal()).toEqual([pendiente]);
    expect(store.pendientesCopublicacion().map((e) => e.titulo)).toEqual(['Rafting']);
    expect(store.totalPendientes()).toBe(2);
    expect(store.confirmable()).toBe(false);
  });

  it('AC_TKT023_07 422 publicacion_invalida al confirmar: errores agrupados por entidad; ninguna cambia', async () => {
    const r = repo();
    const store = crear(r);
    await store.analizar(contenido(), formulario());
    r.publicar.mockRejectedValueOnce(
      http(422, {
        code: 'publicacion_invalida',
        errores_por_entidad: [
          { id: 11, tipo: 'DESTINO', titulo: 'Torres', rol: 'PRINCIPAL', errores: [{ campo: 'resumen', code: 'r', mensaje: 'Falta.' }] },
          { id: 4, tipo: 'TIPO', titulo: 'Kayak', rol: 'COPUBLICACION', errores: [{ campo: 'checklist', code: 'c', mensaje: 'Faltan.' }] },
        ],
      }),
    );
    const { error } = await store.confirmar(contenido(), formulario());
    expect(error?.codigo).toBe('publicacion_invalida');
    expect(store.fase()).toBe('lista');
    expect(store.pendientesPrincipal()[0]).toMatchObject({ campo: 'resumen', mensaje: 'Falta.' });
    expect(store.pendientesCopublicacion()[0]).toMatchObject({ titulo: 'Kayak' });
    expect(store.confirmable()).toBe(false);
  });

  it('AC_TKT023_05 conflicto de versión multi-entidad y error de red reintentable', async () => {
    const r = repo();
    const store = crear(r);
    await store.analizar(contenido(), formulario());
    r.publicar.mockRejectedValueOnce(http(409, { code: 'conflicto_version', entidades_en_conflicto: [{ id: 4, tipo: 'TIPO', titulo: 'Kayak' }] }));
    await store.confirmar(contenido(), formulario());
    expect(store.conflicto()?.map((e) => e.titulo)).toEqual(['Kayak']);
    expect(store.confirmable()).toBe(false);
    await store.analizar(contenido(), formulario());
    r.publicar.mockRejectedValueOnce(http(0));
    const { error } = await store.confirmar(contenido(), formulario());
    expect(error?.categoria).toBe('sin_conexion');
    expect(store.error()?.categoria).toBe('sin_conexion');
    r.analizar.mockRejectedValueOnce(http(500));
    await store.analizar(contenido(), formulario());
    expect(store.error()?.categoria).toBe('servidor');
    store.cerrar();
    expect(store.fase()).toBe('inactiva');
    // Confirmar sin análisis no hace nada.
    expect(await store.confirmar(contenido(), formulario())).toEqual({ error: null, contenido: null });
  });

  it('AC_TKT023_09 actualizar publicación de un destino: tipos del formulario, cascada confirmada y requisitos', async () => {
    const r = repo();
    const tipoCascada = { id: 6, tipo: 'TIPO' as const, titulo: 'Rafting', estado: 'PUBLICADO' as const };
    r.analizar.mockResolvedValue(analisis({ operacion: 'ACTUALIZAR_PUBLICACION', tiposEnCascada: [tipoCascada], copublicarTipos: [{ id: 4, version: 1 }] }));
    r.actualizar.mockResolvedValue(contenido({ estado: 'PUBLICADO', urlPublica: '/destinos/torres', entidadesAfectadas: [{ ...tipoCascada, estado: 'RETIRADO', version: 2, origen: 'CASCADA', urlPublica: null }] }));
    const store = crear(r);
    const publicado = contenido({ estado: 'PUBLICADO', nuncaPublicado: false });
    const f = formulario('DESTINO', { tipos: [4], tipoPrincipal: '4' });
    await store.analizar(publicado, f);
    expect(r.analizar).toHaveBeenCalledWith('DESTINO', 11, 3, { tipos: [4], principal: '4' });
    expect(r.vistaPrevia).toHaveBeenCalledWith(f, 11);
    const { error, contenido: actualizado } = await store.confirmar(publicado, f);
    expect(error).toBeNull();
    expect(actualizado?.estado).toBe('PUBLICADO');
    expect(r.actualizar).toHaveBeenCalledWith(11, f, 3, {
      copublicarTipos: [{ id: 4, version: 1 }],
      confirmarCascada: true,
      cascadaConfirmada: [{ id: 6, tipo: 'TIPO' }],
    });
    expect(store.exito()?.adicionales.map((e) => e.titulo)).toEqual(['Rafting']);
    // Otro tipo publicado: sin opciones multi-entidad; el glosario no tiene vista previa.
    await store.analizar(contenido({ tipo: 'TERMINO', estado: 'PUBLICADO' }), formulario('TERMINO'));
    await store.confirmar(contenido({ tipo: 'TERMINO', estado: 'PUBLICADO' }), formulario('TERMINO'));
    expect(r.actualizar).toHaveBeenLastCalledWith(11, formulario('TERMINO'), 3, null);
  });

  it('AC_TKT023_09 409 impacto_modificado al actualizar: se repite el análisis y se avisa; cascada_bloqueada bloquea', async () => {
    const r = repo();
    const store = crear(r);
    const publicado = contenido({ estado: 'PUBLICADO' });
    await store.analizar(publicado, formulario());
    r.actualizar.mockRejectedValueOnce(http(409, { code: 'impacto_modificado' }));
    await store.confirmar(publicado, formulario());
    expect(r.analizar).toHaveBeenCalledTimes(2);
    expect(store.impactoModificado()).toBe(true);
    r.actualizar.mockRejectedValueOnce(
      http(409, { code: 'cascada_bloqueada', bloqueos_cascada: [{ tipo_aventura: { id: 6, tipo: 'TIPO', titulo: 'Rafting' }, itinerarios: [{ id: 9, tipo: 'ITINERARIO', titulo: 'W' }], total_itinerarios: 1 }] }),
    );
    await store.confirmar(publicado, formulario());
    expect(store.analisis()?.bloqueosCascada[0].tipoAventura.titulo).toBe('Rafting');
    expect(store.totalPendientes()).toBe(1);
    expect(store.confirmable()).toBe(false);
    r.actualizar.mockRejectedValueOnce(http(400, { code: 'validacion', errors: { slug: ['Inmutable.'] } }));
    await store.analizar(publicado, formulario());
    await store.confirmar(publicado, formulario());
    expect(store.pendientesPrincipal()).toEqual([{ campo: 'slug', codigo: 'validacion', mensaje: 'Inmutable.', referencias: [] }]);
  });

  it('AC_TKT023_10 retirar: impacto, motivo obligatorio, cascada confirmada e impacto modificado', async () => {
    const r = repo();
    const store = crear(r);
    const publicado = contenido({ estado: 'PUBLICADO' });
    expect(await store.retirar(publicado, 'x')).toBeNull();
    expect(r.retirar).not.toHaveBeenCalled();
    await store.cargarImpacto(publicado);
    expect(store.impacto()).toEqual(IMPACTO);
    expect(store.retirable()).toBe(true);
    expect(await store.retirar(publicado, '  ')).toBeNull();
    expect(r.retirar).not.toHaveBeenCalled();
    r.retirar.mockRejectedValueOnce(
      http(409, { code: 'impacto_modificado', impacto_cascada: { itinerarios_en_cascada: [], tipos_en_cascada: [{ id: 6, tipo: 'TIPO', titulo: 'Rafting' }], bloqueos_cascada: [] } }),
    );
    expect((await store.retirar(publicado, 'Cierre'))?.codigo).toBe('impacto_modificado');
    expect(r.retirar).toHaveBeenLastCalledWith('DESTINO', 11, 3, 'Cierre', [{ id: 9, tipo: 'ITINERARIO' }], expect.any(String));
    const primeraClave = r.retirar.mock.lastCall?.[5];
    expect(store.impactoModificado()).toBe(true);
    expect(store.impacto()?.tiposEnCascada.map((t) => t.titulo)).toEqual(['Rafting']);
    expect(await store.retirar(publicado, 'Cierre')).toBeNull();
    expect(r.retirar).toHaveBeenLastCalledWith('DESTINO', 11, 3, 'Cierre', [{ id: 6, tipo: 'TIPO' }], expect.any(String));
    expect(r.retirar.mock.lastCall?.[5]).not.toBe(primeraClave);
    expect(store.fase()).toBe('hecha');
    expect(store.exito()?.titulo).toBe('Torres');
  });

  it('AC_TKT023_10 retirar bloqueado: dependencia_bloqueante, cascada_bloqueada, conflicto y error', async () => {
    const r = repo();
    const store = crear(r);
    const publicado = contenido({ estado: 'PUBLICADO' });
    await store.cargarImpacto(publicado);
    r.retirar.mockRejectedValueOnce(http(409, { code: 'dependencia_bloqueante', usos: [{ id: 3, tipo_entidad: 'DESTINO', titulo: 'Torres' }] }));
    await store.retirar(publicado, 'x');
    expect(store.impacto()?.bloqueos.map((u) => u.titulo)).toEqual(['Torres']);
    expect(store.retirable()).toBe(false);
    await store.cargarImpacto(publicado);
    r.retirar.mockRejectedValueOnce(http(409, { code: 'cascada_bloqueada', bloqueos_cascada: [{ tipo_aventura: { id: 6, tipo: 'TIPO', titulo: 'R' }, itinerarios: [], total_itinerarios: 2 }] }));
    await store.retirar(publicado, 'x');
    expect(store.impacto()?.bloqueosCascada).toHaveLength(1);
    await store.cargarImpacto(publicado);
    r.retirar.mockRejectedValueOnce(http(409, { code: 'conflicto_version' }));
    await store.retirar(publicado, 'x');
    expect(store.conflicto()).toEqual([]);
    r.impactoRetiro.mockRejectedValueOnce(http(500));
    await store.cargarImpacto(publicado);
    expect(store.impacto()).toBeNull();
    expect(store.error()?.categoria).toBe('servidor');
  });
});

describe('VistaPreviaStore (SCR-037)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT023_06 usa el borrador en memoria (también del alta) sin persistir; sin borrador, la versión guardada', async () => {
    const r = repo();
    configurar(r, { tipo: 'destinos', id: 'nuevo' });
    TestBed.inject(MemoriaEditor).guardar('DESTINO', null, { formulario: formulario('DESTINO', { titulo: 'Nuevo' }), version: null });
    const store = TestBed.inject(VistaPreviaStore);
    await estable();
    expect(r.vistaPrevia).toHaveBeenCalledWith(formulario('DESTINO', { titulo: 'Nuevo' }), null);
    expect(store.vista()?.titulo).toBe('Torres');
    expect(store.sinDatos()).toBe(false);
    expect(store.rutaEditor()).toBe('/panel/contenido/destinos/nuevo');
    expect(r.crear).not.toHaveBeenCalled();
    expect(r.actualizar).not.toHaveBeenCalled();
    TestBed.resetTestingModule();

    const r2 = repo();
    configurar(r2, { tipo: 'guias', id: '11' });
    const guardado = TestBed.inject(VistaPreviaStore);
    await estable();
    expect(r2.obtener).toHaveBeenCalledWith('GUIA', 11);
    expect(r2.vistaPrevia).toHaveBeenCalledWith(formulario(), 11);
    expect(guardado.vista()).not.toBeNull();
    r2.vistaPrevia.mockRejectedValueOnce(http(500));
    guardado.recargar();
    await estable();
    expect(guardado.error()?.categoria).toBe('servidor');
  });

  it('AC_TKT023_06 alta sin borrador, glosario y tipos inválidos', async () => {
    configurar(repo(), { tipo: 'destinos', id: 'nuevo' });
    let store = TestBed.inject(VistaPreviaStore);
    expect(store.sinDatos()).toBe(true);
    expect(store.noEncontrado()).toBe(false);
    TestBed.resetTestingModule();
    configurar(repo(), { tipo: 'glosario', id: '3' });
    store = TestBed.inject(VistaPreviaStore);
    expect(store.noEncontrado()).toBe(true);
    TestBed.resetTestingModule();
    configurar(repo(), { tipo: 'destinos', id: 'x' });
    store = TestBed.inject(VistaPreviaStore);
    expect(store.noEncontrado()).toBe(true);
    expect(store.rutaEditor()).toBe('/panel');
  });
});
