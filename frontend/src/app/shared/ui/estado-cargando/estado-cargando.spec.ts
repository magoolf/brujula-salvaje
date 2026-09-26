import { TestBed } from '@angular/core/testing';

import { EstadoCargando, RETARDO_ESQUELETO_MS } from './estado-cargando';

describe('EstadoCargando (Skeleton)', () => {
  afterEach(() => vi.useRealTimers());

  it('aria-busy, esqueletos aria-hidden y pulso visible solo tras 300 ms', async () => {
    vi.useFakeTimers();
    const fixture = TestBed.createComponent(EstadoCargando);
    fixture.componentRef.setInput('forma', 'tarjeta');
    fixture.componentRef.setInput('cantidad', 4);
    fixture.detectChanges();
    const raiz = fixture.nativeElement as HTMLElement;

    expect(raiz.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(raiz.querySelector('[role="status"]')?.textContent).toBe('Cargando…');
    const esqueletos = raiz.querySelectorAll('.esqueleto');
    expect(esqueletos).toHaveLength(4);
    expect(esqueletos[0].getAttribute('aria-hidden')).toBe('true');
    expect(esqueletos[0].getAttribute('data-forma')).toBe('tarjeta');
    expect(raiz.querySelector('.esqueleto--visible')).toBeNull();

    vi.advanceTimersByTime(RETARDO_ESQUELETO_MS);
    fixture.detectChanges();
    expect(raiz.querySelectorAll('.esqueleto--visible')).toHaveLength(4);
    fixture.destroy();
  });

  it('acota la cantidad entre 1 y 24', () => {
    const fixture = TestBed.createComponent(EstadoCargando);
    fixture.componentRef.setInput('cantidad', 100);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelectorAll('.esqueleto')).toHaveLength(24);
    fixture.componentRef.setInput('cantidad', 0);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelectorAll('.esqueleto')).toHaveLength(1);
  });
});
