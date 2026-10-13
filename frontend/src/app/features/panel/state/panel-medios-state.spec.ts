import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, Observable, Subject, of, throwError } from 'rxjs';

import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import { LicenciaCatalogo, Medio, PaginaMedios, ResultadoArchivo } from '../domain/medios';
import { BibliotecaMediosStore } from './biblioteca-medios.store';
import { CargaPanelStore } from './carga-panel.store';
import { DetalleMedioStore } from './detalle-medio.store';
import { SelectorMediosStore } from './selector-medios.store';
import { SesionPanelStore } from './sesion-panel.store';
import { ESPERA_LIMITE_MS, REINTENTOS_LIMITE, SubidaMediosStore } from './subida-medios.store';
import { SesionPanel } from '../domain/modelos';

function medio(parcial: Partial<Medio> = {}): Medio {
  return {
    id: 7,
    estado: 'DISPONIBLE',
    tituloInterno: 'Cumbre',
    textoAlternativo: 'Montaña',
    pieDeFoto: null,
    autorCredito: 'Ana',
    fuenteUrl: null,
    licencia: { id: 1, codigo: 'CC-BY-4.0', nombre: 'CC BY 4.0', compatiblePublicacion: true },
    formatoOrigen: 'JPEG',
    anchoPx: 2400,
    altoPx: 1600,
    pesoBytes: 1000,
    derivados: [],
    numeroUsos: 0,
    enUsoPublicado: false,
    subidoPor: '#3',
    subidoEn: new Date('2026-09-30T10:00:00Z'),
    actualizadoEn: new Date('2026-09-30T10:00:00Z'),
    pendientes: [],
    ...parcial,
  };
}

function sesion(): SesionPanel {
  return {
    usuario: 'editora.uno',
    nombreVisible: 'Editora Uno',
    rol: 'EDITOR',
    pasoPendiente: 'NINGUNO',
    mfaActivo: false,
    mfaObligatorio: false,
    expiraInactividadEn: new Date(Date.now() + 30 * 60_000),
    expiraAbsolutaEn: new Date(Date.now() + 12 * 3_600_000),
    redireccion: '/panel',
  };
}

function http(status: number, cuerpo: unknown = { code: 'x' }): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: cuerpo });
}

function paginaDe(medios: readonly Medio[], extra: Partial<PaginaMedios> = {}): PaginaMedios {
  return { medios, pagina: 1, totalPaginas: 1, total: medios.length, ...extra };
}

const LICENCIAS: LicenciaCatalogo[] = [
  { id: 1, codigo: 'CC-BY-4.0', nombre: 'CC BY 4.0', compatiblePublicacion: true, activa: true },
  { id: 2, codigo: 'OLD', nombre: 'Antigua', compatiblePublicacion: true, activa: false },
];

type RepoMedios = Record<keyof PanelMediosRepositorio, ReturnType<typeof vi.fn>>;

function repoMedios(): RepoMedios {
  return {
    listar: vi.fn().mockResolvedValue(paginaDe([medio()])),
    obtener: vi.fn().mockResolvedValue(medio()),
    usos: vi.fn().mockResolvedValue({ usos: [], pagina: 1, totalPaginas: 1, total: 0 }),
    catalogar: vi.fn().mockResolvedValue(medio()),
    retirar: vi.fn().mockResolvedValue(medio({ estado: 'RETIRADO' })),
    reactivar: vi.fn().mockResolvedValue(medio({ estado: 'PENDIENTE_METADATOS' })),
    licencias: vi.fn().mockResolvedValue(LICENCIAS),
    subir: vi.fn(),
  };
}

function archivo(nombre: string, tipo = 'image/png', tamano = 10): File {
  return new File([new Uint8Array(tamano)], nombre, { type: tipo });
}

describe('SubidaMediosStore (FLOW-013)', () => {
  function crear(repo: RepoMedios): SubidaMediosStore {
    TestBed.configureTestingModule({
      providers: [SubidaMediosStore, { provide: PanelMediosRepositorio, useValue: repo }],
    });
    return TestBed.inject(SubidaMediosStore);
  }

  it('AC_TKT022_01 más de 10 archivos: rechaza la selección completa sin subir', async () => {
    const repo = repoMedios();
    const store = crear(repo);
    const once = Array.from({ length: 11 }, (_, i) => archivo(`${i}.png`));
    expect(await store.seleccionar(once)).toBeNull();
    expect(store.errorSeleccion()).toContain('hasta 10 imágenes');
    expect(repo.subir).not.toHaveBeenCalled();
    expect(await store.seleccionar([])).toBeNull();
  });

  it('AC_TKT022_01 rechazos locales sin enviar y subida de los válidos con progreso', async () => {
    const repo = repoMedios();
    const aceptado: ResultadoArchivo = {
      nombreArchivo: 'b.png',
      resultado: 'ACEPTADO',
      medio: medio({ id: 9, estado: 'PENDIENTE_METADATOS' }),
      medioExistenteId: null,
      motivo: null,
      local: false,
    };
    const respuesta = new Subject<readonly ResultadoArchivo[]>();
    repo.subir.mockImplementation((archivos: File[], clave: string, alProgresar: (c: number, t: number | null) => void) => {
      expect(archivos.map((a) => a.name)).toEqual(['b.png']);
      expect(clave).toMatch(/^[0-9a-f-]{36}$/);
      alProgresar(25, 100);
      return respuesta;
    });
    const store = crear(repo);
    const pendiente = store.seleccionar([archivo('a.gif', 'image/gif'), archivo('b.png')]);
    expect(store.subiendo()).toBe(true);
    expect(store.porcentaje()).toBe(25);
    expect(store.resultados().map((r) => r.nombreArchivo)).toEqual(['a.gif']);
    respuesta.next([aceptado]);
    respuesta.complete();
    expect(await pendiente).toBeNull();
    expect(store.subiendo()).toBe(false);
    expect(store.porcentaje()).toBe(0);
    expect(store.resumen()).toBe('1 aceptada, 1 rechazada');
    expect(store.aceptados().map((m) => m.id)).toEqual([9]);
    store.cerrarResultados();
    expect(store.hayResultados()).toBe(false);
    expect(store.resumen()).toBe('');
  });

  it('AC_TKT022_01 todo rechazado en el cliente: no se envía nada', async () => {
    const repo = repoMedios();
    const store = crear(repo);
    expect(await store.seleccionar([archivo('x.gif', 'image/gif'), archivo('y.png', 'image/png', 0)])).toBeNull();
    expect(repo.subir).not.toHaveBeenCalled();
    expect(store.resultados().map((r) => r.motivo)).toEqual(['formato_no_permitido', 'archivo_corrupto']);
  });

  it('ALT-017 un fallo de envío se reintenta con la misma Idempotency-Key', async () => {
    const repo = repoMedios();
    const claves: string[] = [];
    let intentos = 0;
    repo.subir.mockImplementation((_a: File[], clave: string): Observable<readonly ResultadoArchivo[]> => {
      claves.push(clave);
      return intentos++ === 0 ? throwError(() => http(0)) : of([]);
    });
    const store = crear(repo);
    const error = await store.seleccionar([archivo('a.png')]);
    expect(error?.categoria).toBe('sin_conexion');
    expect(store.errorEnvio()?.categoria).toBe('sin_conexion');
    expect(store.puedeReintentar()).toBe(true);
    expect(await store.reintentar()).toBeNull();
    expect(claves[0]).toBe(claves[1]);
    expect(store.errorEnvio()).toBeNull();
    expect(await store.reintentar()).toBeNull();
    expect(intentos).toBe(2);
  });

  function resultado(nombre: string, id: number): ResultadoArchivo {
    return {
      nombreArchivo: nombre,
      resultado: 'ACEPTADO',
      medio: medio({ id, estado: 'PENDIENTE_METADATOS' }),
      medioExistenteId: null,
      motivo: null,
      local: false,
    };
  }

  it('AC_TKT072_06 un archivo por petición, en secuencia, con su propia clave y progreso del lote', async () => {
    const repo = repoMedios();
    const envios: { nombres: string[]; clave: string; respuesta: Subject<readonly ResultadoArchivo[]> }[] = [];
    repo.subir.mockImplementation((archivos: File[], clave: string, alProgresar: (c: number, t: number | null) => void) => {
      const respuesta = new Subject<readonly ResultadoArchivo[]>();
      envios.push({ nombres: archivos.map((a) => a.name), clave, respuesta });
      alProgresar(50, 100);
      return respuesta;
    });
    const store = crear(repo);
    const pendiente = store.seleccionar([archivo('a.png', 'image/png', 100), archivo('x.gif', 'image/gif'), archivo('b.png', 'image/png', 300)]);
    // Solo se envía el primero: el segundo espera a que responda (secuencial).
    expect(envios.map((e) => e.nombres)).toEqual([['a.png']]);
    expect(store.posicion()).toEqual({ actual: 1, total: 2 });
    expect(store.porcentaje()).toBe(13); // 50 de 400 bytes
    envios[0].respuesta.next([resultado('a.png', 1)]);
    envios[0].respuesta.complete();
    await vi.waitFor(() => expect(envios.length).toBe(2));
    // El resultado del primero ya se ve mientras sube el segundo.
    expect(store.resultados().map((r) => r.nombreArchivo)).toEqual(['x.gif', 'a.png']);
    expect(envios[1].nombres).toEqual(['b.png']);
    expect(envios[1].clave).not.toBe(envios[0].clave);
    expect(store.posicion()).toEqual({ actual: 2, total: 2 });
    expect(store.porcentaje()).toBe(63); // 100 + 150 de 400 bytes
    envios[1].respuesta.next([resultado('b.png', 2)]);
    envios[1].respuesta.complete();
    expect(await pendiente).toBeNull();
    expect(store.subiendo()).toBe(false);
    expect(store.posicion()).toBeNull();
    expect(store.resumen()).toBe('2 aceptadas, 1 rechazada');
    expect(store.aceptados().map((m) => m.id)).toEqual([1, 2]);
  });

  it('AC_TKT072_07 si falla un archivo se conservan los anteriores y «Reintentar» sigue desde él con su clave', async () => {
    const repo = repoMedios();
    const envios: { nombre: string; clave: string }[] = [];
    let fallar = true;
    repo.subir.mockImplementation((archivos: File[], clave: string): Observable<readonly ResultadoArchivo[]> => {
      const nombre = archivos[0].name;
      envios.push({ nombre, clave });
      if (nombre === 'b.png' && fallar) {
        fallar = false;
        return throwError(() => http(502));
      }
      return of([resultado(nombre, envios.length)]);
    });
    const store = crear(repo);
    const error = await store.seleccionar([archivo('a.png'), archivo('b.png'), archivo('c.png')]);
    expect(error).not.toBeNull();
    expect(store.archivoFallido()).toBe('b.png');
    expect(store.puedeReintentar()).toBe(true);
    expect(store.resultados().map((r) => r.nombreArchivo)).toEqual(['a.png']);
    expect(store.aceptados().length).toBe(1);
    expect(envios.map((e) => e.nombre)).toEqual(['a.png', 'b.png']);

    expect(await store.reintentar()).toBeNull();
    expect(envios.map((e) => e.nombre)).toEqual(['a.png', 'b.png', 'b.png', 'c.png']);
    expect(envios[2].clave).toBe(envios[1].clave); // ALT-017: misma clave para el mismo archivo
    expect(store.archivoFallido()).toBeNull();
    expect(store.resultados().map((r) => r.nombreArchivo)).toEqual(['a.png', 'b.png', 'c.png']);
    store.cerrarResultados();
    expect(store.archivoFallido()).toBeNull();
    expect(await store.reintentar()).toBeNull();
    expect(envios.length).toBe(4);
  });

  it('AC_TKT072_11 un 429 a mitad de lote espera y reintenta el mismo archivo con su clave', async () => {
    vi.useFakeTimers();
    try {
      const repo = repoMedios();
      const claves: string[] = [];
      let limitado = 2;
      repo.subir.mockImplementation((archivos: File[], clave: string): Observable<readonly ResultadoArchivo[]> => {
        claves.push(clave);
        if (archivos[0].name === 'b.png' && limitado-- > 0) return throwError(() => http(429, { code: 'limite_tasa' }));
        return of([resultado(archivos[0].name, claves.length)]);
      });
      const store = crear(repo);
      const pendiente = store.seleccionar([archivo('a.png'), archivo('b.png')]);
      await vi.waitFor(() => expect(store.esperandoLimite()).toBe(true));
      expect(store.errorEnvio()).toBeNull();
      await vi.advanceTimersByTimeAsync(ESPERA_LIMITE_MS);
      await vi.advanceTimersByTimeAsync(ESPERA_LIMITE_MS);
      expect(await pendiente).toBeNull();
      expect(store.esperandoLimite()).toBe(false);
      expect(claves.length).toBe(4);
      expect(new Set(claves.slice(1)).size).toBe(1); // b.png siempre con la misma clave
      expect(store.resumen()).toBe('2 aceptadas');
    } finally {
      vi.useRealTimers();
    }
  });

  it('AC_TKT072_11 si el límite persiste tras los reintentos, se informa y se puede reintentar', async () => {
    vi.useFakeTimers();
    try {
      const repo = repoMedios();
      repo.subir.mockImplementation(() => throwError(() => http(429, { code: 'limite_tasa' })));
      const store = crear(repo);
      const pendiente = store.seleccionar([archivo('a.png')]);
      for (let i = 0; i < REINTENTOS_LIMITE; i++) await vi.advanceTimersByTimeAsync(ESPERA_LIMITE_MS);
      const error = await pendiente;
      expect(error?.categoria).toBe('limite_tasa');
      expect(repo.subir).toHaveBeenCalledTimes(REINTENTOS_LIMITE + 1);
      expect(store.archivoFallido()).toBe('a.png');
      expect(store.puedeReintentar()).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('AC_TKT072_06 progreso sin total conocido: cuenta solo los archivos ya enviados', async () => {
    const repo = repoMedios();
    const respuesta = new Subject<readonly ResultadoArchivo[]>();
    repo.subir.mockImplementation((_a: File[], _c: string, alProgresar: (c: number, t: number | null) => void) => {
      alProgresar(10, null);
      return respuesta;
    });
    const store = crear(repo);
    const pendiente = store.seleccionar([archivo('a.png')]);
    expect(store.porcentaje()).toBe(0);
    respuesta.next([]);
    respuesta.complete();
    expect(await pendiente).toBeNull();
  });
});

describe('BibliotecaMediosStore (SCR-039)', () => {
  function crear(repo: RepoMedios, query: Record<string, string>) {
    const query$ = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      providers: [
        BibliotecaMediosStore,
        { provide: PanelMediosRepositorio, useValue: repo },
        { provide: ActivatedRoute, useValue: { queryParamMap: query$ } },
      ],
    });
    return { store: TestBed.inject(BibliotecaMediosStore), query$ };
  }

  it('AC_TKT022_02 los filtros salen de la URL y cada cambio relee la página', async () => {
    const repo = repoMedios();
    const { store, query$ } = crear(repo, { estado: 'DISPONIBLE', pagina: '2' });
    expect(store.filtros()).toMatchObject({ estado: 'DISPONIBLE', pagina: 2 });
    expect(store.conFiltros()).toBe(true);
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'DISPONIBLE', pagina: 2 }));
    await vi.waitFor(() => expect(store.licencias().length).toBe(2));
    query$.next(convertToParamMap({ q: 'lago' }));
    await vi.waitFor(() => expect(repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'lago', estado: null })));
    store.recargar();
    expect(store.cargando()).toBe(true);
  });

  it('AC_TKT022_02 biblioteca vacía frente a sin coincidencias', async () => {
    const repo = repoMedios();
    repo.listar.mockResolvedValue(paginaDe([]));
    const vacia = crear(repo, {});
    await vi.waitFor(() => expect(vacia.store.bibliotecaVacia()).toBe(true));
    expect(vacia.store.sinCoincidencias()).toBe(false);
    TestBed.resetTestingModule();
    const filtrada = crear(repo, { q: 'nada' });
    await vi.waitFor(() => expect(filtrada.store.sinCoincidencias()).toBe(true));
    expect(filtrada.store.bibliotecaVacia()).toBe(false);
  });

  it('errores: página fuera de rango y 403', async () => {
    const repo = repoMedios();
    repo.listar.mockRejectedValue(http(404, { code: 'pagina_fuera_de_rango' }));
    const fuera = crear(repo, { pagina: '99' });
    await vi.waitFor(() => expect(fuera.store.paginaFueraDeRango()).toBe(true));
    expect(fuera.store.accesoDenegado()).toBe(false);
    TestBed.resetTestingModule();
    repo.listar.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    const denegado = crear(repo, {});
    await vi.waitFor(() => expect(denegado.store.accesoDenegado()).toBe(true));
  });
});

describe('DetalleMedioStore (SCR-040)', () => {
  function crear(repo: RepoMedios, id: string) {
    TestBed.configureTestingModule({
      providers: [
        DetalleMedioStore,
        { provide: PanelMediosRepositorio, useValue: repo },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ id })) } },
      ],
    });
    return TestBed.inject(DetalleMedioStore);
  }

  const FORM = {
    tituloInterno: '',
    textoAlternativo: 'Alt',
    pieDeFoto: '',
    autorCredito: 'Ana',
    fuenteUrl: '',
    licenciaId: '1',
  };

  it('un id no numérico es «no encontrado» sin pedir nada', () => {
    const repo = repoMedios();
    const store = crear(repo, 'abc');
    expect(store.noEncontrado()).toBe(true);
    expect(repo.obtener).not.toHaveBeenCalled();
    expect(store.validar(FORM)).toEqual({});
  });

  it('AC_TKT022_03 carga, licencias asignables y catalogación que lo deja DISPONIBLE', async () => {
    const repo = repoMedios();
    repo.obtener.mockResolvedValue(medio({ estado: 'PENDIENTE_METADATOS', licencia: null }));
    repo.catalogar.mockResolvedValue(medio({ estado: 'DISPONIBLE' }));
    const store = crear(repo, '7');
    expect(store.cargando()).toBe(true);
    await vi.waitFor(() => expect(store.medio()?.estado).toBe('PENDIENTE_METADATOS'));
    await vi.waitFor(() => expect(store.licencias().map((l) => l.id)).toEqual([1]));
    await vi.waitFor(() => expect(store.usos()).not.toBeNull());
    expect(store.validar({ ...FORM, fuenteUrl: 'ftp://x' })).toEqual({ fuenteUrl: expect.any(String) });
    expect(await store.catalogar(FORM)).toBeNull();
    expect(repo.catalogar).toHaveBeenCalledWith(7, expect.objectContaining({ textoAlternativo: 'Alt', licenciaId: 1, fuenteUrl: null }));
    expect(store.medio()?.estado).toBe('DISPONIBLE');
    expect(store.avisoExito()).toBe('Imagen disponible.');
    repo.catalogar.mockResolvedValue(medio({ estado: 'DISPONIBLE', pieDeFoto: 'Pie' }));
    expect(await store.catalogar(FORM)).toBeNull();
    expect(store.avisoExito()).toBe('Guardaste los datos de la imagen.');
  });

  it('AC_TKT022_03 un 422 de la API vuelve como ErrorApi con campos', async () => {
    const repo = repoMedios();
    repo.catalogar.mockRejectedValue(
      http(422, { code: 'regla_negocio', detail: 'No', errors: { licencia_id: ['Licencia incompatible'] } }),
    );
    const store = crear(repo, '7');
    await vi.waitFor(() => expect(store.medio()).not.toBeNull());
    const error = await store.catalogar(FORM);
    expect(error?.categoria).toBe('regla_negocio');
    expect(error?.campos).toEqual({ licencia_id: ['Licencia incompatible'] });
  });

  it('AC_TKT022_03 retirar (409 en uso → relee), retirar y reactivar; paginación de usos', async () => {
    const repo = repoMedios();
    repo.usos.mockResolvedValue({ usos: [], pagina: 1, totalPaginas: 3, total: 120 });
    const store = crear(repo, '7');
    await vi.waitFor(() => expect(store.medio()).not.toBeNull());
    expect(store.puedeRetirar()).toBe(true);
    expect(store.puedeReactivar()).toBe(false);

    repo.retirar.mockRejectedValueOnce(http(409, { code: 'medio_en_uso', detail: 'En uso' }));
    const llamadas = repo.obtener.mock.calls.length;
    expect((await store.retirar())?.categoria).toBe('conflicto');
    await vi.waitFor(() => expect(repo.obtener.mock.calls.length).toBeGreaterThan(llamadas));

    expect(await store.retirar()).toBeNull();
    expect(store.medio()?.estado).toBe('RETIRADO');
    expect(store.puedeReactivar()).toBe(true);
    expect(store.avisoExito()).toContain('Retiraste');
    expect(await store.reactivar()).toBeNull();
    expect(store.medio()?.estado).toBe('PENDIENTE_METADATOS');
    expect(store.avisoExito()).toContain('Reactivaste');

    await vi.waitFor(() => expect(store.usos()?.totalPaginas).toBe(3));
    store.irAPaginaUsos(9);
    await vi.waitFor(() => expect(repo.usos).toHaveBeenLastCalledWith(7, 3));
    store.irAPaginaUsos(0);
    await vi.waitFor(() => expect(repo.usos).toHaveBeenLastCalledWith(7, 1));
  });

  it('errores de carga: 404, 403, usos y licencias; sin medio los comandos no hacen nada', async () => {
    const repo = repoMedios();
    repo.obtener.mockRejectedValue(http(404, { code: 'no_encontrado' }));
    repo.usos.mockRejectedValue(http(500));
    repo.licencias.mockRejectedValue(http(500));
    const store = crear(repo, '7');
    await vi.waitFor(() => expect(store.noEncontrado()).toBe(true));
    await vi.waitFor(() => expect(store.errorUsos()).toBe(true));
    await vi.waitFor(() => expect(store.errorLicencias()).toBe(true));
    expect(await store.catalogar(FORM)).toBeNull();
    expect(await store.retirar()).toBeNull();
    expect(await store.reactivar()).toBeNull();
    expect(store.puedeRetirar()).toBe(false);
    expect(store.puedeReactivar()).toBe(false);
    TestBed.resetTestingModule();
    repo.obtener.mockRejectedValue(http(403, { code: 'permiso_denegado' }));
    const denegado = crear(repo, '7');
    await vi.waitFor(() => expect(denegado.accesoDenegado()).toBe(true));
  });
});

describe('SelectorMediosStore (SCR-041)', () => {
  function crear(repo: RepoMedios): SelectorMediosStore {
    TestBed.configureTestingModule({
      providers: [SelectorMediosStore, { provide: PanelMediosRepositorio, useValue: repo }],
    });
    return TestBed.inject(SelectorMediosStore);
  }

  const a = medio({ id: 1 });
  const b = medio({ id: 2 });
  const pendiente = medio({ id: 3, estado: 'PENDIENTE_METADATOS' });

  it('AC_TKT022_04 solo carga abierto; DISPONIBLES por defecto; filtros y páginas en memoria', async () => {
    const repo = repoMedios();
    repo.listar.mockResolvedValue(paginaDe([a, b, pendiente], { totalPaginas: 2, total: 60 }));
    const store = crear(repo);
    await new Promise((r) => setTimeout(r, 0));
    expect(repo.listar).not.toHaveBeenCalled();
    store.abrir({ modo: 'varios', maximo: null, permitirNoDisponibles: false, seleccionInicial: [b] });
    await vi.waitFor(() => expect(store.pagina()?.total).toBe(60));
    expect(repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'DISPONIBLE' }));
    await vi.waitFor(() => expect(store.licencias().length).toBe(2));
    expect(store.seleccion()).toEqual([b]);
    store.filtrar({ q: 'lago', estado: null });
    await vi.waitFor(() => expect(repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'lago', estado: null, pagina: 1 })));
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    store.irAPagina(5);
    await vi.waitFor(() => expect(repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ pagina: 2 })));
    store.recargar();
    expect(store.cargando()).toBe(true);
    store.cerrar();
    expect(store.vacio()).toBe(false);
  });

  it('AC_TKT022_04 alternar, máximo, reordenar y quitar; los no disponibles no se seleccionan', () => {
    const store = crear(repoMedios());
    store.abrir({ modo: 'varios', maximo: 2, permitirNoDisponibles: false, seleccionInicial: [] });
    store.alternar(a);
    store.alternar(pendiente);
    expect(store.seleccionable(pendiente)).toBe(false);
    store.alternar(b);
    expect(store.limiteAlcanzado()).toBe(true);
    store.alternar(medio({ id: 9 }));
    expect(store.seleccion().map((m) => m.id)).toEqual([1, 2]);
    store.moverSeleccion(1, 0);
    expect(store.seleccion().map((m) => m.id)).toEqual([2, 1]);
    store.quitar(2);
    expect(store.idsSeleccionados()).toEqual(new Set([1]));

    store.abrir({ modo: 'uno', maximo: null, permitirNoDisponibles: true, seleccionInicial: [] });
    expect(store.modo()).toBe('uno');
    expect(store.filtros().estado).toBeNull();
    store.alternar(pendiente);
    store.alternar(a);
    expect(store.seleccion()).toEqual([a]);
  });

  it('ALT-021 «Usar la existente»: la selecciona si está disponible; si no, lo explica', async () => {
    const repo = repoMedios();
    const store = crear(repo);
    store.abrir({ modo: 'varios', maximo: null, permitirNoDisponibles: false, seleccionInicial: [] });
    repo.obtener.mockResolvedValueOnce(a);
    expect(await store.usarExistente(1)).toBeNull();
    repo.obtener.mockResolvedValueOnce(a);
    expect(await store.usarExistente(1)).toBeNull();
    expect(store.seleccion()).toEqual([a]);
    repo.obtener.mockResolvedValueOnce(pendiente);
    expect((await store.usarExistente(3))?.codigo).toBe('medio_no_disponible');
    repo.obtener.mockRejectedValueOnce(http(404, { code: 'no_encontrado' }));
    expect((await store.usarExistente(4))?.categoria).toBe('no_encontrado');
  });

  it('error del listado', async () => {
    const repo = repoMedios();
    repo.listar.mockRejectedValue(http(500));
    const store = crear(repo);
    store.abrir({ modo: 'uno', maximo: null, permitirNoDisponibles: false, seleccionInicial: [] });
    await vi.waitFor(() => expect(store.error()?.categoria).toBe('servidor'));
  });
});

describe('CargaPanelStore (OBS-C3-01)', () => {
  it('AC_TKT022_07 recuerda la URL de la navegación en curso y la repite tras leer la sesión', async () => {
    const repoAuth = { sesion: vi.fn().mockResolvedValue(sesion()) };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: PanelAuthRepositorio, useValue: repoAuth }],
    });
    const store = TestBed.inject(CargaPanelStore);
    const router = TestBed.inject(Router);
    const navegar = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    expect(store.necesitaCarga()).toBe(true);
    store.recordarDestino();
    expect(await store.continuar()).toBe(true);
    expect(navegar).toHaveBeenCalledWith(router.parseUrl('/'), { replaceUrl: true, onSameUrlNavigation: 'reload' });
    expect(store.necesitaCarga()).toBe(false);
    expect(TestBed.inject(SesionPanelStore).autenticada()).toBe(true);
  });
});
