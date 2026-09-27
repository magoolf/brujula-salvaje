import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { CampoBusqueda } from './campo-busqueda';
import { MAX_CONSULTA, validarConsulta } from './validar-consulta';

describe('validarConsulta (AC-020)', () => {
  it('acepta 2..100 caracteres tras recortar y normalizar espacios', () => {
    expect(validarConsulta('  Patagonia   sur ')).toEqual({
      valida: true,
      consulta: 'Patagonia sur',
    });
    expect(validarConsulta('ñu')).toEqual({ valida: true, consulta: 'ñu' });
  });

  it('rechaza consultas cortas o largas con mensaje de qué hacer', () => {
    expect(validarConsulta(' a ')).toEqual({
      valida: false,
      mensaje: 'Escribe al menos 2 caracteres.',
    });
    expect(validarConsulta(null)).toMatchObject({ valida: false });
    expect(validarConsulta('x'.repeat(MAX_CONSULTA + 1))).toEqual({
      valida: false,
      mensaje: 'Escribe como máximo 100 caracteres.',
    });
  });
});

describe('CampoBusqueda (SearchField)', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  async function crear() {
    const fixture = TestBed.createComponent(CampoBusqueda);
    fixture.componentRef.setInput('idCampo', 'busqueda-prueba');
    await fixture.whenStable();
    const raiz = fixture.nativeElement as HTMLElement;
    return {
      fixture,
      raiz,
      form: raiz.querySelector('form') as HTMLFormElement,
      campo: raiz.querySelector('input') as HTMLInputElement,
    };
  }

  it('form role=search GET /buscar con etiqueta accesible (funciona sin JS)', async () => {
    const { form, campo, raiz } = await crear();
    expect(form.getAttribute('role')).toBe('search');
    expect(form.getAttribute('method')).toBe('get');
    expect(form.getAttribute('action')).toBe('/buscar');
    expect(campo.name).toBe('q');
    expect(campo.type).toBe('search');
    expect(raiz.querySelector('label')?.getAttribute('for')).toBe('busqueda-prueba');
    expect(raiz.querySelector('label')?.textContent).toBe('Buscar destinos, itinerarios y guías');
  });

  it('valida al enviar: muestra el error en línea, marca aria-invalid y no navega', async () => {
    const { fixture, form, campo, raiz } = await crear();
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    campo.value = 'a';
    form.dispatchEvent(new Event('submit', { cancelable: true }));
    await fixture.whenStable();
    expect(navegar).not.toHaveBeenCalled();
    expect(raiz.querySelector('[data-testid="campo-busqueda-error"]')?.textContent).toBe(
      'Escribe al menos 2 caracteres.',
    );
    expect(campo.getAttribute('aria-invalid')).toBe('true');
    expect(campo.getAttribute('aria-describedby')).toBe('busqueda-prueba-error');

    campo.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    expect(raiz.querySelector('[data-testid="campo-busqueda-error"]')).toBeNull();
  });

  it('con una consulta válida navega a /buscar?q=', async () => {
    const { fixture, form, campo } = await crear();
    const navegar = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    campo.value = '  buceo ';
    const evento = new Event('submit', { cancelable: true });
    form.dispatchEvent(evento);
    await fixture.whenStable();
    expect(evento.defaultPrevented).toBe(true);
    expect(navegar).toHaveBeenCalledWith(['/buscar'], { queryParams: { q: 'buceo' } });
  });

  it('enfocar() pone el foco en el campo', async () => {
    const { fixture, campo } = await crear();
    document.body.appendChild(fixture.nativeElement);
    fixture.componentInstance.enfocar();
    expect(document.activeElement).toBe(campo);
    fixture.nativeElement.remove();
  });
});
