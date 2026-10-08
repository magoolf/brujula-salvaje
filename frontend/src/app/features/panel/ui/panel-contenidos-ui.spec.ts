import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { DATOS_ZONA_PANEL } from '../../../core/layout/shell-publico/zona';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import { PanelTableroRepositorio } from '../data/panel-tablero.repositorio';
import { AnalisisPublicacion, ImpactoRetiro, ResultadoTransicion } from '../domain/ciclo-editorial';
import { ContenidoEditable, ContenidoResumen, PaginaContenidos } from '../domain/contenidos';
import { FormularioContenido, formularioVacio } from '../domain/formulario-contenido';
import { SesionPanel, TipoContenido } from '../domain/modelos';
import { VistaPreviaContenido } from '../domain/vista-previa';
import { RUTAS_PANEL } from './panel.routes';
import { pintarHtmlSaneado, serializarHtmlSaneado } from './saneado-html';

// jsdom no implementa <dialog> modal, scrollIntoView ni execCommand.
beforeAll(() => {
  const proto = HTMLDialogElement.prototype as unknown as { showModal?: () => void; close?: () => void };
  if (typeof proto.showModal !== 'function') {
    proto.showModal = function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
    proto.close = function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    };
  }
  if (typeof Element.prototype.scrollIntoView !== 'function') {
    Element.prototype.scrollIntoView = function () {
      /* jsdom */
    };
  }
  const doc = document as unknown as { execCommand?: (c: string, u?: boolean, v?: string) => boolean };
  if (typeof doc.execCommand !== 'function') doc.execCommand = () => true;
});

function sesion(rol: 'EDITOR' | 'ADMINISTRADOR' = 'EDITOR'): SesionPanel {
  return {
    usuario: 'editora.uno',
    nombreVisible: 'Editora Uno',
    rol,
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

function formulario(tipo: TipoContenido = 'DESTINO', cambios: Partial<FormularioContenido> = {}): FormularioContenido {
  return { ...formularioVacio(tipo), titulo: 'Torres del Paine', slug: 'torres-del-paine', ...cambios };
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

function resumen(cambios: Partial<ContenidoResumen> = {}): ContenidoResumen {
  return {
    id: 11,
    tipo: 'DESTINO',
    titulo: 'Torres del Paine',
    slug: 'torres-del-paine',
    estado: 'PUBLICADO',
    fechaRevision: '2026-09-01',
    actualizadoEn: new Date('2026-10-01T10:00:00Z'),
    actualizadoPor: 'Ana',
    publicado: true,
    urlPublica: '/destinos/torres-del-paine',
    ...cambios,
  };
}

const VISTA: VistaPreviaContenido = {
  tipo: 'DESTINO',
  marca: 'VISTA PREVIA – NO PUBLICADO',
  titulo: 'Torres del Paine',
  antetitulo: 'Chile',
  resumen: 'Granito y viento.',
  portada: null,
  datos: [{ etiqueta: 'Dificultad', valor: '3 de 5' }],
  bloques: [{ titulo: 'Descripción', html: '<p>Texto <strong>experto</strong><script>alert(1)</script></p>' }],
  listas: [{ titulo: 'Checklist', ordenada: false, elementos: [{ titulo: 'Agua', detalle: 'Básico', html: null, destacado: true }] }],
  galeria: [],
  fuentes: [{ titulo: 'CONAF', url: 'https://conaf.cl', entidad: 'Gobierno' }],
  enlaces: [{ titulo: 'Circuito W', ruta: '/itinerarios/w' }],
  revision: '2026-09-01',
  requisitos: { cumple: false, pendientes: [{ campo: 'galeria', codigo: 'x', mensaje: 'Faltan imágenes.', referencias: [] }] },
};

function analisis(cambios: Partial<AnalisisPublicacion> = {}): AnalisisPublicacion {
  return {
    operacion: 'PUBLICAR',
    confirmable: true,
    entidad: { id: 11, tipo: 'DESTINO', titulo: 'Torres del Paine', estado: 'BORRADOR', version: 3, rol: 'PRINCIPAL', cumple: true, pendientes: [] },
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
  urlPublica: '/destinos/torres-del-paine',
  entidades: [{ id: 11, tipo: 'DESTINO', titulo: 'Torres del Paine', estado: 'PUBLICADO', version: 4, origen: 'PRINCIPAL', urlPublica: null }],
};

const IMPACTO: ImpactoRetiro = {
  retirable: true,
  bloqueos: [],
  bloqueosCascada: [],
  itinerariosEnCascada: [{ id: 9, tipo: 'ITINERARIO', titulo: 'Circuito W', estado: 'PUBLICADO' }],
  tiposEnCascada: [{ id: 6, tipo: 'TIPO', titulo: 'Rafting', estado: 'PUBLICADO' }],
  colecciones: [{ id: 7, tipo: 'COLECCION', titulo: 'Patagonia', estado: 'PUBLICADO' }],
  destacados: ['DESTINOS'],
  enlacesEntrantes: 2,
};

type Repo = Record<keyof PanelContenidosRepositorio, ReturnType<typeof vi.fn>>;

function repoContenidos(): Repo {
  const pagina: PaginaContenidos = {
    contenidos: [resumen(), resumen({ id: 12, titulo: 'Lago', estado: 'BORRADOR', publicado: false, urlPublica: null, fechaRevision: null })],
    pagina: 1,
    totalPaginas: 1,
    total: 2,
  };
  return {
    listar: vi.fn().mockResolvedValue(pagina),
    obtener: vi.fn().mockResolvedValue(contenido()),
    crear: vi.fn().mockResolvedValue(contenido({ id: 12 })),
    actualizar: vi.fn().mockImplementation((_id: number, f: FormularioContenido) => Promise.resolve(contenido({ version: 4, formulario: f }))),
    eliminar: vi.fn().mockResolvedValue(undefined),
    vistaPrevia: vi.fn().mockResolvedValue(VISTA),
    analizar: vi.fn().mockResolvedValue(analisis()),
    publicar: vi.fn().mockResolvedValue(RESULTADO),
    impactoRetiro: vi.fn().mockResolvedValue(IMPACTO),
    retirar: vi.fn().mockResolvedValue({ ...RESULTADO, estado: 'RETIRADO' }),
    reactivar: vi.fn().mockResolvedValue({ ...RESULTADO, estado: 'BORRADOR' }),
    revisiones: vi.fn().mockResolvedValue({
      revisiones: [{ numero: 2, creadaEn: new Date('2026-09-30T10:00:00Z'), creadaPor: 'Ana', motivo: 'PUBLICACION' }],
      pagina: 1,
      totalPaginas: 1,
    }),
    restaurar: vi.fn().mockResolvedValue({ numero: 2, versionActual: 3, formulario: formulario('DESTINO', { titulo: 'Versión antigua' }) }),
    paises: vi.fn().mockResolvedValue([{ id: 1, nombre: 'Chile' }]),
    categoriasGuia: vi.fn().mockResolvedValue([{ id: 2, nombre: 'Seguridad' }]),
    escalas: vi.fn().mockResolvedValue({
      dificultad: [1, 2, 3, 4, 5].map((n) => ({ nivel: n, etiqueta: `D${n}`, descripcion: '' })),
      presupuesto: [1, 2, 3, 4].map((n) => ({ nivel: n, etiqueta: `P${n}`, descripcion: '' })),
    }),
    tiposAventura: vi.fn().mockResolvedValue([
      { id: 4, nombre: 'Kayak', estado: 'BORRADOR' },
      { id: 6, nombre: 'Trekking', estado: 'PUBLICADO' },
    ]),
    buscar: vi.fn().mockResolvedValue([
      { id: 21, tipo: 'ITINERARIO', titulo: 'Circuito W', estado: 'PUBLICADO', slug: 'circuito-w' },
      { id: 22, tipo: 'GUIA', titulo: 'Capas', estado: 'PUBLICADO', slug: 'capas' },
    ]),
  };
}

interface Montaje {
  harness: RouterTestingHarness;
  repo: Repo;
  router: Router;
}

async function montar(url: string, ajustar?: (repo: Repo) => void, rol: 'EDITOR' | 'ADMINISTRADOR' = 'EDITOR'): Promise<Montaje> {
  const repo = repoContenidos();
  ajustar?.(repo);
  TestBed.configureTestingModule({
    providers: [
      provideRouter([{ path: 'panel', data: DATOS_ZONA_PANEL, children: RUTAS_PANEL }]),
      { provide: PanelAuthRepositorio, useValue: { sesion: vi.fn().mockResolvedValue(sesion(rol)) } },
      { provide: PanelContenidosRepositorio, useValue: repo },
      {
        provide: PanelMediosRepositorio,
        useValue: {
          listar: vi.fn().mockResolvedValue({ medios: [], pagina: 1, totalPaginas: 1, total: 0 }),
          licencias: vi.fn().mockResolvedValue([]),
        },
      },
      { provide: PanelTableroRepositorio, useValue: { tablero: vi.fn().mockReturnValue(new Promise(() => undefined)) } },
    ],
  });
  const harness = await RouterTestingHarness.create();
  await harness.navigateByUrl(url);
  await estable(harness);
  return { harness, repo, router: TestBed.inject(Router) };
}

async function estable(harness: RouterTestingHarness): Promise<void> {
  for (let i = 0; i < 5; i++) {
    await harness.fixture.whenStable();
    await new Promise((r) => setTimeout(r, 0));
  }
}

function el<T extends HTMLElement = HTMLElement>(testId: string): T {
  const elemento = document.body.querySelector<T>(`[data-testid="${testId}"]`);
  if (elemento === null) throw new Error(`No existe [data-testid="${testId}"]`);
  return elemento;
}

function todos(testId: string): HTMLElement[] {
  return Array.from(document.body.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`));
}

function existe(testId: string): boolean {
  return document.body.querySelector(`[data-testid="${testId}"]`) !== null;
}

function escribir(testId: string, valor: string): void {
  const control = el<HTMLInputElement>(testId);
  control.value = valor;
  control.dispatchEvent(new Event('input'));
}

async function pulsar(m: Montaje, testId: string): Promise<void> {
  el(testId).click();
  await estable(m.harness);
}

describe('Panel · contenidos (TKT-023)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT023_01 / AC_TKT023_17 listado: tabla, recuento, navegación activa, «Ver en el sitio» y filtros a la URL', async () => {
    const m = await montar('/panel/contenido/destinos?estado=BORRADOR&q=lago');
    await vi.waitFor(() => expect(existe('contenidos-tabla')).toBe(true));
    expect(m.repo.listar).toHaveBeenCalledWith('DESTINO', { estado: 'BORRADOR', q: 'lago', pagina: 1 });
    expect(el('contenidos-recuento').textContent).toContain('2 destinos');
    expect(el('panel-nav-contenido-destinos').getAttribute('aria-current')).toBe('page');
    expect(todos('contenidos-fila')).toHaveLength(2);
    expect(todos('contenidos-ver-sitio')).toHaveLength(1);
    expect(el('contenidos-ver-sitio').getAttribute('target')).toBe('_blank');
    expect(el<HTMLAnchorElement>('contenidos-editar').getAttribute('href')).toBe('/panel/contenido/destinos/11');
    expect(el<HTMLAnchorElement>('contenidos-nuevo').getAttribute('href')).toBe('/panel/contenido/destinos/nuevo');
    expect(el<HTMLInputElement>('contenidos-q').value).toBe('lago');
    expect(document.title).toContain('Destinos');
    escribir('contenidos-q', 'torres');
    const estado = el<HTMLSelectElement>('contenidos-estado');
    estado.value = 'PUBLICADO';
    estado.dispatchEvent(new Event('change'));
    await pulsar(m, 'contenidos-aplicar');
    expect(m.router.url).toBe('/panel/contenido/destinos?estado=PUBLICADO&q=torres');
    expect(existe('contenidos-limpiar')).toBe(true);
  });

  it('AC_TKT023_01 estados del listado: vacío con «Nuevo», sin coincidencias, error, 403 y tipo inexistente', async () => {
    const m = await montar('/panel/contenido/guias', (r) => r.listar.mockResolvedValue({ contenidos: [], pagina: 1, totalPaginas: 1, total: 0 }));
    await vi.waitFor(() => expect(existe('contenidos-vacio')).toBe(true));
    expect(el('contenidos-vacio').textContent).toContain('Aún no hay guías');
    expect(el('contenidos-vacio-nuevo').textContent).toContain('Nueva guía');
    await m.harness.navigateByUrl('/panel/contenido/guias?q=zz');
    await estable(m.harness);
    expect(existe('contenidos-sin-coincidencias')).toBe(true);
    TestBed.resetTestingModule();
    await montar('/panel/contenido/guias', (r) => r.listar.mockRejectedValue(http(500)));
    await vi.waitFor(() => expect(existe('contenidos-error')).toBe(true));
    TestBed.resetTestingModule();
    await montar('/panel/contenido/guias', (r) => r.listar.mockRejectedValue(http(403, { code: 'permiso_denegado' })));
    await vi.waitFor(() => expect(existe('acceso-denegado')).toBe(true));
    TestBed.resetTestingModule();
    await montar('/panel/contenido/guias?pagina=9', (r) => r.listar.mockRejectedValue(http(404, { code: 'pagina_fuera_de_rango' })));
    await vi.waitFor(() => expect(existe('contenidos-pagina-fuera')).toBe(true));
    TestBed.resetTestingModule();
    await montar('/panel/contenido/otra-cosa');
    await vi.waitFor(() => expect(existe('panel-no-encontrada')).toBe(true));
  });

  it('AC_TKT023_01 páginas institucionales: sin «Nuevo» ni filtros; las legales, solo Administrador', async () => {
    const paginas = (r: Repo) =>
      r.listar.mockResolvedValue({
        contenidos: [
          resumen({ id: 1, tipo: 'PAGINA', titulo: 'Acerca de', slug: 'acerca-de' }),
          resumen({ id: 2, tipo: 'PAGINA', titulo: 'Aviso legal', slug: 'aviso-legal' }),
        ],
        pagina: 1,
        totalPaginas: 1,
        total: 2,
      });
    await montar('/panel/contenido/paginas', paginas);
    await vi.waitFor(() => expect(existe('contenidos-tabla')).toBe(true));
    expect(existe('contenidos-nuevo')).toBe(false);
    expect(existe('contenidos-q')).toBe(false);
    expect(todos('contenidos-editar')).toHaveLength(1);
    expect(el('contenidos-solo-admin').textContent).toContain('Solo administrador');
    TestBed.resetTestingModule();
    await montar('/panel/contenido/paginas', paginas, 'ADMINISTRADOR');
    await vi.waitFor(() => expect(todos('contenidos-editar')).toHaveLength(2));
  });

  it('AC_TKT023_02 / AC_TKT023_04 alta: ErrorSummary enlazado, slug propuesto y alta que abre /{id}', async () => {
    const m = await montar('/panel/contenido/destinos/nuevo');
    await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
    expect(document.querySelector('h1')?.textContent).toContain('Nuevo destino');
    expect(el('editor-estado').textContent).toContain('Nuevo');
    expect(existe('editor-accion-principal')).toBe(false);
    await pulsar(m, 'editor-guardar');
    expect(m.repo.crear).not.toHaveBeenCalled();
    const resumenErrores = el('editor-resumen-errores');
    expect(resumenErrores.textContent).toContain('No se puede guardar todavía. Corrige 1 problema:');
    expect(document.activeElement).toBe(resumenErrores);
    expect(el('campo-titulo-error').textContent).toContain('obligatorio');
    // Enlace con href real al campo (con <base href="/"> un «#» llevaría a Inicio).
    expect(el('editor-resumen-enlace').getAttribute('href')).toBe('/panel/contenido/destinos/nuevo#campo-titulo');
    el('editor-resumen-enlace').click();
    await estable(m.harness);
    expect(document.activeElement?.id).toBe('campo-titulo');
    expect(m.router.url).toBe('/panel/contenido/destinos/nuevo#campo-titulo');
    expect(existe('editor-contenido')).toBe(true);
    escribir('campo-titulo', 'Cañón del Colca');
    await estable(m.harness);
    expect(el<HTMLInputElement>('campo-slug').value).toBe('canon-del-colca');
    expect(existe('campo-titulo-error')).toBe(false);
    expect(el('editor-guardado').textContent).toContain('Cambios sin guardar');
    await pulsar(m, 'editor-guardar');
    expect(m.repo.crear).toHaveBeenCalledWith(expect.objectContaining({ titulo: 'Cañón del Colca', slug: 'canon-del-colca' }), expect.any(String));
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/contenido/destinos/12'));
    await estable(m.harness);
    expect(el('editor-aviso').textContent).toContain('Borrador guardado');
  });

  it('AC_TKT023_03 el editor muestra las secciones de cada tipo (BLUEPRINT §11.2)', async () => {
    const casos: [string, TipoContenido, string[]][] = [
      ['destinos', 'DESTINO', ['identidad', 'datos', 'contenido', 'viaje', 'seguridad', 'ubicacion', 'medios', 'relacionados', 'fuentes', 'seo', 'revision', 'historial']],
      ['itinerarios', 'ITINERARIO', ['identidad', 'datos', 'contenido', 'dias', 'seguridad', 'medios']],
      ['guias', 'GUIA', ['identidad', 'contenido', 'datos', 'medios', 'fuentes']],
      ['tipos-aventura', 'TIPO', ['identidad', 'contenido', 'datos', 'checklist', 'medios']],
      ['colecciones', 'COLECCION', ['identidad', 'contenido', 'elementos', 'medios']],
      ['glosario', 'TERMINO', ['identidad', 'relacionados', 'revision', 'historial']],
      ['paginas', 'PAGINA', ['identidad', 'contenido', 'seo', 'revision']],
    ];
    for (const [ruta, tipo, secciones] of casos) {
      await montar(`/panel/contenido/${ruta}/11`, (r) =>
        r.obtener.mockResolvedValue(contenido({ tipo, estado: tipo === 'PAGINA' ? 'PUBLICADO' : 'BORRADOR', formulario: formulario(tipo), nombrePagina: tipo === 'PAGINA' ? 'Acerca de' : null })),
      );
      await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
      for (const s of secciones) expect(existe(`seccion-${s}`), `${tipo}: ${s}`).toBe(true);
      TestBed.resetTestingModule();
    }
  });

  it('AC_TKT023_03 destino: tipos, principal, meses, días y listas editables; guardar envía todo', async () => {
    const m = await montar('/panel/contenido/destinos/11');
    await vi.waitFor(() => expect(existe('editor-tipo-4')).toBe(true));
    el('editor-tipo-4').click();
    await estable(m.harness);
    el('editor-principal-4').click();
    el('editor-dificultad-3').click();
    escribir('campo-duracionMin', '5');
    escribir('campo-duracionMax', '3');
    escribir('campo-latitud', '-50.94');
    escribir('campo-longitud', '-73.4');
    await estable(m.harness);
    expect(existe('editor-marcador')).toBe(true);
    await pulsar(m, 'editor-anadir-fuente');
    escribir('campo-fuentes-0-titulo', 'CONAF');
    escribir('campo-fuentes-0-url', 'ftp://x');
    await pulsar(m, 'editor-guardar');
    expect(m.repo.actualizar).not.toHaveBeenCalled();
    expect(el('campo-duracionMax-error').textContent).toContain('mínima');
    expect(el('campo-fuentes-0-url-error').textContent).toContain('http');
    escribir('campo-duracionMax', '8');
    escribir('campo-fuentes-0-url', 'https://conaf.cl');
    await pulsar(m, 'editor-guardar');
    expect(m.repo.actualizar).toHaveBeenCalledWith(
      11,
      expect.objectContaining({ tipos: [4], tipoPrincipal: '4', dificultad: '3', duracionMin: '5', duracionMax: '8', latitud: '-50.94' }),
      3,
    );
    expect(el('editor-guardado').textContent).toContain('Guardado a las');
  });

  it('AC_TKT023_03 itinerario: días ordenables con indicador de duración (AC-118) y destino por búsqueda', async () => {
    const m = await montar('/panel/contenido/itinerarios/11', (r) =>
      r.obtener.mockResolvedValue(contenido({ tipo: 'ITINERARIO', formulario: formulario('ITINERARIO', { duracionDias: '2' }) })),
    );
    await vi.waitFor(() => expect(existe('editor-anadir-dia')).toBe(true));
    expect(el('editor-indicador-dias').textContent).toContain('Días: 0 de 2');
    await pulsar(m, 'editor-anadir-dia');
    await pulsar(m, 'editor-anadir-dia');
    expect(el('editor-indicador-dias').textContent).toContain('Días: 2 de 2');
    escribir('campo-dias-0-titulo', 'Llegada');
    escribir('campo-dias-1-titulo', 'Cumbre');
    await estable(m.harness);
    (document.getElementById('editor-dias-bajar-0') as HTMLButtonElement).click();
    await estable(m.harness);
    expect(el<HTMLInputElement>('campo-dias-0-titulo').value).toBe('Cumbre');
    // Sin actividades no se puede guardar (DiaEntrada).
    await pulsar(m, 'editor-guardar');
    expect(m.repo.actualizar).not.toHaveBeenCalled();
    expect(el('editor-resumen-errores').textContent).toContain('Día 1: actividades');
    // Destino del itinerario por Combobox (mínimo 2 caracteres, flechas y Enter).
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    const buscador = el<HTMLInputElement>('editor-buscar-destino');
    buscador.value = 'c';
    buscador.dispatchEvent(new Event('input'));
    buscador.value = 'ci';
    buscador.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(350);
    vi.useRealTimers();
    await estable(m.harness);
    expect(m.repo.buscar).toHaveBeenCalledWith(['DESTINO'], 'ci', null);
    expect(todos('editor-buscar-destino-opcion')).toHaveLength(2);
    buscador.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    await estable(m.harness);
    expect(buscador.getAttribute('aria-activedescendant')).toBe('editor-buscar-destino-opcion-0');
    buscador.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    await estable(m.harness);
    expect(el('editor-destino-elegido').textContent).toContain('Circuito W');
  });

  it('AC_TKT023_05 conflicto de versión: aviso sin sobrescribir y «Recargar» con confirmación', async () => {
    const m = await montar('/panel/contenido/destinos/11', (r) => r.actualizar.mockRejectedValueOnce(http(409, { code: 'conflicto_version' })));
    await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
    escribir('campo-resumen', 'Cambio local');
    await pulsar(m, 'editor-guardar');
    expect(el('editor-conflicto').textContent).toContain('Otra persona guardó cambios');
    expect(el<HTMLTextAreaElement>('campo-resumen').value).toBe('Cambio local');
    m.repo.obtener.mockResolvedValueOnce(contenido({ version: 9, formulario: formulario('DESTINO', { resumen: 'Del servidor' }) }));
    await pulsar(m, 'editor-recargar');
    expect(el('editor-confirmacion').textContent).toContain('Se descartarán tus cambios');
    await pulsar(m, 'editor-confirmacion-confirmar');
    expect(existe('editor-conflicto')).toBe(false);
    expect(el<HTMLTextAreaElement>('campo-resumen').value).toBe('Del servidor');
  });

  it('AC_TKT023_07 publicar: guarda antes, analiza, confirma y muestra «Ver en el sitio»', async () => {
    const m = await montar('/panel/contenido/destinos/11', (r) => {
      r.obtener.mockResolvedValueOnce(contenido()).mockResolvedValue(
        contenido({ estado: 'PUBLICADO', nuncaPublicado: false, slugBloqueado: true, version: 5, urlPublica: '/destinos/torres-del-paine' }),
      );
      r.analizar.mockResolvedValue(
        analisis({
          copublicacion: [{ ...analisis().entidad, id: 4, tipo: 'TIPO', titulo: 'Kayak', rol: 'COPUBLICACION' }],
          copublicarTipos: [{ id: 4, version: 1 }],
        }),
      );
    });
    await vi.waitFor(() => expect(existe('editor-accion-principal')).toBe(true));
    escribir('campo-resumen', 'Nuevo resumen');
    await pulsar(m, 'editor-accion-principal');
    expect(m.repo.actualizar).toHaveBeenCalledTimes(1);
    await vi.waitFor(() => expect(existe('publicacion-resumen')).toBe(true));
    expect(el('dialogo-publicacion').hasAttribute('open')).toBe(true);
    expect(el('publicacion-resumen').textContent).toContain('/destinos/torres-del-paine');
    expect(existe('publicacion-aviso-slug')).toBe(true);
    expect(el('publicacion-copublicacion').textContent).toContain('Kayak');
    await pulsar(m, 'publicacion-confirmar');
    expect(m.repo.publicar).toHaveBeenCalledWith('DESTINO', 11, 4, [{ id: 4, version: 1 }], expect.any(String));
    await vi.waitFor(() => expect(existe('editor-exito')).toBe(true));
    expect(el('editor-exito').textContent).toContain('está publicado');
    expect(el<HTMLAnchorElement>('editor-ver-sitio-exito').getAttribute('href')).toBe('/destinos/torres-del-paine');
    expect(el('editor-estado').textContent).toContain('Publicado');
    expect(el<HTMLInputElement>('campo-slug').readOnly).toBe(true);
    expect(el('dialogo-publicacion').hasAttribute('open')).toBe(false);
  });

  it('AC_TKT023_07 / AC_TKT023_08 publicación inválida: lista enlazada, referencias y bloqueo de cascada', async () => {
    const pendiente = {
      campo: 'tipos',
      codigo: 'tipo_retirado',
      mensaje: 'Reactiva primero el tipo Rafting',
      referencias: [{ id: 6, tipo: 'TIPO' as const, titulo: 'Rafting', estado: 'RETIRADO' as const }],
    };
    const m = await montar('/panel/contenido/destinos/11', (r) =>
      r.analizar.mockResolvedValue(
        analisis({
          confirmable: false,
          entidad: { ...analisis().entidad, cumple: false, pendientes: [pendiente, { ...pendiente, campo: 'resumen', codigo: 'r', mensaje: 'Falta el resumen.', referencias: [] }] },
          bloqueosCascada: [{ tipoAventura: { id: 6, tipo: 'TIPO', titulo: 'Rafting', estado: 'PUBLICADO' }, itinerarios: [{ id: 9, tipo: 'ITINERARIO', titulo: 'W', estado: 'PUBLICADO' }], totalItinerarios: 1 }],
        }),
      ),
    );
    await vi.waitFor(() => expect(existe('editor-accion-principal')).toBe(true));
    await pulsar(m, 'editor-accion-principal');
    await vi.waitFor(() => expect(existe('publicacion-errores')).toBe(true));
    expect(el('publicacion-errores').textContent).toContain('No se puede publicar todavía. Corrige 3 problemas:');
    expect(el('publicacion-errores').querySelector('a[href="/panel/contenido/tipos-aventura/6"]')).not.toBeNull();
    expect(existe('publicacion-bloqueo-cascada')).toBe(true);
    expect(existe('publicacion-confirmar')).toBe(false);
    expect(todos('publicacion-error-campo')[1].getAttribute('href')).toBe('/panel/contenido/destinos/11#campo-resumen');
    todos('publicacion-error-campo')[1].click();
    await estable(m.harness);
    expect(el('dialogo-publicacion').hasAttribute('open')).toBe(false);
    expect(document.activeElement?.id).toBe('campo-resumen');
  });

  it('AC_TKT023_10 retirar: impacto en cascada, motivo obligatorio y éxito', async () => {
    const m = await montar('/panel/contenido/destinos/11', (r) =>
      r.obtener
        .mockResolvedValueOnce(contenido({ estado: 'PUBLICADO', nuncaPublicado: false, urlPublica: '/destinos/torres-del-paine' }))
        .mockResolvedValue(contenido({ estado: 'RETIRADO', nuncaPublicado: false, motivoRetiro: 'Cierre' })),
    );
    await vi.waitFor(() => expect(existe('editor-mas-acciones')).toBe(true));
    expect(el('editor-accion-principal').textContent).toContain('Actualizar publicación');
    expect(existe('editor-ver-sitio')).toBe(true);
    el('editor-mas-acciones').click();
    await estable(m.harness);
    await pulsar(m, 'editor-retirar');
    await vi.waitFor(() => expect(existe('retiro-impacto')).toBe(true));
    expect(el('retiro-itinerarios').textContent).toContain('Circuito W');
    expect(el('retiro-tipos').textContent).toContain('Rafting');
    expect(el('retiro-impacto').textContent).toContain('Patagonia');
    expect(el('retiro-impacto').textContent).toContain('2 páginas lo enlazan');
    expect(el<HTMLButtonElement>('retiro-confirmar').disabled).toBe(true);
    escribir('retiro-motivo', 'Cierre del parque');
    await estable(m.harness);
    await pulsar(m, 'retiro-confirmar');
    expect(m.repo.retirar).toHaveBeenCalledWith('DESTINO', 11, 3, 'Cierre del parque', [{ id: 9, tipo: 'ITINERARIO' }, { id: 6, tipo: 'TIPO' }], expect.any(String));
    await vi.waitFor(() => expect(existe('editor-exito')).toBe(true));
    expect(el('editor-exito').textContent).toContain('se retiró');
    expect(el('editor-retirado').textContent).toContain('Reactívalo como borrador');
    expect(el('editor-accion-principal').textContent).toContain('Reactivar como borrador');
    expect(el<HTMLFieldSetElement>('seccion-identidad').querySelector('fieldset')?.disabled).toBe(true);
  });

  it('AC_TKT023_10 retiro bloqueado por usos: solo «Entendido»', async () => {
    const m = await montar('/panel/contenido/tipos-aventura/11', (r) => {
      r.obtener.mockResolvedValue(contenido({ tipo: 'TIPO', estado: 'PUBLICADO', nuncaPublicado: false, formulario: formulario('TIPO') }));
      r.impactoRetiro.mockResolvedValue({ ...IMPACTO, retirable: false, itinerariosEnCascada: [], tiposEnCascada: [], bloqueos: [{ id: 1, tipoEntidad: 'DESTINO', titulo: 'Torres', estado: 'PUBLICADO' }] });
    });
    await vi.waitFor(() => expect(existe('editor-mas-acciones')).toBe(true));
    el('editor-mas-acciones').click();
    await estable(m.harness);
    await pulsar(m, 'editor-retirar');
    await vi.waitFor(() => expect(existe('retiro-bloqueado')).toBe(true));
    expect(existe('retiro-motivo')).toBe(false);
    await pulsar(m, 'retiro-entendido');
    expect(el('dialogo-retiro').hasAttribute('open')).toBe(false);
  });

  it('AC_TKT023_11 reactivar como borrador y eliminar un borrador nunca publicado', async () => {
    let m = await montar('/panel/contenido/guias/11', (r) =>
      r.obtener
        .mockResolvedValueOnce(contenido({ tipo: 'GUIA', estado: 'RETIRADO', nuncaPublicado: false, formulario: formulario('GUIA') }))
        .mockResolvedValue(contenido({ tipo: 'GUIA', estado: 'BORRADOR', nuncaPublicado: false, formulario: formulario('GUIA') })),
    );
    await vi.waitFor(() => expect(existe('editor-retirado')).toBe(true));
    await pulsar(m, 'editor-accion-principal');
    expect(el('editor-confirmacion').textContent).toContain('conservará su dirección');
    await pulsar(m, 'editor-confirmacion-confirmar');
    expect(m.repo.reactivar).toHaveBeenCalled();
    await vi.waitFor(() => expect(el('editor-estado').textContent).toContain('Borrador'));
    expect(el('editor-aviso').textContent).toContain('Reactivaste');
    expect(existe('editor-eliminar')).toBe(false);
    TestBed.resetTestingModule();

    m = await montar('/panel/contenido/destinos/11');
    await vi.waitFor(() => expect(existe('editor-mas-acciones')).toBe(true));
    el('editor-mas-acciones').click();
    await estable(m.harness);
    await pulsar(m, 'editor-eliminar');
    expect(el('editor-confirmacion').textContent).toContain('no se puede deshacer');
    expect(document.activeElement).toBe(el('editor-confirmacion-cancelar'));
    await pulsar(m, 'editor-confirmacion-confirmar');
    expect(m.repo.eliminar).toHaveBeenCalled();
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/contenido/destinos'));
    await estable(m.harness);
    expect(el('contenidos-aviso').textContent).toContain('Se eliminó el borrador');
  });

  it('AC_TKT023_12 historial: restaurar una revisión carga el formulario sin publicar nada', async () => {
    const m = await montar('/panel/contenido/destinos/11');
    await vi.waitFor(() => expect(existe('editor-restaurar-2')).toBe(true));
    await pulsar(m, 'editor-restaurar-2');
    expect(el('editor-confirmacion').textContent).toContain('No cambia nada público');
    await pulsar(m, 'editor-confirmacion-confirmar');
    expect(m.repo.restaurar).toHaveBeenCalledWith('DESTINO', 11, 2);
    expect(el<HTMLInputElement>('campo-titulo').value).toBe('Versión antigua');
    expect(el('editor-guardado').textContent).toContain('Cambios sin guardar');
    expect(el('editor-aviso').textContent).toContain('revisión 2');
    expect(m.repo.actualizar).not.toHaveBeenCalled();
    expect(m.repo.publicar).not.toHaveBeenCalled();
  });

  it('AC_TKT023_13 salir con cambios sin guardar pide confirmación («Seguir editando» / «Salir sin guardar»)', async () => {
    const m = await montar('/panel/contenido/destinos/11');
    await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
    escribir('campo-resumen', 'Sin guardar');
    await estable(m.harness);
    // Con una navegación pendiente (el guard espera a la persona) la app no está «estable»: se
    // espera a los elementos en lugar de a whenStable.
    const navegacion = m.router.navigateByUrl('/panel/medios');
    await vi.waitFor(() => expect(el('editor-confirmacion').hasAttribute('open')).toBe(true));
    expect(el('editor-confirmacion').textContent).toContain('Si sales ahora, se perderán.');
    expect(el('editor-confirmacion-cancelar').textContent).toContain('Seguir editando');
    el('editor-confirmacion-cancelar').click();
    expect(await navegacion).toBe(false);
    expect(m.router.url).toBe('/panel/contenido/destinos/11');
    await vi.waitFor(() => expect(el('editor-confirmacion').hasAttribute('open')).toBe(false));
    const segunda = m.router.navigateByUrl('/panel/medios');
    await vi.waitFor(() => expect(el('editor-confirmacion').hasAttribute('open')).toBe(true));
    el('editor-confirmacion-confirmar').click();
    expect(await segunda).toBe(true);
    expect(m.router.url).toBe('/panel/medios');
  });

  it('AC_TKT023_06 vista previa sin persistir (también del alta) y vuelta al editor con los cambios', async () => {
    const m = await montar('/panel/contenido/destinos/nuevo');
    await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
    escribir('campo-titulo', 'Borrador sin guardar');
    await estable(m.harness);
    await pulsar(m, 'editor-vista-previa');
    await vi.waitFor(() => expect(existe('vista-previa-titulo')).toBe(true));
    expect(m.router.url).toBe('/panel/contenido/destinos/nuevo/vista-previa');
    expect(m.repo.vistaPrevia).toHaveBeenCalledWith(expect.objectContaining({ titulo: 'Borrador sin guardar' }), null);
    expect(m.repo.crear).not.toHaveBeenCalled();
    expect(el('vista-previa-marca').textContent).toBe('VISTA PREVIA – NO PUBLICADO');
    expect(el('vista-previa-franja').getAttribute('role')).toBe('region');
    expect(existe('panel-contenido')).toBe(false);
    expect(document.querySelector('main')?.getAttribute('data-testid')).toBe('vista-previa');
    expect(document.querySelector('meta[name="robots"]')?.getAttribute('content')).toContain('noindex');
    expect(document.title).toContain('Vista previa (no publicado) — Torres del Paine');
    const cuerpo = document.querySelector('.cuerpo-enriquecido');
    expect(cuerpo?.querySelector('strong')?.textContent).toBe('experto');
    expect(cuerpo?.querySelector('script')).toBeNull();
    expect(el('vista-previa-enlace').getAttribute('href')).toBe('/itinerarios/w');
    expect(existe('vista-previa-pendientes')).toBe(true);
    await pulsar(m, 'vista-previa-volver');
    await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
    expect(el<HTMLInputElement>('campo-titulo').value).toBe('Borrador sin guardar');
    expect(el('editor-aviso').textContent).toContain('Recuperamos los cambios');
  });

  it('AC_TKT023_06 vista previa: abierta directamente usa la versión guardada; error y alta sin datos', async () => {
    const m = await montar('/panel/contenido/guias/11/vista-previa', (r) => r.obtener.mockResolvedValue(contenido({ tipo: 'GUIA', formulario: formulario('GUIA') })));
    await vi.waitFor(() => expect(existe('vista-previa-titulo')).toBe(true));
    expect(m.repo.vistaPrevia).toHaveBeenCalledWith(formulario('GUIA'), 11);
    TestBed.resetTestingModule();
    await montar('/panel/contenido/guias/11/vista-previa', (r) => r.vistaPrevia.mockRejectedValue(http(500)));
    await vi.waitFor(() => expect(existe('vista-previa-error')).toBe(true));
    TestBed.resetTestingModule();
    await montar('/panel/contenido/guias/nuevo/vista-previa');
    await vi.waitFor(() => expect(document.body.textContent).toContain('No hay nada que previsualizar'));
  });

  it('AC_TKT023_14 relacionados y glosario por Combobox; texto enriquecido con barra y enlaces seguros', async () => {
    const m = await montar('/panel/contenido/guias/11', (r) =>
      r.obtener.mockResolvedValue(contenido({ tipo: 'GUIA', formulario: formulario('GUIA', { descripcion: '<p>Hola <b>mundo</b></p><img src=x onerror="alert(1)">' }) })),
    );
    await vi.waitFor(() => expect(existe('campo-descripcion')).toBe(true));
    const area = el('campo-descripcion');
    expect(area.getAttribute('role')).toBe('textbox');
    expect(area.querySelector('strong')?.textContent).toBe('mundo');
    expect(area.querySelector('img')).toBeNull();
    // Enlace: solo http, https o rutas internas.
    await pulsar(m, 'campo-descripcion-enlace');
    escribir('campo-descripcion-url', 'javascript:alert(1)');
    await estable(m.harness);
    await pulsar(m, 'campo-descripcion-url-aplicar');
    expect(document.body.textContent).toContain('Usa una dirección que empiece por http');
    escribir('campo-descripcion-url', '/destinos/torres');
    await estable(m.harness);
    await pulsar(m, 'campo-descripcion-url-aplicar');
    expect(area.querySelector('a[href="/destinos/torres"]')).not.toBeNull();
    await pulsar(m, 'campo-descripcion-negrita');
    // Relacionados: se añaden, se reordenan y no se repiten.
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    const buscador = el<HTMLInputElement>('editor-buscar-relacionados');
    buscador.value = 'ca';
    buscador.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(350);
    vi.useRealTimers();
    await estable(m.harness);
    todos('editor-buscar-relacionados-opcion')[0].click();
    await estable(m.harness);
    expect(el('editor-relaciones').textContent).toContain('Circuito W');
    await pulsar(m, 'editor-guardar');
    expect(m.repo.actualizar).toHaveBeenCalledWith(
      11,
      expect.objectContaining({ relaciones: [expect.objectContaining({ id: 21, tipo: 'ITINERARIO' })], descripcion: expect.stringContaining('<a href="/destinos/torres">') }),
      3,
    );
  });

  it('AC_TKT023_18 medios: portada y galería con el selector SCR-041 (ordenable, sin duplicados)', async () => {
    const medio = (id: number, titulo: string) => ({
      id,
      estado: 'DISPONIBLE' as const,
      tituloInterno: titulo,
      textoAlternativo: titulo,
      pieDeFoto: null,
      autorCredito: 'Ana',
      fuenteUrl: null,
      licencia: { id: 1, codigo: 'CC', nombre: 'CC', compatiblePublicacion: true },
      formatoOrigen: 'JPEG' as const,
      anchoPx: 2000,
      altoPx: 1500,
      pesoBytes: 1000,
      derivados: [{ formato: 'WEBP' as const, ancho: 320, alto: 240, url: `/m/${id}.webp` }],
      numeroUsos: 0,
      enUsoPublicado: false,
      subidoPor: 'Ana',
      subidoEn: new Date(),
      actualizadoEn: new Date(),
      pendientes: [],
    });
    const m = await montar('/panel/contenido/destinos/11');
    const medios = TestBed.inject(PanelMediosRepositorio) as unknown as { listar: ReturnType<typeof vi.fn> };
    medios.listar.mockResolvedValue({ medios: [medio(1, 'Uno'), medio(2, 'Dos')], pagina: 1, totalPaginas: 1, total: 2 });
    await vi.waitFor(() => expect(existe('editor-elegir-portada')).toBe(true));
    expect(el('editor-galeria-recuento').textContent).toContain('0 de 3 mínimo');
    await pulsar(m, 'editor-elegir-portada');
    const portada = document.querySelector<HTMLDialogElement>('dialog[aria-labelledby="editor-selector-portada-titulo"]')!;
    await vi.waitFor(() => expect(portada.querySelector('[data-testid="selector-control-1"]')).not.toBeNull());
    portada.querySelector<HTMLInputElement>('[data-testid="selector-control-1"]')!.click();
    await estable(m.harness);
    portada.querySelector<HTMLButtonElement>('[data-testid="selector-anadir"]')!.click();
    await estable(m.harness);
    expect(el('editor-portada').textContent).toContain('Uno');

    await pulsar(m, 'editor-anadir-imagenes');
    const galeria = document.querySelector<HTMLDialogElement>('dialog[aria-labelledby="editor-selector-galeria-titulo"]')!;
    await vi.waitFor(() => expect(galeria.querySelector('[data-testid="selector-control-2"]')).not.toBeNull());
    galeria.querySelector<HTMLInputElement>('[data-testid="selector-control-1"]')!.click();
    galeria.querySelector<HTMLInputElement>('[data-testid="selector-control-2"]')!.click();
    await estable(m.harness);
    galeria.querySelector<HTMLButtonElement>('[data-testid="selector-anadir"]')!.click();
    await estable(m.harness);
    expect(el('editor-galeria-recuento').textContent).toContain('2 de 3 mínimo');
    expect(el('editor-galeria').textContent).toMatch(/1\. Uno[\s\S]*2\. Dos/);
    (document.getElementById('campo-galeria-bajar-0') as HTMLButtonElement).click();
    await estable(m.harness);
    expect(el('editor-galeria').textContent).toMatch(/1\. Dos[\s\S]*2\. Uno/);
    // Volver a elegir una imagen ya presente no la duplica.
    await pulsar(m, 'editor-anadir-imagenes');
    galeria.querySelector<HTMLInputElement>('[data-testid="selector-control-1"]')!.click();
    await estable(m.harness);
    galeria.querySelector<HTMLButtonElement>('[data-testid="selector-anadir"]')!.click();
    await estable(m.harness);
    expect(el('editor-galeria-recuento').textContent).toContain('2 de 3 mínimo');
    const quitar = Array.from(el('editor-galeria').querySelectorAll('button')).find((b) => b.textContent?.includes('Quitar'))!;
    quitar.click();
    await estable(m.harness);
    expect(el('editor-galeria-recuento').textContent).toContain('1 de 3 mínimo');
    el('editor-portada-quitar').click();
    await estable(m.harness);
    expect(existe('editor-portada')).toBe(false);
    await pulsar(m, 'editor-guardar');
    expect(m.repo.actualizar).toHaveBeenCalledWith(11, expect.objectContaining({ portada: null, galeria: [expect.objectContaining({ id: 1 })] }), 3);
  });

  it('AC_TKT023_13 sin conexión: guardar y publicar deshabilitados, datos conservados', async () => {
    const m = await montar('/panel/contenido/destinos/11');
    await vi.waitFor(() => expect(existe('editor-contenido')).toBe(true));
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
    window.dispatchEvent(new Event('offline'));
    await estable(m.harness);
    expect(existe('editor-sin-conexion')).toBe(true);
    expect(el<HTMLButtonElement>('editor-guardar').disabled).toBe(true);
    expect(el<HTMLButtonElement>('editor-accion-principal').disabled).toBe(true);
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    window.dispatchEvent(new Event('online'));
    await estable(m.harness);
    expect(existe('editor-sin-conexion')).toBe(false);
  });
});

describe('saneado del texto enriquecido (RULE-022)', () => {
  const analizar = (html: string) => new DOMParser().parseFromString(html, 'text/html');

  it('AC_TKT023_14 pinta solo la lista blanca, sin scripts ni atributos peligrosos', () => {
    const destino = document.createElement('div');
    pintarHtmlSaneado(
      destino,
      'suelto <b>negrita</b><div>bloque</div><script>alert(1)</script><h2 onclick="x()">T</h2><a href="javascript:alert(1)">mal</a><a href="https://x.org" data-glosario="cumbre" target="_blank">ok</a><a href="/g" data-glosario="MAL">g</a><span style="color:red">sp</span><br><ul><li>i</li></ul>',
      analizar,
    );
    const html = serializarHtmlSaneado(destino);
    expect(html).toBe(
      '<p>suelto <strong>negrita</strong></p><p>bloque</p><h2>T</h2><p>mal<a href="https://x.org" data-glosario="cumbre">ok</a><a href="/g">g</a>sp </p><ul><li>i</li></ul>',
    );
    expect(destino.querySelector('script')).toBeNull();
    expect(destino.querySelector('[onclick]')).toBeNull();
    pintarHtmlSaneado(destino, '', analizar);
    expect(destino.childNodes).toHaveLength(0);
  });

  it('AC_TKT023_14 serializa escapando texto y atributos; vacío → cadena vacía', () => {
    const origen = document.createElement('div');
    const p = document.createElement('p');
    p.appendChild(document.createTextNode('a < b & "c" d'));
    const a = document.createElement('a');
    a.setAttribute('href', '/x?a=1&b="2"');
    a.textContent = 'e';
    p.appendChild(a);
    origen.appendChild(p);
    const vacio = document.createElement('p');
    vacio.appendChild(document.createElement('br'));
    origen.appendChild(vacio);
    expect(serializarHtmlSaneado(origen)).toBe('<p>a &lt; b &amp; "c" d<a href="/x?a=1&amp;b=&quot;2&quot;">e</a></p>');
    const soloVacio = document.createElement('div');
    soloVacio.appendChild(document.createElement('p'));
    expect(serializarHtmlSaneado(soloVacio)).toBe('');
  });
});
