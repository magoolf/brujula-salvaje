import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import {
  DESTINO_REGISTRO_ERRORES,
  ManejadorErroresGlobal,
  RegistroError,
  rutaSinParametros,
  sanearTexto,
} from './manejador-errores.handler';
import { VERSION_APP } from './version-app';

describe('ManejadorErroresGlobal (§27.5)', () => {
  let registros: RegistroError[];
  let manejador: ManejadorErroresGlobal;

  beforeEach(() => {
    registros = [];
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        ManejadorErroresGlobal,
        { provide: DESTINO_REGISTRO_ERRORES, useValue: (r: RegistroError) => registros.push(r) },
      ],
    });
    manejador = TestBed.inject(ManejadorErroresGlobal);
    vi.spyOn(TestBed.inject(Router), 'url', 'get').mockReturnValue('/buscar?q=juan.perez@correo.co#r');
  });

  it('registra traceId, ruta sin parámetros y versión, sin PII', () => {
    manejador.handleError(new Error('Fallo al cargar /buscar?q=juan.perez@correo.co con tel 3001234567'));
    expect(registros).toEqual([
      {
        evento: 'error_no_controlado',
        nombre: 'Error',
        mensaje: 'Fallo al cargar /buscar?[omitido] con tel [numero]',
        traceId: null,
        ruta: '/buscar',
        version: VERSION_APP,
      },
    ]);
    expect(JSON.stringify(registros)).not.toContain('juan.perez');
  });

  it('extrae el trace_id de un error HTTP con Problem Details', () => {
    manejador.handleError(
      new HttpErrorResponse({ status: 500, error: { code: 'error_interno', trace_id: '4bf92f3577b34da6a3ce929d0e0e4736' } }),
    );
    expect(registros[0].traceId).toBe('4bf92f3577b34da6a3ce929d0e0e4736');
  });

  it('acepta valores lanzados que no son Error', () => {
    manejador.handleError('texto');
    expect(registros[0]).toMatchObject({ nombre: 'string', mensaje: '' });
  });

  it('el destino por defecto escribe en consola', () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [provideRouter([]), ManejadorErroresGlobal] });
    const consola = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    TestBed.inject(ManejadorErroresGlobal).handleError(new Error('x'));
    expect(consola).toHaveBeenCalledOnce();
    consola.mockRestore();
  });
});

describe('saneado', () => {
  it('sanearTexto elimina correos, query strings y números largos, y limita la longitud', () => {
    expect(sanearTexto('a@b.co ?x=1 123456')).toBe('[correo] ?[omitido] [numero]');
    expect(sanearTexto('x'.repeat(500))).toHaveLength(300);
  });

  it('rutaSinParametros', () => {
    expect(rutaSinParametros('/destinos?pagina=2#top')).toBe('/destinos');
    expect(rutaSinParametros('?q=1')).toBe('/');
  });
});
