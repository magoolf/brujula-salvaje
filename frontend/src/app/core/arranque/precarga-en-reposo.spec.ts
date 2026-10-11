import {
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

describe('precargarEnReposo (TKT-056, QA c2 F-03)', () => {
  type Entorno = Parameters<typeof precargarEnReposo>[0];

  function entorno(readyState: DocumentReadyState, conReposo = true) {
    const alCargar: { cb: () => void; opciones?: { once: boolean } }[] = [];
    const reposo: { cb: () => void; args: unknown[] }[] = [];
    const temporizadores: { cb: () => void; ms?: number }[] = [];
    const e: Entorno = {
      document: { readyState },
      addEventListener: (_tipo, cb, opciones) => alCargar.push({ cb, opciones }),
      setTimeout: (cb, ms) => temporizadores.push({ cb, ms }),
    };
    if (conReposo) {
      e.requestIdleCallback = (cb: () => void, ...args: unknown[]) => reposo.push({ cb, args });
    }
    return { e, alCargar, reposo, temporizadores };
  }

  it('antes de load no programa nada: espera al evento load y luego al reposo SIN plazo', () => {
    const { e, alCargar, reposo, temporizadores } = entorno('interactive');
    const precargar = vi.fn(() => Promise.resolve());
    precargarEnReposo(e, precargar);
    expect(reposo).toHaveLength(0);
    expect(alCargar).toHaveLength(1);
    expect(alCargar[0].opciones).toEqual({ once: true });
    alCargar[0].cb();
    expect(precargar).not.toHaveBeenCalled();
    expect(reposo).toHaveLength(1);
    // Sin `timeout`: si el hilo no queda ocioso, no se fuerza la precarga dentro de FCP→TTI.
    expect(reposo[0].args).toEqual([]);
    expect(temporizadores).toHaveLength(0);
    reposo[0].cb();
    expect(precargar).toHaveBeenCalledTimes(1);
  });

  it('con la página ya cargada va directo al reposo e ignora el error de la precarga', async () => {
    const { e, alCargar, reposo } = entorno('complete');
    const precargar = vi.fn(() => Promise.reject(new Error('sin red')));
    precargarEnReposo(e, precargar);
    expect(alCargar).toHaveLength(0);
    reposo[0].cb();
    expect(precargar).toHaveBeenCalledTimes(1);
    await Promise.resolve();
  });

  it('sin requestIdleCallback (Safari) espera con setTimeout tras load', () => {
    const { e, alCargar, temporizadores } = entorno('loading', false);
    const precargar = vi.fn(() => Promise.resolve());
    precargarEnReposo(e, precargar);
    expect(temporizadores).toHaveLength(0);
    alCargar[0].cb();
    expect(temporizadores[0].ms).toBe(RESPALDO_SIN_REPOSO_MS);
    temporizadores[0].cb();
    expect(precargar).toHaveBeenCalledTimes(1);
  });
});
