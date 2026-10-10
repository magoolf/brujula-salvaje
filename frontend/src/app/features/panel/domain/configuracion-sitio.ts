/**
 * Configuración del sitio (SCR-047, FEAT-047, RULE-014, AC-070, TKT-024): marca, lema, texto del
 * descargo y datos del Responsable del tratamiento. Solo la edita el Administrador. Puro: sin
 * Angular ni RxJS (Regla 08).
 */
import { ErroresTraducidos, erroresPorCampo, longitudTexto } from './errores-formulario';

export interface ConfiguracionSitio {
  readonly nombreMarca: string;
  readonly lema: string | null;
  readonly textoDescargo: string;
  readonly responsableNombre: string | null;
  readonly responsableIdentificacion: string | null;
  readonly responsableDomicilio: string | null;
  readonly responsableCanalAtencion: string | null;
  readonly actualizadoEn: Date;
}

/** Valores del formulario (texto tal y como se escribe). */
export interface FormularioConfiguracion {
  readonly nombreMarca: string;
  readonly lema: string;
  readonly textoDescargo: string;
  readonly responsableNombre: string;
  readonly responsableIdentificacion: string;
  readonly responsableDomicilio: string;
  readonly responsableCanalAtencion: string;
}

export type CampoConfiguracion = keyof FormularioConfiguracion;

/** Entrada de escritura (ConfiguracionSitioEntrada): vacíos opcionales → null. */
export type EntradaConfiguracion = Omit<ConfiguracionSitio, 'actualizadoEn'>;

/** Longitudes máximas del contrato (ConfiguracionSitioCampos). */
export const LIMITES_CONFIGURACION: Readonly<Record<CampoConfiguracion, number>> = {
  nombreMarca: 60,
  lema: 120,
  textoDescargo: 5000,
  responsableNombre: 150,
  responsableIdentificacion: 40,
  responsableDomicilio: 200,
  responsableCanalAtencion: 200,
};

/** Campos del formulario en orden de pantalla (foco en el primer error). */
export const CAMPOS_CONFIGURACION: readonly CampoConfiguracion[] = [
  'nombreMarca',
  'lema',
  'textoDescargo',
  'responsableNombre',
  'responsableIdentificacion',
  'responsableDomicilio',
  'responsableCanalAtencion',
];

/** Nombre del campo en el contrato (para traducir los errores 400 por campo). */
export const CAMPO_API_CONFIGURACION: Readonly<Record<CampoConfiguracion, string>> = {
  nombreMarca: 'nombre_marca',
  lema: 'lema',
  textoDescargo: 'texto_descargo',
  responsableNombre: 'responsable_nombre',
  responsableIdentificacion: 'responsable_identificacion',
  responsableDomicilio: 'responsable_domicilio',
  responsableCanalAtencion: 'responsable_canal_atencion',
};

const OBLIGATORIOS: readonly CampoConfiguracion[] = ['nombreMarca', 'textoDescargo'];

const RESPONSABLE: readonly CampoConfiguracion[] = [
  'responsableNombre',
  'responsableIdentificacion',
  'responsableDomicilio',
  'responsableCanalAtencion',
];

export const AVISO_RESPONSABLE_VACIO =
  'Mientras falten estos datos, las páginas legales mostrarán [RESPONSABLE POR DEFINIR].';

export function formularioDesdeConfiguracion(c: ConfiguracionSitio): FormularioConfiguracion {
  return {
    nombreMarca: c.nombreMarca,
    lema: c.lema ?? '',
    textoDescargo: c.textoDescargo,
    responsableNombre: c.responsableNombre ?? '',
    responsableIdentificacion: c.responsableIdentificacion ?? '',
    responsableDomicilio: c.responsableDomicilio ?? '',
    responsableCanalAtencion: c.responsableCanalAtencion ?? '',
  };
}

/** Validación de formato antes de enviar (el servidor sigue siendo la autoridad). */
export function validarConfiguracion(
  f: FormularioConfiguracion,
): Partial<Record<CampoConfiguracion, string>> {
  const errores: Partial<Record<CampoConfiguracion, string>> = {};
  for (const campo of CAMPOS_CONFIGURACION) {
    const valor = f[campo];
    if (OBLIGATORIOS.includes(campo) && valor.trim() === '') {
      errores[campo] = 'Este campo es obligatorio.';
    } else if (longitudTexto(valor.trim()) > LIMITES_CONFIGURACION[campo]) {
      errores[campo] = `Usa como máximo ${LIMITES_CONFIGURACION[campo]} caracteres.`;
    }
  }
  return errores;
}

function opcional(valor: string): string | null {
  const limpio = valor.trim();
  return limpio === '' ? null : limpio;
}

export function entradaDesdeFormulario(f: FormularioConfiguracion): EntradaConfiguracion {
  return {
    nombreMarca: f.nombreMarca.trim(),
    lema: opcional(f.lema),
    textoDescargo: f.textoDescargo.trim(),
    responsableNombre: opcional(f.responsableNombre),
    responsableIdentificacion: opcional(f.responsableIdentificacion),
    responsableDomicilio: opcional(f.responsableDomicilio),
    responsableCanalAtencion: opcional(f.responsableCanalAtencion),
  };
}

/** GAP-004 / AC-070: falta algún dato del Responsable → marcador en las páginas legales. */
export function responsableIncompleto(f: FormularioConfiguracion): boolean {
  return RESPONSABLE.some((campo) => f[campo].trim() === '');
}

export function hayCambiosConfiguracion(
  actual: FormularioConfiguracion,
  guardado: FormularioConfiguracion | null,
): boolean {
  if (guardado === null) return false;
  return CAMPOS_CONFIGURACION.some((campo) => actual[campo] !== guardado[campo]);
}

/**
 * Errores de la API por campo del formulario (400 con `errors`); los que no son de un campo
 * conocido (o el mensaje del problema si no hay ninguno) van al resumen.
 */
export function erroresConfiguracion(
  campos: Readonly<Record<string, readonly string[]>>,
  mensaje: string,
): ErroresTraducidos<CampoConfiguracion> {
  return erroresPorCampo(CAMPO_API_CONFIGURACION, campos, mensaje);
}
