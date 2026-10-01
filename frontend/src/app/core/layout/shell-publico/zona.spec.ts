import {
  DATOS_ZONA_PANEL,
  NodoRutaZona,
  esZonaPanel,
  zonaDeEstado,
  zonaDeRuta,
  zonaDeUrl,
} from './zona';

/** Árbol de rutas mínimo: raíz → [config de cada nivel]; devuelve la raíz. */
function arbol(...niveles: (Readonly<Record<string, unknown>> | undefined)[]): NodoRutaZona {
  const raiz: { routeConfig: null; parent: null; firstChild: NodoRutaZona | null } = {
    routeConfig: null,
    parent: null,
    firstChild: null,
  };
  let padre: { firstChild: NodoRutaZona | null } & NodoRutaZona = raiz;
  for (const data of niveles) {
    const nodo: {
      routeConfig: { data?: Readonly<Record<string, unknown>> };
      parent: NodoRutaZona;
      firstChild: NodoRutaZona | null;
    } = {
      routeConfig: { data },
      parent: padre,
      firstChild: null,
    };
    padre.firstChild = nodo;
    padre = nodo;
  }
  return raiz;
}

function hoja(raiz: NodoRutaZona): NodoRutaZona {
  let nodo = raiz;
  while (nodo.firstChild !== null) nodo = nodo.firstChild;
  return nodo;
}

describe('zona (TKT-010)', () => {
  it('por URL (solo primer render): /panel y /panel/** son panel; /panelx y anclas no', () => {
    expect(esZonaPanel('/panel')).toBe(true);
    expect(esZonaPanel('/panel/')).toBe(true);
    expect(esZonaPanel('/panel?x=1')).toBe(true);
    expect(esZonaPanel('/panel/acceso?siguiente=%2Fpanel')).toBe(true);
    expect(esZonaPanel('/panelx')).toBe(false);
    expect(esZonaPanel('/')).toBe(false);
    expect(esZonaPanel('/destinos#panel')).toBe(false);
    expect(zonaDeUrl('/panel/no-existe')).toBe('panel');
    expect(zonaDeUrl('/destinos')).toBe('publico');
  });

  it('por ruta: panel si la ruta o un ancestro declara DATOS_ZONA_PANEL', () => {
    const panel = arbol(DATOS_ZONA_PANEL, undefined, { titulo: 'x' });
    expect(zonaDeRuta(hoja(panel))).toBe('panel');
    expect(zonaDeEstado(panel)).toBe('panel');
    const publica = arbol(undefined, { slug: 'acerca-de' });
    expect(zonaDeRuta(hoja(publica))).toBe('publico');
    expect(zonaDeEstado(publica)).toBe('publico');
    expect(zonaDeRuta(arbol())).toBe('publico');
    expect(zonaDeRuta(hoja(arbol({ zona: 'otra' })))).toBe('publico');
  });
});
