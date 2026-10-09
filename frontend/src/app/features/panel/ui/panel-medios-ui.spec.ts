import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { Observable, of, throwError } from 'rxjs';

import { DATOS_ZONA_PANEL } from '../../../core/layout/shell-publico/zona';
import { PanelAuthRepositorio } from '../data/panel-auth.repositorio';
import { PanelMediosRepositorio } from '../data/panel-medios.repositorio';
import { PanelTableroRepositorio } from '../data/panel-tablero.repositorio';
import { LicenciaCatalogo, Medio, PaginaMedios, ResultadoArchivo } from '../domain/medios';
import { SesionPanel } from '../domain/modelos';
import { RUTAS_PANEL } from './panel.routes';

// jsdom no implementa <dialog> modal, IntersectionObserver ni scrollIntoView.
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

function medio(parcial: Partial<Medio> = {}): Medio {
  return {
    id: 7,
    estado: 'DISPONIBLE',
    tituloInterno: 'Cumbre',
    textoAlternativo: 'Montaña nevada',
    pieDeFoto: null,
    autorCredito: 'Ana',
    fuenteUrl: null,
    licencia: { id: 1, codigo: 'CC-BY-4.0', nombre: 'CC BY 4.0', compatiblePublicacion: true },
    formatoOrigen: 'JPEG',
    anchoPx: 2400,
    altoPx: 1600,
    pesoBytes: 1_572_864,
    derivados: [{ formato: 'WEBP', ancho: 320, alto: 213, url: '/w/320.webp' }],
    numeroUsos: 0,
    enUsoPublicado: false,
    subidoPor: '#3',
    subidoEn: new Date('2026-09-30T10:00:00Z'),
    actualizadoEn: new Date('2026-09-30T10:00:00Z'),
    pendientes: [],
    ...parcial,
  };
}

function http(status: number, cuerpo: unknown = { code: 'x' }): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: cuerpo });
}

function pagina(medios: readonly Medio[], extra: Partial<PaginaMedios> = {}): PaginaMedios {
  return { medios, pagina: 1, totalPaginas: 1, total: medios.length, ...extra };
}

const LICENCIAS: LicenciaCatalogo[] = [
  { id: 1, codigo: 'CC-BY-4.0', nombre: 'CC BY 4.0', compatiblePublicacion: true, activa: true },
  { id: 3, codigo: 'NC', nombre: 'No comercial', compatiblePublicacion: false, activa: true },
];

type RepoMedios = Record<keyof PanelMediosRepositorio, ReturnType<typeof vi.fn>>;

function repoMedios(): RepoMedios {
  return {
    listar: vi.fn().mockResolvedValue(pagina([medio(), medio({ id: 8, estado: 'PENDIENTE_METADATOS', tituloInterno: 'Lago' })])),
    obtener: vi.fn().mockResolvedValue(medio()),
    usos: vi.fn().mockResolvedValue({ usos: [], pagina: 1, totalPaginas: 1, total: 0 }),
    catalogar: vi.fn().mockResolvedValue(medio()),
    retirar: vi.fn().mockResolvedValue(medio({ estado: 'RETIRADO' })),
    reactivar: vi.fn().mockResolvedValue(medio({ estado: 'PENDIENTE_METADATOS', pendientes: ['licencia'] })),
    licencias: vi.fn().mockResolvedValue(LICENCIAS),
    subir: vi.fn().mockReturnValue(of([])),
  };
}

interface Montaje {
  harness: RouterTestingHarness;
  repo: RepoMedios;
  auth: { sesion: ReturnType<typeof vi.fn> };
  router: Router;
}

async function montar(
  url: string,
  ajustar?: (repo: RepoMedios) => void,
  leerSesion: () => Promise<SesionPanel> = () => Promise.resolve(sesion()),
): Promise<Montaje> {
  const repo = repoMedios();
  ajustar?.(repo);
  const auth = { sesion: vi.fn().mockImplementation(leerSesion) };
  TestBed.configureTestingModule({
    providers: [
      provideRouter([{ path: 'panel', data: DATOS_ZONA_PANEL, children: RUTAS_PANEL }]),
      { provide: PanelAuthRepositorio, useValue: auth },
      { provide: PanelMediosRepositorio, useValue: repo },
      { provide: PanelTableroRepositorio, useValue: { tablero: vi.fn().mockReturnValue(new Promise(() => undefined)) } },
    ],
  });
  const harness = await RouterTestingHarness.create();
  await harness.navigateByUrl(url);
  await estable(harness);
  return { harness, repo, auth, router: TestBed.inject(Router) };
}

async function estable(harness: RouterTestingHarness): Promise<void> {
  for (let i = 0; i < 4; i++) {
    await harness.fixture.whenStable();
    await new Promise((r) => setTimeout(r, 0));
  }
}

function raiz(): HTMLElement {
  return document.body;
}

function el<T extends HTMLElement = HTMLElement>(testId: string): T {
  const elemento = raiz().querySelector<T>(`[data-testid="${testId}"]`);
  if (elemento === null) throw new Error(`No existe [data-testid="${testId}"]`);
  return elemento;
}

function existe(testId: string): boolean {
  return raiz().querySelector(`[data-testid="${testId}"]`) !== null;
}

function escribir(testId: string, valor: string): void {
  const control = el<HTMLInputElement>(testId);
  control.value = valor;
  control.dispatchEvent(new Event('input'));
}

function elegir(testId: string, valor: string): void {
  const control = el<HTMLSelectElement>(testId);
  control.value = valor;
  control.dispatchEvent(new Event('change'));
}

async function pulsar(m: Montaje, testId: string): Promise<void> {
  el(testId).click();
  await estable(m.harness);
}

function conArchivos(input: HTMLInputElement, archivos: File[]): void {
  Object.defineProperty(input, 'files', { value: archivos, configurable: true });
  input.dispatchEvent(new Event('change'));
}

function archivo(nombre: string, tipo = 'image/png', tamano = 10): File {
  return new File([new Uint8Array(tamano)], nombre, { type: tipo });
}

describe('Panel · medios (TKT-022)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('AC_TKT022_07 carga completa: armazón con <main> mientras se lee la sesión y después la pantalla', async () => {
    let resolver: (s: SesionPanel) => void = () => undefined;
    const m = await montar('/panel/medios?estado=DISPONIBLE', undefined, () => new Promise((r) => (resolver = r)));
    const carga = el('panel-cargando');
    expect(carga.tagName).toBe('MAIN');
    expect(carga.getAttribute('aria-busy')).toBe('true');
    expect(carga.textContent).toContain('Cargando el panel…');
    resolver(sesion());
    await vi.waitFor(() => expect(existe('pagina-medios')).toBe(true));
    expect(m.router.url).toBe('/panel/medios?estado=DISPONIBLE');
    expect(existe('panel-cargando')).toBe(false);
    expect(document.activeElement).toBe(document.body);
  });

  it('AC_TKT022_07 sin sesión, tras la carga va a SCR-030 con un siguiente seguro', async () => {
    const m = await montar('/panel/medios/7', undefined, () => Promise.reject(http(401, { code: 'no_autenticado' })));
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/acceso?siguiente=%2Fpanel%2Fmedios%2F7'));
  });

  it('AC_TKT022_02 biblioteca: rejilla, recuento, navegación activa y filtros que se aplican a la URL', async () => {
    const m = await montar('/panel/medios?pagina=2&q=lago');
    await vi.waitFor(() => expect(existe('medios-rejilla')).toBe(true));
    expect(el('medios-recuento').textContent).toContain('2 imágenes');
    expect(el('panel-nav-medios').getAttribute('aria-current')).toBe('page');
    expect(el('medio-mosaico-7').getAttribute('aria-label')).toBe('Cumbre, Disponible, CC BY 4.0, usado en 0 contenidos');
    expect(el('medio-mosaico-8').textContent).toContain('Pendiente de datos');
    expect(el<HTMLInputElement>('medios-q').value).toBe('lago');
    expect(m.repo.listar).toHaveBeenCalledWith(expect.objectContaining({ q: 'lago', pagina: 2 }));

    elegir('medios-estado', 'RETIRADO');
    elegir('medios-en-uso', 'false');
    elegir('medios-licencia', 'CC-BY-4.0');
    escribir('medios-q', ' río ');
    await pulsar(m, 'medios-aplicar');
    await vi.waitFor(() =>
      expect(m.router.url).toBe('/panel/medios?estado=RETIRADO&licencia=CC-BY-4.0&en_uso=false&q=r%C3%ADo'),
    );
    await estable(m.harness);
    await pulsar(m, 'medios-limpiar');
    await vi.waitFor(() => expect(m.router.url).toBe('/panel/medios'));

    const detalles = el<HTMLDetailsElement>('medios-filtros');
    detalles.open = false;
    detalles.dispatchEvent(new Event('toggle'));
    await estable(m.harness);
    expect(detalles.open).toBe(false);
  });

  it('AC_TKT022_02 estados: vacía, sin coincidencias, página fuera de rango, error con reintento y 403', async () => {
    const vacia = await montar('/panel/medios', (r) => r.listar.mockResolvedValue(pagina([])));
    await vi.waitFor(() => expect(existe('medios-vacio')).toBe(true));
    await pulsar(vacia, 'medios-vacio-subir');
    expect(el('medios-subir').getAttribute('aria-expanded')).toBe('true');
    TestBed.resetTestingModule();

    await montar('/panel/medios?q=nada', (r) => r.listar.mockResolvedValue(pagina([])));
    await vi.waitFor(() => expect(existe('medios-sin-coincidencias')).toBe(true));
    TestBed.resetTestingModule();

    await montar('/panel/medios?pagina=50', (r) => r.listar.mockRejectedValue(http(404, { code: 'pagina_fuera_de_rango' })));
    await vi.waitFor(() => expect(existe('medios-pagina-fuera')).toBe(true));
    TestBed.resetTestingModule();

    let intentos = 0;
    const fallo = await montar('/panel/medios', (r) =>
      r.listar.mockImplementation(() => (intentos++ === 0 ? Promise.reject(http(500)) : Promise.resolve(pagina([medio()])))),
    );
    await vi.waitFor(() => expect(existe('medios-error')).toBe(true));
    await pulsar(fallo, 'estado-error-reintentar');
    await vi.waitFor(() => expect(existe('medios-rejilla')).toBe(true));
    TestBed.resetTestingModule();

    await montar('/panel/medios', (r) => r.listar.mockRejectedValue(http(403, { code: 'permiso_denegado' })));
    await vi.waitFor(() => expect(existe('acceso-denegado')).toBe(true));
  });

  it('AC_TKT022_01 subida desde la biblioteca: validación previa, resultados por archivo, resumen y recarga', async () => {
    const aceptado: ResultadoArchivo = {
      nombreArchivo: 'b.png',
      resultado: 'ACEPTADO',
      medio: medio({ id: 21, estado: 'PENDIENTE_METADATOS' }),
      medioExistenteId: null,
      motivo: null,
      local: false,
    };
    const duplicado: ResultadoArchivo = { ...aceptado, nombreArchivo: 'c.png', resultado: 'DUPLICADO', medio: null, medioExistenteId: 5 };
    const rechazado: ResultadoArchivo = { ...aceptado, nombreArchivo: 'd.png', resultado: 'RECHAZADO', medio: null, motivo: 'megapixeles_excedidos' };
    const m = await montar('/panel/medios', (r) => r.subir.mockReturnValue(of([aceptado, duplicado, rechazado])));
    await vi.waitFor(() => expect(existe('medios-rejilla')).toBe(true));
    await pulsar(m, 'medios-subir');
    expect(el('subida-reglas').textContent).toContain('hasta 10 MB');
    const input = el<HTMLInputElement>('subida-archivos');
    const clic = vi.spyOn(input, 'click').mockImplementation(() => undefined);
    await pulsar(m, 'subida-seleccionar');
    expect(clic).toHaveBeenCalled();
    const llamadasListado = m.repo.listar.mock.calls.length;
    conArchivos(input, [archivo('a.gif', 'image/gif'), archivo('b.png'), archivo('c.png'), archivo('d.png')]);
    await estable(m.harness);
    await vi.waitFor(() => expect(existe('subida-resultados')).toBe(true));
    expect(m.repo.subir.mock.calls[0][0].map((f: File) => f.name)).toEqual(['b.png', 'c.png', 'd.png']);
    expect(el('subida-resumen').textContent).toBe('1 aceptada, 2 rechazadas, 1 duplicada');
    expect(el('subida-anuncio').textContent).toBe('1 aceptada, 2 rechazadas, 1 duplicada');
    expect(el('subida-resultado-0').getAttribute('data-motivo')).toBe('formato_no_permitido');
    expect(el('subida-resultado-1').querySelector('[data-testid="subida-completar"]')?.getAttribute('href')).toBe('/panel/medios/21');
    expect(el('subida-resultado-2').querySelector('[data-testid="subida-usar-existente"]')?.getAttribute('href')).toBe('/panel/medios/5');
    expect(el('subida-resultado-3').textContent).toContain('Supera los 40 megapíxeles.');
    await vi.waitFor(() => expect(m.repo.listar.mock.calls.length).toBeGreaterThan(llamadasListado));
    await pulsar(m, 'subida-cerrar-resultados');
    expect(existe('subida-resultados')).toBe(false);

    // Más de 10: se rechaza la selección completa.
    conArchivos(input, Array.from({ length: 11 }, (_, i) => archivo(`${i}.png`)));
    await estable(m.harness);
    expect(el('subida-error-seleccion').textContent).toContain('hasta 10 imágenes');

    // Arrastrar y soltar (opcional, 2.5.7).
    const zona = input.parentElement as HTMLElement;
    const sobre = new Event('dragover', { cancelable: true });
    zona.dispatchEvent(sobre);
    await estable(m.harness);
    expect(zona.classList.contains('arrastrando')).toBe(true);
    zona.dispatchEvent(new Event('dragleave'));
    const soltar = new Event('drop', { cancelable: true });
    Object.defineProperty(soltar, 'dataTransfer', { value: { files: [archivo('e.png')] } });
    zona.dispatchEvent(soltar);
    await estable(m.harness);
    expect(m.repo.subir).toHaveBeenCalledTimes(2);
  });

  it('ALT-017 un fallo al subir se informa y «Reintentar» reenvía', async () => {
    let intentos = 0;
    const m = await montar('/panel/medios', (r) =>
      r.subir.mockImplementation((): Observable<readonly ResultadoArchivo[]> =>
        intentos++ === 0 ? throwError(() => http(0)) : of([]),
      ),
    );
    await vi.waitFor(() => expect(existe('medios-rejilla')).toBe(true));
    await pulsar(m, 'medios-subir');
    conArchivos(el<HTMLInputElement>('subida-archivos'), [archivo('a.png')]);
    await estable(m.harness);
    await vi.waitFor(() => expect(existe('subida-error-envio')).toBe(true));
    expect(el('subida-error-envio').textContent).toContain('Sin conexión');
    await pulsar(m, 'subida-reintentar');
    expect(intentos).toBe(2);
    expect(existe('subida-error-envio')).toBe(false);
  });

  it('AC_TKT022_03 detalle: ficha, validación previa con foco, guardado que lo deja DISPONIBLE', async () => {
    const pendiente = medio({
      estado: 'PENDIENTE_METADATOS',
      textoAlternativo: null,
      autorCredito: null,
      licencia: null,
      pendientes: ['texto_alternativo', 'autor_credito', 'licencia'],
    });
    const m = await montar('/panel/medios/7', (r) => {
      r.obtener.mockResolvedValue(pendiente);
      r.catalogar.mockResolvedValue(medio());
      r.usos.mockResolvedValue({
        usos: [{ tipoContenido: 'DESTINO', contenidoId: 3, titulo: 'Patagonia', estadoEditorial: 'BORRADOR', rol: 'GALERIA' }],
        pagina: 1,
        totalPaginas: 2,
        total: 60,
      });
    });
    await vi.waitFor(() => expect(existe('medio-formulario')).toBe(true));
    expect(el('medio-ficha').textContent).toContain('2400 × 1600 px');
    expect(el('medio-ficha').textContent).toContain('1,5 MB');
    expect(el('medio-pendientes').textContent).toContain('Falta la licencia');
    await vi.waitFor(() => expect(existe('medio-uso')).toBe(true));
    expect(el('medio-uso').textContent).toContain('Patagonia');
    raiz().querySelector<HTMLButtonElement>('[data-testid="medio-usos"] .paginado button:last-of-type')?.click();
    await estable(m.harness);
    await vi.waitFor(() => expect(m.repo.usos).toHaveBeenLastCalledWith(7, 2));

    escribir('medio-campo-fuente', 'javascript:alert(1)');
    await pulsar(m, 'medio-guardar');
    expect(el('medio-campo-fuente-error').textContent).toContain('http:// o https://');
    expect(document.activeElement).toBe(el('medio-campo-fuente'));
    expect(m.repo.catalogar).not.toHaveBeenCalled();
    escribir('medio-campo-fuente', '');
    await estable(m.harness);
    expect(existe('medio-campo-fuente-error')).toBe(false);

    escribir('medio-campo-alt', 'Lago al amanecer');
    escribir('medio-campo-credito', 'Ana');
    elegir('medio-campo-licencia', '1');
    await pulsar(m, 'medio-guardar');
    expect(m.repo.catalogar).toHaveBeenCalledWith(7, expect.objectContaining({ textoAlternativo: 'Lago al amanecer', licenciaId: 1 }));
    await vi.waitFor(() => expect(el('medio-exito').textContent).toContain('Imagen disponible.'));
    expect(el('medio-estado').textContent).toContain('Disponible');
  });

  it('AC_TKT022_03 errores de la API por campo: 422 bajo la licencia y 400 con errores generales', async () => {
    const m = await montar('/panel/medios/7', (r) => {
      r.obtener.mockResolvedValue(medio({ enUsoPublicado: true }));
      r.catalogar.mockRejectedValueOnce(
        http(422, { code: 'regla_negocio', detail: 'Regla', errors: { licencia_id: ['Licencia incompatible: en uso.'] } }),
      );
      r.catalogar.mockRejectedValueOnce(http(400, { code: 'validacion', detail: 'Datos no válidos', errors: { otro: ['Campo raro'] } }));
    });
    await vi.waitFor(() => expect(existe('medio-formulario')).toBe(true));
    // Retirar bloqueado: en uso por contenido publicado (AC-117).
    expect(el('medio-retirar').getAttribute('aria-disabled')).toBe('true');
    expect(existe('medio-retiro-bloqueado')).toBe(true);
    await pulsar(m, 'medio-retirar');
    expect(el<HTMLDialogElement>('medio-dialogo-retiro').open).toBe(false);

    elegir('medio-campo-licencia', '3');
    await pulsar(m, 'medio-guardar');
    await vi.waitFor(() => expect(existe('medio-campo-licencia-error')).toBe(true));
    expect(el('medio-campo-licencia-error').textContent).toContain('Licencia incompatible');
    expect(el('medio-campo-licencia').getAttribute('aria-invalid')).toBe('true');
    expect(document.activeElement).toBe(el('medio-campo-licencia'));
    elegir('medio-campo-licencia', '1');
    await estable(m.harness);
    expect(existe('medio-campo-licencia-error')).toBe(false);

    await pulsar(m, 'medio-guardar');
    await vi.waitFor(() => expect(existe('medio-errores')).toBe(true));
    expect(el('medio-errores').textContent).toContain('Campo raro');
    expect(document.activeElement).toBe(el('medio-errores'));

    // DISPONIBLE: no se puede vaciar un dato obligatorio (RULE-005).
    escribir('medio-campo-credito', ' ');
    await pulsar(m, 'medio-guardar');
    expect(el('medio-campo-credito-error').textContent).toContain('Obligatorio');
  });

  it('AC_TKT022_03 retirar y reactivar con confirmación; error de la acción; 404 y 403', async () => {
    const m = await montar('/panel/medios/7', (r) => r.retirar.mockRejectedValueOnce(http(409, { code: 'medio_en_uso', detail: 'Está en uso.' })));
    await vi.waitFor(() => expect(existe('medio-retirar')).toBe(true));
    const retirar = el<HTMLButtonElement>('medio-retirar');
    retirar.focus();
    await pulsar(m, 'medio-retirar');
    const dialogo = el<HTMLDialogElement>('medio-dialogo-retiro');
    expect(dialogo.open).toBe(true);
    expect(document.activeElement).toBe(el('medio-dialogo-retiro-cancelar'));
    dialogo.dispatchEvent(new Event('cancel', { cancelable: true }));
    await estable(m.harness);
    expect(dialogo.open).toBe(false);
    expect(document.activeElement).toBe(retirar);

    await pulsar(m, 'medio-retirar');
    await pulsar(m, 'medio-dialogo-retiro-confirmar');
    await vi.waitFor(() => expect(existe('medio-error-accion')).toBe(true));
    expect(el('medio-error-accion').textContent).toContain('Está en uso.');

    await pulsar(m, 'medio-retirar');
    await pulsar(m, 'medio-dialogo-retiro-confirmar');
    await vi.waitFor(() => expect(existe('medio-retirado')).toBe(true));
    expect(existe('medio-formulario')).toBe(false);
    await pulsar(m, 'medio-reactivar');
    await pulsar(m, 'medio-dialogo-reactivar-cancelar');
    expect(el<HTMLDialogElement>('medio-dialogo-reactivar').open).toBe(false);
    await pulsar(m, 'medio-reactivar');
    await pulsar(m, 'medio-dialogo-reactivar-confirmar');
    await vi.waitFor(() => expect(el('medio-estado').textContent).toContain('Pendiente de datos'));
    TestBed.resetTestingModule();

    await montar('/panel/medios/abc');
    expect(existe('panel-no-encontrada')).toBe(true);
    TestBed.resetTestingModule();
    await montar('/panel/medios/7', (r) => r.obtener.mockRejectedValue(http(403, { code: 'permiso_denegado' })));
    await vi.waitFor(() => expect(existe('acceso-denegado')).toBe(true));
    TestBed.resetTestingModule();
    let intentos = 0;
    const fallo = await montar('/panel/medios/7', (r) =>
      r.obtener.mockImplementation(() => (intentos++ === 0 ? Promise.reject(http(500)) : Promise.resolve(medio()))),
    );
    await vi.waitFor(() => expect(existe('medio-error')).toBe(true));
    await pulsar(fallo, 'estado-error-reintentar');
    await vi.waitFor(() => expect(existe('medio-formulario')).toBe(true));
  });

  it('AC_TKT022_04 selector (varios): diálogo modal, foco atrapado, pestañas, selección ordenable y confirmación', async () => {
    const a = medio({ id: 1, tituloInterno: 'Uno' });
    const b = medio({ id: 2, tituloInterno: 'Dos' });
    const pendiente = medio({ id: 3, tituloInterno: 'Tres', estado: 'PENDIENTE_METADATOS' });
    const m = await montar('/panel/desarrollo/selector-medios', (r) =>
      r.listar.mockResolvedValue(pagina([a, b, pendiente], { totalPaginas: 2, total: 60 })),
    );
    const abrir = el<HTMLButtonElement>('banco-abrir-varios');
    abrir.focus();
    await pulsar(m, 'banco-abrir-varios');
    const dialogo = raiz().querySelector<HTMLDialogElement>('[data-testid="selector-medios"][aria-labelledby="banco-varios-titulo"]')!;
    expect(dialogo.open).toBe(true);
    expect(document.activeElement?.id).toBe('banco-varios-q');
    await vi.waitFor(() => expect(dialogo.querySelector('[data-testid="selector-rejilla"]')).not.toBeNull());
    expect(m.repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'DISPONIBLE' }));

    // No disponible: casilla deshabilitada con el motivo.
    const control3 = dialogo.querySelector<HTMLInputElement>('[data-testid="selector-control-3"]')!;
    expect(control3.disabled).toBe(true);
    expect(dialogo.querySelector('#medio-3-motivo')?.textContent).toContain('Completa sus datos');

    dialogo.querySelector<HTMLInputElement>('[data-testid="selector-control-1"]')!.click();
    dialogo.querySelector<HTMLInputElement>('[data-testid="selector-control-2"]')!.click();
    await estable(m.harness);
    expect(dialogo.querySelector('[data-testid="selector-recuento"]')?.textContent).toBe('2 seleccionadas');
    expect(dialogo.querySelector('[data-testid="selector-anadir"]')?.textContent).toContain('Añadir 2 imágenes');

    // Reordenar con «Bajar» y anuncio; quitar.
    dialogo.querySelector<HTMLButtonElement>('#banco-varios-mover-despues-0')!.click();
    await estable(m.harness);
    expect(Array.from(dialogo.querySelectorAll('[data-testid^="selector-elegida-"]')).map((e) => e.getAttribute('data-testid'))).toEqual([
      'selector-elegida-2',
      'selector-elegida-1',
    ]);
    expect(dialogo.querySelector('[data-testid="selector-anuncio"]')?.textContent).toBe('Uno movida a la posición 2 de 2.');
    dialogo.querySelector<HTMLButtonElement>('#banco-varios-mover-antes-0')!.click();
    dialogo.querySelector<HTMLButtonElement>('#banco-varios-mover-despues-1')!.click();
    await estable(m.harness);

    // Foco atrapado: Tab en el último va al primero; Mayús+Tab en el primero, al último.
    const enfocables = Array.from(dialogo.querySelectorAll<HTMLElement>('button, input:not([type=hidden]):not([tabindex="-1"]), select, a[href]')).filter(
      (e) => !e.closest('[hidden]') && !(e as HTMLButtonElement).disabled,
    );
    // jsdom no calcula cajas: getClientRects() vacío; se simula para la prueba.
    for (const e of enfocables) vi.spyOn(e, 'getClientRects').mockReturnValue([{}] as unknown as DOMRectList);
    const ultimo = enfocables[enfocables.length - 1];
    ultimo.focus();
    ultimo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true }));
    expect(document.activeElement).toBe(enfocables[0]);
    enfocables[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true }));
    expect(document.activeElement).toBe(ultimo);
    enfocables[1].focus();
    enfocables[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true }));
    expect(document.activeElement).toBe(enfocables[1]);
    enfocables[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true }));

    // Pestañas con flechas, Inicio y Fin.
    const tab = dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-tab-biblioteca"]')!;
    tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true, cancelable: true }));
    await estable(m.harness);
    expect(dialogo.querySelector('[data-testid="selector-panel-subir"]')?.hasAttribute('hidden')).toBe(false);
    expect(document.activeElement?.id).toBe('banco-varios-tab-subir');
    (document.activeElement as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true, cancelable: true }));
    await estable(m.harness);
    expect(document.activeElement?.id).toBe('banco-varios-tab-biblioteca');
    tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true, cancelable: true }));
    tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true, cancelable: true }));
    tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'x', bubbles: true, cancelable: true }));
    await estable(m.harness);

    // Filtros en memoria y paginación del diálogo.
    const q = dialogo.querySelector<HTMLInputElement>('[data-testid="selector-q"]')!;
    q.value = 'lago';
    q.dispatchEvent(new Event('input'));
    const estado = dialogo.querySelector<HTMLSelectElement>('[data-testid="selector-estado"]')!;
    estado.value = 'no';
    estado.dispatchEvent(new Event('change'));
    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-buscar"]')!.click();
    await estable(m.harness);
    expect(m.repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'lago', estado: null }));
    expect(m.router.url).toBe('/panel/desarrollo/selector-medios');
    await vi.waitFor(() => expect(dialogo.querySelector('[data-testid="selector-siguiente"]')).not.toBeNull());
    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-siguiente"]')!.click();
    await estable(m.harness);
    expect(m.repo.listar).toHaveBeenLastCalledWith(expect.objectContaining({ pagina: 2 }));

    // Añadir: devuelve la selección en el orden de la bandeja, cierra y devuelve el foco.
    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-anadir"]')!.click();
    await estable(m.harness);
    expect(dialogo.open).toBe(false);
    expect(document.activeElement).toBe(abrir);
    expect(el('banco-estado').textContent).toBe('Se eligieron 2 imágenes.');
    expect(el('banco-resultado').textContent).toMatch(/Dos[\s\S]*Uno/);

    // Reabrir con la selección previa; Escape cancela.
    await pulsar(m, 'banco-abrir-varios');
    expect(dialogo.querySelector('[data-testid="selector-recuento"]')?.textContent).toBe('2 seleccionadas');
    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-quitar-2"]')!.click();
    await estable(m.harness);
    expect(dialogo.querySelector('[data-testid="selector-anuncio"]')?.textContent).toBe('Dos quitada de la selección.');
    dialogo.dispatchEvent(new Event('cancel', { cancelable: true }));
    await estable(m.harness);
    expect(dialogo.open).toBe(false);
    expect(el('banco-estado').textContent).toBe('Selección cancelada.');
  });

  it('AC_TKT022_04 selector (uno): radios, subir desde el diálogo y «Usar la existente»', async () => {
    const a = medio({ id: 1, tituloInterno: 'Uno' });
    const duplicado: ResultadoArchivo = {
      nombreArchivo: 'x.png',
      resultado: 'DUPLICADO',
      medio: null,
      medioExistenteId: 1,
      motivo: null,
      local: false,
    };
    const m = await montar('/panel/desarrollo/selector-medios', (r) => {
      r.listar.mockResolvedValue(pagina([a]));
      r.obtener.mockResolvedValueOnce(medio({ id: 4, estado: 'PENDIENTE_METADATOS' })).mockResolvedValue(a);
      r.subir.mockReturnValue(of([duplicado]));
    });
    await pulsar(m, 'banco-abrir-uno');
    const dialogo = raiz().querySelector<HTMLDialogElement>('[data-testid="selector-medios"][aria-labelledby="banco-uno-titulo"]')!;
    await vi.waitFor(() => expect(dialogo.querySelector('[role="radiogroup"]')).not.toBeNull());
    const radio = dialogo.querySelector<HTMLInputElement>('[data-testid="selector-control-1"]')!;
    expect(radio.type).toBe('radio');
    expect(dialogo.querySelector('[data-testid="selector-anadir"]')?.getAttribute('aria-disabled')).toBe('true');

    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-tab-subir"]')!.click();
    await estable(m.harness);
    const entrada = dialogo.querySelector<HTMLInputElement>('[data-testid="subida-archivos"]')!;
    conArchivos(entrada, [archivo('x.png')]);
    await estable(m.harness);
    const usar = dialogo.querySelector<HTMLButtonElement>('[data-testid="subida-usar-existente"]')!;
    usar.click();
    await estable(m.harness);
    await vi.waitFor(() => expect(dialogo.querySelector('[data-testid="selector-error-existente"]')).not.toBeNull());
    usar.click();
    await estable(m.harness);
    await vi.waitFor(() => expect(radio.checked).toBe(true));
    expect(document.activeElement?.id).toBe('banco-uno-tab-biblioteca');
    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-anadir"]')!.click();
    await estable(m.harness);
    expect(el('banco-estado').textContent).toBe('Se eligió 1 imagen.');

    await pulsar(m, 'banco-abrir-uno');
    dialogo.querySelector<HTMLButtonElement>('[data-testid="selector-cerrar"]')!.click();
    await estable(m.harness);
    expect(dialogo.open).toBe(false);
  });

  it('selector: lista vacía lleva a «Subir» y un error del listado se puede reintentar', async () => {
    let intentos = 0;
    const m = await montar('/panel/desarrollo/selector-medios', (r) =>
      r.listar.mockImplementation(() => (intentos++ === 0 ? Promise.reject(http(500)) : Promise.resolve(pagina([])))),
    );
    await pulsar(m, 'banco-abrir-uno');
    await vi.waitFor(() => expect(existe('selector-error')).toBe(true));
    raiz().querySelector<HTMLButtonElement>('[data-testid="selector-error"] [data-testid="estado-error-reintentar"]')!.click();
    await estable(m.harness);
    await vi.waitFor(() => expect(existe('selector-vacio')).toBe(true));
    raiz().querySelector<HTMLButtonElement>('[data-testid="selector-vacio"] button')!.click();
    await estable(m.harness);
    expect(document.activeElement?.id).toBe('banco-uno-tab-subir');
  });

  it('miniaturas: se cargan al acercarse a la pantalla y se reintentan si fallan', async () => {
    const observadores: { cb: IntersectionObserverCallback; desconectado: boolean }[] = [];
    class IOFalso {
      desconectado = false;
      constructor(public cb: IntersectionObserverCallback) {
        observadores.push(this as unknown as { cb: IntersectionObserverCallback; desconectado: boolean });
      }
      observe(): void {
        // Sin efecto: la prueba dispara el callback a mano.
      }
      disconnect(): void {
        this.desconectado = true;
      }
    }
    vi.stubGlobal('IntersectionObserver', IOFalso);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const m = await montar('/panel/medios', (r) => r.listar.mockResolvedValue(pagina([medio()])));
      await vi.waitFor(() => expect(existe('medio-mosaico-7')).toBe(true));
      const mosaico = el('medio-mosaico-7');
      expect(mosaico.querySelector('img')).toBeNull();
      observadores.forEach((o) => o.cb([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver));
      await estable(m.harness);
      const img = mosaico.querySelector('img')!;
      expect(img.getAttribute('src')).toBe('/w/320.webp');
      img.dispatchEvent(new Event('error'));
      await vi.advanceTimersByTimeAsync(1600);
      await estable(m.harness);
      mosaico.querySelector('img')!.dispatchEvent(new Event('error'));
      await vi.advanceTimersByTimeAsync(3100);
      await estable(m.harness);
      mosaico.querySelector('img')!.dispatchEvent(new Event('error'));
      await estable(m.harness);
      expect(mosaico.textContent).toContain('Vista previa no disponible');
    } finally {
      vi.useRealTimers();
      vi.unstubAllGlobals();
    }
  });
});
