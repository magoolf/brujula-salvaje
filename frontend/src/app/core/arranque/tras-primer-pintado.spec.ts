import {
  ENTRADA_FCP,
  ESPERA_MAXIMA_PINTADO_MS,
  EntornoPintado,
  SELECTOR_RAIZ,
  trasPrimerPintado,
  traeContenidoSsr,
} from './tras-primer-pintado';

interface OpcionesEntorno {
  /** Hijos de <app-root>: 0 = ruta solo cliente; `null` = sin <app-root>. Por defecto 3 (SSR). */
  hijosRaiz?: number | null;
  oculta?: boolean;
  fcpPrevio?: boolean;
  sinObservador?: boolean;
  observadorFalla?: boolean;
}

/** Entorno manual: el FCP, los temporizadores y el observador los dispara la prueba. */
function entornoManual(opciones: OpcionesEntorno = {}) {
  const entradas: string[] = opciones.fcpPrevio ? [ENTRADA_FCP] : [];
  const temporizadores: { cb: () => void; ms: number | undefined }[] = [];
  const observadores: { cb: () => void; tipo?: string; buffered?: boolean; desconectado: boolean }[] = [];
  class ObservadorFalso {
    private readonly registro;
    constructor(cb: () => void) {
      this.registro = { cb, desconectado: false } as (typeof observadores)[number];
      observadores.push(this.registro);
    }
    observe(o: { type: string; buffered?: boolean }): void {
      if (opciones.observadorFalla) throw new TypeError('tipo no soportado');
      this.registro.tipo = o.type;
      this.registro.buffered = o.buffered;
    }
    disconnect(): void {
      this.registro.desconectado = true;
    }
  }
  const entorno: EntornoPintado = {
    document: {
      visibilityState: opciones.oculta ? 'hidden' : 'visible',
      querySelector: (selector) => {
        expect(selector).toBe(SELECTOR_RAIZ);
        const hijos = opciones.hijosRaiz === undefined ? 3 : opciones.hijosRaiz;
        return hijos === null ? null : { childElementCount: hijos };
      },
    },
    performance: { getEntriesByName: (n) => entradas.filter((e) => e === n) },
    PerformanceObserver: opciones.sinObservador ? undefined : ObservadorFalso,
    setTimeout: (cb, ms) => temporizadores.push({ cb, ms }),
  };
  const pintar = (nombre = ENTRADA_FCP) => {
    entradas.push(nombre);
    observadores.forEach((o) => o.cb());
  };
  return { entorno, temporizadores, observadores, pintar };
}

async function estado(promesa: Promise<void>): Promise<'resuelta' | 'pendiente'> {
  return Promise.race([
    promesa.then(() => 'resuelta' as const),
    new Promise<'pendiente'>((r) => queueMicrotask(() => queueMicrotask(() => r('pendiente')))),
  ]);
}

describe('trasPrimerPintado (TKT-056)', () => {
  it('espera al primer pintado con contenido y resuelve en la tarea siguiente', async () => {
    const { entorno, temporizadores, observadores, pintar } = entornoManual();
    const promesa = trasPrimerPintado(entorno);

    expect(observadores).toHaveLength(1);
    expect(observadores[0]).toMatchObject({ tipo: 'paint', buffered: true });
    expect(temporizadores.map((t) => t.ms)).toEqual([ESPERA_MAXIMA_PINTADO_MS]);
    expect(await estado(promesa)).toBe('pendiente');

    // first-paint (sin contenido) no basta.
    pintar('first-paint');
    expect(temporizadores).toHaveLength(1);
    expect(await estado(promesa)).toBe('pendiente');

    pintar();
    expect(temporizadores[1].ms).toBe(0);
    expect(await estado(promesa)).toBe('pendiente');
    temporizadores[1].cb();
    expect(await estado(promesa)).toBe('resuelta');
    expect(observadores[0].desconectado).toBe(true);
    // La espera máxima posterior no tiene efecto.
    temporizadores[0].cb();
  });

  it('resuelve por la espera máxima si el pintado no llega', async () => {
    const { entorno, temporizadores, observadores } = entornoManual();
    const promesa = trasPrimerPintado(entorno, 50);
    expect(temporizadores.map((t) => t.ms)).toEqual([50]);
    temporizadores[0].cb();
    expect(await estado(promesa)).toBe('resuelta');
    expect(observadores[0].desconectado).toBe(true);
  });

  it.each<[string, OpcionesEntorno]>([
    ['la ruta es solo cliente (<app-root> vacío, p. ej. /panel/**; QA F-01)', { hijosRaiz: 0 }],
    ['no hay <app-root>', { hijosRaiz: null }],
    ['el FCP ya ocurrió', { fcpPrevio: true }],
    ['la pestaña está oculta', { oculta: true }],
    ['no hay PerformanceObserver', { sinObservador: true }],
    ['el tipo paint no está soportado', { observadorFalla: true }],
  ])('no espera si %s', async (_caso, opciones) => {
    const { entorno, temporizadores } = entornoManual(opciones);
    const promesa = trasPrimerPintado(entorno);
    expect(temporizadores.map((t) => t.ms)).toEqual([0]);
    temporizadores[0].cb();
    expect(await estado(promesa)).toBe('resuelta');
  });

  it('traeContenidoSsr distingue el HTML del SSR de una raíz vacía (DOM real)', () => {
    const raiz = document.createElement('app-root');
    document.body.appendChild(raiz);
    try {
      expect(traeContenidoSsr(document)).toBe(false);
      raiz.textContent = 'solo texto';
      expect(traeContenidoSsr(document)).toBe(false);
      raiz.appendChild(document.createElement('app-shell-publico'));
      expect(traeContenidoSsr(document)).toBe(true);
    } finally {
      raiz.remove();
    }
  });

  it('funciona con la ventana real del entorno de pruebas', async () => {
    await expect(trasPrimerPintado(window, 20)).resolves.toBeUndefined();
  });
});
