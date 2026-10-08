import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';

import { ErrorApi } from '../../../core/http/error-api.model';
import { construirSecciones } from '../domain/mapa-del-sitio';
import { SeccionMapa } from '../domain/modelos';
import { MapaDelSitioStore } from '../state/mapa-del-sitio.store';
import { PaginaMapaDelSitio } from './pagina-mapa-del-sitio';

const SECCIONES = construirSecciones({
  entradas: [
    { tipo: 'DESTINO', slug: 'cocuy', titulo: 'El Cocuy', agrupacion: { slug: 'andes', nombre: 'Andes' } },
    { tipo: 'GUIA', slug: 'mochila', titulo: 'Mochila', agrupacion: { slug: 'equipo', nombre: 'Equipo' } },
    { tipo: 'CATEGORIA_GUIA', slug: 'equipo', titulo: 'Equipo', agrupacion: null },
  ],
  meses: [],
  terminos: [{ slug: 'vivac', termino: 'Vivac', pagina: 2 }],
});

function montar(estado: { secciones: readonly SeccionMapa[] | null; error?: ErrorApi | null }) {
  const recargar = vi.fn();
  const store = {
    secciones: signal(estado.secciones),
    error: signal(estado.error ?? null),
    total: signal(5),
    cargando: signal(estado.secciones === null),
    recargar,
  };
  TestBed.configureTestingModule({
    imports: [PaginaMapaDelSitio],
    providers: [provideRouter([])],
  });
  TestBed.overrideComponent(PaginaMapaDelSitio, {
    set: { providers: [{ provide: MapaDelSitioStore, useValue: store }] },
  });
  const fixture = TestBed.createComponent(PaginaMapaDelSitio);
  fixture.detectChanges();
  return { fixture, el: fixture.nativeElement as HTMLElement, recargar };
}

describe('PaginaMapaDelSitio', () => {
  it('AC_TKT019_01 fija el título SEO y un único h1', () => {
    const { el } = montar({ secciones: SECCIONES });
    expect(TestBed.inject(Title).getTitle()).toContain('Mapa del sitio');
    expect(el.querySelectorAll('h1')).toHaveLength(1);
  });

  it('AC_TKT019_02 pinta una sección h2 por cada sección y el índice interno', () => {
    const { el } = montar({ secciones: SECCIONES });
    const h2 = [...el.querySelectorAll('h2')].map((h) => h.textContent?.trim());
    expect(h2).toEqual(SECCIONES.map((s) => s.titulo));
    expect(el.querySelectorAll('[data-testid="mapa-indice"] a')).toHaveLength(SECCIONES.length);
    expect(el.querySelector('[data-testid="mapa-indice"] a')?.getAttribute('href')).toBe('#seccion-general');
  });

  it('AC_TKT019_03 enlaza destinos bajo su región (h3) y la categoría de guías', () => {
    const { el } = montar({ secciones: SECCIONES });
    const region = el.querySelector('[data-testid="mapa-grupo-destinos-andes"]');
    expect(region?.querySelector('h3')?.textContent?.trim()).toBe('Andes');
    expect(region?.querySelector('a')?.getAttribute('href')).toBe('/destinos/cocuy');
    const categoria = el.querySelector('[data-testid="mapa-grupo-guias-equipo"] h3 a');
    expect(categoria?.getAttribute('href')).toBe('/guias/categoria/equipo');
  });

  it('AC_TKT019_03 los términos llevan página y ancla', () => {
    const { el } = montar({ secciones: SECCIONES });
    const termino = el.querySelector('[data-testid="mapa-grupo-glosario-terminos"] a');
    expect(termino?.getAttribute('href')).toBe('/glosario?pagina=2#vivac');
  });

  it('AC_TKT019_07 muestra el esqueleto mientras carga', () => {
    const { el } = montar({ secciones: null });
    expect(el.querySelector('app-estado-cargando')).not.toBeNull();
    expect(el.querySelector('h2')).toBeNull();
  });

  it('AC_TKT019_07 muestra el error con reintento', () => {
    const { el, recargar } = montar({
      secciones: null,
      error: { tipo: 'servidor', mensaje: 'Algo falló', campos: {}, traceId: null } as unknown as ErrorApi,
    });
    expect(el.textContent).toContain('Algo falló');
    el.querySelector('app-estado-error button')?.dispatchEvent(new Event('click'));
    expect(recargar).toHaveBeenCalled();
  });
});
