import { ErrorApi } from '../http/error-api.model';
import { aErroresDeCampo } from './errores-de-campo';

function error(campos: Record<string, string[]>, mensaje = 'Revisa los campos marcados.'): ErrorApi {
  return { tipo: 'validacion', categoria: 'validacion', codigo: 'validacion', mensaje, campos, traceId: null, extra: {} };
}

describe('aErroresDeCampo (Skill_Frontend §11)', () => {
  it('asigna los mensajes a los controles del formulario y el resto a generales', () => {
    const resultado = aErroresDeCampo(
      error({ nombre: ['Obligatorio.'], _general: ['Conflicto de versión.'], 'dias.2.titulo': ['Máximo 80.'] }),
      ['nombre', 'resumen'],
    );
    expect(resultado.porCampo).toEqual({ nombre: ['Obligatorio.'] });
    expect(resultado.generales).toEqual(['Conflicto de versión.', 'Máximo 80.']);
  });

  it('sin errores por campo usa el mensaje del problema como general', () => {
    expect(aErroresDeCampo(error({}, 'Sesión expirada.'), ['nombre'])).toEqual({ porCampo: {}, generales: ['Sesión expirada.'] });
  });
});
