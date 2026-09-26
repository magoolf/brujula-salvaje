import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { BannerSinConexion } from './banner-sin-conexion/banner-sin-conexion';
import { Conectividad } from './conectividad';

describe('Conectividad (FEAT-028)', () => {
  afterEach(() => vi.useRealTimers());

  it('refleja offline/online y marca «restablecida» durante 3 s', () => {
    vi.useFakeTimers();
    const servicio = TestBed.inject(Conectividad);
    expect(servicio.enLinea()).toBe(true);

    window.dispatchEvent(new Event('offline'));
    expect(servicio.enLinea()).toBe(false);
    expect(servicio.restablecida()).toBe(false);

    window.dispatchEvent(new Event('online'));
    expect(servicio.enLinea()).toBe(true);
    expect(servicio.restablecida()).toBe(true);
    vi.advanceTimersByTime(3000);
    expect(servicio.restablecida()).toBe(false);
  });

  it('comprobar() relee navigator.onLine', () => {
    const servicio = TestBed.inject(Conectividad);
    const onLine = vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(false);
    servicio.comprobar();
    expect(servicio.enLinea()).toBe(false);
    onLine.mockReturnValue(true);
    servicio.comprobar();
    expect(servicio.enLinea()).toBe(true);
    onLine.mockRestore();
  });

  it('en el servidor siempre está en línea y no escucha eventos', () => {
    TestBed.configureTestingModule({ providers: [{ provide: PLATFORM_ID, useValue: 'server' }] });
    const servicio = TestBed.inject(Conectividad);
    window.dispatchEvent(new Event('offline'));
    expect(servicio.enLinea()).toBe(true);
    servicio.comprobar();
    expect(servicio.enLinea()).toBe(true);
  });
});

describe('BannerSinConexion (GI-04)', () => {
  it('muestra el aviso sin conexión en role=status con Reintentar, y el de conexión restablecida', async () => {
    const fixture = TestBed.createComponent(BannerSinConexion);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    const region = raiz.querySelector('[data-testid="banner-sin-conexion"]') as HTMLElement;
    expect(region.getAttribute('role')).toBe('status');
    expect(region.textContent?.trim()).toBe('');

    window.dispatchEvent(new Event('offline'));
    await fixture.whenStable();
    expect(region.textContent).toContain('Sin conexión. Lo que ya cargaste sigue disponible.');

    const comprobar = vi.spyOn(TestBed.inject(Conectividad), 'comprobar').mockImplementation(() => undefined);
    (region.querySelector('button') as HTMLButtonElement).click();
    expect(comprobar).toHaveBeenCalled();

    window.dispatchEvent(new Event('online'));
    await fixture.whenStable();
    expect(region.textContent).toContain('Conexión restablecida.');
  });
});
