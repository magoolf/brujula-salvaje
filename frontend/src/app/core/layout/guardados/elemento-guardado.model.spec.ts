import {
  ElementoGuardado,
  LIMITE_GUARDADOS,
  agregarElemento,
  claveElemento,
  estaGuardado,
  quitarElemento,
  rutaElemento,
  validarElementoGuardado,
} from './elemento-guardado.model';

const DESTINO_VALIDO: ElementoGuardado = {
  tipo: 'DESTINO',
  slug: 'patagonia',
  titulo: 'Patagonia',
  pais: 'Argentina',
};

describe('validarElementoGuardado (THREAT-026: dato no confiable)', () => {
  it('acepta un elemento con la forma correcta', () => {
    expect(validarElementoGuardado(DESTINO_VALIDO)).toEqual(DESTINO_VALIDO);
  });

  it('acepta país nulo/ausente', () => {
    expect(validarElementoGuardado({ ...DESTINO_VALIDO, pais: undefined })).toEqual({
      ...DESTINO_VALIDO,
      pais: null,
    });
  });

  it.each([
    [null],
    [undefined],
    ['una cadena'],
    [42],
    [{ tipo: 'GUIA', slug: 'x', titulo: 'x' }],
    [{ tipo: 'DESTINO', slug: 'Mayúscula-Invalida', titulo: 'x' }],
    [{ tipo: 'DESTINO', slug: '', titulo: 'x' }],
    [{ tipo: 'DESTINO', slug: 'valido', titulo: '' }],
    [{ tipo: 'DESTINO', slug: 'valido', titulo: '   ' }],
    [{ tipo: 'DESTINO', slug: 'a'.repeat(121), titulo: 'x' }],
  ])('rechaza la forma inválida %j devolviendo null', (valor) => {
    expect(validarElementoGuardado(valor)).toBeNull();
  });

  it('recorta título y país a 200 caracteres', () => {
    const largo = 'a'.repeat(250);
    const resultado = validarElementoGuardado({ tipo: 'ITINERARIO', slug: 'x', titulo: largo, pais: largo });
    expect(resultado?.titulo.length).toBe(200);
    expect(resultado?.pais?.length).toBe(200);
  });
});

describe('claveElemento / rutaElemento', () => {
  it('construye una clave estable por tipo+slug', () => {
    expect(claveElemento('DESTINO', 'patagonia')).toBe('DESTINO:patagonia');
  });

  it('construye la ruta interna solo desde tipo y slug', () => {
    expect(rutaElemento({ ...DESTINO_VALIDO, tipo: 'DESTINO' })).toBe('/destinos/patagonia');
    expect(rutaElemento({ ...DESTINO_VALIDO, tipo: 'ITINERARIO' })).toBe('/itinerarios/patagonia');
  });
});

describe('estaGuardado', () => {
  it('detecta presencia por tipo+slug', () => {
    expect(estaGuardado([DESTINO_VALIDO], 'DESTINO', 'patagonia')).toBe(true);
    expect(estaGuardado([DESTINO_VALIDO], 'DESTINO', 'otro')).toBe(false);
    expect(estaGuardado([], 'DESTINO', 'patagonia')).toBe(false);
  });
});

describe('agregarElemento', () => {
  it('añade al frente de la lista', () => {
    const resultado = agregarElemento([], DESTINO_VALIDO);
    expect(resultado).toEqual([DESTINO_VALIDO]);
  });

  it('mueve al frente sin duplicar si ya existía', () => {
    const otro = { ...DESTINO_VALIDO, slug: 'otro', titulo: 'Otro' };
    const resultado = agregarElemento([otro, DESTINO_VALIDO], { ...DESTINO_VALIDO, titulo: 'Actualizado' });
    expect(resultado).toEqual([{ ...DESTINO_VALIDO, titulo: 'Actualizado' }, otro]);
  });

  it('respeta LIMITE_GUARDADOS', () => {
    const llena = Array.from({ length: LIMITE_GUARDADOS }, (_, i) => ({
      tipo: 'DESTINO' as const,
      slug: `d${i}`,
      titulo: `D${i}`,
      pais: null,
    }));
    const resultado = agregarElemento(llena, { tipo: 'DESTINO', slug: 'nuevo', titulo: 'Nuevo', pais: null });
    expect(resultado).toHaveLength(LIMITE_GUARDADOS);
    expect(resultado[0].slug).toBe('nuevo');
    expect(resultado.some((e) => e.slug === `d${LIMITE_GUARDADOS - 1}`)).toBe(false);
  });
});

describe('quitarElemento', () => {
  it('quita solo el elemento indicado', () => {
    const otro = { ...DESTINO_VALIDO, slug: 'otro' };
    expect(quitarElemento([DESTINO_VALIDO, otro], 'DESTINO', 'patagonia')).toEqual([otro]);
  });

  it('no falla si el elemento no existe', () => {
    expect(quitarElemento([DESTINO_VALIDO], 'DESTINO', 'inexistente')).toEqual([DESTINO_VALIDO]);
  });
});
