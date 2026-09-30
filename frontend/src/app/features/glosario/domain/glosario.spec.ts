import { TerminoGlosarioVista } from './modelos';
import { agruparPorLetra, letraInicial } from './glosario';

const TERMINO = (over: Partial<TerminoGlosarioVista>): TerminoGlosarioVista => ({
  slug: 'x',
  termino: 'X',
  definicion: 'x',
  usadoEn: [],
  ...over,
});

describe('letraInicial', () => {
  it('mayúscula sin tildes', () => {
    expect(letraInicial('árbol')).toBe('A');
    expect(letraInicial('Buceo')).toBe('B');
  });

  it('# para texto vacío', () => {
    expect(letraInicial('')).toBe('#');
  });
});

describe('agruparPorLetra', () => {
  it('agrupa preservando el orden alfabético de llegada', () => {
    const terminos = [
      TERMINO({ termino: 'Altitud', slug: 'altitud' }),
      TERMINO({ termino: 'Alpinismo', slug: 'alpinismo' }),
      TERMINO({ termino: 'Buceo', slug: 'buceo' }),
    ];
    const grupos = agruparPorLetra(terminos);
    expect(grupos.map((g) => g.letra)).toEqual(['A', 'B']);
    expect(grupos[0].terminos.map((t) => t.slug)).toEqual(['altitud', 'alpinismo']);
    expect(grupos[1].terminos).toHaveLength(1);
  });

  it('lista vacía produce lista de grupos vacía', () => {
    expect(agruparPorLetra([])).toEqual([]);
  });
});
