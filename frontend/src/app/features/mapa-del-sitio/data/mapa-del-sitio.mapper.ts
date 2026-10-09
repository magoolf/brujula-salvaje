/**
 * DATA: traducción del contrato OpenAPI hacia el dominio del Mapa del sitio (Skill_Frontend
 * §5.3). Los DTO del cliente generado mueren aquí (Regla 04).
 */
import { EntradaIndice } from '../../../api/models/entrada-indice';
import { Meses } from '../../../api/models/meses';
import { TerminoGlosarioPublico } from '../../../api/models/termino-glosario-publico';
import { EntradaIndiceVista, MesVista, TerminoVista } from '../domain/modelos';

export function mapEntradaIndice(dto: EntradaIndice): EntradaIndiceVista {
  const agrupacion = dto.agrupacion ?? null;
  return {
    tipo: dto.tipo,
    slug: dto.slug,
    titulo: dto.titulo,
    agrupacion: agrupacion === null ? null : { slug: agrupacion.slug, nombre: agrupacion.nombre },
  };
}

export function mapMeses(dto: Meses): readonly MesVista[] {
  return dto.meses.map((m) => ({
    numero: m.mes,
    slug: m.slug,
    nombre: m.nombre,
    numeroDestinos: m.numero_destinos,
  }));
}

export function mapTermino(dto: TerminoGlosarioPublico, pagina: number): TerminoVista {
  return { slug: dto.slug, termino: dto.termino, pagina };
}
