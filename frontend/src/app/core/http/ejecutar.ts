import { Observable, firstValueFrom } from 'rxjs';

import { ErrorApi } from './error-api.model';
import { normalizarError } from './normalizar-error';

/**
 * Mecanismo único de escritura (Skill_Frontend Regla 11) y contrato de los comandos (Regla 12):
 * ejecuta la operación y devuelve `null` si tuvo éxito o el `ErrorApi` normalizado si falló.
 * Los stores lo usan en sus comandos; así STATE y UI no necesitan `catchError` (Regla 10).
 *
 * @param operacion Observable frío de la escritura (p. ej. una función del cliente generado).
 * @param alCompletar Efecto opcional tras el éxito (p. ej. `recurso.reload()`, §7).
 */
export async function ejecutar<T>(
  operacion: Observable<T>,
  alCompletar?: (valor: T) => void,
): Promise<ErrorApi | null> {
  try {
    const valor = await firstValueFrom(operacion);
    alCompletar?.(valor);
    return null;
  } catch (error: unknown) {
    return normalizarError(error);
  }
}
