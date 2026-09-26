import { ErrorHandler, LOCALE_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, TitleStrategy, provideRouter } from '@angular/router';

import { App } from './app';
import { appConfig } from './app.config';
import { routes } from './app.routes';
import { ManejadorErroresGlobal } from './core/observabilidad/manejador-errores.handler';
import { EstrategiaTitulo } from './core/seo/estrategia-titulo';

describe('App (shell global)', () => {
  it('SkipLink → cabecera → main#contenido-principal → pie, con landmarks', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter(routes)] });
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;

    const hijos = Array.from(raiz.children).map((e) => e.tagName.toLowerCase());
    expect(hijos).toEqual(['app-skip-link', 'app-cabecera-sitio', 'main', 'app-pie-sitio', 'app-banner-sin-conexion']);
    const main = raiz.querySelector('main') as HTMLElement;
    expect(main.id).toBe('contenido-principal');
    expect(main.getAttribute('tabindex')).toBe('-1');
    expect(raiz.querySelector('[data-testid="skip-link"]')?.getAttribute('href')).toBe('#contenido-principal');
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
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="pagina-en-preparacion"]')).not.toBeNull();
    await router.navigateByUrl('/ruta/que-no-existe');
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="pagina-no-encontrada"]')).not.toBeNull();
    expect(routes.at(-1)?.path).toBe('**');
  });

  it('la configuración es zoneless (sin zone.js) y registra los proveedores transversales', () => {
    TestBed.configureTestingModule({ providers: appConfig.providers });
    expect((globalThis as { Zone?: unknown }).Zone).toBeUndefined();
    expect(TestBed.inject(ErrorHandler)).toBeInstanceOf(ManejadorErroresGlobal);
    expect(TestBed.inject(TitleStrategy)).toBeInstanceOf(EstrategiaTitulo);
    expect(TestBed.inject(LOCALE_ID)).toBe('es-CO');
  });
});
