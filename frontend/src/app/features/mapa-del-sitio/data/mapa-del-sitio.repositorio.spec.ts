import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { PLATFORM_ID, TransferState, makeStateKey } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { MAX_PAGINAS, MapaDelSitioRepositorio } from './mapa-del-sitio.repositorio';

function meta(pagina: number, totalPaginas: number) {
  return { anterior: null, siguiente: null, pagina, tamano_pagina: 1, total: totalPaginas, total_paginas: totalPaginas };
}

const MESES = { meses: [{ mes: 1, nombre: 'Enero', slug: 'enero', numero_destinos: 2, destacado: null }] };

describe('MapaDelSitioRepositorio', () => {
  let http: HttpTestingController;
  let repo: MapaDelSitioRepositorio;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    repo = TestBed.inject(MapaDelSitioRepositorio);
  });

  afterEach(() => http.verify());

  async function tick(): Promise<void> {
    await new Promise((r) => setTimeout(r, 0));
  }

  it('AC_TKT019_03 compone índice (todas sus páginas), meses y glosario (todas sus páginas)', async () => {
    const promesa = repo.obtener();

    const indice1 = http.expectOne((r) => r.url === '/api/v1/publico/indice' && !r.params.has('pagina'));
    indice1.flush({
      ...meta(1, 2),
      resultados: [{ tipo: 'DESTINO', slug: 'a', titulo: 'A', agrupacion: null, publicado_actualizado_en: 'x' }],
    });
    http.expectOne('/api/v1/publico/meses').flush(MESES);
    const glosario1 = http.expectOne((r) => r.url === '/api/v1/publico/glosario' && !r.params.has('pagina'));
    glosario1.flush({ ...meta(1, 2), resultados: [{ slug: 'g1', termino: 'G1', definicion: '', usado_en: [] }] });
    await tick();

    http
      .expectOne((r) => r.url === '/api/v1/publico/indice' && r.params.get('pagina') === '2')
      .flush({
        ...meta(2, 2),
        resultados: [{ tipo: 'TIPO', slug: 'b', titulo: 'B', publicado_actualizado_en: 'x' }],
      });
    http
      .expectOne((r) => r.url === '/api/v1/publico/glosario' && r.params.get('pagina') === '2')
      .flush({ ...meta(2, 2), resultados: [{ slug: 'g2', termino: 'G2', definicion: '', usado_en: [] }] });

    const datos = await promesa;
    expect(datos.entradas.map((e) => e.slug)).toEqual(['a', 'b']);
    expect(datos.meses).toEqual([{ numero: 1, slug: 'enero', nombre: 'Enero', numeroDestinos: 2 }]);
    expect(datos.terminos).toEqual([
      { slug: 'g1', termino: 'G1', pagina: 1 },
      { slug: 'g2', termino: 'G2', pagina: 2 },
    ]);
  });

  it('no pide más páginas si total_paginas es 0 o 1', async () => {
    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/indice').flush({ ...meta(1, 0), resultados: [] });
    http.expectOne('/api/v1/publico/meses').flush({ meses: [] });
    http.expectOne('/api/v1/publico/glosario').flush({ ...meta(1, 1), resultados: [] });
    const datos = await promesa;
    expect(datos).toEqual({ entradas: [], meses: [], terminos: [] });
  });

  it('limita las páginas pedidas a MAX_PAGINAS', async () => {
    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/indice').flush({ ...meta(1, MAX_PAGINAS + 5), resultados: [] });
    http.expectOne('/api/v1/publico/meses').flush({ meses: [] });
    http.expectOne('/api/v1/publico/glosario').flush({ ...meta(1, 1), resultados: [] });
    await tick();
    const resto = http.match((r) => r.url === '/api/v1/publico/indice');
    expect(resto).toHaveLength(MAX_PAGINAS - 1);
    for (const peticion of resto) peticion.flush({ ...meta(2, MAX_PAGINAS + 5), resultados: [] });
    await promesa;
  });

  it('AC_TKT019_07 propaga el error si falla el índice', async () => {
    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/indice').flush({}, { status: 500, statusText: 'Error' });
    http.expectOne('/api/v1/publico/meses').flush({ meses: [] });
    http.expectOne('/api/v1/publico/glosario').flush({ ...meta(1, 1), resultados: [] });
    await expect(promesa).rejects.toBeTruthy();
  });

  it('AC_TKT019_06 reutiliza una sola vez los datos transferidos por el SSR (sin petición)', async () => {
    const transferencia = TestBed.inject(TransferState);
    const clave = makeStateKey<unknown>('publico-mapa-del-sitio');
    const datos = { entradas: [], meses: [], terminos: [] };
    transferencia.set(clave, datos);
    expect(repo.datosTransferidos()).toEqual(datos);
    expect(await repo.obtener()).toEqual(datos);
    expect(repo.datosTransferidos()).toBeNull();
  });
});

describe('MapaDelSitioRepositorio en el servidor', () => {
  it('guarda los datos en TransferState para la hidratación', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
        { provide: PLATFORM_ID, useValue: 'server' },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const repo = TestBed.inject(MapaDelSitioRepositorio);
    const promesa = repo.obtener();
    http.expectOne('/api/v1/publico/indice').flush({ ...meta(1, 1), resultados: [] });
    http.expectOne('/api/v1/publico/meses').flush({ meses: [] });
    http.expectOne('/api/v1/publico/glosario').flush({ ...meta(1, 1), resultados: [] });
    await promesa;
    expect(repo.datosTransferidos()).toEqual({ entradas: [], meses: [], terminos: [] });
    http.verify();
  });
});
