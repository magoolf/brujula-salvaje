import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiConfiguration } from '../../../api/api-configuration';
import { GuardadosRepositorio } from './guardados.repositorio';

describe('GuardadosRepositorio', () => {
  it('destinoAleatorio() llama a /publico/destinos/aleatorio', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiConfiguration, useValue: { rootUrl: '' } },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const repo = TestBed.inject(GuardadosRepositorio);

    const promesa = repo.destinoAleatorio();
    http.expectOne('/api/v1/publico/destinos/aleatorio').flush({ slug: 'patagonia' });
    expect(await promesa).toBe('patagonia');
    http.verify();
  });
});
