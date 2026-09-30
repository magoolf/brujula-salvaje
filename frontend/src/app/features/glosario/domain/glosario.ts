import { TerminoGlosarioVista } from './modelos';

export interface GrupoLetra {
  readonly letra: string;
  readonly terminos: readonly TerminoGlosarioVista[];
}

/** Primera letra (A-Z) del término, sin tildes (alfabeto español simplificado, DEC-AUTO-similar a RULE-018). */
export function letraInicial(termino: string): string {
  const primera = termino.trim().charAt(0).toUpperCase();
  const sinTilde = primera.normalize('NFD').replace(/[̀-ͯ]/g, '');
  return sinTilde === '' ? '#' : sinTilde;
}

/**
 * SCR-018: agrupa los términos por letra inicial, preservando el orden alfabético en el que ya
 * llegan del backend (RULE-018-adjacent: orden alfabético español sin tildes).
 */
export function agruparPorLetra(terminos: readonly TerminoGlosarioVista[]): readonly GrupoLetra[] {
  const grupos: GrupoLetra[] = [];
  const indicePorLetra = new Map<string, number>();
  for (const termino of terminos) {
    const letra = letraInicial(termino.termino);
    let indice = indicePorLetra.get(letra);
    if (indice === undefined) {
      indice = grupos.length;
      indicePorLetra.set(letra, indice);
      grupos.push({ letra, terminos: [] });
    }
    (grupos[indice].terminos as TerminoGlosarioVista[]).push(termino);
  }
  return grupos;
}

/** Letras del alfabeto español (sin Ñ tratada aparte: DEC-AUTO simplificado, 26 letras A-Z). */
export const ALFABETO: readonly string[] = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
