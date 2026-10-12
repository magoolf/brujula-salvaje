import { Component, PLATFORM_ID, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, RouterOutlet, provideRouter } from '@angular/router';

import { ESPERA_MAXIMA_FRAGMENTO_MS, FocoRuta, irAAncla } from './foco-ruta';
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

/** Datos que «llegan» después de la navegación (como el glosario cuando responde la API). */
const datosCargados = signal(false);

@Component({
  template: `<h1>Glosario</h1>
    @if (datos()) {
      <div id="termino-x" class="termino"><p>Definición</p></div>
    }`,
})
class VistaConDatosDiferidos {
  readonly datos = datosCargados;
}

@Component({
  template: `<h1>Con ancla</h1>
    <section id="seccion-a"><h2>A</h2></section>`,
})
class VistaConAncla {}

/** Crea `<etiqueta id>` dentro de `padre` (sin innerHTML, §27.4). */
function crear(padre: HTMLElement, etiqueta: string, id: string): HTMLElement {
  const el = document.createElement(etiqueta);
  el.id = id;
  padre.appendChild(el);
  return el;
}

describe('irAAncla (TKT-042)', () => {
  it('desplaza y enfoca el destino (tabindex=-1); sin destino devuelve false', () => {
    const contenedor = document.createElement('div');
    document.body.appendChild(contenedor);
    const destino = crear(contenedor, 'section', 'destino');
    const desplazar = vi.fn();
    destino.scrollIntoView = desplazar;

    expect(irAAncla(document, 'no-existe')).toBe(false);
    expect(irAAncla(document, '')).toBe(false);
    expect(irAAncla(document, 'destino')).toBe(true);
    expect(desplazar).toHaveBeenCalledWith({ block: 'start' });
    expect(destino.getAttribute('tabindex')).toBe('-1');
    expect(document.activeElement).toBe(destino);
    contenedor.remove();
  });

  it('no quita el foco si ya está dentro del destino y respeta un tabindex existente', () => {
    const contenedor = document.createElement('div');
    document.body.appendChild(contenedor);
    const destino = crear(contenedor, 'section', 'd');
    destino.setAttribute('tabindex', '0');
    destino.scrollIntoView = vi.fn();
    const campo = crear(destino, 'input', 'campo');
    campo.focus();

    expect(irAAncla(document, 'd')).toBe(true);
    expect(document.activeElement).toBe(campo);
    expect(destino.getAttribute('tabindex')).toBe('0');
    contenedor.remove();
  });

  it('con enfocar=false solo desplaza', () => {
    const contenedor = document.createElement('div');
    document.body.appendChild(contenedor);
    const destino = crear(contenedor, 'div', 'solo-scroll');
    const desplazar = vi.fn();
    destino.scrollIntoView = desplazar;

    expect(irAAncla(document, 'solo-scroll', false)).toBe(true);
    expect(desplazar).toHaveBeenCalled();
    expect(destino.hasAttribute('tabindex')).toBe(false);
    expect(document.activeElement).not.toBe(destino);
    contenedor.remove();
  });
});

describe('FocoRuta con fragmentos (TKT-042)', () => {
  let desplazar: ReturnType<typeof vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>>;
  const original = Element.prototype.scrollIntoView;

  beforeEach(() => {
    datosCargados.set(false);
    desplazar = vi.fn<(arg?: boolean | ScrollIntoViewOptions) => void>();
    Element.prototype.scrollIntoView = desplazar;
  });

  afterEach(() => {
    Element.prototype.scrollIntoView = original;
    vi.useRealTimers();
  });

  async function montar(): Promise<{
    fixture: ComponentFixture<Shell>;
    router: Router;
    foco: FocoRuta;
  }> {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: '', component: VistaSinTitulo },
          { path: 'glosario', component: VistaConDatosDiferidos },
          { path: 'ancla', component: VistaConAncla },
        ]),
      ],
    });
    const fixture = TestBed.createComponent(Shell);
    document.body.appendChild(fixture.nativeElement);
    const foco = TestBed.inject(FocoRuta);
    foco.iniciar();
    const router = TestBed.inject(Router);
    await router.navigateByUrl('/');
    await fixture.whenStable();
    return { fixture, router, foco };
  }

  const raiz = (f: ComponentFixture<Shell>): HTMLElement => f.nativeElement as HTMLElement;

  it('si el destino ya existe, va directamente a él (no al h1)', async () => {
    const { fixture, router } = await montar();
    await router.navigateByUrl('/ancla#seccion-a');
    await fixture.whenStable();
    const seccion = raiz(fixture).querySelector('#seccion-a') as HTMLElement;
    expect(document.activeElement).toBe(seccion);
    expect(desplazar).toHaveBeenCalledWith({ block: 'start' });
    raiz(fixture).remove();
  });

  it('si los datos llegan después: anuncia la vista (h1) y luego lleva vista y foco al término', async () => {
    const { fixture, router } = await montar();
    await router.navigateByUrl('/glosario#termino-x');
    await fixture.whenStable();
    const h1 = raiz(fixture).querySelector('h1') as HTMLElement;
    expect(document.activeElement).toBe(h1);

    datosCargados.set(true);
    await fixture.whenStable();
    const termino = raiz(fixture).querySelector('#termino-x') as HTMLElement;
    expect(document.activeElement).toBe(termino);
    expect(termino.getAttribute('tabindex')).toBe('-1');
    expect(desplazar).toHaveBeenCalledTimes(1);

    // La espera terminó: renders posteriores no vuelven a mover la vista.
    datosCargados.set(false);
    await fixture.whenStable();
    datosCargados.set(true);
    await fixture.whenStable();
    expect(desplazar).toHaveBeenCalledTimes(1);
    raiz(fixture).remove();
  });

  it('una interacción del visitante cancela la espera', async () => {
    const { fixture, router } = await montar();
    await router.navigateByUrl('/glosario#termino-x');
    await fixture.whenStable();
    document.dispatchEvent(new Event('wheel'));
    datosCargados.set(true);
    await fixture.whenStable();
    expect(desplazar).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(raiz(fixture).querySelector('h1'));
    raiz(fixture).remove();
  });

  it('la siguiente navegación cancela la espera', async () => {
    const { fixture, router } = await montar();
    await router.navigateByUrl('/glosario#termino-x');
    await fixture.whenStable();
    await router.navigateByUrl('/glosario#otro');
    await fixture.whenStable();
    datosCargados.set(true);
    await fixture.whenStable();
    // Solo sigue viva la espera de «otro», que no existe: nadie desplaza a «termino-x».
    expect(desplazar).not.toHaveBeenCalled();
    raiz(fixture).remove();
  });

  it('pasado el tiempo máximo se abandona la espera', async () => {
    const { fixture, router } = await montar();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    await router.navigateByUrl('/glosario#termino-x');
    await fixture.whenStable();
    vi.advanceTimersByTime(ESPERA_MAXIMA_FRAGMENTO_MS);
    vi.useRealTimers();
    datosCargados.set(true);
    await fixture.whenStable();
    expect(desplazar).not.toHaveBeenCalled();
    raiz(fixture).remove();
  });

  it('en la carga inicial solo desplaza al destino diferido, sin mover el foco', async () => {
    TestBed.configureTestingModule({
      providers: [provideRouter([{ path: 'glosario', component: VistaConDatosDiferidos }])],
    });
    const fixture = TestBed.createComponent(Shell);
    document.body.appendChild(fixture.nativeElement);
    TestBed.inject(FocoRuta).iniciar();
    await TestBed.inject(Router).navigateByUrl('/glosario#termino-x');
    await fixture.whenStable();
    expect(document.activeElement).toBe(document.body);

    datosCargados.set(true);
    await fixture.whenStable();
    expect(desplazar).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(document.body);
    raiz(fixture).remove();
  });

  it('irAAncla del servicio salta sin navegar y cancela una espera pendiente', async () => {
    const { fixture, router, foco } = await montar();
    await router.navigateByUrl('/glosario#termino-x');
    await fixture.whenStable();
    expect(foco.irAAncla('no-existe')).toBe(false);
    datosCargados.set(true);
    await fixture.whenStable();
    expect(desplazar).not.toHaveBeenCalled();
    expect(foco.irAAncla('termino-x')).toBe(true);
    expect(desplazar).toHaveBeenCalledTimes(1);
    raiz(fixture).remove();
  });

  it('en el servidor irAAncla no hace nada', () => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: PLATFORM_ID, useValue: 'server' }],
    });
    expect(TestBed.inject(FocoRuta).irAAncla('x')).toBe(false);
  });
});
