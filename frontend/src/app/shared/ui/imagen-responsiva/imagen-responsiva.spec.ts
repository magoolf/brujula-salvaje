import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import {
  DerivadoImagen,
  ImagenResponsiva,
  construirSrcset,
  elegirSrcRespaldo,
  formatoDeUrl,
  planificarFormatos,
} from './imagen-responsiva';

/** Derivados como los publica el backend (DEC-AUTO-044): 2 anchos × AVIF/WebP/JPEG, AVIF primero. */
const DERIVADOS_3_FORMATOS: readonly DerivadoImagen[] = [
  { url: '/media/publico/derivados/h-400.avif', ancho: 400 },
  { url: '/media/publico/derivados/h-400.webp', ancho: 400 },
  { url: '/media/publico/derivados/h-400.jpeg', ancho: 400 },
  { url: '/media/publico/derivados/h-800.avif', ancho: 800 },
  { url: '/media/publico/derivados/h-800.webp', ancho: 800 },
  { url: '/media/publico/derivados/h-800.jpeg', ancho: 800 },
];

describe('TKT-020: reparto de derivados por formato', () => {
  it('AC_TKT020_01: un <source> tipado por formato eficiente y JPEG como respaldo del <img>', () => {
    const plan = planificarFormatos(DERIVADOS_3_FORMATOS);
    expect(plan.fuentes.map((f) => [f.formato, f.tipo, f.srcset])).toEqual([
      [
        'AVIF',
        'image/avif',
        '/media/publico/derivados/h-400.avif 400w, /media/publico/derivados/h-800.avif 800w',
      ],
      [
        'WEBP',
        'image/webp',
        '/media/publico/derivados/h-400.webp 400w, /media/publico/derivados/h-800.webp 800w',
      ],
    ]);
    expect(construirSrcset(plan.respaldo)).toBe(
      '/media/publico/derivados/h-400.jpeg 400w, /media/publico/derivados/h-800.jpeg 800w',
    );
  });

  it('AC_TKT020_02: AVIF es el primer <source> (el navegador que lo soporta lo elige)', () => {
    expect(planificarFormatos([...DERIVADOS_3_FORMATOS].reverse()).fuentes[0].formato).toBe('AVIF');
  });

  it('el formato explícito prevalece sobre la extensión; extensión desconocida va al <img>', () => {
    const plan = planificarFormatos([
      { url: '/m/sin-extension', ancho: 400, formato: 'AVIF' },
      { url: '/m/x.png', ancho: 400 },
      { url: '/m/y.JPG?v=1', ancho: 800 },
    ]);
    expect(plan.fuentes.map((f) => f.formato)).toEqual(['AVIF']);
    expect(plan.respaldo.map((d) => d.url)).toEqual(['/m/x.png', '/m/y.JPG?v=1']);
  });

  it('sin JPEG ni desconocidos: el <img> lleva el menos exigente (WebP) y no se repite en <source>', () => {
    const soloEficientes = DERIVADOS_3_FORMATOS.filter((d) => !d.url.endsWith('.jpeg'));
    const plan = planificarFormatos(soloEficientes);
    expect(plan.fuentes.map((f) => f.formato)).toEqual(['AVIF']);
    expect(plan.respaldo.every((d) => d.url.endsWith('.webp'))).toBe(true);

    const soloAvif = planificarFormatos([{ url: '/a.avif', ancho: 10 }]);
    expect(soloAvif.fuentes).toEqual([]);
    expect(soloAvif.respaldo.map((d) => d.url)).toEqual(['/a.avif']);
    expect(planificarFormatos([])).toEqual({ fuentes: [], respaldo: [] });
  });

  it('los formatos descartados desaparecen de los <source>, nunca del respaldo', () => {
    const plan = planificarFormatos(DERIVADOS_3_FORMATOS, new Set(['AVIF']));
    expect(plan.fuentes.map((f) => f.formato)).toEqual(['WEBP']);
    expect(plan.respaldo).toHaveLength(2);
  });

  it('formatoDeUrl reconoce avif/webp/jpg/jpeg y devuelve null en el resto', () => {
    expect(formatoDeUrl('/a.avif')).toBe('AVIF');
    expect(formatoDeUrl('/a.WEBP#x')).toBe('WEBP');
    expect(formatoDeUrl('/a.jpg')).toBe('JPEG');
    expect(formatoDeUrl('/a.jpeg')).toBe('JPEG');
    expect(formatoDeUrl('/a.png')).toBeNull();
    expect(formatoDeUrl('/sin-extension')).toBeNull();
  });

  it('elegirSrcRespaldo sustituye un src AVIF/WebP por el JPEG del mismo ancho (o el menor)', () => {
    const plan = planificarFormatos(DERIVADOS_3_FORMATOS);
    expect(
      elegirSrcRespaldo('/media/publico/derivados/h-800.avif', DERIVADOS_3_FORMATOS, plan.respaldo),
    ).toBe('/media/publico/derivados/h-800.jpeg');
    expect(elegirSrcRespaldo('/otra.webp', DERIVADOS_3_FORMATOS, plan.respaldo)).toBe(
      '/media/publico/derivados/h-400.jpeg',
    );
    // Ya es del respaldo, formato del respaldo, formato desconocido o sin respaldo: se respeta.
    expect(
      elegirSrcRespaldo('/media/publico/derivados/h-800.jpeg', DERIVADOS_3_FORMATOS, plan.respaldo),
    ).toBe('/media/publico/derivados/h-800.jpeg');
    expect(elegirSrcRespaldo('/otra.jpg', DERIVADOS_3_FORMATOS, plan.respaldo)).toBe('/otra.jpg');
    expect(elegirSrcRespaldo('/otra', DERIVADOS_3_FORMATOS, plan.respaldo)).toBe('/otra');
    expect(elegirSrcRespaldo('/a.avif', [], [])).toBe('/a.avif');
  });
});

describe('construirSrcset', () => {
  it('ordena por ancho, elimina duplicados e inválidos y codifica la URL', () => {
    expect(
      construirSrcset([
        { url: '/media/publico/a 960.webp', ancho: 960 },
        { url: '/media/publico/a-320.webp', ancho: 320 },
        { url: '/media/publico/dup.webp', ancho: 320 },
        { url: '', ancho: 480 },
        { url: '/x.webp', ancho: 0 },
      ]),
    ).toBe('/media/publico/a-320.webp 320w, /media/publico/a%20960.webp 960w');
    expect(construirSrcset([])).toBe('');
  });
});

/**
 * Espía mínimo de `IntersectionObserver` (TKT-018): jsdom no lo implementa (confirmado al ejecutar
 * la suite sin este espía: el componente detecta `typeof IntersectionObserver === 'undefined'` y
 * degrada a carga inmediata, que es exactamente lo que cubre el primer test de este describe). Este
 * espía existe para poder probar el camino CON soporte: controla manualmente cuándo "interseca".
 */
class IntersectionObserverEspia {
  static instancias: IntersectionObserverEspia[] = [];
  observados: Element[] = [];
  desconectado = false;
  constructor(
    readonly callback: (entradas: Pick<IntersectionObserverEntry, 'isIntersecting'>[]) => void,
    readonly opciones?: IntersectionObserverInit,
  ) {
    IntersectionObserverEspia.instancias.push(this);
  }
  observe(el: Element): void {
    this.observados.push(el);
  }
  disconnect(): void {
    this.desconectado = true;
  }
  simularInterseccion(valor: boolean): void {
    this.callback([{ isIntersecting: valor }]);
  }
}

describe('ImagenResponsiva', () => {
  async function crear(entradas: Record<string, unknown>) {
    const fixture = TestBed.createComponent(ImagenResponsiva);
    for (const [clave, valor] of Object.entries(entradas))
      fixture.componentRef.setInput(clave, valor);
    await fixture.whenStable();
    return fixture;
  }

  it('lazy por defecto, dimensiones reservadas y srcset + sizes', async () => {
    const fixture = await crear({
      src: '/media/publico/a-640.webp',
      alt: 'Glaciar',
      ancho: 640,
      alto: 480,
      derivados: [{ url: '/media/publico/a-320.webp', ancho: 320 }],
      sizes: '50vw',
    });
    const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
    expect(img.getAttribute('loading')).toBe('lazy');
    expect(img.getAttribute('decoding')).toBe('async');
    expect(img.hasAttribute('fetchpriority')).toBe(false);
    expect(img.getAttribute('width')).toBe('640');
    expect(img.getAttribute('height')).toBe('480');
    expect(img.getAttribute('srcset')).toBe('/media/publico/a-320.webp 320w');
    expect(img.getAttribute('sizes')).toBe('50vw');
    expect(img.alt).toBe('Glaciar');
    expect(
      ((fixture.nativeElement as HTMLElement).querySelector('.marco') as HTMLElement).style
        .aspectRatio,
    ).toBe('640 / 480');
  });

  it('imagen LCP: eager + fetchpriority=high, sin srcset si no hay derivados', async () => {
    const fixture = await crear({
      src: '/h.webp',
      alt: 'Portada',
      ancho: 1600,
      alto: 900,
      prioritaria: true,
      relacion: '16 / 9',
    });
    const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
    expect(img.getAttribute('loading')).toBe('eager');
    expect(img.getAttribute('fetchpriority')).toBe('high');
    expect(img.hasAttribute('srcset')).toBe(false);
    expect(img.hasAttribute('sizes')).toBe(false);
  });

  it('si falla la carga conserva el marco y muestra el texto alternativo (ALT-009)', async () => {
    const fixture = await crear({
      src: '/roto.webp',
      alt: 'Laguna al amanecer',
      ancho: 4,
      alto: 3,
    });
    (fixture.nativeElement as HTMLElement).querySelector('img')?.dispatchEvent(new Event('error'));
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('img')).toBeNull();
    expect(raiz.querySelector('[data-testid="imagen-fallida"]')?.textContent).toBe(
      'Laguna al amanecer',
    );
  });

  it('imagen decorativa que falla no muestra texto', async () => {
    const fixture = await crear({ src: '/roto.webp', alt: '', ancho: 4, alto: 3 });
    (fixture.nativeElement as HTMLElement).querySelector('img')?.dispatchEvent(new Event('error'));
    await fixture.whenStable();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('[data-testid="imagen-fallida"]'),
    ).toBeNull();
  });

  describe('TKT-018: petición de red retenida hasta estar cerca del viewport', () => {
    let original: typeof IntersectionObserver | undefined;

    beforeEach(() => {
      original = globalThis.IntersectionObserver;
      IntersectionObserverEspia.instancias = [];
      (globalThis as { IntersectionObserver: unknown }).IntersectionObserver =
        IntersectionObserverEspia;
    });

    afterEach(() => {
      if (original === undefined) {
        delete (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver;
      } else {
        globalThis.IntersectionObserver = original;
      }
    });

    it('no prioritaria decorativa: sin src/srcset hasta que el observer confirma intersección', async () => {
      const fixture = await crear({
        src: '/media/publico/a-640.webp',
        alt: '',
        ancho: 640,
        alto: 480,
        derivados: [{ url: '/media/publico/a-320.webp', ancho: 320 }],
      });
      const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
      // Antes de intersecar: el <img> existe (reserva ancho/alto, CLS 0) pero sin red.
      expect(img).not.toBeNull();
      expect(img.hasAttribute('src')).toBe(false);
      expect(img.hasAttribute('srcset')).toBe(false);
      expect(img.getAttribute('width')).toBe('640');
      expect(img.getAttribute('height')).toBe('480');
      expect(IntersectionObserverEspia.instancias).toHaveLength(1);

      IntersectionObserverEspia.instancias[0].simularInterseccion(true);
      await fixture.whenStable();

      expect(img.getAttribute('src')).toBe('/media/publico/a-640.webp');
      expect(img.getAttribute('srcset')).toBe('/media/publico/a-320.webp 320w');
      expect(IntersectionObserverEspia.instancias[0].desconectado).toBe(true);
    });

    it('usa el margen de pre-carga documentado (TKT-018) como rootMargin', async () => {
      await crear({ src: '/x.webp', alt: '', ancho: 10, alto: 10 });
      expect(IntersectionObserverEspia.instancias[0].opciones?.rootMargin).toBe('300px 0px');
    });

    it('prioritaria: no crea observer, src/srcset disponibles de inmediato', async () => {
      const fixture = await crear({
        src: '/h.webp',
        alt: 'Portada',
        ancho: 1600,
        alto: 900,
        prioritaria: true,
      });
      const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
      expect(img.getAttribute('src')).toBe('/h.webp');
      expect(IntersectionObserverEspia.instancias).toHaveLength(0);
    });

    it('AC_TKT020_01: <picture> con <source type> AVIF y WebP y <img> JPEG del mismo ancho', async () => {
      const fixture = await crear({
        src: '/media/publico/derivados/h-400.avif',
        alt: 'Glaciar',
        ancho: 800,
        alto: 600,
        derivados: DERIVADOS_3_FORMATOS,
        sizes: '50vw',
      });
      const raiz = fixture.nativeElement as HTMLElement;
      const fuentes = [...raiz.querySelectorAll('picture > source')];
      expect(fuentes.map((s) => s.getAttribute('type'))).toEqual(['image/avif', 'image/webp']);
      expect(fuentes[0].getAttribute('srcset')).toBe(
        '/media/publico/derivados/h-400.avif 400w, /media/publico/derivados/h-800.avif 800w',
      );
      expect(fuentes[1].getAttribute('srcset')).toBe(
        '/media/publico/derivados/h-400.webp 400w, /media/publico/derivados/h-800.webp 800w',
      );
      expect(fuentes.every((s) => s.getAttribute('sizes') === '50vw')).toBe(true);
      const img = raiz.querySelector('picture > img') as HTMLImageElement;
      expect(img.getAttribute('src')).toBe('/media/publico/derivados/h-400.jpeg');
      expect(img.getAttribute('srcset')).toBe(
        '/media/publico/derivados/h-400.jpeg 400w, /media/publico/derivados/h-800.jpeg 800w',
      );
      expect(img.getAttribute('sizes')).toBe('50vw');
    });

    it('AC_TKT020_03: informativa (alt no vacío) emite src/srcset de inmediato, sin esperar al observer', async () => {
      const fixture = await crear({
        src: '/media/publico/derivados/h-400.jpeg',
        alt: 'Laguna al amanecer',
        ancho: 800,
        alto: 600,
        derivados: DERIVADOS_3_FORMATOS,
      });
      const raiz = fixture.nativeElement as HTMLElement;
      const img = raiz.querySelector('img') as HTMLImageElement;
      expect(img.getAttribute('src')).toBe('/media/publico/derivados/h-400.jpeg');
      expect(img.getAttribute('loading')).toBe('lazy');
      expect(raiz.querySelector('source')?.hasAttribute('srcset')).toBe(true);
      expect(IntersectionObserverEspia.instancias[0].observados).toHaveLength(1);
    });

    it('AC_TKT020_04: decorativa no prioritaria sigue diferida también en sus <source>', async () => {
      const fixture = await crear({
        src: '/media/publico/derivados/h-400.avif',
        alt: '',
        ancho: 800,
        alto: 600,
        derivados: DERIVADOS_3_FORMATOS,
      });
      const raiz = fixture.nativeElement as HTMLElement;
      const nodos = [...raiz.querySelectorAll('source, img')];
      expect(nodos).toHaveLength(3);
      expect(nodos.some((n) => n.hasAttribute('srcset') || n.hasAttribute('src'))).toBe(false);

      IntersectionObserverEspia.instancias[0].simularInterseccion(true);
      await fixture.whenStable();
      expect(nodos.every((n) => n.hasAttribute('srcset'))).toBe(true);
    });

    it('AC_TKT020_04: la prioritaria (LCP) conserva fetchpriority=high y no se difiere', async () => {
      const fixture = await crear({
        src: '/media/publico/derivados/h-800.avif',
        alt: '',
        ancho: 800,
        alto: 600,
        derivados: DERIVADOS_3_FORMATOS,
        prioritaria: true,
      });
      const raiz = fixture.nativeElement as HTMLElement;
      const img = raiz.querySelector('img') as HTMLImageElement;
      expect(img.getAttribute('fetchpriority')).toBe('high');
      expect(img.getAttribute('loading')).toBe('eager');
      expect(img.getAttribute('src')).toBe('/media/publico/derivados/h-800.jpeg');
      expect(raiz.querySelector('source[type="image/avif"]')?.hasAttribute('srcset')).toBe(true);
      expect(IntersectionObserverEspia.instancias).toHaveLength(0);
    });
  });

  describe('AC_TKT020_06: alFallar solo actúa cuando fallan todos los formatos', () => {
    function fallarCon(fixture: Awaited<ReturnType<typeof crear>>, currentSrc: string) {
      const img = (fixture.nativeElement as HTMLElement).querySelector('img') as HTMLImageElement;
      Object.defineProperty(img, 'currentSrc', { configurable: true, value: currentSrc });
      img.dispatchEvent(new Event('error'));
      return fixture.whenStable();
    }
    const tipos = (fixture: Awaited<ReturnType<typeof crear>>) =>
      [...(fixture.nativeElement as HTMLElement).querySelectorAll('source')].map((s) =>
        s.getAttribute('type'),
      );
    const entradas = {
      src: '/media/publico/derivados/h-400.avif',
      alt: 'Laguna al amanecer',
      ancho: 800,
      alto: 600,
      derivados: DERIVADOS_3_FORMATOS,
    };

    it('AC_TKT020_06: AVIF falla -> se descarta su <source>; luego WebP; solo el JPEG fallido muestra el alternativo', async () => {
      const fixture = await crear(entradas);
      const raiz = fixture.nativeElement as HTMLElement;

      await fallarCon(fixture, 'http://localhost/media/publico/derivados/h-800.avif');
      expect(tipos(fixture)).toEqual(['image/webp']);
      expect(raiz.querySelector('img')).not.toBeNull();
      expect(raiz.querySelector('[data-testid="imagen-fallida"]')).toBeNull();

      await fallarCon(fixture, 'http://localhost/media/publico/derivados/h-400.webp');
      expect(tipos(fixture)).toEqual([]);
      expect(raiz.querySelector('img')).not.toBeNull();

      await fallarCon(fixture, 'http://localhost/media/publico/derivados/h-400.jpeg');
      expect(raiz.querySelector('img')).toBeNull();
      expect(raiz.querySelector('[data-testid="imagen-fallida"]')?.textContent).toBe(
        'Laguna al amanecer',
      );
    });

    it('AC_TKT020_06: si el que falla es el respaldo (los <source> no eran soportados), fallo definitivo', async () => {
      const fixture = await crear(entradas);
      await fallarCon(fixture, 'http://localhost/media/publico/derivados/h-800.jpeg');
      expect((fixture.nativeElement as HTMLElement).querySelector('img')).toBeNull();
    });

    it('AC_TKT020_06: sin currentSrc conocido descarta el primer <source> restante', async () => {
      const fixture = await crear(entradas);
      await fallarCon(fixture, '');
      expect(tipos(fixture)).toEqual(['image/webp']);
      expect((fixture.nativeElement as HTMLElement).querySelector('img')).not.toBeNull();
    });
  });

  describe('AC_TKT020_03: HTML del servidor (SSR, sin JavaScript)', () => {
    beforeEach(() => {
      TestBed.configureTestingModule({ providers: [{ provide: PLATFORM_ID, useValue: 'server' }] });
    });

    it('AC_TKT020_03: en el servidor la informativa lleva src y la decorativa no', async () => {
      const informativa = await crear({
        src: '/media/publico/derivados/h-400.avif',
        alt: 'Miniatura con crédito',
        ancho: 64,
        alto: 64,
      });
      const imgInformativa = (informativa.nativeElement as HTMLElement).querySelector('img');
      expect(imgInformativa?.getAttribute('src')).toBe('/media/publico/derivados/h-400.avif');

      const decorativa = await crear({
        src: '/media/publico/derivados/h-400.avif',
        alt: '',
        ancho: 64,
        alto: 64,
      });
      const imgDecorativa = (decorativa.nativeElement as HTMLElement).querySelector('img');
      expect(imgDecorativa?.hasAttribute('src')).toBe(false);
    });
  });
});
