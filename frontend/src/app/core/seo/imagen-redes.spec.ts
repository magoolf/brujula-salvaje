import { ANCHO_OBJETIVO_REDES, urlImagenRedes } from './imagen-redes';

describe('urlImagenRedes (TKT-056, OBS-QA048-05)', () => {
  const derivados = [
    { url: '/m/h-400.avif', ancho: 400 },
    { url: '/m/h-800.avif', ancho: 800 },
    { url: '/m/h-1600.avif', ancho: 1600 },
    { url: '/m/h-400.webp', ancho: 400 },
    { url: '/m/h-1600.webp', ancho: 1600 },
    { url: '/m/h-400.jpeg', ancho: 400 },
    { url: '/m/h-800.jpeg', ancho: 800 },
    { url: '/m/h-1200.jpeg', ancho: 1200 },
    { url: '/m/h-1600.jpeg', ancho: 1600 },
  ];

  it('prefiere JPEG y el menor ancho que alcanza el objetivo', () => {
    expect(ANCHO_OBJETIVO_REDES).toBe(1200);
    expect(urlImagenRedes('/m/h-400.avif', derivados)).toBe('/m/h-1200.jpeg');
  });

  it('sin un JPEG suficientemente grande usa el mayor JPEG disponible', () => {
    const pocos = derivados.filter((d) => d.ancho <= 800);
    expect(urlImagenRedes('/m/h-400.avif', pocos)).toBe('/m/h-800.jpeg');
  });

  it('sin JPEG usa WebP; reconoce .jpg y URLs con consulta', () => {
    const sinJpeg = derivados.filter((d) => !d.url.endsWith('.jpeg'));
    expect(urlImagenRedes('/m/h-400.avif', sinJpeg)).toBe('/m/h-1600.webp');
    expect(
      urlImagenRedes('/m/x.avif', [
        { url: '/m/x-1300.JPG?v=2', ancho: 1300 },
        { url: '/m/x-2000.jpg', ancho: 2000 },
      ]),
    ).toBe('/m/x-1300.JPG?v=2');
  });

  it('conserva el src si no hay derivados compatibles o válidos', () => {
    expect(urlImagenRedes('/m/h-400.avif')).toBe('/m/h-400.avif');
    expect(urlImagenRedes('/m/h-400.avif', derivados.filter((d) => d.url.endsWith('.avif')))).toBe(
      '/m/h-400.avif',
    );
    expect(
      urlImagenRedes('/m/h.avif', [
        { url: '', ancho: 1200 },
        { url: '/m/h-0.jpeg', ancho: 0 },
        { url: '/m/h-n.jpeg', ancho: Number.NaN },
      ]),
    ).toBe('/m/h.avif');
  });
});
