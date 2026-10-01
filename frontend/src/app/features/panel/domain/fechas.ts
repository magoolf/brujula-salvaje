/**
 * Formato de fechas del panel con Intl (es-CO), sin DatePipe: así el panel no arrastra
 * CommonModule al chunk que comparte con la carga inicial pública (QA TKT-010 ciclo 1, FALLO-02).
 */
import { LOCALE } from '../../../core/seo/marca';

const FECHA_LARGA = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'long' });
const FECHA_HORA = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeStyle: 'short' });

/** «1 de febrero de 2026». */
export function formatearFechaLarga(fecha: Date): string {
  return FECHA_LARGA.format(fecha);
}

/** «29/09/2026, 3:00 a. m.» (según la configuración regional del navegador para es-CO). */
export function formatearFechaHora(fecha: Date): string {
  return FECHA_HORA.format(fecha);
}
