import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ImagenTarjeta, TarjetaContenido } from './tarjeta-contenido';

@Component({
  imports: [TarjetaContenido],
  template: `
    <app-tarjeta-contenido titulo="Patagonia" ruta="/destinos/patagonia" overline="Destino"
                           [imagen]="imagen()" [nivelTitulo]="nivel()" testId="tarjeta-destino-patagonia">
      <p>Argentina · Chile</p>
      <button tarjeta-accion type="button" aria-label="Guardar Patagonia">Guardar</button>
    </app-tarjeta-contenido>
  `,
})
class Anfitrion {
  readonly imagen = signal<ImagenTarjeta | null>({ src: '/media/publico/p-640.webp', ancho: 640, alto: 480 });
  readonly nivel = signal<2 | 3 | 4>(3);
}

describe('TarjetaContenido', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  it('un único enlace principal en el título, imagen decorativa y acción fuera del enlace', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const tarjeta = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="tarjeta-destino-patagonia"]') as HTMLElement;
    const enlaces = tarjeta.querySelectorAll('a');
    expect(enlaces).toHaveLength(1);
    expect(enlaces[0].getAttribute('href')).toBe('/destinos/patagonia');
    expect(tarjeta.querySelector('h3')?.textContent).toBe('Patagonia');
    expect(tarjeta.querySelector('img')?.getAttribute('alt')).toBe('');
    expect(tarjeta.querySelector('.bs-overline')?.textContent).toBe('Destino');
    expect(tarjeta.querySelector('a button')).toBeNull();
    expect(tarjeta.querySelector('.accion button')?.getAttribute('aria-label')).toBe('Guardar Patagonia');
    expect(tarjeta.querySelector('.metadatos')?.textContent).toContain('Argentina');
  });

  it('respeta el nivel de encabezado y funciona sin imagen', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    fixture.componentInstance.imagen.set(null);
    fixture.componentInstance.nivel.set(2);
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    expect(raiz.querySelector('h2 a')?.textContent).toBe('Patagonia');
    expect(raiz.querySelector('img')).toBeNull();
    fixture.componentInstance.nivel.set(4);
    await fixture.whenStable();
    expect(raiz.querySelector('h4 a')).not.toBeNull();
  });
});
