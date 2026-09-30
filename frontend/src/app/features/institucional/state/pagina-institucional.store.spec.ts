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
