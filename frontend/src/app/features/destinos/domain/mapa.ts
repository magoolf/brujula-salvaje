/**
 * Lógica pura del mapa de destinos (FEAT-005, SCR-003). DEC-AUTO-TKT008-01 (documentada en el
 * HANDOFF del ticket): se usa una proyección equirrectangular (Plate Carrée) en vez de Equal Earth
 * y una cartografía decorativa simplificada en vez del SVG real de Natural Earth 1:110m — riesgo
 * bajo y reversible; la posición matemática de cada marcador es correcta, solo cambia la fidelidad
 * visual del fondo. Sin dependencias de Angular ni RxJS (Regla 08).
 */
import { PuntoMapa } from './modelos';

/** Proyecta lat/lon a un punto en porcentaje (0-100) dentro del contenedor del mapa. */
export function proyectar(latitud: number, longitud: number): { readonly xPct: number; readonly yPct: number } {
  const xPct = ((longitud + 180) / 360) * 100;
  const yPct = ((90 - latitud) / 180) * 100;
  return { xPct: clamp(xPct, 0, 100), yPct: clamp(yPct, 0, 100) };
}

function clamp(valor: number, minimo: number, maximo: number): number {
  return Math.min(maximo, Math.max(minimo, valor));
}

export interface MarcadorProyectado {
  readonly punto: PuntoMapa;
  readonly xPct: number;
  readonly yPct: number;
}

export interface ClusterMapa {
  readonly tipo: 'cluster';
  readonly xPct: number;
  readonly yPct: number;
  readonly puntos: readonly PuntoMapa[];
  readonly region: string;
}

export interface MarcadorIndividual {
  readonly tipo: 'marcador';
  readonly punto: PuntoMapa;
  readonly xPct: number;
  readonly yPct: number;
}

export type ElementoMapa = ClusterMapa | MarcadorIndividual;

/**
 * Agrupa marcadores proyectados a menos de `umbralPct` de distancia entre sí en un MapCluster
 * (agrupación simple de una pasada: cada punto se une al primer grupo cercano encontrado).
 */
export function agruparMarcadores(
  puntos: readonly PuntoMapa[],
  umbralPct = 5,
): readonly ElementoMapa[] {
  const proyectados: MarcadorProyectado[] = puntos.map((punto) => ({
    punto,
    ...proyectar(punto.latitud, punto.longitud),
  }));

  const grupos: MarcadorProyectado[][] = [];
  for (const actual of proyectados) {
    const grupo = grupos.find((g) =>
      g.some((otro) => distancia(otro, actual) < umbralPct),
    );
    if (grupo) grupo.push(actual);
    else grupos.push([actual]);
  }

  return grupos.map((grupo) => {
    if (grupo.length === 1) {
      return { tipo: 'marcador', punto: grupo[0].punto, xPct: grupo[0].xPct, yPct: grupo[0].yPct };
    }
    const xPct = promedio(grupo.map((g) => g.xPct));
    const yPct = promedio(grupo.map((g) => g.yPct));
    return {
      tipo: 'cluster',
      xPct,
      yPct,
      puntos: grupo.map((g) => g.punto),
      region: grupo[0].punto.region.nombre,
    };
  });
}

function distancia(a: { xPct: number; yPct: number }, b: { xPct: number; yPct: number }): number {
  return Math.hypot(a.xPct - b.xPct, a.yPct - b.yPct);
}

function promedio(valores: readonly number[]): number {
  return valores.reduce((suma, v) => suma + v, 0) / valores.length;
}

/** Centro (promedio simple) de un conjunto de puntos, usado para centrar el zoom por preset de región. */
export function centroide(puntos: readonly PuntoMapa[]): { readonly latitud: number; readonly longitud: number } | null {
  if (puntos.length === 0) return null;
  return {
    latitud: promedio(puntos.map((p) => p.latitud)),
    longitud: promedio(puntos.map((p) => p.longitud)),
  };
}

/** Formato es-CO de coordenadas, p. ej. «4,5709° N, 74,2973° O» (SCR-004 Ubicación). */
export function formatoCoordenadas(latitud: number, longitud: number): string {
  const lat = Math.abs(latitud).toLocaleString('es-CO', { maximumFractionDigits: 4, minimumFractionDigits: 4 });
  const lon = Math.abs(longitud).toLocaleString('es-CO', { maximumFractionDigits: 4, minimumFractionDigits: 4 });
  const nortesur = latitud >= 0 ? 'N' : 'S';
  const esteoeste = longitud >= 0 ? 'E' : 'O';
  return `${lat}° ${nortesur}, ${lon}° ${esteoeste}`;
}
