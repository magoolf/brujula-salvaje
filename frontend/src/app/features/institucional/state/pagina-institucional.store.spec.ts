import { TransferState, makeStateKey } from '@angular/core';
import { provideClientHydration } from '@angular/platform-browser';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { InstitucionalRepositorio } from '../data/institucional.repositorio';
import { ConfiguracionVista, EscalasVista, PaginaInstitucionalVista } from '../domain/modelos';
import { PaginaInstitucionalStore } from './pagina-institucional.store';

const PAGINA = { slug: 'acerca-de', titulo: 'Acerca de' } as PaginaInstitucionalVista;
const ESCALAS: EscalasVista = { dificultad: [], presupuesto: [] };
const CONFIGURACION = {
  nombreMarca: 'Brújula Salvaje',
  lema: null,
  textoDescargo: 'x',
  responsable: { definido: false, nombre: null, identificacion: null, domicilio: null, canalAtencion: null },
} as ConfiguracionVista;

describe('PaginaInstitucionalStore', () => {
  function crear(slug: string) {
    const data$ = new BehaviorSubject({ slug });
    const pagina = vi.fn().mockResolvedValue(PAGINA);
    const escalas = vi.fn().mockResolvedValue(ESCALAS);
    const configuracion = vi.fn().mockResolvedValue(CONFIGURACION);
    TestBed.configureTestingModule({
      providers: [
        PaginaInstitucionalStore,
        { provide: ActivatedRoute, useValue: { data: data$ } },
        { provide: InstitucionalRepositorio, useValue: { pagina, escalas, configuracion } },
      ],
    });
    return { store: TestBed.inject(PaginaInstitucionalStore), pagina, escalas, configuracion };
  }

  it('carga la página según el slug de los datos de ruta', async () => {
    const { store, pagina } = crear('acerca-de');
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    expect(pagina).toHaveBeenCalledWith('acerca-de');
  });

  it('carga siempre escalas y configuración (bajo coste, la UI decide qué mostrar)', async () => {
    const { store, escalas, configuracion } = crear('aviso-legal');
    await vi.waitFor(() => expect(store.escalas()).not.toBeNull());
    expect(escalas).toHaveBeenCalled();
    await vi.waitFor(() => expect(store.configuracion()).not.toBeNull());
    expect(configuracion).toHaveBeenCalled();
  });

  it('recargar() vuelve a pedir la página', async () => {
    const { store, pagina } = crear('acerca-de');
    await vi.waitFor(() => expect(store.pagina()).not.toBeNull());
    store.recargar();
    await vi.waitFor(() => expect(pagina).toHaveBeenCalledTimes(2));
  });
});

/**
 * TKT-016 (Skill_UI_UX §47.2): el recurso transfiere el valor del SSR con una clave que incluye
 * los parámetros de la URL. Se comprueba que nace resuelto al hidratar la misma URL y que nunca
 * reutiliza un valor transferido de otra URL, tampoco en la navegación posterior en el cliente.
 */
describe('PaginaInstitucionalStore — hidratación con TransferState (TKT-016)', () => {
  const SSR = { origen: 'ssr' };
  const RED = { origen: 'red' };

  function crearHidratado(transferidos: Readonly<Record<string, unknown>>) {
    const ruta$ = new BehaviorSubject({ slug: 'acerca-de' });
    const pagina = vi.fn().mockResolvedValue(RED);
    TestBed.configureTestingModule({
      providers: [
        PaginaInstitucionalStore,
        provideClientHydration(),
        { provide: ActivatedRoute, useValue: { data: ruta$ } },
        { provide: InstitucionalRepositorio, useValue: { pagina, escalas: vi.fn().mockResolvedValue(ESCALAS), configuracion: vi.fn().mockResolvedValue(CONFIGURACION) } },
      ],
    });
    const estado = TestBed.inject(TransferState);
    for (const [clave, valor] of Object.entries(transferidos)) estado.set(makeStateKey(clave), valor);
    return { store: TestBed.inject(PaginaInstitucionalStore), ruta$, pagina };
  }

  it('AC_TKT016_06 nace resuelto con el valor del SSR de la misma URL y no lo vuelve a pedir', () => {
    const { store, pagina } = crearHidratado({ ['recurso:pagina-institucional:acerca-de']: SSR });
    expect(store.pagina()).toEqual(SSR);
    TestBed.tick();
    expect(pagina).not.toHaveBeenCalled();
  });

  it('AC_TKT016_06 no reutiliza un valor transferido de otra URL, ni al navegar después en el cliente', async () => {
    const { store, ruta$, pagina } = crearHidratado({ ['recurso:pagina-institucional:aviso-legal']: SSR });
    await vi.waitFor(() => expect(store.pagina()).toEqual(RED));
    expect(pagina).toHaveBeenCalledWith('acerca-de');
    pagina.mockResolvedValue({ origen: 'red-2' });
    ruta$.next({ slug: 'aviso-legal' });
    await vi.waitFor(() => expect(store.pagina()).toEqual({ origen: 'red-2' }));
    expect(pagina).toHaveBeenLastCalledWith('aviso-legal');
  });
});
