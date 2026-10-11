import {
  PLAZO_REPOSO_MS,
  RESPALDO_SIN_REPOSO_MS,
  precargadorDe,
  precargarEnReposo,
} from './precarga-en-reposo';

describe('precargadorDe (TKT-056, QA F-02)', () => {
  it('comparte una única carga entre llamadas', async () => {
    const cargar = vi.fn(() => Promise.resolve({ modulo: 1 }));
    const precargar = precargadorDe(cargar);
    const [a, b] = await Promise.all([precargar(), precargar()]);
    expect(a).toBe(b);
    await precargar();
    expect(cargar).toHaveBeenCalledTimes(1);
  });

  it('un fallo no queda cacheado: el siguiente intento vuelve a cargar', async () => {
    const cargar = vi
      .fn<() => Promise<string>>()
      .mockRejectedValueOnce(new TypeError('red'))
      .mockResolvedValueOnce('ok');
    const precargar = precargadorDe(cargar);
    await expect(precargar()).rejects.toThrow('red');
    await expect(precargar()).resolves.toBe('ok');
    expect(cargar).toHaveBeenCalledTimes(2);
  });
});

describe('precargarEnReposo (TKT-056, QA F-02)', () => {
  it('usa requestIdleCallback con plazo máximo e ignora el error de la precarga', async () => {
    const reposo: { cb: () => void; opciones?: { timeout: number } }[] = [];
    const setTimeout = vi.fn();
    const precargar = vi.fn(() => Promise.reject(new Error('sin red')));
    precargarEnReposo(
      { requestIdleCallback: (cb, opciones) => reposo.push({ cb, opciones }), setTimeout },
      precargar,
    );
    expect(precargar).not.toHaveBeenCalled();
    expect(reposo[0].opciones).toEqual({ timeout: PLAZO_REPOSO_MS });
    expect(setTimeout).not.toHaveBeenCalled();
    reposo[0].cb();
    expect(precargar).toHaveBeenCalledTimes(1);
    await Promise.resolve();
  });

  it('sin requestIdleCallback (Safari) espera con setTimeout', () => {
    const temporizadores: { cb: () => void; ms?: number }[] = [];
    const precargar = vi.fn(() => Promise.resolve());
    precargarEnReposo({ setTimeout: (cb, ms) => temporizadores.push({ cb, ms }) }, precargar);
    expect(temporizadores[0].ms).toBe(RESPALDO_SIN_REPOSO_MS);
    temporizadores[0].cb();
    expect(precargar).toHaveBeenCalledTimes(1);
  });
});
