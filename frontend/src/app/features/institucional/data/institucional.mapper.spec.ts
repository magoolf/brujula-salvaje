import { ConfiguracionPublica } from '../../../api/models/configuracion-publica';
import { Escalas } from '../../../api/models/escalas';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { PaginaCreditoMedio } from '../../../api/models/pagina-credito-medio';
import { PaginaInstitucionalPublica } from '../../../api/models/pagina-institucional-publica';
import {
  mapConfiguracion,
  mapContenidoRef,
  mapCreditoMedio,
  mapEscalas,
  mapPaginaCreditos,
  mapPaginaInstitucional,
} from './institucional.mapper';

const IMAGEN: ImagenPublica = {
  ancho: 800,
  alto: 600,
  autor_credito: 'Jane Doe',
  derivados: [{ ancho: 400, formato: 'WEBP', url: '/media/x-400.webp' }],
  fuente_url: 'https://fuente.example',
  licencia: { codigo: 'CC-BY', nombre: 'CC BY 4.0', requiere_atribucion: true, url_texto_legal: 'https://x' },
  pie_de_foto: null,
  texto_alternativo: 'Alt',
};

describe('mapContenidoRef', () => {
  it('construye la ruta interna a partir del tipo', () => {
    expect(mapContenidoRef({ slug: 'patagonia', tipo: 'DESTINO', titulo: 'Patagonia' }).ruta).toBe('/destinos/patagonia');
  });
});

describe('mapPaginaInstitucional', () => {
  it('mapea todos los campos', () => {
    const dto: PaginaInstitucionalPublica = {
      cuerpo: '<p>x</p>',
      metadatos: { autoria: 'Equipo editorial', fecha_ultima_revision: '2026-01-01', publicado_actualizado_en: '2026-01-01', seo_descripcion: 'x', seo_titulo: 'x' },
      slug: 'aviso-legal',
      titulo: 'Aviso legal',
      version_documento: '1.0',
      vigente_desde: '2026-01-01',
    };
    const resultado = mapPaginaInstitucional(dto);
    expect(resultado.slug).toBe('aviso-legal');
    expect(resultado.versionDocumento).toBe('1.0');
  });
});

describe('mapEscalas', () => {
  it('mapea dificultad y presupuesto', () => {
    const dto: Escalas = {
      dificultad: [{ descripcion: 'x', escala: 'DIFICULTAD', etiqueta: 'Fácil', nivel: 1 }],
      presupuesto: [{ descripcion: 'x', escala: 'PRESUPUESTO', etiqueta: 'Económico', nivel: 1 }],
    };
    expect(mapEscalas(dto).dificultad).toHaveLength(1);
    expect(mapEscalas(dto).presupuesto).toHaveLength(1);
  });
});

describe('mapConfiguracion', () => {
  it('mapea el responsable no definido', () => {
    const dto: ConfiguracionPublica = { nombre_marca: 'Brújula Salvaje', responsable: { definido: false }, texto_descargo: 'x' };
    expect(mapConfiguracion(dto).responsable).toEqual({ definido: false, nombre: null, identificacion: null, domicilio: null, canalAtencion: null });
  });

  it('mapea el responsable definido', () => {
    const dto: ConfiguracionPublica = {
      nombre_marca: 'Brújula Salvaje',
      responsable: { definido: true, nombre: 'Equipo BS', identificacion: '900', domicilio: 'x', canal_atencion: 'correo@x.com' },
      texto_descargo: 'x',
    };
    expect(mapConfiguracion(dto).responsable.nombre).toBe('Equipo BS');
  });
});

describe('mapCreditoMedio / mapPaginaCreditos', () => {
  it('mapea el crédito y sus usos', () => {
    const resultado = mapCreditoMedio({ imagen: IMAGEN, usado_en: [{ slug: 'patagonia', tipo: 'DESTINO', titulo: 'Patagonia' }] });
    expect(resultado.usadoEn).toHaveLength(1);
    expect(resultado.imagen.fuenteUrl).toBe('https://fuente.example');
  });

  it('mapea la página de créditos', () => {
    const dto: PaginaCreditoMedio = {
      anterior: null,
      pagina: 1,
      siguiente: null,
      tamano_pagina: 24,
      total: 1,
      total_paginas: 1,
      resultados: [{ imagen: IMAGEN, usado_en: [] }],
    };
    expect(mapPaginaCreditos(dto).resultados).toHaveLength(1);
  });
});
