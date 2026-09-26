import { Dialog } from '@angular/cdk/dialog';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { MenuMovil } from '../menu-movil/menu-movil';
import { NAVEGACION_PRINCIPAL } from '../navegacion';
import { CabeceraSitio } from './cabecera-sitio';

describe('CabeceraSitio (GI-01)', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  async function crear() {
    const fixture = TestBed.createComponent(CabeceraSitio);
    document.body.appendChild(fixture.nativeElement);
    await fixture.whenStable();
    return { fixture, raiz: fixture.nativeElement as HTMLElement };
  }

  it('logo a Inicio y navegación principal MUST (sin enlaces SHOULD/COULD no implementados, RULE-030)', async () => {
    const { raiz, fixture } = await crear();
    expect(raiz.querySelector('header')).not.toBeNull();
    expect(raiz.querySelector('[data-testid="cabecera-logo"]')?.getAttribute('href')).toBe('/');
    const nav = raiz.querySelector('nav[aria-label="Principal"]') as HTMLElement;
    const enlaces = Array.from(nav.querySelectorAll('a')).map((a) => [a.textContent?.trim(), a.getAttribute('href')]);
    expect(enlaces).toEqual(NAVEGACION_PRINCIPAL.map((e) => [e.etiqueta, e.ruta]));
    expect(raiz.textContent).not.toMatch(/Colecciones|Cuándo ir|Guardados/);
    expect(raiz.querySelector('form[role="search"][data-testid="cabecera-busqueda"]')).not.toBeNull();
    fixture.nativeElement.remove();
  });

  it('botón Buscar despliega la búsqueda enfocada; Esc la cierra y devuelve el foco', async () => {
    const { fixture, raiz } = await crear();
    const boton = raiz.querySelector('[data-testid="cabecera-boton-buscar"]') as HTMLButtonElement;
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    boton.click();
    await fixture.whenStable();
    expect(boton.getAttribute('aria-expanded')).toBe('true');
    const campo = raiz.querySelector('#busqueda-desplegable-campo') as HTMLInputElement;
    expect(document.activeElement).toBe(campo);

    campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await fixture.whenStable();
    expect(raiz.querySelector('#busqueda-desplegable')).toBeNull();
    expect(document.activeElement).toBe(boton);

    // Esc con la búsqueda cerrada no mueve el foco.
    raiz.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    boton.click();
    await fixture.whenStable();
    boton.click();
    await fixture.whenStable();
    expect(raiz.querySelector('#busqueda-desplegable')).toBeNull();
    fixture.nativeElement.remove();
  });

  it('botón Menú abre el cajón modal (CDK Dialog) con retorno del foco', async () => {
    const { raiz, fixture } = await crear();
    const abrir = vi.spyOn(TestBed.inject(Dialog), 'open');
    (raiz.querySelector('[data-testid="cabecera-boton-menu"]') as HTMLButtonElement).click();
    expect(abrir).toHaveBeenCalledWith(
      MenuMovil,
      expect.objectContaining({ ariaLabelledBy: 'menu-movil-titulo', restoreFocus: raiz.querySelector('[data-testid="cabecera-boton-menu"]') }),
    );
    TestBed.inject(Dialog).closeAll();
    fixture.nativeElement.remove();
  });
});

describe('MenuMovil', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([{ path: '**', children: [] }])] }));

  it('muestra búsqueda y navegación principal y se cierra al navegar', async () => {
    const dialogo = TestBed.inject(Dialog);
    const ref = dialogo.open(MenuMovil);
    const cerrar = vi.spyOn(ref, 'close');
    await Promise.resolve();
    TestBed.tick();
    const cajon = document.querySelector('[data-testid="menu-movil"]') as HTMLElement;
    expect(cajon.querySelector('#menu-movil-titulo')?.textContent).toBe('Menú');
    expect(cajon.querySelectorAll('nav a')).toHaveLength(NAVEGACION_PRINCIPAL.length);
    expect(cajon.querySelector('form[role="search"]')).not.toBeNull();

    await TestBed.inject(Router).navigateByUrl('/destinos');
    TestBed.tick();
    expect(cerrar).toHaveBeenCalled();
    dialogo.closeAll();
  });

  it('el botón Cerrar cierra el cajón', async () => {
    const dialogo = TestBed.inject(Dialog);
    const ref = dialogo.open(MenuMovil);
    const cerrar = vi.spyOn(ref, 'close');
    await Promise.resolve();
    TestBed.tick();
    (document.querySelector('[data-testid="menu-movil-cerrar"]') as HTMLButtonElement).click();
    expect(cerrar).toHaveBeenCalled();
    dialogo.closeAll();
  });
});
