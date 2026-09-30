import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { GuardadosRepositorio } from '../data/guardados.repositorio';
import { GuardadosSorpresaStore } from './guardados-sorpresa.store';

describe('GuardadosSorpresaStore', () => {
  it('navega al destino aleatorio devuelto por el repositorio', async () => {
    const destinoAleatorio = vi.fn().mockResolvedValue('patagonia');
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: GuardadosRepositorio, useValue: { destinoAleatorio } }],
    });
    const store = TestBed.inject(GuardadosSorpresaStore);
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    expect(await store.sorprenderme()).toBeNull();
    expect(navigate).toHaveBeenCalledWith(['/destinos', 'patagonia']);
  });

  it('devuelve ErrorApi si falla la petición', async () => {
    const destinoAleatorio = vi.fn().mockRejectedValue(new Error('sin destinos'));
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: GuardadosRepositorio, useValue: { destinoAleatorio } }],
    });
    const store = TestBed.inject(GuardadosSorpresaStore);
    expect(await store.sorprenderme()).not.toBeNull();
  });
});
