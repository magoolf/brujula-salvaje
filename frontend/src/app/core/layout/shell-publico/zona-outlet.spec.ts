import { Component, OnDestroy } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router, Routes, provideRouter } from '@angular/router';
import { filter } from 'rxjs';

import { App } from '../../../app';
import { ZonaOutlet } from './zona-outlet';
import { DATOS_ZONA_PANEL } from './zona';

/**
 * Cruces de zona (QA TKT-010 ciclo 2, HALLAZGO-ZONA) con App como raíz real: ninguna página se
 * vuelve a montar en el armazón de la otra zona, la saliente sigue en su armazón hasta que la
 * entrante se activa y nunca conviven dos armazones ni dos <main>.
 */

const creadas: string[] = [];
const destruidas: string[] = [];

function registrar(nombre: string): void {
  creadas.push(nombre);
}

@Component({
  selector: 'app-vista-publica',
  template: '<h1 data-testid="vista-publica">pública</h1>',
})
class VistaPublica implements OnDestroy {
  constructor() {
    registrar('publica');
  }
  ngOnDestroy(): void {
    destruidas.push('publica');
  }
}

@Component({
  selector: 'app-vista-otra',
  template: '<h1 data-testid="vista-otra">otra</h1>',
})
class VistaOtra {
  constructor() {
    registrar('otra');
  }
}

@Component({
  selector: 'app-vista-panel',
  template: '<h1 data-testid="vista-panel">panel</h1>',
})
class VistaPanel implements OnDestroy {
  constructor() {
    registrar('panel');
  }
  ngOnDestroy(): void {
    destruidas.push('panel');
  }
}

/** Armazón del panel con su propio <main> y un ZonaOutlet anidado, como ShellPanel. */
@Component({
  selector: 'app-layout-prueba',
  imports: [ZonaOutlet],
  template: '<main data-testid="main-panel"><router-outlet appZona="panel" /></main>',
})
class LayoutPrueba implements OnDestroy {
  constructor() {
    registrar('layout');
  }
  ngOnDestroy(): void {
    destruidas.push('layout');
  }
}

let liberarGuard: (valor: boolean) => void = () => undefined;

const RUTAS: Routes = [
  {
    path: 'panel',
    data: DATOS_ZONA_PANEL,
    children: [
      {
        path: '',
        component: LayoutPrueba,
        children: [
          { path: 'prueba', component: VistaPanel },
          {
            path: 'lenta',
            component: VistaPanel,
            canActivate: [() => new Promise<boolean>((r) => (liberarGuard = r))],
          },
        ],
      },
    ],
  },
  { path: '', component: VistaPublica },
  { path: 'otra', component: VistaOtra },
];

async function montar(url: string) {
  TestBed.configureTestingModule({ providers: [provideRouter(RUTAS)] });
  const fixture = TestBed.createComponent(App);
  const router = TestBed.inject(Router);
  await router.navigateByUrl(url);
  await fixture.whenStable();
  const raiz = fixture.nativeElement as HTMLElement;
  return { fixture, router, raiz };
}

/** Deja correr temporizadores y renders sin esperar a la navegación pendiente (whenStable sí la espera). */
async function tareas(): Promise<void> {
  for (let i = 0; i < 3; i++) await new Promise((r) => setTimeout(r, 0));
}

function estado(raiz: HTMLElement) {
  return {
    shell: raiz.querySelector(':scope > app-shell-publico') !== null,
    layoutEnRaiz: raiz.querySelector(':scope > app-layout-prueba') !== null,
    publicaEnShell: raiz.querySelector('app-shell-publico main app-vista-publica') !== null,
    panelEnShell:
      raiz.querySelector(
        'app-shell-publico app-layout-prueba, app-shell-publico app-vista-panel',
      ) !== null,
    publicaFueraDeShell:
      raiz.querySelector(':scope > app-vista-publica, app-layout-prueba app-vista-publica') !==
      null,
    mains: raiz.querySelectorAll('main').length,
  };
}

describe('ZonaOutlet (TKT-010, HALLAZGO-ZONA)', () => {
  beforeEach(() => {
    creadas.length = 0;
    destruidas.length = 0;
  });
  afterEach(() => TestBed.resetTestingModule());

  it('público → panel: la página pública no se vuelve a montar y sigue en su armazón hasta la activación', async () => {
    const { fixture, router, raiz } = await montar('/');
    expect(creadas).toEqual(['publica']);
    expect(estado(raiz)).toMatchObject({ shell: true, publicaEnShell: true, mains: 1 });

    // Guard pendiente: la navegación ya empezó, pero la página saliente sigue intacta.
    const navegacion = router.navigateByUrl('/panel/lenta');
    await tareas();
    expect(estado(raiz)).toMatchObject({
      shell: true,
      publicaEnShell: true,
      layoutEnRaiz: false,
      mains: 1,
    });
    expect(creadas).toEqual(['publica']);

    // En NavigationEnd (activación hecha, aún sin render) la saliente sigue visible en su armazón.
    let alTerminar: ReturnType<typeof estado> | null = null;
    router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe(() => (alTerminar = estado(raiz)));
    liberarGuard(true);
    await navegacion;
    expect(alTerminar).toMatchObject({
      shell: true,
      publicaEnShell: true,
      panelEnShell: false,
      layoutEnRaiz: false,
      mains: 1,
    });
    expect(destruidas).toEqual([]);

    await fixture.whenStable();
    expect(estado(raiz)).toEqual({
      shell: false,
      layoutEnRaiz: true,
      publicaEnShell: false,
      panelEnShell: false,
      publicaFueraDeShell: false,
      mains: 1,
    });
    expect(raiz.querySelector('app-layout-prueba main app-vista-panel')).not.toBeNull();
    // Cada componente se creó una sola vez: ni la saliente se remontó ni la entrante se duplicó.
    expect(creadas).toEqual(['publica', 'layout', 'panel']);
    expect(destruidas).toEqual(['publica']);
  });

  it('panel → público: el armazón del panel (con su página) se retira entero, sin dos <main>', async () => {
    const { fixture, router, raiz } = await montar('/panel/prueba');
    expect(estado(raiz)).toMatchObject({ shell: false, layoutEnRaiz: true, mains: 1 });

    let alTerminar: ReturnType<typeof estado> | null = null;
    let panelVisible = false;
    router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => {
      alTerminar = estado(raiz);
      panelVisible = raiz.querySelector('app-layout-prueba main app-vista-panel') !== null;
    });
    await router.navigateByUrl('/');
    // La activación ya ocurrió: el panel (armazón y página) sigue completo hasta el render.
    expect(alTerminar).toMatchObject({ shell: false, layoutEnRaiz: true, mains: 1 });
    expect(panelVisible).toBe(true);
    expect(destruidas).toEqual([]);

    await fixture.whenStable();
    expect(estado(raiz)).toMatchObject({
      shell: true,
      layoutEnRaiz: false,
      publicaEnShell: true,
      panelEnShell: false,
      mains: 1,
    });
    expect(creadas).toEqual(['layout', 'panel', 'publica']);
    expect([...destruidas].sort()).toEqual(['layout', 'panel']);
  });

  it('dentro de una zona se comporta como RouterOutlet (sin retener la página saliente)', async () => {
    const { fixture, router, raiz } = await montar('/');
    await router.navigateByUrl('/otra');
    await fixture.whenStable();
    expect(destruidas).toEqual(['publica']);
    expect(raiz.querySelector('app-shell-publico main app-vista-otra')).not.toBeNull();
    expect(raiz.querySelectorAll('app-shell-publico main > router-outlet ~ *').length).toBe(1);
    expect(creadas).toEqual(['publica', 'otra']);
  });

  it('ida y vuelta: cada página se crea una vez por visita y nunca aparece en el armazón ajeno', async () => {
    const { fixture, router, raiz } = await montar('/');
    for (const url of ['/panel/prueba', '/', '/panel/prueba', '/otra']) {
      await router.navigateByUrl(url);
      await fixture.whenStable();
      const e = estado(raiz);
      expect(e.mains).toBe(1);
      expect(e.panelEnShell).toBe(false);
      expect(e.publicaFueraDeShell).toBe(false);
      expect(e.shell).toBe(!url.startsWith('/panel'));
    }
    expect(creadas).toEqual(['publica', 'layout', 'panel', 'publica', 'layout', 'panel', 'otra']);
  });

  it('una navegación cancelada no cambia de zona ni retira la página', async () => {
    const { fixture, router, raiz } = await montar('/');
    const navegacion = router.navigateByUrl('/panel/lenta');
    await tareas();
    liberarGuard(false);
    expect(await navegacion).toBe(false);
    await fixture.whenStable();
    expect(estado(raiz)).toMatchObject({
      shell: true,
      publicaEnShell: true,
      layoutEnRaiz: false,
      mains: 1,
    });
    expect(creadas).toEqual(['publica']);
    expect(destruidas).toEqual([]);
    // Y la siguiente navegación dentro de la zona funciona con normalidad.
    await router.navigateByUrl('/otra');
    await fixture.whenStable();
    expect(raiz.querySelector('app-shell-publico main app-vista-otra')).not.toBeNull();
    expect(raiz.querySelectorAll('app-shell-publico main > router-outlet ~ *').length).toBe(1);
  });
});
