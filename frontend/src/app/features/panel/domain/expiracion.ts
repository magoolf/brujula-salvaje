/**
 * Expiración de la sesión por inactividad (AC-109, FEAT-029): aviso 2 min antes con cuenta atrás
 * (HANDOFF_UI_UX, diálogo «Tu sesión está por expirar»; WCAG 2.2.1 permite extender).
 */
export const AVISO_EXPIRACION_SEGUNDOS = 120;
/** La cuenta atrás se anuncia al abrir y al quedar 30 s (evita ruido de lector de pantalla). */
export const ANUNCIO_FINAL_SEGUNDOS = 30;

export function segundosRestantes(expiraEn: Date, ahora: Date): number {
  return Math.max(0, Math.floor((expiraEn.getTime() - ahora.getTime()) / 1000));
}

export function debeAvisarExpiracion(restantes: number): boolean {
  return restantes > 0 && restantes <= AVISO_EXPIRACION_SEGUNDOS;
}

/** «1:45», «0:09». */
export function formatearCuentaAtras(segundos: number): string {
  const s = Math.max(0, Math.floor(segundos));
  const minutos = Math.floor(s / 60);
  const resto = s % 60;
  return `${minutos}:${resto.toString().padStart(2, '0')}`;
}

/** Texto para la región viva: solo al abrir el aviso y al quedar 30 s. */
export function textoAnuncioExpiracion(restantes: number, alAbrir: boolean): string | null {
  if (alAbrir || restantes === ANUNCIO_FINAL_SEGUNDOS) {
    return `Por inactividad, tu sesión se cerrará en ${formatearCuentaAtras(restantes)}.`;
  }
  return null;
}
