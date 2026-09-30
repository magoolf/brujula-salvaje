import { ImagenPublica } from '../../../api/models/imagen-publica';
import { Inicio as InicioDto } from '../../../api/models/inicio';
import { mapInicio } from './inicio.mapper';

const IMAGEN: ImagenPublica = {
  ancho: 800,
  alto: 600,
  autor_credito: 'Jane Doe',
  derivados: [{ ancho: 400, formato: 'WEBP', url: '/x-400.webp' }],
  licencia: { codigo: 'CC-BY', nombre: 'CC BY', requiere_atribucion: true },
  texto_alternativo: 'Alt',
};

describe('mapInicio', () => {
  it('mapea hero, destinos, itinerarios, guías y tipos', () => {
    const dto: InicioDto = {
      hero: { titular: 'Titular', subtitulo: 'Subtítulo', imagen: IMAGEN },
      destinos: [
        {
          dificultad: 2,
          pais: { slug: 'colombia', nombre: 'Colombia' },
          portada: IMAGEN,
          region: { slug: 'suramerica', nombre: 'Suramérica' },
          slug: 'patagonia',
          tipos: [],
          titulo: 'Patagonia',
        },
      ],
      itinerarios: [
        { destino: { slug: 'patagonia', nombre: 'Patagonia' }, dificultad: 2, duracion_dias: 5, portada: null, slug: 'ruta', titulo: 'Ruta' },
      ],
      guias: [
        { categoria: { slug: 'seguridad', nombre: 'Seguridad' }, fecha_ultima_revision: '2026-01-01', portada: null, resumen: 'r', slug: 'guia', titulo: 'Guía' },
      ],
      tipos: [
        { nivel_exigencia: 3, numero_destinos: 4, portada: null, resumen: 'r', slug: 'senderismo', titulo: 'Senderismo' },
      ],
    };

    const resultado = mapInicio(dto);
    expect(resultado.hero).toEqual({ titular: 'Titular', subtitulo: 'Subtítulo', imagen: expect.objectContaining({ src: '/x-400.webp' }) });
    expect(resultado.destinos).toHaveLength(1);
    expect(resultado.itinerarios[0].duracionDias).toBe(5);
    expect(resultado.guias[0].resumen).toBe('r');
    expect(resultado.tipos[0].numeroDestinos).toBe(4);
  });

  it('hero null cuando el backend no envía bloque principal', () => {
    const dto: InicioDto = { hero: null, destinos: [], itinerarios: [], guias: [], tipos: [] };
    expect(mapInicio(dto).hero).toBeNull();
  });
});
