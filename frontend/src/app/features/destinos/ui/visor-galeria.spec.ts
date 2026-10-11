import { Dialog } from '@angular/cdk/dialog';
import { Injector } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ImagenVista } from '../domain/modelos';
import { VisorGaleria, abrirVisorGaleria } from './visor-galeria';

function imagen(n: number): ImagenVista {
  return {
    src: `/media/publico/g${n}-800.jpeg`,
    alt: `Foto ${n}`,
    ancho: 800,
    alto: 600,
    derivados: [],
    autorCredito: `Autor ${n}`,
    pieDeFoto: n === 1 ? 'Amanecer' : null,
    licenciaNombre: 'CC BY-SA 4.0',
    licenciaUrl: null,
  };
}

describe('abrirVisorGaleria / VisorGaleria (SCR-005, TKT-056)', () => {
  afterEach(() => TestBed.inject(Dialog).closeAll());

  it('abre el visor en CDK Dialog con los datos, a pantalla completa y foco inicial', () => {
    const dialogo = TestBed.inject(Dialog);
    const abrir = vi.spyOn(dialogo, 'open');
    const datos = { imagenes: [imagen(1), imagen(2)], indiceInicial: 1, tituloDestino: 'Ha Long' };

    const ref = abrirVisorGaleria(TestBed.inject(Injector), datos);

    expect(ref.componentInstance).toBeInstanceOf(VisorGaleria);
    expect(abrir).toHaveBeenCalledWith(
      VisorGaleria,
      expect.objectContaining({
        data: datos,
        backdropClass: 'bs-fondo-dialogo',
        panelClass: 'bs-panel-dialogo-completo',
        autoFocus: 'first-tabbable',
      }),
    );
  });

  it('navega entre fotos sin bucle en los extremos y cierra', async () => {
    const ref = abrirVisorGaleria(TestBed.inject(Injector), {
      imagenes: [imagen(1), imagen(2)],
      indiceInicial: 5,
      tituloDestino: 'Ha Long',
    });
    await Promise.resolve();
    TestBed.tick();
    const visor = document.querySelector('[data-testid="visor-galeria"]') as HTMLElement;
    expect(visor.getAttribute('aria-label')).toBe('Galería de Ha Long');
    const posicion = () => visor.querySelector('.posicion')?.textContent?.trim();
    // Índice inicial fuera de rango: se acota a la última foto.
    expect(posicion()).toBe('2 de 2');
    const [anterior, siguiente] = Array.from(
      visor.querySelectorAll<HTMLButtonElement>('button.control'),
    );
    expect(siguiente.disabled).toBe(true);

    anterior.click();
    TestBed.tick();
    expect(posicion()).toBe('1 de 2');
    expect(visor.querySelector('img')?.getAttribute('alt')).toBe('Foto 1');
    expect(visor.querySelector('figcaption')?.textContent).toContain('Amanecer');
    expect(anterior.disabled).toBe(true);
    anterior.click();
    TestBed.tick();
    expect(posicion()).toBe('1 de 2');

    siguiente.click();
    TestBed.tick();
    expect(posicion()).toBe('2 de 2');

    const cerrar = vi.spyOn(ref, 'close');
    (visor.querySelector('[aria-label="Cerrar galería"]') as HTMLButtonElement).click();
    expect(cerrar).toHaveBeenCalled();
  });
});
