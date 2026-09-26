import { DOCUMENT } from '@angular/common';
import { CSP_NONCE, REQUEST, RESPONSE_INIT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router, provideRouter } from '@angular/router';

import { migasDePanJsonLd, serializarJsonLd, sitioWebJsonLd, urlAbsoluta } from './datos-estructurados';
import { EstadoHttp } from './estado-http';
import { EstrategiaTitulo } from './estrategia-titulo';
import { Seo, tituloConMarca } from './seo';

describe('Seo (FEAT-027)', () => {
  function configurar(peticion: Request | null = null, nonce: string | null = null): { seo: Seo; doc: Document } {
    TestBed.configureTestingModule({
      providers: [
        { provide: REQUEST, useValue: peticion },
        { provide: CSP_NONCE, useValue: nonce },
      ],
    });
    return { seo: TestBed.inject(Seo), doc: TestBed.inject(DOCUMENT) };
  }

  afterEach(() => {
    const doc = TestBed.inject(DOCUMENT);
    doc.head.querySelectorAll('#bs-canonica, #bs-json-ld, meta[name], meta[property]').forEach((n) => n.remove());
  });

  it('fija title, description, canónica absoluta, Open Graph y JSON-LD con nonce', () => {
    const { seo, doc } = configurar(new Request('http://127.0.0.1:8080/destinos/patagonia?x=1'), 'abcdef0123456789abcdef');
    seo.establecer({
      titulo: 'Patagonia',
      descripcion: 'Glaciares y montañas.',
      imagen: { url: '/media/publico/p.webp', alt: 'Torres del Paine' },
      tipoOg: 'article',
      datosEstructurados: { '@type': 'TouristDestination', name: 'Patagonia </script><script>alert(1)</script>' },
    });

    expect(doc.title).toBe('Patagonia — Brújula Salvaje');
    expect(doc.head.querySelector('meta[name="description"]')?.getAttribute('content')).toBe('Glaciares y montañas.');
    expect(doc.head.querySelector('#bs-canonica')?.getAttribute('href')).toBe('http://127.0.0.1:8080/destinos/patagonia');
    expect(doc.head.querySelector('meta[property="og:url"]')?.getAttribute('content')).toBe('http://127.0.0.1:8080/destinos/patagonia');
    expect(doc.head.querySelector('meta[property="og:type"]')?.getAttribute('content')).toBe('article');
    expect(doc.head.querySelector('meta[property="og:locale"]')?.getAttribute('content')).toBe('es_CO');
    expect(doc.head.querySelector('meta[property="og:image"]')?.getAttribute('content')).toBe('http://127.0.0.1:8080/media/publico/p.webp');
    expect(doc.head.querySelector('meta[name="twitter:card"]')?.getAttribute('content')).toBe('summary_large_image');
    expect(doc.head.querySelector('meta[name="robots"]')).toBeNull();

    const jsonLd = doc.head.querySelector('#bs-json-ld');
    expect(jsonLd?.getAttribute('type')).toBe('application/ld+json');
    expect(jsonLd?.getAttribute('nonce')).toBe('abcdef0123456789abcdef');
    expect(jsonLd?.textContent).not.toContain('</script>');
    expect(JSON.parse(jsonLd?.textContent ?? '{}').name).toContain('</script>');
  });

  it('las vistas no indexables llevan noindex, sin canónica y reemplazan el JSON-LD previo', () => {
    const { seo, doc } = configurar();
    seo.establecer({ titulo: 'Inicio', datosEstructurados: { '@type': 'WebSite' } });
    expect(doc.head.querySelectorAll('#bs-json-ld')).toHaveLength(1);
    expect(doc.head.querySelector('#bs-canonica')).not.toBeNull();

    seo.establecer({ titulo: 'Página no encontrada', indexable: false });
    expect(doc.head.querySelector('meta[name="robots"]')?.getAttribute('content')).toBe('noindex, nofollow');
    expect(doc.head.querySelector('#bs-canonica')).toBeNull();
    expect(doc.head.querySelector('#bs-json-ld')).toBeNull();
    expect(doc.head.querySelector('meta[name="description"]')).toBeNull();
    expect(doc.head.querySelector('meta[name="twitter:card"]')?.getAttribute('content')).toBe('summary');
  });

  it('en el navegador usa el origen y la ruta del documento', () => {
    const { seo } = configurar();
    expect(seo.origen()).toBe(TestBed.inject(DOCUMENT).location.origin);
    expect(seo.rutaActual()).toBe(TestBed.inject(DOCUMENT).location.pathname);
  });

  it('tituloConMarca no duplica la marca', () => {
    expect(tituloConMarca('Brújula Salvaje')).toBe('Brújula Salvaje');
    expect(tituloConMarca('  ')).toBe('Brújula Salvaje');
    expect(tituloConMarca('Guías')).toBe('Guías — Brújula Salvaje');
  });
});

describe('EstadoHttp', () => {
  it('fija el código de la respuesta del SSR', () => {
    const respuesta: { status?: number } = {};
    TestBed.configureTestingModule({ providers: [{ provide: RESPONSE_INIT, useValue: respuesta }] });
    TestBed.inject(EstadoHttp).establecer(410);
    expect(respuesta.status).toBe(410);
  });

  it('no hace nada en el navegador', () => {
    TestBed.configureTestingModule({});
    expect(() => TestBed.inject(EstadoHttp).establecer(404)).not.toThrow();
  });
});

describe('EstrategiaTitulo', () => {
  it('añade la marca al title de la ruta', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'guias', title: 'Guías', children: [] }]),
        { provide: EstrategiaTitulo, useClass: EstrategiaTitulo },
      ],
    });
    const router = TestBed.inject(Router);
    const estrategia = TestBed.inject(EstrategiaTitulo);
    await router.navigateByUrl('/guias');
    estrategia.updateTitle(router.routerState.snapshot);
    expect(TestBed.inject(Title).getTitle()).toBe('Guías — Brújula Salvaje');
  });
});

describe('datos estructurados', () => {
  it('BreadcrumbList con posiciones y URL absolutas', () => {
    expect(
      migasDePanJsonLd('https://ejemplo.co/', [
        { etiqueta: 'Inicio', ruta: '/' },
        { etiqueta: 'Destinos', ruta: 'destinos?pagina=2' },
      ]),
    ).toEqual({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://ejemplo.co/' },
        { '@type': 'ListItem', position: 2, name: 'Destinos', item: 'https://ejemplo.co/destinos' },
      ],
    });
  });

  it('WebSite con SearchAction hacia /buscar', () => {
    const datos = sitioWebJsonLd('https://ejemplo.co', 'Brújula Salvaje', 'es-CO');
    expect(datos['url']).toBe('https://ejemplo.co/');
    expect(JSON.stringify(datos)).toContain('https://ejemplo.co/buscar?q={consulta}');
  });

  it('serializarJsonLd escapa <, >, & y separadores de línea', () => {
    const texto = serializarJsonLd({ a: '<b>&  ' });
    expect(texto).toBe('{"a":"\\u003cb\\u003e\\u0026\\u2028\\u2029"}');
    expect(JSON.parse(texto)).toEqual({ a: '<b>&  ' });
    expect(urlAbsoluta('https://e.co', '#x')).toBe('https://e.co/');
  });
});
