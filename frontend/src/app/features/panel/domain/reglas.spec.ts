import { formatearFechaHora, formatearFechaLarga } from './fechas';
import {
  MENSAJE_ACTUAL_OBLIGATORIA,
  MENSAJE_NO_COINCIDEN,
  MENSAJE_POLITICA_CONTRASENA,
  validarCambioContrasena,
} from './contrasena';
import {
  debeAvisarExpiracion,
  formatearCuentaAtras,
  segundosRestantes,
  textoAnuncioExpiracion,
} from './expiracion';
import { TableroPanel } from './modelos';
import {
  SeccionPanel,
  accesosRapidos,
  activoSoloExacto,
  enlaceDisponible,
  puedeAcceder,
  seccionDeRuta,
  seccionesVisibles,
  SECCIONES_PANEL,
} from './secciones';
import { esTableroVacio, hayAvisosDeSalud, totalConteo, varianteEstado } from './tablero';

describe('cambio de contraseña (RULE-017)', () => {
  it('AC_TKT010_04 contraseña débil (< 12) → error bajo «Nueva contraseña»', () => {
    expect(validarCambioContrasena({ actual: 'x', nueva: 'corta', confirmacion: 'corta' })).toEqual({
      contrasena_nueva: MENSAJE_POLITICA_CONTRASENA,
    });
  });

  it('AC_TKT010_04 confirmación distinta y actual vacía', () => {
    expect(
      validarCambioContrasena({ actual: '', nueva: 'una frase larga y segura', confirmacion: 'otra' }),
    ).toEqual({ contrasena_actual: MENSAJE_ACTUAL_OBLIGATORIA, confirmacion: MENSAJE_NO_COINCIDEN });
  });

  it('datos válidos → sin errores', () => {
    expect(
      validarCambioContrasena({
        actual: 'temporal',
        nueva: 'una frase larga y segura',
        confirmacion: 'una frase larga y segura',
      }),
    ).toEqual({});
  });
});

describe('expiración por inactividad (AC-109)', () => {
  const base = new Date('2026-09-30T10:00:00Z');

  it('AC_TKT010_11 segundos restantes y ventana de aviso de 2 minutos', () => {
    expect(segundosRestantes(new Date(base.getTime() + 90_500), base)).toBe(90);
    expect(segundosRestantes(new Date(base.getTime() - 5_000), base)).toBe(0);
    expect(debeAvisarExpiracion(121)).toBe(false);
    expect(debeAvisarExpiracion(120)).toBe(true);
    expect(debeAvisarExpiracion(1)).toBe(true);
    expect(debeAvisarExpiracion(0)).toBe(false);
  });

  it('AC_TKT010_11 cuenta atrás «m:ss» y anuncios solo al abrir y a los 30 s', () => {
    expect(formatearCuentaAtras(105)).toBe('1:45');
    expect(formatearCuentaAtras(9)).toBe('0:09');
    expect(formatearCuentaAtras(-3)).toBe('0:00');
    expect(textoAnuncioExpiracion(105, true)).toBe('Por inactividad, tu sesión se cerrará en 1:45.');
    expect(textoAnuncioExpiracion(30, false)).toBe('Por inactividad, tu sesión se cerrará en 0:30.');
    expect(textoAnuncioExpiracion(29, false)).toBeNull();
  });
});

describe('catálogo de secciones (DEC-ESTRUCTURA-03, RULE-030)', () => {
  const catalogo: readonly SeccionPanel[] = [
    { id: 'tablero', etiqueta: 'Tablero', ruta: '/panel', rolMinimo: 'EDITOR', accesosRapidos: [] },
    {
      id: 'medios',
      etiqueta: 'Medios',
      ruta: '/panel/medios',
      rolMinimo: 'EDITOR',
      accesosRapidos: [{ id: 'subir', etiqueta: 'Subir medios', ruta: '/panel/medios' }],
    },
    {
      id: 'usuarios',
      etiqueta: 'Cuentas',
      ruta: '/panel/usuarios',
      rolMinimo: 'ADMINISTRADOR',
      accesosRapidos: [{ id: 'cuentas', etiqueta: 'Cuentas', ruta: '/panel/usuarios' }],
    },
  ];

  it('AC_TKT010_08 el Editor no accede a lo de Administrador; el Administrador accede a todo', () => {
    expect(puedeAcceder('EDITOR', 'EDITOR')).toBe(true);
    expect(puedeAcceder('EDITOR', 'ADMINISTRADOR')).toBe(false);
    expect(puedeAcceder('ADMINISTRADOR', 'ADMINISTRADOR')).toBe(true);
    expect(puedeAcceder(null, 'EDITOR')).toBe(false);
    expect(puedeAcceder(undefined, 'EDITOR')).toBe(false);
  });

  it('AC_TKT010_08 la navegación oculta al Editor las secciones de Administrador', () => {
    expect(seccionesVisibles('EDITOR', catalogo).map((s) => s.id)).toEqual(['tablero', 'medios']);
    expect(seccionesVisibles('ADMINISTRADOR', catalogo).map((s) => s.id)).toEqual([
      'tablero',
      'medios',
      'usuarios',
    ]);
  });

  it('AC_TKT010_09 accesos rápidos del Tablero según el rol', () => {
    expect(accesosRapidos('EDITOR', catalogo).map((a) => a.id)).toEqual(['subir']);
    expect(accesosRapidos('ADMINISTRADOR', catalogo).map((a) => a.id)).toEqual(['subir', 'cuentas']);
  });

  it('AC_TKT010_09 el catálogo real solo contiene secciones implementadas (TKT-022 añade Medios)', () => {
    expect(SECCIONES_PANEL.map((s) => s.ruta)).toEqual(['/panel', '/panel/medios', '/panel/cuenta']);
    expect(accesosRapidos('EDITOR').map((a) => a.ruta)).toEqual(['/panel/medios']);
    expect(accesosRapidos('ADMINISTRADOR').map((a) => a.id)).toEqual(['subir-medios']);
    expect(seccionesVisibles('EDITOR').length).toBe(3);
  });

  it('sección de una URL: prefijo más largo; el Tablero solo coincide exacto', () => {
    expect(seccionDeRuta('/panel', catalogo)?.id).toBe('tablero');
    expect(seccionDeRuta('/panel/', catalogo)?.id).toBe('tablero');
    expect(seccionDeRuta('/panel/medios/12?x=1', catalogo)?.id).toBe('medios');
    expect(seccionDeRuta('/panel/contenido/destinos', catalogo)).toBeNull();
    expect(seccionDeRuta('/panel/cuenta')?.id).toBe('cuenta');
    expect(activoSoloExacto(catalogo[0])).toBe(true);
    expect(activoSoloExacto(catalogo[1])).toBe(false);
  });

  it('AC_TKT010_09 un enlace de alerta solo se muestra si su sección existe y el rol la permite', () => {
    expect(enlaceDisponible('/panel/medios/3', 'EDITOR', catalogo)).toBe('/panel/medios/3');
    expect(enlaceDisponible('/panel/usuarios', 'EDITOR', catalogo)).toBeNull();
    expect(enlaceDisponible('/panel/configuracion', 'ADMINISTRADOR', catalogo)).toBeNull();
    expect(enlaceDisponible(null, 'ADMINISTRADOR', catalogo)).toBeNull();
  });
});

describe('tablero (SCR-034)', () => {
  const vacio: TableroPanel = {
    conteos: [{ tipo: 'DESTINO', borrador: 0, publicado: 0, retirado: 0 }],
    recientes: [],
    alertas: [],
    saludEditorial: null,
  };

  it('AC_TKT010_09 estado vacío: sin contenidos ni cambios recientes', () => {
    expect(esTableroVacio(vacio)).toBe(true);
    expect(
      esTableroVacio({ ...vacio, conteos: [{ tipo: 'GUIA', borrador: 1, publicado: 0, retirado: 0 }] }),
    ).toBe(false);
    expect(totalConteo({ tipo: 'GUIA', borrador: 1, publicado: 2, retirado: 3 })).toBe(6);
  });

  it('variantes de insignia por estado editorial', () => {
    expect(varianteEstado('BORRADOR')).toBe('borrador');
    expect(varianteEstado('PUBLICADO')).toBe('publicado');
    expect(varianteEstado('RETIRADO')).toBe('retirado');
  });

  it('salud editorial: solo si hay algo que atender', () => {
    const sinNada = {
      revisionesAntiguas: [],
      mediosPendientesMetadatos: 0,
      mediosSinUso: 0,
      coleccionesBajoMinimo: [],
      contenidosConPocosRelacionados: [],
    };
    expect(hayAvisosDeSalud(vacio)).toBe(false);
    expect(hayAvisosDeSalud({ ...vacio, saludEditorial: sinNada })).toBe(false);
    for (const parcial of [
      { mediosSinUso: 2 },
      { mediosPendientesMetadatos: 1 },
      { revisionesAntiguas: [{ id: 1, tipo: 'DESTINO' as const, titulo: 'x' }] },
      { coleccionesBajoMinimo: [{ id: 1, tipo: 'COLECCION' as const, titulo: 'x' }] },
      { contenidosConPocosRelacionados: [{ id: 1, tipo: 'GUIA' as const, titulo: 'x' }] },
    ]) {
      expect(hayAvisosDeSalud({ ...vacio, saludEditorial: { ...sinNada, ...parcial } })).toBe(true);
    }
  });
});

describe('fechas del panel (Intl es-CO, sin DatePipe)', () => {
  it('formatea fecha larga y fecha con hora en español', () => {
    const fecha = new Date('2026-02-01T15:30:00Z');
    expect(formatearFechaLarga(fecha)).toMatch(/2026/);
    expect(formatearFechaLarga(fecha).toLowerCase()).toContain('febrero');
    expect(formatearFechaHora(fecha)).toMatch(/2026/);
    expect(formatearFechaHora(fecha)).toMatch(/\d{1,2}:\d{2}/);
  });
});
