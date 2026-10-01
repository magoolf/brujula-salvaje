import { Component, ErrorHandler, LOCALE_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, TitleStrategy, provideRouter } from '@angular/router';

import { App } from './app';
import { appConfig } from './app.config';
import { routes } from './app.routes';
import { esZonaPanel } from './core/layout/shell-publico/zona';
import { ManejadorErroresGlobal } from './core/observabilidad/manejador-errores.handler';
import { EstrategiaTitulo } from './core/seo/estrategia-titulo';

describe('App (shell global)', () => {
  it('en el sitio público: ShellPublico (SkipLink → cabecera → main → pie) + aviso sin conexión', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
    const fixture = TestBed.createComponent(App);
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/acerca-de');
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;

    const hijos = Array.from(raiz.children).map((e) => e.tagName.toLowerCase());
    expect(hijos).toEqual(['app-shell-publico', 'app-banner-sin-conexion']);
    const shell = raiz.querySelector('app-shell-publico') as HTMLElement;
    expect(Array.from(shell.children).map((e) => e.tagName.toLowerCase())).toEqual([
      'app-skip-link',
      'app-cabecera-sitio',
      'main',
      'app-pie-sitio',
    ]);
    const main = raiz.querySelector('main') as HTMLElement;
    expect(main.id).toBe('contenido-principal');
    expect(main.getAttribute('tabindex')).toBe('-1');
    expect(raiz.querySelector('[data-testid="skip-link"]')?.getAttribute('href')).toBe(
      '#contenido-principal',
    );
    expect(raiz.querySelector('header')).not.toBeNull();
    expect(raiz.querySelector('footer')).not.toBeNull();
    expect(document.documentElement.getAttribute('data-app-lista')).toBe('true');
  });

  it('las rutas iniciales resuelven la raíz y el comodín 404 con títulos', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
    const fixture = TestBed.createComponent(App);
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/');
    await fixture.whenStable();
    // TKT-008: la raíz ahora resuelve a features/inicio (PaginaInicio), no al antiguo placeholder
    // pagina-en-preparacion. Esta prueba unitaria no tiene backend real (a diferencia del e2e
    // contra el stack de compose.yaml), así que PaginaInicio puede quedar en su estado de error de
    // red (ST-ERROR: "No pudimos cargar esta sección") en vez del bloque principal con datos; por
    // eso se comprueba la presencia del componente de la ruta real, no un testid que depende de una
    // respuesta de red exitosa (mismo criterio ya aplicado en e2e/shell.spec.ts para este caso).
    expect((fixture.nativeElement as HTMLElement).querySelector('app-pagina-inicio')).not.toBeNull();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('[data-testid="pagina-no-encontrada"]'),
    ).toBeNull();
    await router.navigateByUrl('/ruta/que-no-existe');
    await fixture.whenStable();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('[data-testid="pagina-no-encontrada"]'),
    ).not.toBeNull();
    // TKT-010 (QA ciclo 1, FALLO-02/OBS-04): rutas planas, sin ruta de layout; comodín al final.
    expect(routes.at(-1)?.path).toBe('**');
    expect(routes.some((r) => r.children !== undefined || r.component !== undefined)).toBe(false);
  });

  it('TKT-010: /panel carga en diferido el panel editorial, fuera del shell público', async () => {
    expect(routes[0].path).toBe('panel');
    const cargar = routes[0].loadChildren as () => Promise<unknown>;
    const { RUTAS_PANEL } = await import('./features/panel/ui/panel.routes');
    expect(await cargar()).toBe(RUTAS_PANEL);
  });

  it('la configuración es zoneless (sin zone.js) y registra los proveedores transversales', () => {
    TestBed.configureTestingModule({ providers: appConfig.providers });
    expect((globalThis as { Zone?: unknown }).Zone).toBeUndefined();
    expect(TestBed.inject(ErrorHandler)).toBeInstanceOf(ManejadorErroresGlobal);
    expect(TestBed.inject(TitleStrategy)).toBeInstanceOf(EstrategiaTitulo);
    expect(TestBed.inject(LOCALE_ID)).toBe('es-CO');
  });

  it('TKT-010: en /panel/** no hay chrome público y al volver al sitio reaparece', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'panel/prueba', component: VistaPrueba },
          { path: '', component: VistaPrueba },
        ]),
      ],
    });
    const fixture = TestBed.createComponent(App);
    const router = TestBed.inject(Router);
    const raiz = fixture.nativeElement as HTMLElement;
    await router.navigateByUrl('/panel/prueba');
    await fixture.whenStable();
    expect(raiz.querySelector('app-shell-publico')).toBeNull();
    expect(raiz.querySelector('header')).toBeNull();
    expect(raiz.querySelector('[data-testid="vista-prueba"]')).not.toBeNull();
    await router.navigateByUrl('/');
    await fixture.whenStable();
    expect(raiz.querySelector('app-shell-publico main [data-testid="vista-prueba"]')).not.toBeNull();
  });

  it('TKT-010: zona del panel por URL', () => {
    expect(esZonaPanel('/panel')).toBe(true);
    expect(esZonaPanel('/panel/acceso?siguiente=%2Fpanel')).toBe(true);
    expect(esZonaPanel('/panelx')).toBe(false);
    expect(esZonaPanel('/')).toBe(false);
    expect(esZonaPanel('/destinos#panel')).toBe(false);
  });
});

@Component({ selector: 'app-vista-prueba', template: '<p data-testid="vista-prueba">vista</p>' })
class VistaPrueba {}
