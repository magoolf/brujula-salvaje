/**
 * DATA: respuesta de la vista previa (VistaPrevia: `forma` + `datos` con la forma del `*Detalle`
 * público, los campos aún no completados pueden faltar o ser null) → modelo de presentación de
 * SCR-037. Lectura defensiva: nunca falla por un campo ausente.
 */
import { VistaPrevia } from '../../../api/models/vista-previa';
import {
  BloqueTexto,
  DatoClave,
  DerivadoVistaPrevia,
  ElementoLista,
  EnlacePublico,
  FuenteVistaPrevia,
  ImagenVistaPrevia,
  VistaPreviaContenido,
  rutaPublica,
  textoDuracion,
  textoEscala,
  textoMeses,
} from '../domain/vista-previa';
import { TipoContenido } from '../domain/modelos';
import { mapRequisitos } from './contenidos.mapper';

type Datos = Readonly<Record<string, unknown>>;

const FORMATOS: readonly DerivadoVistaPrevia['formato'][] = ['AVIF', 'WEBP', 'JPEG'];

function objeto(valor: unknown): Datos | null {
  return typeof valor === 'object' && valor !== null && !Array.isArray(valor) ? (valor as Datos) : null;
}

function objetos(valor: unknown): readonly Datos[] {
  return Array.isArray(valor) ? valor.map(objeto).filter((o): o is Datos => o !== null) : [];
}

function texto(valor: unknown): string | null {
  return typeof valor === 'string' && valor.trim() !== '' ? valor : null;
}

function numero(valor: unknown): number | null {
  return typeof valor === 'number' && Number.isFinite(valor) ? valor : null;
}

function numeros(valor: unknown): readonly number[] {
  return Array.isArray(valor) ? valor.filter((v): v is number => typeof v === 'number') : [];
}

function nombre(valor: unknown): string | null {
  return texto(objeto(valor)?.['nombre']);
}

function imagen(valor: unknown): ImagenVistaPrevia | null {
  const dato = objeto(valor);
  if (dato === null) return null;
  const derivados = objetos(dato['derivados']).flatMap((d): DerivadoVistaPrevia[] => {
    const url = texto(d['url']);
    const ancho = numero(d['ancho']);
    const formato = FORMATOS.find((f) => f === d['formato']);
    return url && ancho && formato ? [{ url, ancho, formato }] : [];
  });
  if (derivados.length === 0) return null;
  const mayor = [...derivados].sort((a, b) => b.ancho - a.ancho)[0];
  const ancho = numero(dato['ancho']) ?? mayor.ancho;
  const alto = numero(dato['alto']) ?? Math.round((ancho * 2) / 3);
  return {
    src: mayor.url,
    alt: texto(dato['texto_alternativo']) ?? '',
    ancho,
    alto,
    derivados,
    credito: texto(dato['autor_credito']),
    pie: texto(dato['pie_de_foto']),
  };
}

function dato(etiqueta: string, valor: string | null): DatoClave[] {
  return valor === null ? [] : [{ etiqueta, valor }];
}

function bloque(titulo: string, valor: unknown): BloqueTexto[] {
  const html = texto(valor);
  return html === null ? [] : [{ titulo, html }];
}

function fuentes(valor: unknown): readonly FuenteVistaPrevia[] {
  return objetos(valor).flatMap((f) => {
    const titulo = texto(f['titulo']);
    if (titulo === null) return [];
    const url = texto(f['url']);
    return [
      {
        titulo,
        url: url !== null && /^https?:\/\//i.test(url) ? url : null,
        entidad: texto(f['entidad_editora']),
      },
    ];
  });
}

function enlaces(valor: unknown, tipoPorDefecto: string | null = null): readonly EnlacePublico[] {
  return objetos(valor).flatMap((r) => {
    const titulo = texto(r['titulo']);
    const tipo = texto(r['tipo']) ?? tipoPorDefecto;
    const ruta = tipo === null ? null : rutaPublica(tipo, texto(r['slug']));
    return titulo !== null && ruta !== null ? [{ titulo, ruta }] : [];
  });
}

function nombresDe(valor: unknown): string | null {
  const nombres = objetos(valor)
    .map((o) => texto(o['nombre']))
    .filter((n): n is string => n !== null);
  return nombres.length === 0 ? null : nombres.join(', ');
}

function revision(datos: Datos): string | null {
  return texto(objeto(datos['metadatos'])?.['fecha_ultima_revision']);
}

function vacio(tipo: TipoContenido, datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  return {
    tipo,
    titulo: texto(datos['titulo']) ?? 'Sin título',
    antetitulo: null,
    resumen: texto(datos['resumen']),
    portada: imagen(datos['portada']),
    datos: [],
    bloques: [],
    listas: [],
    galeria: objetos(datos['galeria'])
      .map(imagen)
      .filter((i): i is ImagenVistaPrevia => i !== null),
    fuentes: fuentes(datos['fuentes']),
    enlaces: enlaces(datos['relacionados']),
    revision: revision(datos),
  };
}

function destino(datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  return {
    ...vacio('DESTINO', datos),
    antetitulo: nombre(datos['pais']),
    datos: [
      ...dato('Tipo principal', nombre(datos['tipo_principal'])),
      ...dato('Tipos de aventura', nombresDe(datos['tipos'])),
      ...dato('Dificultad', textoEscala(numero(datos['dificultad']), 5)),
      ...dato('Duración', textoDuracion(numero(datos['duracion_min_dias']), numero(datos['duracion_max_dias']))),
      ...dato('Presupuesto', textoEscala(numero(datos['nivel_presupuesto']), 4)),
      ...dato('Mejores meses', textoMeses(numeros(datos['meses_mejor_epoca']))),
      ...dato('Clima', texto(datos['clima'])),
      ...dato('Altitud máxima', numero(datos['altitud_max_m']) === null ? null : `${numero(datos['altitud_max_m'])} m`),
      ...dato(
        'Coordenadas',
        numero(datos['latitud']) === null || numero(datos['longitud']) === null
          ? null
          : `${numero(datos['latitud'])}, ${numero(datos['longitud'])}`,
      ),
    ],
    bloques: [
      ...bloque('Descripción', datos['descripcion_experta']),
      ...bloque('Cómo llegar', datos['como_llegar']),
      ...bloque('Seguridad y riesgos', datos['seguridad_riesgos']),
      ...bloque('Sostenibilidad', datos['sostenibilidad']),
    ],
  };
}

function itinerario(datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  const dias: ElementoLista[] = [...objetos(datos['dias'])]
    .sort((a, b) => (numero(a['numero_dia']) ?? 0) - (numero(b['numero_dia']) ?? 0))
    .map((d) => ({
      titulo: `Día ${numero(d['numero_dia']) ?? '?'}: ${texto(d['titulo']) ?? ''}`.trim(),
      detalle: texto(d['alojamiento_orientativo']),
      html: texto(d['actividades']),
      destacado: false,
    }));
  const base = vacio('ITINERARIO', datos);
  return {
    ...base,
    antetitulo: texto(objeto(datos['destino'])?.['titulo']),
    datos: [
      ...dato('Duración', textoDuracion(numero(datos['duracion_dias']), null)),
      ...dato('Dificultad', textoEscala(numero(datos['dificultad']), 5)),
      ...dato('Tipos de aventura', nombresDe(datos['tipos'])),
      ...dato('Distancia total', numero(datos['distancia_total_km']) === null ? null : `${numero(datos['distancia_total_km'])} km`),
      ...dato('Desnivel acumulado', numero(datos['desnivel_acumulado_m']) === null ? null : `${numero(datos['desnivel_acumulado_m'])} m`),
    ],
    bloques: bloque('Riesgos y seguridad', datos['riesgos_seguridad']),
    listas: dias.length === 0 ? [] : [{ titulo: 'Día a día', elementos: dias, ordenada: true }],
    enlaces: [...enlaces([objeto(datos['destino'])].filter(Boolean), 'DESTINO'), ...base.enlaces],
  };
}

function guia(datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  const base = vacio('GUIA', datos);
  return {
    ...base,
    antetitulo: nombre(datos['categoria']),
    datos: dato('Tipos relacionados', nombresDe(datos['tipos_relacionados'])),
    bloques: bloque('Guía', datos['cuerpo']),
    enlaces: [...enlaces(datos['destinos_relacionados'], 'DESTINO'), ...base.enlaces],
  };
}

function tipo(datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  const checklist: ElementoLista[] = [...objetos(datos['checklist'])]
    .sort((a, b) => (numero(a['orden']) ?? 0) - (numero(b['orden']) ?? 0))
    .flatMap((c) => {
      const t = texto(c['texto']);
      return t === null
        ? []
        : [{ titulo: t, detalle: texto(c['grupo']), html: null, destacado: c['esencial'] === true }];
    });
  return {
    ...vacio('TIPO', datos),
    datos: dato('Nivel de exigencia', textoEscala(numero(datos['nivel_exigencia']), 5)),
    bloques: bloque('Descripción', datos['descripcion']),
    listas: checklist.length === 0 ? [] : [{ titulo: 'Checklist', elementos: checklist, ordenada: false }],
  };
}

function coleccion(datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  const elementos = [...objetos(datos['elementos'])]
    .sort((a, b) => (numero(a['orden']) ?? 0) - (numero(b['orden']) ?? 0))
    .flatMap((e): { readonly elemento: ElementoLista; readonly enlace: EnlacePublico | null }[] => {
      const contenido = objeto(e['destino']) ?? objeto(e['itinerario']);
      const titulo = texto(contenido?.['titulo']);
      if (titulo === null) return [];
      const tipoElemento = e['tipo'] === 'ITINERARIO' ? 'ITINERARIO' : 'DESTINO';
      const ruta = rutaPublica(tipoElemento, texto(contenido?.['slug']));
      return [
        {
          elemento: { titulo, detalle: texto(e['nota_editorial']), html: null, destacado: false },
          enlace: ruta === null ? null : { titulo, ruta },
        },
      ];
    });
  return {
    ...vacio('COLECCION', datos),
    bloques: bloque('Descripción', datos['descripcion']),
    listas:
      elementos.length === 0
        ? []
        : [{ titulo: 'En esta colección', elementos: elementos.map((e) => e.elemento), ordenada: true }],
    enlaces: elementos.map((e) => e.enlace).filter((e): e is EnlacePublico => e !== null),
  };
}

function pagina(datos: Datos): Omit<VistaPreviaContenido, 'marca' | 'requisitos'> {
  const version = texto(datos['version_documento']);
  return {
    ...vacio('PAGINA', datos),
    datos: [
      ...dato('Versión', version),
      ...dato('Vigente desde', texto(datos['vigente_desde'])),
    ],
    bloques: bloque('Contenido', datos['cuerpo']),
  };
}

const POR_FORMA: Readonly<Record<VistaPrevia['forma'], (datos: Datos) => Omit<VistaPreviaContenido, 'marca' | 'requisitos'>>> = {
  DestinoDetalle: destino,
  ItinerarioDetalle: itinerario,
  GuiaDetalle: guia,
  TipoAventuraDetalle: tipo,
  ColeccionDetalle: coleccion,
  PaginaInstitucionalPublica: pagina,
};

export function mapVistaPrevia(dto: VistaPrevia): VistaPreviaContenido {
  const datos = objeto(dto.datos) ?? {};
  return {
    ...POR_FORMA[dto.forma](datos),
    marca: dto.marca,
    requisitos: mapRequisitos(dto.requisitos_publicacion),
  };
}
