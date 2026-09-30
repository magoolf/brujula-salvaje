import { TestBed } from '@angular/core/testing';

import { Compartir } from './compartir';

function definirNavigatorShare(impl: ((datos: ShareData) => Promise<void>) | undefined): void {
  Object.defineProperty(window.navigator, 'share', { value: impl, configurable: true });
}

function definirClipboard(impl: { writeText: (texto: string) => Promise<void> } | undefined): void {
  Object.defineProperty(window.navigator, 'clipboard', { value: impl, configurable: true });
}

describe('Compartir', () => {
  afterEach(() => {
    definirNavigatorShare(undefined);
    definirClipboard(undefined);
  });

  it('usa la función nativa cuando existe', async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    definirNavigatorShare(share);
    const servicio = TestBed.inject(Compartir);

    expect(servicio.soportaNativo()).toBe(true);
    const resultado = await servicio.compartir({ titulo: 'Patagonia', url: 'https://x/destinos/patagonia' });
    expect(resultado).toEqual({ error: null, via: 'nativo' });
    expect(share).toHaveBeenCalledWith({
      title: 'Patagonia',
      text: undefined,
      url: 'https://x/destinos/patagonia',
    });
  });

  it('cancelar el share nativo (AbortError) no es un error', async () => {
    definirNavigatorShare(vi.fn().mockRejectedValue(new DOMException('cancelado', 'AbortError')));
    const servicio = TestBed.inject(Compartir);
    const resultado = await servicio.compartir({ titulo: 'x', url: 'https://x' });
    expect(resultado).toEqual({ error: null, via: 'cancelado' });
  });

  it('sin función nativa, copia al portapapeles', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    definirClipboard({ writeText });
    const servicio = TestBed.inject(Compartir);

    expect(servicio.soportaNativo()).toBe(false);
    const resultado = await servicio.compartir({ titulo: 'x', url: 'https://x/y' });
    expect(resultado).toEqual({ error: null, via: 'portapapeles' });
    expect(writeText).toHaveBeenCalledWith('https://x/y');
  });

  it('si el share nativo falla por otra razón, cae al portapapeles', async () => {
    definirNavigatorShare(vi.fn().mockRejectedValue(new Error('fallo desconocido')));
    const writeText = vi.fn().mockResolvedValue(undefined);
    definirClipboard({ writeText });
    const servicio = TestBed.inject(Compartir);

    const resultado = await servicio.compartir({ titulo: 'x', url: 'https://x/y' });
    expect(resultado.via).toBe('portapapeles');
  });

  it('sin función nativa ni portapapeles, devuelve error', async () => {
    const servicio = TestBed.inject(Compartir);
    const resultado = await servicio.compartir({ titulo: 'x', url: 'https://x' });
    expect(resultado.error?.tipo).toBe('compartir_no_disponible');
  });

  it('si falla la copia al portapapeles, devuelve error', async () => {
    definirClipboard({ writeText: vi.fn().mockRejectedValue(new Error('denegado')) });
    const servicio = TestBed.inject(Compartir);
    const resultado = await servicio.compartir({ titulo: 'x', url: 'https://x' });
    expect(resultado.error?.tipo).toBe('compartir_no_disponible');
  });
});
