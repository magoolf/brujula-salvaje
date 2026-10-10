import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { PanelConfiguracionRepositorio } from '../data/panel-configuracion.repositorio';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import { PanelCuentasRepositorio } from '../data/panel-cuentas.repositorio';
import { ConfiguracionSitio, formularioDesdeConfiguracion } from '../domain/configuracion-sitio';
import { CuentaEquipo } from '../domain/cuentas';
import { ConfigInicio, formularioDesdeConfig } from '../domain/destacados';
import { RefContenido } from '../domain/formulario-contenido';
import { SesionPanel } from '../domain/modelos';
import { FORMULARIO_CATALOGO_VACIO, NivelEscalaPanel, Pais, Region } from '../domain/taxonomias';
import { AuditoriaStore } from './auditoria.store';
import { ConfiguracionSitioStore } from './configuracion-sitio.store';
import { CuentasEquipoStore, FormularioCuentaStore } from './cuentas-equipo.store';
import { DestacadosStore } from './destacados.store';
import { SesionPanelStore } from './sesion-panel.store';
import { TaxonomiasStore } from './taxonomias.store';

function http(status: number, cuerpo: unknown = { code: 'x' }): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: cuerpo });
}

function sesionFalsa(usuario = 'admin.uno', rol: SesionPanel['rol'] = 'ADMINISTRADOR') {
  const sesion = { usuario, rol } as SesionPanel;
  return { sesion: () => sesion, rol: () => rol };
}

const refs = (n: number, tipo: RefContenido['tipo']): RefContenido[] =>
  Array.from({ length: n }, (_, i) => ({ id: i + 1, tipo, titulo: `${tipo} ${i + 1}`, estado: 'PUBLICADO' }));

const INICIO: ConfigInicio = {
  titular: 'Aventura',
  subtitulo: 'Sub',
  medio: { id: 9, estado: 'DISPONIBLE', miniatura: null, textoAlternativo: 'Cima' },
  destinos: refs(6, 'DESTINO'),
  itinerarios: refs(3, 'ITINERARIO'),
  guias: refs(3, 'GUIA'),
  actualizadoEn: new Date('2026-10-01T10:00:00Z'),
  actualizadoPor: 'ana',
};

const CONFIG: ConfiguracionSitio = {
  nombreMarca: 'Brújula',
  lema: null,
  textoDescargo: 'Cuidado',
  responsableNombre: null,
  responsableIdentificacion: null,
  responsableDomicilio: null,
  responsableCanalAtencion: null,
  actualizadoEn: new Date('2026-10-01T10:00:00Z'),
};

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

type Repo<T> = Record<keyof T, ReturnType<typeof vi.fn>>;

function repoConfiguracion(): Repo<PanelConfiguracionRepositorio> {
  return {
    inicio: vi.fn().mockResolvedValue(INICIO),
    guardarInicio: vi.fn().mockResolvedValue({ ...INICIO, titular: 'Nuevo' }),
    configuracion: vi.fn().mockResolvedValue(CONFIG),
    guardarConfiguracion: vi.fn().mockResolvedValue({ ...CONFIG, lema: 'Lema' }),
    listar: vi.fn().mockResolvedValue([]),
    crear: vi.fn(),
    actualizar: vi.fn(),
    escalas: vi.fn().mockResolvedValue({ dificultad: [], presupuesto: [] }),
    actualizarNivel: vi.fn(),
  };
}

function repoCuentas(): Repo<PanelCuentasRepositorio> {
  return {
    listar: vi.fn().mockResolvedValue({ cuentas: [cuenta()], pagina: 1, totalPaginas: 1, total: 1 }),
    administradoresActivos: vi.fn().mockResolvedValue(2),
    obtener: vi.fn().mockResolvedValue(cuenta()),
    crear: vi.fn(),
    actualizar: vi.fn(),
    ejecutarAccion: vi.fn(),
    auditoria: vi.fn().mockResolvedValue({ eventos: [], pagina: 1, totalPaginas: 1, total: 0 }),
    actores: vi.fn().mockResolvedValue([{ id: 5, etiqueta: 'ana' }]),
  };
}

describe('ConfiguracionSitioStore (SCR-047)', () => {
  function crear(repo: Repo<PanelConfiguracionRepositorio>): ConfiguracionSitioStore {
    TestBed.configureTestingModule({ providers: [ConfiguracionSitioStore, { provide: PanelConfiguracionRepositorio, useValue: repo }] });
    return TestBed.inject(ConfiguracionSitioStore);
  }

  it('AC_TKT024_10 carga, valida y guarda fijando la respuesta del servidor', async () => {
    const repo = repoConfiguracion();
    const store = crear(repo);
    await vi.waitFor(() => expect(store.configuracion()).not.toBeNull());
    const f = store.guardado();
    expect(f?.lema).toBe('');
    expect(store.validar({ ...f!, nombreMarca: '' })).toEqual({ nombreMarca: expect.any(String) });
    expect(await store.guardar({ ...f!, lema: 'Lema' })).toBeNull();
    expect(repo.guardarConfiguracion).toHaveBeenCalledWith(expect.objectContaining({ lema: 'Lema', responsableNombre: null }));
    expect(store.guardado()?.lema).toBe('Lema');
    expect(store.avisoExito()).toBe('Configuración guardada.');
    store.descartarAviso();
    expect(store.avisoExito()).toBeNull();
  });

  it('AC_TKT024_11 un 403 lleva a SCR-048 y un 400 vuelve como ErrorApi', async () => {
    const repo = repoConfiguracion();
    repo.configuracion.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    const store = crear(repo);
    await vi.waitFor(() => expect(store.accesoDenegado()).toBe(true));
    repo.configuracion.mockResolvedValue(CONFIG);
    store.recargar();
    await vi.waitFor(() => expect(store.configuracion()).not.toBeNull());
    repo.guardarConfiguracion.mockRejectedValue(http(400, { code: 'validacion', errors: { lema: ['Largo'] } }));
    const error = await store.guardar(formularioDesdeConfiguracion(CONFIG));
    expect(error?.campos).toEqual({ lema: ['Largo'] });
  });
});

describe('DestacadosStore (SCR-042, FLOW-014)', () => {
  function crear(repo: Repo<PanelConfiguracionRepositorio>, contenidos: { buscar: ReturnType<typeof vi.fn> }): DestacadosStore {
    TestBed.configureTestingModule({
      providers: [
        DestacadosStore,
        { provide: PanelConfiguracionRepositorio, useValue: repo },
        { provide: PanelContenidosRepositorio, useValue: contenidos },
      ],
    });
    return TestBed.inject(DestacadosStore);
  }

  it('AC_TKT024_02 carga, busca solo contenido PUBLICADO del tipo de la lista y guarda', async () => {
    const repo = repoConfiguracion();
    const contenidos = { buscar: vi.fn().mockResolvedValue(refs(1, 'GUIA')) };
    const store = crear(repo, contenidos);
    await vi.waitFor(() => expect(store.config()).not.toBeNull());
    expect(await store.buscar('guias', '  agua  ')).toEqual({ resultados: refs(1, 'GUIA'), error: null });
    expect(contenidos.buscar).toHaveBeenCalledWith(['GUIA'], 'agua', 'PUBLICADO');
    contenidos.buscar.mockRejectedValue(http(500));
    expect((await store.buscar('destinos', 'x')).error).toEqual(expect.any(String));
    const f = formularioDesdeConfig(INICIO);
    expect(store.validar({ ...f, destinos: [] }).destinos).toContain('al menos 6');
    expect(await store.guardar({ ...f, titular: 'Nuevo' })).toBeNull();
    expect(repo.guardarInicio).toHaveBeenCalledWith(expect.objectContaining({ titular: 'Nuevo', medioId: 9 }));
    expect(store.guardado()?.titular).toBe('Nuevo');
    expect(store.guardadoOk()).toBe(true);
    store.descartarAviso();
    expect(store.guardadoOk()).toBe(false);
  });

  it('AC_TKT024_03 un 422 por mínimos o contenido no publicado vuelve como ErrorApi; error de carga', async () => {
    const repo = repoConfiguracion();
    repo.inicio.mockRejectedValue(http(500));
    const store = crear(repo, { buscar: vi.fn() });
    await vi.waitFor(() => expect(store.error()).not.toBeNull());
    expect(store.accesoDenegado()).toBe(false);
    repo.inicio.mockResolvedValue(INICIO);
    store.recargar();
    await vi.waitFor(() => expect(store.config()).not.toBeNull());
    repo.guardarInicio.mockRejectedValue(http(422, { code: 'regla_negocio', errors: { destinos_ids: ['No publicado'] } }));
    const error = await store.guardar(formularioDesdeConfig(INICIO));
    expect(error?.categoria).toBe('regla_negocio');
    expect(store.guardadoOk()).toBe(false);
  });
});

describe('TaxonomiasStore (SCR-043)', () => {
  const REGION: Region = { catalogo: 'regiones', id: 1, nombre: 'Andes', slug: 'andes', continente: 'AMERICA', orden: 0, activo: true };
  const PAIS: Pais = { catalogo: 'paises', id: 2, nombre: 'Colombia', slug: 'colombia', codigoIso2: 'CO', regionId: 1, activo: true };
  const NIVEL: NivelEscalaPanel = { id: 3, escala: 'DIFICULTAD', nivel: 1, etiqueta: 'Fácil', descripcion: 'D' };

  function crear(repo: Repo<PanelConfiguracionRepositorio>, catalogo: string | null, rol: SesionPanel['rol'] = 'EDITOR') {
    const query$ = new BehaviorSubject(convertToParamMap(catalogo === null ? {} : { catalogo }));
    TestBed.configureTestingModule({
      providers: [
        TaxonomiasStore,
        { provide: PanelConfiguracionRepositorio, useValue: repo },
        { provide: SesionPanelStore, useValue: sesionFalsa('editora', rol) },
        { provide: ActivatedRoute, useValue: { queryParamMap: query$ } },
      ],
    });
    return { store: TestBed.inject(TaxonomiasStore), query$ };
  }

  it('AC_TKT024_04 pestaña por defecto, alta y edición con relectura del catálogo', async () => {
    const repo = repoConfiguracion();
    repo.listar.mockResolvedValue([REGION]);
    repo.crear.mockResolvedValue({ ...REGION, id: 9, nombre: 'Patagonia' });
    repo.actualizar.mockResolvedValue({ ...REGION, nombre: 'Andes del norte' });
    const { store } = crear(repo, null);
    expect(store.catalogo()).toBe('regiones');
    expect(store.puedeEditar()).toBe(true);
    await vi.waitFor(() => expect(store.elementos()).toEqual([REGION]));
    const f = { ...FORMULARIO_CATALOGO_VACIO, nombre: 'Patagonia', slug: 'patagonia', continente: 'AMERICA', orden: '1' };
    expect(store.validar('regiones', f)).toEqual({});
    expect(await store.guardar(f, null)).toBeNull();
    expect(repo.crear).toHaveBeenCalledWith(expect.objectContaining({ catalogo: 'regiones', nombre: 'Patagonia', activo: true }));
    expect(store.avisoExito()).toContain('Patagonia');
    expect(await store.guardar(f, { ...REGION, activo: false })).toBeNull();
    expect(repo.actualizar).toHaveBeenCalledWith(1, expect.objectContaining({ activo: false }));
    expect(store.avisoExito()).toContain('Se guardaron los cambios');
    await vi.waitFor(() => expect(repo.listar.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('AC_TKT024_05 retirar en uso deja el bloqueo con los usos; reactivar; otros errores se devuelven', async () => {
    const repo = repoConfiguracion();
    repo.listar.mockImplementation((c: string) => Promise.resolve(c === 'paises' ? [PAIS] : [REGION]));
    const { store } = crear(repo, 'paises');
    await vi.waitFor(() => expect(store.elementos()).toEqual([PAIS]));
    await vi.waitFor(() => expect(store.regiones()).toEqual([REGION]));
    expect(store.nombreRegion(1)).toBe('Andes');
    expect(store.nombreRegion(99)).toBe('Región #99');
    repo.actualizar.mockRejectedValueOnce(
      http(409, { code: 'dependencia_bloqueante', detail: 'En uso', usos: [{ tipo_entidad: 'DESTINO', id: 8, titulo: 'Cocora' }], total_usos: 1 }),
    );
    expect(await store.cambiarEstado(PAIS, false)).toBeNull();
    expect(store.bloqueo()).toMatchObject({ mensaje: 'En uso', total: 1, usos: [{ titulo: 'Cocora' }] });
    repo.actualizar.mockResolvedValueOnce({ ...PAIS, activo: true });
    expect(await store.cambiarEstado({ ...PAIS, activo: false }, true)).toBeNull();
    expect(store.bloqueo()).toBeNull();
    expect(store.avisoExito()).toContain('vuelve a estar activo');
    repo.actualizar.mockResolvedValueOnce({ ...PAIS, activo: false });
    await store.cambiarEstado(PAIS, false);
    expect(store.avisoExito()).toContain('Se retiró');
    repo.actualizar.mockRejectedValueOnce(http(500));
    expect((await store.cambiarEstado(PAIS, false))?.categoria).toBe('servidor');
  });

  it('AC_TKT024_04 escalas: solo lectura para el Editor y edición de niveles para el Administrador', async () => {
    const repo = repoConfiguracion();
    repo.escalas.mockResolvedValue({ dificultad: [NIVEL], presupuesto: [] });
    repo.actualizarNivel.mockResolvedValue({ ...NIVEL, etiqueta: 'Suave' });
    const { store } = crear(repo, 'escalas', 'ADMINISTRADOR');
    expect(store.puedeEditar()).toBe(true);
    expect(store.elementos()).toBeNull();
    await vi.waitFor(() => expect(store.escalas()?.dificultad).toEqual([NIVEL]));
    expect(repo.listar).not.toHaveBeenCalled();
    expect(await store.guardar(FORMULARIO_CATALOGO_VACIO, null)).toBeNull();
    expect(await store.guardarNivel(NIVEL, { ...FORMULARIO_CATALOGO_VACIO, etiqueta: 'Suave', descripcion: 'D' })).toBeNull();
    expect(repo.actualizarNivel).toHaveBeenCalledWith(3, { etiqueta: 'Suave', descripcion: 'D' });
    expect(store.avisoExito()).toContain('Suave');
    store.recargar();
    await vi.waitFor(() => expect(repo.escalas.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it('AC_TKT024_11 licencias en solo lectura para el Editor; 403 → SCR-048; cambio de pestaña', async () => {
    const repo = repoConfiguracion();
    repo.listar.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    const { store, query$ } = crear(repo, 'licencias');
    expect(store.puedeEditar()).toBe(false);
    await vi.waitFor(() => expect(store.accesoDenegado()).toBe(true));
    repo.escalas.mockRejectedValue(http(500));
    query$.next(convertToParamMap({ catalogo: 'escalas' }));
    await vi.waitFor(() => expect(store.error()?.categoria).toBe('servidor'));
    expect(store.cargando()).toBe(false);
    repo.listar.mockResolvedValue([]);
    query$.next(convertToParamMap({ catalogo: 'categorias' }));
    await vi.waitFor(() => expect(store.elementos()).toEqual([]));
    store.recargar();
    await vi.waitFor(() => expect(repo.listar.mock.calls.length).toBeGreaterThanOrEqual(2));
  });
});

describe('CuentasEquipoStore y FormularioCuentaStore (SCR-044/045)', () => {
  function crearListado(repo: Repo<PanelCuentasRepositorio>, pagina: string | null) {
    TestBed.configureTestingModule({
      providers: [
        CuentasEquipoStore,
        { provide: PanelCuentasRepositorio, useValue: repo },
        { provide: SesionPanelStore, useValue: sesionFalsa('ana') },
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap(pagina === null ? {} : { pagina })) } },
      ],
    });
    return TestBed.inject(CuentasEquipoStore);
  }

  function crearFormulario(repo: Repo<PanelCuentasRepositorio>, id: string, usuario = 'admin.uno') {
    TestBed.configureTestingModule({
      providers: [
        FormularioCuentaStore,
        { provide: PanelCuentasRepositorio, useValue: repo },
        { provide: SesionPanelStore, useValue: sesionFalsa(usuario) },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ id })) } },
      ],
    });
    return TestBed.inject(FormularioCuentaStore);
  }

  it('AC_TKT024_06 listado paginado por la URL; página fuera de rango; 403', async () => {
    const repo = repoCuentas();
    const store = crearListado(repo, '2');
    await vi.waitFor(() => expect(store.listado()?.total).toBe(1));
    expect(repo.listar).toHaveBeenCalledWith(2);
    expect(store.usuarioSesion()).toBe('ana');
    repo.listar.mockRejectedValue(http(404, { code: 'pagina_fuera_de_rango' }));
    store.recargar();
    await vi.waitFor(() => expect(store.paginaFueraDeRango()).toBe(true));
    expect(store.accesoDenegado()).toBe(false);
    expect(store.cargando()).toBe(false);
  });

  it('AC_TKT024_06 alta: contraseña temporal una sola vez, clave de idempotencia y error de duplicado', async () => {
    const repo = repoCuentas();
    const store = crearFormulario(repo, 'nuevo');
    expect(store.esAlta()).toBe(true);
    expect(store.cuenta()).toBeNull();
    expect(repo.obtener).not.toHaveBeenCalled();
    expect(store.acciones()).toEqual([]);
    expect(store.motivoRol()).toBeNull();
    expect(store.validar({ usuario: '', nombreVisible: 'B', rol: 'EDITOR' })).toEqual({ usuario: expect.any(String) });
    repo.crear.mockRejectedValueOnce(http(0));
    expect((await store.crear({ usuario: 'bea', nombreVisible: 'Bea', rol: 'EDITOR' }))?.categoria).toBe('sin_conexion');
    repo.crear.mockRejectedValueOnce(http(409, { code: 'duplicado' }));
    expect((await store.crear({ usuario: 'bea', nombreVisible: 'Bea', rol: 'EDITOR' }))?.codigo).toBe('duplicado');
    repo.crear.mockResolvedValueOnce({ cuenta: cuenta({ id: 6, usuario: 'bea' }), contrasenaTemporal: 'temporal-1234567890' });
    expect(await store.crear({ usuario: 'bea', nombreVisible: 'Bea', rol: 'EDITOR' })).toBeNull();
    const claves = repo.crear.mock.calls.map((c) => c[1] as string);
    expect(claves[0]).toBe(claves[1]);
    expect(claves[2]).not.toBe(claves[1]);
    expect(store.secreto()).toEqual({ usuario: 'bea', contrasena: 'temporal-1234567890', cuentaId: 6 });
    store.olvidarSecreto();
    expect(store.secreto()).toBeNull();
  });

  it('AC_TKT024_07 / AC_TKT024_08 edición: RULE-015 preventivo, cambios, acciones con secreto y 409', async () => {
    const repo = repoCuentas();
    const admin = cuenta({ id: 1, usuario: 'admin.dos', etiqueta: 'admin.dos', rol: 'ADMINISTRADOR' });
    repo.obtener.mockResolvedValue(admin);
    repo.administradoresActivos.mockResolvedValue(1);
    const store = crearFormulario(repo, '1');
    await vi.waitFor(() => expect(store.cuenta()).not.toBeNull());
    await vi.waitFor(() => expect(store.contexto().adminsActivos).toBe(1));
    expect(store.contexto().esPropia).toBe(false);
    expect(store.motivoRol()).toContain('último administrador');
    expect(store.acciones().find((a) => a.accion === 'desactivar')?.motivo).toContain('último administrador');

    expect(await store.guardar({ usuario: 'admin.dos', nombreVisible: 'Ana', rol: 'ADMINISTRADOR' })).toBeNull();
    expect(repo.actualizar).not.toHaveBeenCalled();
    expect(store.avisoExito()).toBe('No hay cambios que guardar.');
    repo.actualizar.mockResolvedValueOnce({ ...admin, nombreVisible: 'Ana B' });
    expect(await store.guardar({ usuario: 'admin.dos', nombreVisible: 'Ana B', rol: 'ADMINISTRADOR' })).toBeNull();
    expect(store.avisoExito()).toBe('Se guardaron los cambios.');
    repo.actualizar.mockResolvedValueOnce({ ...admin, rol: 'EDITOR' });
    expect(await store.guardar({ usuario: 'admin.dos', nombreVisible: 'Ana B', rol: 'EDITOR' })).toBeNull();
    expect(store.avisoExito()).toContain('cambio de rol');
    repo.actualizar.mockRejectedValueOnce(http(409, { code: 'ultimo_administrador' }));
    expect((await store.guardar({ usuario: 'admin.dos', nombreVisible: 'Ana C', rol: 'EDITOR' }))?.codigo).toBe('ultimo_administrador');

    repo.ejecutarAccion.mockResolvedValueOnce({ cuenta: admin, contrasenaTemporal: 'temporal-abcdefghij' });
    expect(await store.ejecutarAccion('restablecerContrasena')).toBeNull();
    expect(store.secreto()?.contrasena).toBe('temporal-abcdefghij');
    expect(store.avisoExito()).toContain('Se restableció la contraseña');
    repo.ejecutarAccion.mockResolvedValueOnce({ cuenta: { ...admin, estado: 'DESACTIVADA' }, contrasenaTemporal: null });
    store.olvidarSecreto();
    expect(await store.ejecutarAccion('desactivar')).toBeNull();
    expect(store.secreto()).toBeNull();
    expect(store.cuenta()?.estado).toBe('DESACTIVADA');
    expect(store.acciones().map((a) => a.accion)).toEqual(['reactivar', 'anonimizar']);
    repo.ejecutarAccion.mockRejectedValueOnce(http(409, { code: 'transicion_invalida' }));
    expect((await store.ejecutarAccion('anonimizar'))?.codigo).toBe('transicion_invalida');
  });

  it('AC_TKT024_08 la propia cuenta: sin desactivar ni cambiar el rol; id inválido y 404', async () => {
    const repo = repoCuentas();
    repo.obtener.mockResolvedValue(cuenta({ usuario: 'admin.uno', rol: 'ADMINISTRADOR' }));
    const store = crearFormulario(repo, '5', 'admin.uno');
    await vi.waitFor(() => expect(store.contexto().esPropia).toBe(true));
    expect(store.motivoRol()).toBe('No puedes cambiar tu propio rol.');
    expect(store.acciones().find((a) => a.accion === 'desactivar')?.motivo).toBe('No puedes desactivar tu propia cuenta.');
    TestBed.resetTestingModule();
    const invalido = crearFormulario(repoCuentas(), 'abc');
    expect(invalido.noEncontrado()).toBe(true);
    expect(await invalido.guardar({ usuario: '', nombreVisible: '', rol: '' })).toBeNull();
    expect(await invalido.ejecutarAccion('desactivar')).toBeNull();
    TestBed.resetTestingModule();
    const repo404 = repoCuentas();
    repo404.obtener.mockRejectedValue(http(404, { code: 'no_encontrado' }));
    const noExiste = crearFormulario(repo404, '77');
    await vi.waitFor(() => expect(noExiste.noEncontrado()).toBe(true));
    expect(noExiste.accesoDenegado()).toBe(false);
    noExiste.recargar();
  });
});

describe('AuditoriaStore (SCR-046)', () => {
  function crear(repo: Repo<PanelCuentasRepositorio>, query: Record<string, string>) {
    const query$ = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      providers: [
        AuditoriaStore,
        { provide: PanelCuentasRepositorio, useValue: repo },
        { provide: ActivatedRoute, useValue: { queryParamMap: query$ } },
      ],
    });
    return { store: TestBed.inject(AuditoriaStore), query$ };
  }

  it('AC_TKT024_09 filtros de la URL, actores y rango inválido sin consulta', async () => {
    const repo = repoCuentas();
    const { store, query$ } = crear(repo, { accion: 'CONFIG_SITIO', actor: '5' });
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(repo.auditoria).toHaveBeenCalledWith(expect.objectContaining({ accion: 'CONFIG_SITIO', actor: 5 }));
    expect(store.conFiltros()).toBe(true);
    await vi.waitFor(() => expect(store.actores()).toEqual([{ id: 5, etiqueta: 'ana' }]));
    query$.next(convertToParamMap({ desde: '2026-10-10', hasta: '2026-10-01' }));
    expect(store.errorFechas()).toContain('posterior');
    expect(repo.auditoria).toHaveBeenCalledTimes(1);
    repo.auditoria.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    query$.next(convertToParamMap({}));
    await vi.waitFor(() => expect(store.accesoDenegado()).toBe(true));
    expect(store.paginaFueraDeRango()).toBe(false);
    expect(store.cargando()).toBe(false);
    store.recargar();
  });
});
