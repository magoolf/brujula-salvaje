import { DestinoTarjeta } from '../../../api/models/destino-tarjeta';
import { GuiaTarjeta } from '../../../api/models/guia-tarjeta';
import { ImagenPublica } from '../../../api/models/imagen-publica';
import { ImagenPublicaNula } from '../../../api/models/imagen-publica-nula';
import { Inicio as InicioDto } from '../../../api/models/inicio';
import { ItinerarioTarjeta } from '../../../api/models/itinerario-tarjeta';
import { TipoAventuraTarjeta } from '../../../api/models/tipo-aventura-tarjeta';
import {
  DestinoTarjetaInicio,
  GuiaTarjetaInicio,
  Inicio,
  ImagenVista,
  ItinerarioTarjetaInicio,
  TipoTarjetaInicio,
} from '../domain/modelos';

function mapImagen(dto: ImagenPublicaNula | ImagenPublica | undefined): ImagenVista | null {
  if (dto === undefined || dto === null) return null;
  return {
    src: dto.derivados[0]?.url ?? '',
    alt: dto.texto_alternativo,
    ancho: dto.ancho ?? 0,
    alto: dto.alto ?? 0,
    derivados: dto.derivados.map((d) => ({ url: d.url, ancho: d.ancho })),
  };
}

function mapDestino(dto: DestinoTarjeta): DestinoTarjetaInicio {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    pais: { slug: dto.pais.slug, nombre: dto.pais.nombre },
    dificultad: dto.dificultad,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapItinerario(dto: ItinerarioTarjeta): ItinerarioTarjetaInicio {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    duracionDias: dto.duracion_dias,
    dificultad: dto.dificultad,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapGuia(dto: GuiaTarjeta): GuiaTarjetaInicio {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

function mapTipo(dto: TipoAventuraTarjeta): TipoTarjetaInicio {
  return {
    slug: dto.slug,
    titulo: dto.titulo,
    resumen: dto.resumen,
    nivelExigencia: dto.nivel_exigencia,
    numeroDestinos: dto.numero_destinos,
    imagen: mapImagen(dto.portada ?? undefined),
  };
}

export function mapInicio(dto: InicioDto): Inicio {
  return {
    hero: dto.hero
      ? { titular: dto.hero.titular, subtitulo: dto.hero.subtitulo, imagen: mapImagen(dto.hero.imagen) }
      : null,
    destinos: dto.destinos.map(mapDestino),
    itinerarios: dto.itinerarios.map(mapItinerario),
    guias: dto.guias.map(mapGuia),
    tipos: dto.tipos.map(mapTipo),
  };
}
