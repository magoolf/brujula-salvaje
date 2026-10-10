/**
 * DATA: traducción contrato ↔ dominio de la configuración editorial (TKT-024): destacados de inicio
 * (ConfigInicio*), configuración del sitio (ConfiguracionSitio*) y taxonomías (Region, Pais,
 * CategoriaGuiaPanel, Licencia, EscalasPanel). Los DTO mueren aquí (Regla 04).
 */
import { CategoriaGuiaEntrada } from '../../../api/models/categoria-guia-entrada';
import { CategoriaGuiaPanel } from '../../../api/models/categoria-guia-panel';
import { ConfigInicioEntrada } from '../../../api/models/config-inicio-entrada';
import { ConfigInicioPanel } from '../../../api/models/config-inicio-panel';
import { ConfiguracionSitio as ConfiguracionSitioDto } from '../../../api/models/configuracion-sitio';
import { ConfiguracionSitioEntrada } from '../../../api/models/configuracion-sitio-entrada';
import { EscalasPanel as EscalasPanelDto } from '../../../api/models/escalas-panel';
import { Licencia as LicenciaDto } from '../../../api/models/licencia';
import { LicenciaEntrada } from '../../../api/models/licencia-entrada';
import { NivelEscalaPanel as NivelEscalaDto } from '../../../api/models/nivel-escala-panel';
import { Pais as PaisDto } from '../../../api/models/pais';
import { PaisEntrada } from '../../../api/models/pais-entrada';
import { Region as RegionDto } from '../../../api/models/region';
import { RegionEntrada } from '../../../api/models/region-entrada';
import { ConfiguracionSitio, EntradaConfiguracion } from '../domain/configuracion-sitio';
import { ConfigInicio, EntradaDestacados } from '../domain/destacados';
import { RefContenido } from '../domain/formulario-contenido';
import {
  CategoriaGuia,
  EscalasPanel,
  Licencia,
  NivelEscalaPanel,
  Pais,
  Region,
} from '../domain/taxonomias';

// ------------------------------------------------------------------ destacados de inicio
export function mapConfigInicio(dto: ConfigInicioPanel): ConfigInicio {
  const contenidos = new Map((dto.referencias.contenidos ?? []).map((c) => [`${c.tipo}:${c.id}`, c]));
  const refs = (ids: readonly number[] | undefined, tipo: RefContenido['tipo']): readonly RefContenido[] =>
    (ids ?? []).map((id) => {
      const ref = contenidos.get(`${tipo}:${id}`);
      return ref
        ? { id, tipo, titulo: ref.titulo, estado: ref.estado_editorial, slug: ref.slug ?? null }
        : { id, tipo, titulo: `#${id}`, estado: null };
    });
  const miniatura = (dto.referencias.medios ?? []).find((m) => m.id === dto.hero_medio_id) ?? null;
  return {
    titular: dto.hero_titular ?? '',
    subtitulo: dto.hero_subtitulo ?? '',
    medio:
      dto.hero_medio_id === undefined
        ? null
        : {
            id: dto.hero_medio_id,
            estado: miniatura?.estado ?? null,
            miniatura: miniatura?.url_miniatura ?? null,
            textoAlternativo: miniatura?.texto_alternativo ?? null,
          },
    destinos: refs(dto.destinos_ids, 'DESTINO'),
    itinerarios: refs(dto.itinerarios_ids, 'ITINERARIO'),
    guias: refs(dto.guias_ids, 'GUIA'),
    actualizadoEn: new Date(dto.actualizado_en),
    actualizadoPor: dto.actualizado_por.etiqueta,
  };
}

export function aConfigInicioDto(e: EntradaDestacados): ConfigInicioEntrada {
  return {
    hero_titular: e.titular,
    hero_subtitulo: e.subtitulo,
    hero_medio_id: e.medioId,
    destinos_ids: [...e.destinosIds],
    itinerarios_ids: [...e.itinerariosIds],
    guias_ids: [...e.guiasIds],
  };
}

// ------------------------------------------------------------------ configuración del sitio
export function mapConfiguracion(dto: ConfiguracionSitioDto): ConfiguracionSitio {
  return {
    nombreMarca: dto.nombre_marca ?? '',
    lema: dto.lema ?? null,
    textoDescargo: dto.texto_descargo ?? '',
    responsableNombre: dto.responsable_nombre ?? null,
    responsableIdentificacion: dto.responsable_identificacion ?? null,
    responsableDomicilio: dto.responsable_domicilio ?? null,
    responsableCanalAtencion: dto.responsable_canal_atencion ?? null,
    actualizadoEn: new Date(dto.actualizado_en),
  };
}

export function aConfiguracionDto(e: EntradaConfiguracion): ConfiguracionSitioEntrada {
  return {
    nombre_marca: e.nombreMarca,
    lema: e.lema,
    texto_descargo: e.textoDescargo,
    responsable_nombre: e.responsableNombre,
    responsable_identificacion: e.responsableIdentificacion,
    responsable_domicilio: e.responsableDomicilio,
    responsable_canal_atencion: e.responsableCanalAtencion,
  };
}

// ------------------------------------------------------------------ taxonomías
export function mapRegion(dto: RegionDto): Region {
  return {
    catalogo: 'regiones',
    id: dto.id,
    nombre: dto.nombre ?? `Región #${dto.id}`,
    slug: dto.slug ?? '',
    continente: dto.continente ?? 'AMERICA',
    orden: dto.orden ?? 0,
    activo: dto.activo !== false,
  };
}

export function mapPais(dto: PaisDto): Pais {
  return {
    catalogo: 'paises',
    id: dto.id,
    nombre: dto.nombre ?? `País #${dto.id}`,
    slug: dto.slug ?? '',
    codigoIso2: dto.codigo_iso2 ?? '',
    regionId: dto.region_id ?? 0,
    activo: dto.activo !== false,
  };
}

export function mapCategoria(dto: CategoriaGuiaPanel): CategoriaGuia {
  return {
    catalogo: 'categorias',
    id: dto.id,
    nombre: dto.nombre ?? `Categoría #${dto.id}`,
    slug: dto.slug ?? '',
    descripcion: dto.descripcion ?? '',
    orden: dto.orden ?? 0,
    activo: dto.activo !== false,
  };
}

export function mapLicenciaCatalogo(dto: LicenciaDto): Licencia {
  return {
    catalogo: 'licencias',
    id: dto.id,
    codigo: dto.codigo ?? '',
    nombre: dto.nombre ?? `Licencia #${dto.id}`,
    urlTextoLegal: dto.url_texto_legal ?? null,
    requiereAtribucion: dto.requiere_atribucion !== false,
    compatiblePublicacion: dto.compatible_publicacion === true,
    activo: dto.activo !== false,
  };
}

export function mapNivel(dto: NivelEscalaDto): NivelEscalaPanel {
  return { id: dto.id, escala: dto.escala, nivel: dto.nivel, etiqueta: dto.etiqueta, descripcion: dto.descripcion };
}

export function mapEscalas(dto: EscalasPanelDto): EscalasPanel {
  const ordenar = (lista: readonly NivelEscalaDto[]): readonly NivelEscalaPanel[] =>
    [...lista].sort((a, b) => a.nivel - b.nivel).map(mapNivel);
  return { dificultad: ordenar(dto.dificultad), presupuesto: ordenar(dto.presupuesto) };
}

export function aRegionDto(e: Omit<Region, 'id'>): RegionEntrada {
  return { nombre: e.nombre, slug: e.slug, continente: e.continente, orden: e.orden, activo: e.activo };
}

export function aPaisDto(e: Omit<Pais, 'id'>): PaisEntrada {
  return { nombre: e.nombre, slug: e.slug, codigo_iso2: e.codigoIso2, region_id: e.regionId, activo: e.activo };
}

export function aCategoriaDto(e: Omit<CategoriaGuia, 'id'>): CategoriaGuiaEntrada {
  return { nombre: e.nombre, slug: e.slug, descripcion: e.descripcion, orden: e.orden, activo: e.activo };
}

export function aLicenciaDto(e: Omit<Licencia, 'id'>): LicenciaEntrada {
  return {
    codigo: e.codigo,
    nombre: e.nombre,
    url_texto_legal: e.urlTextoLegal,
    requiere_atribucion: e.requiereAtribucion,
    compatible_publicacion: e.compatiblePublicacion,
    activo: e.activo,
  };
}
