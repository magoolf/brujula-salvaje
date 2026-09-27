import { Component, PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, RouterOutlet, provideRouter } from '@angular/router';

import { FocoRuta } from './foco-ruta';
import { ID_CONTENIDO_PRINCIPAL } from './navegacion';

@Component({ template: '<h1>Destinos</h1>' })
class VistaConTitulo {}

@Component({ template: '<p>Sin título</p>' })
class VistaSinTitulo {}

@Component({
  imports: [RouterOutlet],
  template: `<main [id]="id"><router-outlet /></main>`,
})
class Shell {
  readonly id = ID_CONTENIDO_PRINCIPAL;
}

describe('FocoRuta', () => {
  it('tras una navegación interna enfoca el h1 de la vista (no en la carga inicial)', async () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: '', component: VistaSinTitulo },
          { path: 'destinos', component: VistaConTitulo },
          { path: 'otra', component: VistaSinTitulo },
        ]),
      ],
    });
    const fixture = TestBed.createComponent(Shell);
    document.body.appendChild(fixture.nativeElement);
    const foco = TestBed.inject(FocoRuta);
    foco.iniciar();
    foco.iniciar(); // idempotente
    const router = TestBed.inject(Router);

    await router.navigateByUrl('/');
    await fixture.whenStable();
    expect(document.activeElement).toBe(document.body);

    await router.navigateByUrl('/destinos');
    await fixture.whenStable();
    const h1 = (fixture.nativeElement as HTMLElement).querySelector('h1') as HTMLElement;
    expect(h1.getAttribute('tabindex')).toBe('-1');
    expect(document.activeElement).toBe(h1);

    await router.navigateByUrl('/otra');
    await fixture.whenStable();
    expect(document.activeElement?.id).toBe(ID_CONTENIDO_PRINCIPAL);
    fixture.nativeElement.remove();
  });

  it('no hace nada en el servidor ni sin contenido principal', () => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: PLATFORM_ID, useValue: 'server' }],
    });
    const foco = TestBed.inject(FocoRuta);
    expect(() => foco.iniciar()).not.toThrow();
    expect(() => foco.enfocarVista()).not.toThrow();
  });
});
