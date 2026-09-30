import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ElementoGuardado } from './elemento-guardado.model';
import { GuardadosStore } from './guardados.store';

const DESTINO: ElementoGuardado = { tipo: 'DESTINO', slug: 'patagonia', titulo: 'Patagonia', pais: 'Argentina' };

describe('GuardadosStore', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
  });

  it('inicia con lo que ya hubiera en el almacenamiento', () => {
    localStorage.setItem('bs-guardados-v1', JSON.stringify([DESTINO]));
    const store = TestBed.inject(GuardadosStore);
    expect(store.elementos()).toEqual([DESTINO]);
    expect(store.cantidad()).toBe(1);
  });

  it('guardar / quitar / vaciar actualizan el estado y persisten', () => {
    const store = TestBed.inject(GuardadosStore);
    expect(store.guardar(DESTINO)).toBeNull();
    expect(store.elementos()).toEqual([DESTINO]);

    const otro: ElementoGuardado = { ...DESTINO, slug: 'otro', titulo: 'Otro' };
    store.guardar(otro);
    expect(store.elementos()).toEqual([otro, DESTINO]);

    expect(store.quitar('DESTINO', 'patagonia')).toBeNull();
    expect(store.elementos()).toEqual([otro]);

    expect(store.vaciar()).toBeNull();
    expect(store.elementos()).toEqual([]);

    // Persistido de verdad, no solo en memoria.
    const recreado = TestBed.inject(GuardadosStore);
    expect(recreado.elementos()).toEqual([]);
  });

  it('sin almacenamiento disponible (SSR), los comandos devuelven ErrorApi y no cambian el estado', () => {
    TestBed.overrideProvider(PLATFORM_ID, { useValue: 'server' });
    const store = TestBed.inject(GuardadosStore);
    expect(store.disponible).toBe(false);

    const error = store.guardar(DESTINO);
    expect(error?.categoria).toBe('desconocido');
    expect(store.elementos()).toEqual([]);
    expect(store.quitar('DESTINO', 'patagonia')?.tipo).toBe('guardado_no_disponible');
    expect(store.vaciar()?.tipo).toBe('guardado_no_disponible');
  });
});
