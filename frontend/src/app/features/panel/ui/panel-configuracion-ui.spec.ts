import { Location } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { DATOS_ZONA_PANEL } from '../../../core/layout/shell-publico/zona';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { PanelConfiguracionRepositorio } from '../data/panel-configuracion.repositorio';
import { PanelContenidosRepositorio } from '../data/panel-contenidos.repositorio';
import { PanelCuentasRepositorio } from '../data/panel-cuentas.repositorio';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import { PanelTableroRepositorio } from '../data/panel-tablero.repositorio';
import { EventoAuditoria } from '../domain/auditoria';
import { ConfiguracionSitio } from '../domain/configuracion-sitio';
import { CuentaEquipo } from '../domain/cuentas';
import { ConfigInicio } from '../domain/destacados';
import { RefContenido } from '../domain/formulario-contenido';
import { RolPanel, SesionPanel } from '../domain/modelos';
import { Licencia, Region } from '../domain/taxonomias';
import { RUTAS_PANEL } from './panel.routes';

// jsdom no implementa <dialog> modal.
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
});

function sesion(rol: RolPanel = 'ADMINISTRADOR', usuario = 'admin.uno'): SesionPanel {
  return {
    usuario,
    nombreVisible: 'Persona',
    rol,
    pasoPendiente: 'NINGUNO',
    mfaActivo: true,
    mfaObligatorio: rol === 'ADMINISTRADOR',
    expiraInactividadEn: new Date(Date.now() + 30 * 60_000),
    expiraAbsolutaEn: new Date(Date.now() + 12 * 3_600_000),
    redireccion: '/panel',
  };
}

function http(status: number, cuerpo: unknown = { code: 'x' }): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: cuerpo });
}

const refs = (n: number, tipo: RefContenido['tipo']): RefContenido[] =>
  Array.from({ length: n }, (_, i) => ({ id: i + 1, tipo, titulo: `${tipo} ${i + 1}`, estado: 'PUBLICADO' }));

const INICIO: ConfigInicio = {
  titular: 'Aventura',
  subtitulo: 'Lugares salvajes',
  medio: { id: 9, estado: 'DISPONIBLE', miniatura: '/m/9.webp', textoAlternativo: 'Cima nevada' },
  destinos: refs(6, 'DESTINO'),
  itinerarios: refs(3, 'ITINERARIO'),
  guias: refs(3, 'GUIA'),
  actualizadoEn: new Date('2026-10-01T10:00:00Z'),
  actualizadoPor: 'ana',
};

const CONFIG: ConfiguracionSitio = {
  nombreMarca: 'Brújula Salvaje',
  lema: null,
  textoDescargo: 'Viaja con cuidado.',
  responsableNombre: null,
  responsableIdentificacion: null,
  responsableDomicilio: null,
  responsableCanalAtencion: null,
  actualizadoEn: new Date('2026-10-01T10:00:00Z'),
};

const REGION: Region = { catalogo: 'regiones', id: 1, nombre: 'Andes', slug: 'andes', continente: 'AMERICA', orden: 0, activo: true };
const LICENCIA: Licencia = {
  catalogo: 'licencias',
  id: 4,
  codigo: 'CC-BY-4.0',
  nombre: 'CC BY',
  urlTextoLegal: null,
  requiereAtribucion: true,
  compatiblePublicacion: true,
  activo: true,
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
    ultimoAccesoEn: new Date('2026-10-09T10:00:00Z'),
    creadoEn: new Date('2026-09-01T10:00:00Z'),
    desactivadoEn: null,
    ...parcial,
  };
}

const EVENTO: EventoAuditoria = {
  id: 1,
  ocurridoEn: new Date('2026-10-10T20:05:00Z'),
  actor: 'ana',
  actorId: 5,
  accion: 'EDITAR',
  resultado: 'EXITO',
  tipoEntidad: 'DESTINO',
  entidadId: 7,
  entidadTitulo: 'Cotopaxi',
  camposCambiados: ['titulo', 'resumen'],
  ipTruncada: null,
};

type Repo<T> = Record<keyof T, ReturnType<typeof vi.fn>>;

interface Montaje {
  harness: RouterTestingHarness;
  router: Router;
  config: Repo<PanelConfiguracionRepositorio>;
  cuentas: Repo<PanelCuentasRepositorio>;
  contenidos: { buscar: ReturnType<typeof vi.fn> };
}

async function montar(
  url: string,
  rol: RolPanel = 'ADMINISTRADOR',
  ajustar?: (m: Omit<Montaje, 'harness' | 'router'>) => void,
): Promise<Montaje> {
  const config: Repo<PanelConfiguracionRepositorio> = {
    inicio: vi.fn().mockResolvedValue(INICIO),
    guardarInicio: vi.fn().mockResolvedValue(INICIO),
    configuracion: vi.fn().mockResolvedValue(CONFIG),
    guardarConfiguracion: vi.fn().mockResolvedValue({ ...CONFIG, responsableNombre: 'Brújula SAS' }),
    listar: vi.fn().mockImplementation((c: string) => Promise.resolve(c === 'licencias' ? [LICENCIA] : [REGION])),
    crear: vi.fn().mockResolvedValue({ ...REGION, id: 2, nombre: 'Patagonia' }),
    actualizar: vi.fn().mockResolvedValue(REGION),
    escalas: vi.fn().mockResolvedValue({
      dificultad: [{ id: 1, escala: 'DIFICULTAD', nivel: 1, etiqueta: 'Fácil', descripcion: 'Paseo' }],
      presupuesto: [{ id: 6, escala: 'PRESUPUESTO', nivel: 1, etiqueta: 'Bajo', descripcion: 'Barato' }],
    }),
    actualizarNivel: vi.fn(),
  };
  const cuentas: Repo<PanelCuentasRepositorio> = {
    listar: vi.fn().mockResolvedValue({
      cuentas: [cuenta(), cuenta({ id: 6, usuario: null, nombreVisible: null, etiqueta: 'anon-7f3', estado: 'ANONIMIZADA' })],
      pagina: 1,
      totalPaginas: 1,
      total: 2,
    }),
    administradoresActivos: vi.fn().mockResolvedValue(1),
    obtener: vi.fn().mockResolvedValue(cuenta()),
    crear: vi.fn().mockResolvedValue({ cuenta: cuenta({ id: 8, usuario: 'bea', etiqueta: 'bea' }), contrasenaTemporal: 'temporal-ABCDEFGH12' }),
    actualizar: vi.fn().mockResolvedValue(cuenta()),
    ejecutarAccion: vi.fn().mockResolvedValue({ cuenta: cuenta({ estado: 'DESACTIVADA' }), contrasenaTemporal: null }),
    auditoria: vi.fn().mockResolvedValue({ eventos: [EVENTO], pagina: 1, totalPaginas: 1, total: 1 }),
    actores: vi.fn().mockResolvedValue([{ id: 5, etiqueta: 'ana' }]),
  };
  const contenidos = { buscar: vi.fn().mockResolvedValue([{ id: 40, tipo: 'DESTINO', titulo: 'Valle del Cocora', estado: 'PUBLICADO' }]) };
  ajustar?.({ config, cuentas, contenidos });
  TestBed.configureTestingModule({
    providers: [
      provideRouter([{ path: 'panel', data: DATOS_ZONA_PANEL, children: RUTAS_PANEL }]),
      { provide: PanelAuthRepositorio, useValue: { sesion: vi.fn().mockResolvedValue(sesion(rol, rol === 'EDITOR' ? 'editora' : 'admin.uno')) } },
      { provide: PanelConfiguracionRepositorio, useValue: config },
      { provide: PanelCuentasRepositorio, useValue: cuentas },
      { provide: PanelContenidosRepositorio, useValue: contenidos },
      { provide: PanelMediosRepositorio, useValue: { listar: vi.fn().mockReturnValue(new Promise(() => undefined)), licencias: vi.fn().mockResolvedValue([]) } },
      { provide: PanelTableroRepositorio, useValue: { tablero: vi.fn().mockReturnValue(new Promise(() => undefined)) } },
    ],
  });
  const harness = await RouterTestingHarness.create();
  await harness.navigateByUrl(url);
  await estable(harness);
  return { harness, router: TestBed.inject(Router), config, cuentas, contenidos };
}

async function estable(harness: RouterTestingHarness): Promise<void> {
  for (let i = 0; i < 4; i++) {
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
  return [...document.body.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`)];
}

function existe(testId: string): boolean {
  return document.body.querySelector(`[data-testid="${testId}"]`) !== null;
}

function escribir(testId: string, valor: string): void {
  const control = el<HTMLInputElement>(testId);
  control.value = valor;
  control.dispatchEvent(new Event('input'));
}

function elegir(id: string, valor: string): void {
  const control = document.getElementById(id) as HTMLSelectElement;
  control.value = valor;
  control.dispatchEvent(new Event('change'));
}

async function pulsar(m: Montaje, testId: string): Promise<void> {
  el(testId).click();
  await estable(m.harness);
}

// Casos de varias pantallas con router real: margen ante la carga del equipo (la suite completa
// comparte CPU); el valor por defecto (5 s) se agotaba con la suite completa en paralelo.
describe('Panel · configuración editorial y administración (TKT-024)', { timeout: 20_000 }, () => {
  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT010_08 / AC_TKT024_11 un Editor en /panel/usuarios ve SCR-048 conservando la URL; el Administrador accede', async () => {
    const editor = await montar('/panel/usuarios', 'EDITOR');
    await vi.waitFor(() => expect(existe('acceso-denegado')).toBe(true));
    expect(TestBed.inject(Location).path()).toBe('/panel/usuarios');
    expect(existe('panel-nav-usuarios')).toBe(false);
    expect(existe('panel-nav-inicio')).toBe(true);
    expect(existe('panel-nav-taxonomias')).toBe(true);
    expect(editor.cuentas.listar).not.toHaveBeenCalled();
    TestBed.resetTestingModule();
    for (const url of ['/panel/auditoria', '/panel/configuracion', '/panel/usuarios/nuevo']) {
      await montar(url, 'EDITOR');
      await vi.waitFor(() => expect(existe('acceso-denegado')).toBe(true));
      expect(TestBed.inject(Location).path()).toBe(url);
      TestBed.resetTestingModule();
    }
    await montar('/panel/usuarios');
    await vi.waitFor(() => expect(existe('cuentas-tabla')).toBe(true));
    expect(el('panel-nav-usuarios').getAttribute('aria-current')).toBe('page');
    expect(existe('panel-nav-auditoria')).toBe(true);
    expect(existe('panel-nav-configuracion')).toBe(true);
  });

  it('AC_TKT024_02 SCR-042: listas con contador, alta desde el combobox, reordenación y guardado con «Ver inicio»', async () => {
    const m = await montar('/panel/inicio', 'EDITOR');
    await vi.waitFor(() => expect(existe('destacados-formulario')).toBe(true));
    expect(el('destacados-destinos-contador').textContent).toContain('6 de 6 mínimo');
    expect(el('destacados-destinos-contador').getAttribute('role')).toBe('status');
    expect(todos('destacados-destinos-elemento')).toHaveLength(6);
    expect(el('destacados-imagen-elegida').textContent).toContain('Cima nevada');
    expect(el<HTMLInputElement>('destacados-campo-titular').value).toBe('Aventura');
    // Alta desde el combobox (contenido publicado del tipo de la lista).
    escribir('destacados-destinos-buscar', 'coc');
    await vi.waitFor(() => expect(todos('destacados-destinos-buscar-opcion')).toHaveLength(1), { timeout: 2000 });
    expect(m.contenidos.buscar).toHaveBeenCalledWith(['DESTINO'], 'coc', 'PUBLICADO');
    todos('destacados-destinos-buscar-opcion')[0].click();
    await estable(m.harness);
    expect(todos('destacados-destinos-elemento')).toHaveLength(7);
    expect(el('destacados-destinos-contador').textContent).toContain('7 de 6 mínimo');
    // Reordenar: «Subir» el último lo deja penúltimo.
    (document.getElementById('destacados-destinos-subir-6') as HTMLButtonElement).click();
    await estable(m.harness);
    expect(todos('destacados-destinos-elemento')[5].textContent).toContain('Valle del Cocora');
    await pulsar(m, 'destacados-guardar');
    expect(m.config.guardarInicio).toHaveBeenCalledWith(expect.objectContaining({ destinosIds: [1, 2, 3, 4, 5, 40, 6] }));
    await vi.waitFor(() => expect(existe('destacados-exito')).toBe(true));
    expect(el('destacados-exito').textContent).toContain('Los cambios ya se ven en el inicio.');
    expect(el<HTMLAnchorElement>('destacados-ver-inicio').getAttribute('href')).toBe('/');
  });

  it('AC_TKT024_03 SCR-042: por debajo del mínimo no se envía y se resume el error; lista vacía con relleno automático', async () => {
    const m = await montar('/panel/inicio', 'EDITOR', ({ config }) =>
      config.inicio.mockResolvedValue({ ...INICIO, guias: [] }),
    );
    await vi.waitFor(() => expect(existe('destacados-formulario')).toBe(true));
    expect(el('destacados-guias-vacia').textContent).toContain('se completará automáticamente');
    await pulsar(m, 'destacados-guardar');
    expect(m.config.guardarInicio).not.toHaveBeenCalled();
    expect(el('destacados-errores').textContent).toContain('Elige al menos 3 guías');
    expect(el('destacados-guias-error').textContent).toContain('al menos 3');
    expect(document.activeElement).toBe(el('destacados-errores'));
    // Al salir con cambios sin guardar se pide confirmación (no aquí: no hay cambios todavía).
    const navegacion = m.router.navigateByUrl('/panel/acceso-denegado');
    await estable(m.harness);
    expect(await navegacion).toBe(true);
  });

  it('AC_TKT024_03 SCR-042: un 422 del servidor se muestra en la sección; salir con cambios pide confirmación', async () => {
    const m = await montar('/panel/inicio', 'EDITOR', ({ config }) =>
      config.guardarInicio.mockRejectedValue(http(422, { code: 'regla_negocio', detail: 'No', errors: { 'destinos_ids.0': ['DESTINO 1 no está publicado.'] } })),
    );
    await vi.waitFor(() => expect(existe('destacados-formulario')).toBe(true));
    escribir('destacados-campo-titular', 'Otra portada');
    await pulsar(m, 'destacados-guardar');
    await vi.waitFor(() => expect(existe('destacados-destinos-error')).toBe(true));
    expect(el('destacados-destinos-error').textContent).toContain('no está publicado');
    const salida = m.router.navigateByUrl('/panel/acceso-denegado');
    // La navegación queda pendiente del diálogo: no se espera a la estabilidad de la app.
    await vi.waitFor(() => expect(el('destacados-dialogo-salir').hasAttribute('open')).toBe(true));
    el('destacados-dialogo-salir-confirmar').click();
    expect(await salida).toBe(true);
    expect(TestBed.inject(Location).path()).toBe('/panel/acceso-denegado');
  });

  it('AC_TKT024_04 SCR-043: pestañas en la URL, alta en diálogo con slug propuesto y licencias en solo lectura para el Editor', async () => {
    const m = await montar('/panel/taxonomias', 'EDITOR');
    await vi.waitFor(() => expect(existe('taxonomias-tabla')).toBe(true));
    expect(el('taxonomias-tab-regiones').getAttribute('aria-selected')).toBe('true');
    await pulsar(m, 'taxonomias-nuevo');
    expect(el('taxonomias-dialogo').hasAttribute('open')).toBe(true);
    escribir('taxonomias-campo-nombre', 'Patagonia Sur');
    await estable(m.harness);
    expect(el<HTMLInputElement>('taxonomias-campo-slug').value).toBe('patagonia-sur');
    await pulsar(m, 'taxonomias-dialogo-guardar');
    expect(m.config.crear).not.toHaveBeenCalled();
    expect(existe('taxonomias-campo-continente')).toBe(true);
    elegir('taxonomias-campo-continente', 'AMERICA');
    await pulsar(m, 'taxonomias-dialogo-guardar');
    expect(m.config.crear).toHaveBeenCalledWith(expect.objectContaining({ nombre: 'Patagonia Sur', slug: 'patagonia-sur', continente: 'AMERICA' }));
    await vi.waitFor(() => expect(existe('taxonomias-exito')).toBe(true));
    expect(el('taxonomias-dialogo').hasAttribute('open')).toBe(false);
    // Teclado: flecha derecha mueve el foco a la siguiente pestaña; el clic la activa.
    el('taxonomias-tab-regiones').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
    expect(document.activeElement).toBe(el('taxonomias-tab-paises'));
    await pulsar(m, 'taxonomias-tab-licencias');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/taxonomias?catalogo=licencias'));
    await vi.waitFor(() => expect(existe('taxonomias-solo-admin')).toBe(true));
    expect(el('taxonomias-solo-admin').textContent).toContain('Solo un administrador puede modificar las licencias y las escalas.');
    expect(existe('taxonomias-nuevo')).toBe(false);
    expect(existe('taxonomias-editar-4')).toBe(false);
    expect(el('taxonomias-tabla').textContent).toContain('CC BY (CC-BY-4.0)');
  });

  it('AC_TKT024_05 SCR-043: retirar algo en uso muestra el bloqueo con los usos (RULE-007)', async () => {
    const m = await montar('/panel/taxonomias?catalogo=regiones', 'EDITOR', ({ config }) =>
      config.actualizar.mockRejectedValue(
        http(409, { code: 'dependencia_bloqueante', detail: 'La región está en uso.', usos: [{ tipo_entidad: 'DESTINO', id: 8, titulo: 'Cocora', estado_editorial: 'PUBLICADO' }], total_usos: 1 }),
      ),
    );
    await vi.waitFor(() => expect(existe('taxonomias-retirar-1')).toBe(true));
    await pulsar(m, 'taxonomias-retirar-1');
    expect(el('taxonomias-dialogo-estado').hasAttribute('open')).toBe(true);
    await pulsar(m, 'taxonomias-dialogo-estado-confirmar');
    await vi.waitFor(() => expect(existe('taxonomias-bloqueo')).toBe(true));
    expect(el('taxonomias-bloqueo').textContent).toContain('Lo usa 1 contenido publicado');
    expect(el('taxonomias-bloqueo-usos').querySelector('a')?.getAttribute('href')).toBe('/panel/contenido/destinos/8');
  });

  it('AC_TKT024_04 SCR-043: el Administrador edita un nivel de escala', async () => {
    const m = await montar('/panel/taxonomias?catalogo=escalas', 'ADMINISTRADOR', ({ config }) =>
      config.actualizarNivel.mockResolvedValue({ id: 1, escala: 'DIFICULTAD', nivel: 1, etiqueta: 'Suave', descripcion: 'Paseo' }),
    );
    await vi.waitFor(() => expect(existe('taxonomias-tabla-dificultad')).toBe(true));
    expect(existe('taxonomias-tabla-presupuesto')).toBe(true);
    await pulsar(m, 'taxonomias-editar-nivel-1');
    expect(el<HTMLInputElement>('taxonomias-campo-etiqueta').value).toBe('Fácil');
    escribir('taxonomias-campo-etiqueta', 'Suave');
    await pulsar(m, 'taxonomias-dialogo-guardar');
    expect(m.config.actualizarNivel).toHaveBeenCalledWith(1, { etiqueta: 'Suave', descripcion: 'Paseo' });
  });

  it('AC_TKT024_10 SCR-047: aviso de Responsable vacío, vista previa del descargo y guardado', async () => {
    const m = await montar('/panel/configuracion');
    await vi.waitFor(() => expect(existe('config-formulario')).toBe(true));
    expect(el('config-responsable-vacio').textContent).toContain('[RESPONSABLE POR DEFINIR]');
    expect(el('config-vista-descargo').textContent).toContain('Viaja con cuidado.');
    escribir('config-campo-descargo', 'Nuevo descargo');
    await estable(m.harness);
    expect(el('config-vista-descargo').textContent).toContain('Nuevo descargo');
    escribir('config-campo-marca', '');
    await pulsar(m, 'config-guardar');
    expect(m.config.guardarConfiguracion).not.toHaveBeenCalled();
    expect(el('config-campo-marca-error').textContent).toContain('obligatorio');
    escribir('config-campo-marca', 'Brújula');
    escribir('config-campo-responsable-nombre', 'Brújula SAS');
    await pulsar(m, 'config-guardar');
    expect(m.config.guardarConfiguracion).toHaveBeenCalledWith(expect.objectContaining({ nombreMarca: 'Brújula', responsableNombre: 'Brújula SAS', lema: null }));
    await vi.waitFor(() => expect(existe('config-exito')).toBe(true));
  });

  it('AC_TKT024_06 SCR-044/045: listado con seudónimo sin enlace; alta con contraseña temporal una sola vez', async () => {
    const m = await montar('/panel/usuarios');
    await vi.waitFor(() => expect(existe('cuentas-tabla')).toBe(true));
    expect(el('cuentas-recuento').textContent).toContain('2 cuentas');
    expect(el('cuentas-seudonimo').tagName).toBe('EM');
    expect(existe('cuentas-enlace-6')).toBe(false);
    await pulsar(m, 'cuentas-nueva');
    await vi.waitFor(() => expect(existe('cuenta-formulario')).toBe(true));
    expect(m.router.url).toBe('/panel/usuarios/nuevo');
    escribir('cuenta-campo-usuario', 'bea');
    escribir('cuenta-campo-nombre', 'Bea');
    await pulsar(m, 'cuenta-guardar');
    expect(el('cuenta-campo-rol-error').textContent).toContain('Elige un rol');
    el('cuenta-rol-EDITOR').click();
    el('cuenta-rol-EDITOR').dispatchEvent(new Event('change'));
    await pulsar(m, 'cuenta-guardar');
    expect(m.cuentas.crear).toHaveBeenCalledWith({ usuario: 'bea', nombreVisible: 'Bea', rol: 'EDITOR' }, expect.any(String));
    await vi.waitFor(() => expect(existe('secreto-temporal')).toBe(true));
    expect(el('secreto-valor').textContent).toContain('temporal-ABCDEFGH12');
    expect(el('secreto-temporal').textContent).toContain('Se muestra solo esta vez.');
    expect(existe('cuenta-formulario')).toBe(false);
    await pulsar(m, 'secreto-guardado');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/usuarios/8'));
    expect(existe('secreto-temporal')).toBe(false);
  });

  it('AC_TKT024_08 SCR-045: el último Administrador activo no se puede desactivar ni degradar (motivo visible)', async () => {
    const m = await montar('/panel/usuarios/1', 'ADMINISTRADOR', ({ cuentas }) =>
      cuentas.obtener.mockResolvedValue(cuenta({ id: 1, usuario: 'admin.dos', etiqueta: 'admin.dos', rol: 'ADMINISTRADOR' })),
    );
    await vi.waitFor(() => expect(existe('cuenta-accion-desactivar-motivo')).toBe(true));
    expect(el('cuenta-accion-desactivar-motivo').textContent).toContain('último administrador activo');
    expect(el('cuenta-accion-desactivar').getAttribute('aria-disabled')).toBe('true');
    expect(el('cuenta-rol-motivo').textContent).toContain('último administrador activo');
    expect(el<HTMLInputElement>('cuenta-rol-EDITOR').disabled).toBe(true);
    await pulsar(m, 'cuenta-accion-desactivar');
    expect(el('cuenta-dialogo-accion').hasAttribute('open')).toBe(false);
  });

  it('AC_TKT024_07 SCR-045: desactivar con confirmación que describe el efecto; restablecer muestra el secreto; 409 explicado', async () => {
    const m = await montar('/panel/usuarios/5', 'ADMINISTRADOR', ({ cuentas }) => {
      cuentas.administradoresActivos.mockResolvedValue(2);
      cuentas.ejecutarAccion
        .mockResolvedValueOnce({ cuenta: cuenta(), contrasenaTemporal: 'temporal-ZZZZZZZZ99' })
        .mockRejectedValueOnce(http(409, { code: 'ultimo_administrador', detail: 'x' }))
        .mockResolvedValueOnce({ cuenta: cuenta({ estado: 'DESACTIVADA' }), contrasenaTemporal: null });
    });
    await vi.waitFor(() => expect(existe('cuenta-acciones')).toBe(true));
    expect(el('cuenta-titulo').textContent).toContain('ana');
    await pulsar(m, 'cuenta-accion-restablecerContrasena');
    await pulsar(m, 'cuenta-dialogo-accion-confirmar');
    await vi.waitFor(() => expect(existe('secreto-temporal')).toBe(true));
    expect(el('secreto-temporal').textContent).toContain('Contraseña temporal de ana');
    await pulsar(m, 'secreto-guardado');
    expect(existe('secreto-temporal')).toBe(false);
    await pulsar(m, 'cuenta-accion-desactivar');
    expect(el('cuenta-dialogo-accion').textContent).toContain('Se cerrarán todas sus sesiones de inmediato.');
    await pulsar(m, 'cuenta-dialogo-accion-confirmar');
    await vi.waitFor(() => expect(existe('cuenta-error-accion')).toBe(true));
    expect(el('cuenta-error-accion').textContent).toContain('No puedes desactivar ni cambiar el rol del último administrador activo.');
    await pulsar(m, 'cuenta-accion-desactivar');
    await pulsar(m, 'cuenta-dialogo-accion-confirmar');
    await vi.waitFor(() => expect(el('cuenta-estado').textContent).toContain('Desactivada'));
    expect(existe('cuenta-accion-anonimizar')).toBe(true);
    expect(existe('cuenta-accion-reactivar')).toBe(true);
  });

  it('AC_TKT024_09 SCR-046: solo lectura, filtros que se aplican a la URL y «Ver cambios» desplegable', async () => {
    const m = await montar('/panel/auditoria?accion=EDITAR');
    await vi.waitFor(() => expect(existe('auditoria-tabla')).toBe(true));
    expect(el('auditoria-nota').textContent).toContain('Registro de solo lectura. Se conserva 365 días.');
    expect(el<HTMLSelectElement>('auditoria-accion').value).toBe('EDITAR');
    expect(m.cuentas.auditoria).toHaveBeenCalledWith(expect.objectContaining({ accion: 'EDITAR' }));
    expect(el('auditoria-entidad').getAttribute('href')).toBe('/panel/contenido/destinos/7');
    expect(el('auditoria-tabla').textContent).toContain('hora de Bogotá');
    const ver = el('auditoria-ver-cambios-1');
    expect(ver.getAttribute('aria-expanded')).toBe('false');
    await pulsar(m, 'auditoria-ver-cambios-1');
    expect(ver.getAttribute('aria-expanded')).toBe('true');
    expect((document.getElementById('auditoria-cambios-1') as HTMLElement).hidden).toBe(false);
    expect(document.getElementById('auditoria-cambios-1')?.textContent).toContain('titulo, resumen');
    expect(document.body.querySelectorAll('button').length).toBeGreaterThan(0);
    expect(existe('auditoria-eliminar')).toBe(false);
    await vi.waitFor(() => expect(document.getElementById('auditoria-actor')?.textContent).toContain('ana'));
    elegir('auditoria-actor', '5');
    escribir('auditoria-desde', '2026-10-01');
    await pulsar(m, 'auditoria-aplicar');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/auditoria?desde=2026-10-01&actor=5&accion=EDITAR'));
    escribir('auditoria-hasta', '2026-09-01');
    await pulsar(m, 'auditoria-aplicar');
    await vi.waitFor(() => expect(existe('auditoria-fechas-error')).toBe(true));
  });

  it('AC_TKT024_09 SCR-046: vacío con filtros y error con reintento', async () => {
    const m = await montar('/panel/auditoria?tipo=MEDIO', 'ADMINISTRADOR', ({ cuentas }) =>
      cuentas.auditoria.mockResolvedValue({ eventos: [], pagina: 1, totalPaginas: 1, total: 0 }),
    );
    await vi.waitFor(() => expect(existe('auditoria-vacio')).toBe(true));
    expect(el('auditoria-vacio').textContent).toContain('No hay eventos con estos filtros');
    m.cuentas.auditoria.mockRejectedValue(http(500));
    await pulsar(m, 'auditoria-vacio-limpiar');
    await vi.waitFor(() => expect(existe('auditoria-error')).toBe(true));
  });
});
