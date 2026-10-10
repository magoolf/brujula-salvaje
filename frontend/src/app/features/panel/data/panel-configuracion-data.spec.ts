import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { ConfigInicioPanel } from '../../../api/models/config-inicio-panel';
import { Cuenta } from '../../../api/models/cuenta';
import { FILTROS_AUDITORIA_VACIOS } from '../domain/auditoria';
import { PanelContenidosRepositorio } from './panel-contenidos.repositorio';
import { mapConfigInicio, mapEscalas, mapLicenciaCatalogo, mapPais, mapRegion } from './configuracion.mapper';
import { aCambioDto, mapCuenta, mapEvento, paramsAuditoria } from './cuentas.mapper';
import { PanelConfiguracionRepositorio } from './panel-configuracion.repositorio';
import { PanelCuentasRepositorio } from './panel-cuentas.repositorio';

const BASE = '/api/v1/panel';

function pagina<T>(resultados: T[], extra: Record<string, unknown> = {}) {
  return { resultados, pagina: 1, total_paginas: 1, total: resultados.length, tamano_pagina: 100, anterior: null, siguiente: null, ...extra };
}

export const INICIO_DTO: ConfigInicioPanel = {
  hero_titular: 'Aventura',
  hero_subtitulo: 'Sub',
  hero_medio_id: 9,
  destinos_ids: [1, 2],
  itinerarios_ids: [3],
  guias_ids: [4],
  actualizado_en: '2026-10-01T10:00:00Z',
  actualizado_por: { id: 5, etiqueta: 'ana' },
  referencias: {
    medios: [{ id: 9, estado: 'DISPONIBLE', url_miniatura: '/m/9.webp', texto_alternativo: 'Cima' }],
    contenidos: [
      { id: 1, tipo: 'DESTINO', titulo: 'Cocora', estado_editorial: 'PUBLICADO', slug: 'cocora' },
      { id: 3, tipo: 'ITINERARIO', titulo: 'Ruta', estado_editorial: 'RETIRADO' },
      { id: 4, tipo: 'GUIA', titulo: 'Guía', estado_editorial: 'PUBLICADO' },
    ],
  },
};

export const CUENTA_DTO: Cuenta = {
  id: 5,
  usuario: 'ana',
  nombre_visible: 'Ana',
  etiqueta: 'ana',
  rol: 'EDITOR',
  estado: 'ACTIVA',
  mfa_activo: true,
  debe_cambiar_credencial: false,
  ultimo_acceso_en: '2026-10-09T10:00:00Z',
  creado_en: '2026-09-01T10:00:00Z',
};

describe('configuracion.mapper y cuentas.mapper (contrato → dominio)', () => {
  it('AC_TKT024_02 destacados: referencias de contenidos y medio; huecos sin referencia', () => {
    const config = mapConfigInicio(INICIO_DTO);
    expect(config.medio).toEqual({ id: 9, estado: 'DISPONIBLE', miniatura: '/m/9.webp', textoAlternativo: 'Cima' });
    expect(config.destinos).toEqual([
      { id: 1, tipo: 'DESTINO', titulo: 'Cocora', estado: 'PUBLICADO', slug: 'cocora' },
      { id: 2, tipo: 'DESTINO', titulo: '#2', estado: null },
    ]);
    expect(config.itinerarios[0].estado).toBe('RETIRADO');
    expect(config.actualizadoPor).toBe('ana');
    const vacio = mapConfigInicio({ actualizado_en: '2026-10-01T10:00:00Z', actualizado_por: { id: null, etiqueta: 'sistema' }, referencias: {} });
    expect(vacio).toMatchObject({ titular: '', subtitulo: '', medio: null, destinos: [], itinerarios: [], guias: [] });
    expect(mapConfigInicio({ ...INICIO_DTO, referencias: {} }).medio).toEqual({ id: 9, estado: null, miniatura: null, textoAlternativo: null });
  });

  it('taxonomías con valores por omisión', () => {
    expect(mapRegion({ id: 1 })).toEqual({ catalogo: 'regiones', id: 1, nombre: 'Región #1', slug: '', continente: 'AMERICA', orden: 0, activo: true });
    expect(mapPais({ id: 2, activo: false })).toMatchObject({ nombre: 'País #2', codigoIso2: '', regionId: 0, activo: false });
    expect(mapLicenciaCatalogo({ id: 3 })).toMatchObject({ nombre: 'Licencia #3', requiereAtribucion: true, compatiblePublicacion: false, urlTextoLegal: null });
    const nivel = (n: number, escala: 'DIFICULTAD' | 'PRESUPUESTO') => ({ id: n, nivel: n, escala, etiqueta: `N${n}`, descripcion: 'd' });
    expect(mapEscalas({ dificultad: [nivel(2, 'DIFICULTAD'), nivel(1, 'DIFICULTAD')], presupuesto: [] }).dificultad.map((n) => n.nivel)).toEqual([1, 2]);
  });

  it('cuentas y eventos con nulos; cambios parciales; parámetros de la auditoría', () => {
    expect(mapCuenta({ ...CUENTA_DTO, usuario: undefined, nombre_visible: undefined, ultimo_acceso_en: null, desactivado_en: '2026-10-02T00:00:00Z' })).toMatchObject({
      usuario: null,
      nombreVisible: null,
      ultimoAccesoEn: null,
    });
    expect(aCambioDto({ rol: 'ADMINISTRADOR' })).toEqual({ rol: 'ADMINISTRADOR' });
    expect(aCambioDto({ nombreVisible: 'B' })).toEqual({ nombre_visible: 'B' });
    expect(mapEvento({ id: 1, ocurrido_en: '2026-10-10T20:05:00Z', actor: { id: null, etiqueta: 'sistema' }, accion: 'LOGIN_OK', resultado: 'EXITO' })).toMatchObject({
      actorId: null,
      tipoEntidad: null,
      camposCambiados: [],
      ipTruncada: null,
    });
    expect(paramsAuditoria(FILTROS_AUDITORIA_VACIOS)).toEqual({});
    expect(paramsAuditoria({ desde: '2026-10-01', hasta: '2026-10-02', actor: 5, accion: 'EDITAR', tipo: 'DESTINO', pagina: 2 })).toEqual({
      desde: '2026-10-01T00:00:00-05:00',
      hasta: '2026-10-02T23:59:59.999-05:00',
      actor_id: 5,
      accion: 'EDITAR',
      tipo_entidad: 'DESTINO',
      pagina: 2,
    });
  });
});

describe('repositorios de configuración y cuentas (cliente generado)', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: ApiConfiguration, useValue: { rootUrl: '' } }],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('AC_TKT024_02 / AC_TKT024_10 inicio y configuración: lectura y escritura', async () => {
    const repo = TestBed.inject(PanelConfiguracionRepositorio);
    const inicio = repo.inicio();
    http.expectOne(`${BASE}/inicio`).flush(INICIO_DTO);
    expect((await inicio).titular).toBe('Aventura');

    const guardar = repo.guardarInicio({ titular: 'T', subtitulo: 'S', medioId: 9, destinosIds: [1], itinerariosIds: [2], guiasIds: [3] });
    const put = http.expectOne(`${BASE}/inicio`);
    expect(put.request.method).toBe('PUT');
    expect(put.request.body).toEqual({ hero_titular: 'T', hero_subtitulo: 'S', hero_medio_id: 9, destinos_ids: [1], itinerarios_ids: [2], guias_ids: [3] });
    put.flush(INICIO_DTO);
    await guardar;

    const config = repo.configuracion();
    http.expectOne(`${BASE}/configuracion`).flush({ nombre_marca: 'M', texto_descargo: 'D', actualizado_en: '2026-10-01T10:00:00Z' });
    expect(await config).toMatchObject({ nombreMarca: 'M', lema: null, responsableNombre: null });

    const guardarConfig = repo.guardarConfiguracion({
      nombreMarca: 'M',
      lema: null,
      textoDescargo: 'D',
      responsableNombre: 'R',
      responsableIdentificacion: null,
      responsableDomicilio: null,
      responsableCanalAtencion: null,
    });
    const putConfig = http.expectOne(`${BASE}/configuracion`);
    expect(putConfig.request.body).toMatchObject({ nombre_marca: 'M', lema: null, responsable_nombre: 'R' });
    putConfig.flush({ nombre_marca: 'M', texto_descargo: 'D', responsable_nombre: 'R', actualizado_en: '2026-10-02T10:00:00Z' });
    expect((await guardarConfig).responsableNombre).toBe('R');
  });

  it('AC_TKT024_04 taxonomías: listar (todas las páginas), crear y actualizar cada catálogo; escalas', async () => {
    const repo = TestBed.inject(PanelConfiguracionRepositorio);
    const regiones = repo.listar('regiones');
    http.expectOne((r) => r.url === `${BASE}/taxonomias/regiones` && !r.params.has('pagina')).flush(pagina([{ id: 1, nombre: 'A' }], { total_paginas: 2, siguiente: '/x?pagina=2' }));
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne((r) => r.url === `${BASE}/taxonomias/regiones` && r.params.get('pagina') === '2').flush(pagina([{ id: 2, nombre: 'B' }], { pagina: 2, total_paginas: 2 }));
    expect((await regiones).map((r) => r.id)).toEqual([1, 2]);

    for (const [catalogo, ruta] of [
      ['paises', 'paises'],
      ['categorias', 'categorias-guia'],
      ['licencias', 'licencias'],
    ] as const) {
      const lista = repo.listar(catalogo);
      http.expectOne(`${BASE}/taxonomias/${ruta}`).flush(pagina([{ id: 7 }]));
      expect((await lista)[0].catalogo).toBe(catalogo);
    }

    const casos = [
      { entrada: { catalogo: 'regiones', nombre: 'A', slug: 'a', continente: 'ASIA', orden: 1, activo: true }, ruta: 'regiones', cuerpo: { nombre: 'A', slug: 'a', continente: 'ASIA', orden: 1, activo: true } },
      { entrada: { catalogo: 'paises', nombre: 'P', slug: 'p', codigoIso2: 'PE', regionId: 1, activo: true }, ruta: 'paises', cuerpo: { nombre: 'P', slug: 'p', codigo_iso2: 'PE', region_id: 1, activo: true } },
      { entrada: { catalogo: 'categorias', nombre: 'C', slug: 'c', descripcion: 'd', orden: 0, activo: true }, ruta: 'categorias-guia', cuerpo: { nombre: 'C', slug: 'c', descripcion: 'd', orden: 0, activo: true } },
      {
        entrada: { catalogo: 'licencias', codigo: 'CC0', nombre: 'L', urlTextoLegal: null, requiereAtribucion: false, compatiblePublicacion: true, activo: true },
        ruta: 'licencias',
        cuerpo: { codigo: 'CC0', nombre: 'L', url_texto_legal: null, requiere_atribucion: false, compatible_publicacion: true, activo: true },
      },
    ] as const;
    for (const caso of casos) {
      const crear = repo.crear(caso.entrada);
      const post = http.expectOne(`${BASE}/taxonomias/${caso.ruta}`);
      expect(post.request.method).toBe('POST');
      expect(post.request.body).toEqual(caso.cuerpo);
      post.flush({ id: 10, ...caso.cuerpo });
      expect((await crear).id).toBe(10);
      const actualizar = repo.actualizar(10, { ...caso.entrada, activo: false });
      const put = http.expectOne(`${BASE}/taxonomias/${caso.ruta}/10`);
      expect(put.request.method).toBe('PUT');
      expect((put.request.body as { activo: boolean }).activo).toBe(false);
      put.flush({ id: 10, ...caso.cuerpo, activo: false });
      expect((await actualizar).activo).toBe(false);
    }

    const escalas = repo.escalas();
    http.expectOne(`${BASE}/taxonomias/escalas`).flush({ dificultad: [], presupuesto: [] });
    expect(await escalas).toEqual({ dificultad: [], presupuesto: [] });
    const nivel = repo.actualizarNivel(3, { etiqueta: 'E', descripcion: 'D' });
    const putNivel = http.expectOne(`${BASE}/taxonomias/escalas/3`);
    expect(putNivel.request.body).toEqual({ etiqueta: 'E', descripcion: 'D' });
    putNivel.flush({ id: 3, nivel: 2, escala: 'DIFICULTAD', etiqueta: 'E', descripcion: 'D' });
    expect((await nivel).nivel).toBe(2);
  });

  it('AC_TKT024_06 / AC_TKT024_07 cuentas: listado, admins activos, alta con Idempotency-Key, cambios y acciones', async () => {
    const repo = TestBed.inject(PanelCuentasRepositorio);
    const listado = repo.listar(2);
    const get = http.expectOne((r) => r.url === `${BASE}/cuentas`);
    expect(get.request.params.get('pagina')).toBe('2');
    get.flush(pagina([CUENTA_DTO], { pagina: 2, total_paginas: 2, total: 51 }));
    expect(await listado).toMatchObject({ pagina: 2, total: 51 });
    const primera = repo.listar(1);
    const getPrimera = http.expectOne((r) => r.url === `${BASE}/cuentas`);
    expect(getPrimera.request.params.has('pagina')).toBe(false);
    getPrimera.flush(pagina([]));
    await primera;

    const admins = repo.administradoresActivos();
    const getAdmins = http.expectOne((r) => r.url === `${BASE}/cuentas`);
    expect(getAdmins.request.params.get('estado')).toBe('ACTIVA');
    expect(getAdmins.request.params.get('rol')).toBe('ADMINISTRADOR');
    getAdmins.flush(pagina([], { total: 2 }));
    expect(await admins).toBe(2);

    const obtener = repo.obtener(5);
    http.expectOne(`${BASE}/cuentas/5`).flush(CUENTA_DTO);
    expect((await obtener).usuario).toBe('ana');

    const crear = repo.crear({ usuario: 'bea', nombreVisible: 'Bea', rol: 'EDITOR' }, 'clave-1');
    const post = http.expectOne(`${BASE}/cuentas`);
    expect(post.request.headers.get('Idempotency-Key')).toBe('clave-1');
    expect(post.request.body).toEqual({ usuario: 'bea', nombre_visible: 'Bea', rol: 'EDITOR' });
    post.flush({ cuenta: { ...CUENTA_DTO, id: 6, usuario: 'bea' }, contrasena_temporal: 'temporal-123456789' });
    expect(await crear).toMatchObject({ contrasenaTemporal: 'temporal-123456789', cuenta: { id: 6 } });

    const actualizar = repo.actualizar(5, { rol: 'ADMINISTRADOR' });
    const patch = http.expectOne(`${BASE}/cuentas/5`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ rol: 'ADMINISTRADOR' });
    patch.flush({ ...CUENTA_DTO, rol: 'ADMINISTRADOR' });
    expect((await actualizar).rol).toBe('ADMINISTRADOR');

    for (const [accion, ruta, conSecreto] of [
      ['restablecerContrasena', 'restablecer-contrasena', true],
      ['restablecerMfa', 'restablecer-mfa', true],
      ['reactivar', 'reactivar', true],
      ['desactivar', 'desactivar', false],
      ['anonimizar', 'anonimizar', false],
    ] as const) {
      const resultado = repo.ejecutarAccion(5, accion);
      const peticion = http.expectOne(`${BASE}/cuentas/5/${ruta}`);
      expect(peticion.request.method).toBe('POST');
      peticion.flush(conSecreto ? { cuenta: CUENTA_DTO, contrasena_temporal: 'otra-temporal-12345' } : CUENTA_DTO);
      expect((await resultado).contrasenaTemporal).toBe(conSecreto ? 'otra-temporal-12345' : null);
    }
  });

  it('AC_TKT024_09 auditoría con filtros y actores de todas las páginas, ordenados', async () => {
    const repo = TestBed.inject(PanelCuentasRepositorio);
    const auditoria = repo.auditoria({ ...FILTROS_AUDITORIA_VACIOS, accion: 'CONFIG_INICIO' });
    const get = http.expectOne((r) => r.url === `${BASE}/auditoria`);
    expect(get.request.params.get('accion')).toBe('CONFIG_INICIO');
    get.flush(pagina([{ id: 1, ocurrido_en: '2026-10-10T20:05:00Z', actor: { id: 5, etiqueta: 'ana' }, accion: 'CONFIG_INICIO', resultado: 'EXITO' }]));
    expect((await auditoria).eventos[0].accion).toBe('CONFIG_INICIO');

    const actores = repo.actores();
    http.expectOne((r) => r.url === `${BASE}/cuentas` && !r.params.has('pagina')).flush(pagina([{ ...CUENTA_DTO, id: 1, etiqueta: 'zoe' }], { total_paginas: 2, siguiente: '/x?pagina=2' }));
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne((r) => r.url === `${BASE}/cuentas` && r.params.get('pagina') === '2').flush(pagina([{ ...CUENTA_DTO, id: 2, etiqueta: 'álvaro' }], { pagina: 2, total_paginas: 2 }));
    expect(await actores).toEqual([
      { id: 2, etiqueta: 'álvaro' },
      { id: 1, etiqueta: 'zoe' },
    ]);
  });

  it('la búsqueda de destacados usa el listado de contenido publicado', async () => {
    const repo = TestBed.inject(PanelContenidosRepositorio);
    const buscar = repo.buscar(['GUIA'], 'agua', 'PUBLICADO');
    const get = http.expectOne((r) => r.url === `${BASE}/contenidos/guias`);
    expect(get.request.params.get('estado')).toBe('PUBLICADO');
    get.flush(pagina([]));
    expect(await buscar).toEqual([]);
  });
});
