import { ChecklistItemVista } from './modelos';
import { agruparChecklist, formatoFechaEsCo, tieneChecklist } from './tipo-aventura';

const ITEM = (over: Partial<ChecklistItemVista>): ChecklistItemVista => ({
  texto: 'x',
  esencial: false,
  grupo: null,
  orden: 0,
  ...over,
});

describe('agruparChecklist', () => {
  it('agrupa por grupo preservando el orden de aparición de cada grupo', () => {
    const items = [
      ITEM({ texto: 'Botas', grupo: 'Calzado', orden: 2 }),
      ITEM({ texto: 'Mochila', grupo: 'Equipo', orden: 1 }),
      ITEM({ texto: 'Medias', grupo: 'Calzado', orden: 1 }),
    ];
    const grupos = agruparChecklist(items);
    expect(grupos.map((g) => g.nombre)).toEqual(['Equipo', 'Calzado']);
    expect(grupos[1].items.map((i) => i.texto)).toEqual(['Medias', 'Botas']);
  });

  it('elementos sin grupo quedan en un grupo null', () => {
    const grupos = agruparChecklist([ITEM({ texto: 'Agua', grupo: null, orden: 1 })]);
    expect(grupos).toEqual([{ nombre: null, items: [ITEM({ texto: 'Agua', grupo: null, orden: 1 })] }]);
  });

  it('lista vacía produce lista de grupos vacía', () => {
    expect(agruparChecklist([])).toEqual([]);
  });
});

describe('tieneChecklist', () => {
  it('false si no hay elementos', () => {
    expect(tieneChecklist([])).toBe(false);
  });

  it('true si hay al menos un elemento', () => {
    expect(tieneChecklist([ITEM({})])).toBe(true);
  });
});

describe('formatoFechaEsCo', () => {
  it('formatea una fecha ISO en es-CO', () => {
    expect(formatoFechaEsCo('2026-01-15')).toContain('2026');
  });

  it('devuelve el valor original si no es una fecha válida', () => {
    expect(formatoFechaEsCo('no-es-fecha')).toBe('no-es-fecha');
  });
});
