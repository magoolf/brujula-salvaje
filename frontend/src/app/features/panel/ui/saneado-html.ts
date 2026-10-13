/**
 * Saneado del texto enriquecido en el editor (RULE-022, RULE-021, THREAT-005; Skill_Frontend
 * §27.4). Lista blanca: p, h2-h4, ul, ol, li, strong, em, blockquote y a[href] (http, https o
 * ruta interna) con `data-glosario` opcional. Todo lo demás se elimina conservando su texto, y
 * script/style/template/iframe/object se eliminan con su contenido.
 *
 * Saneado documentado (DEC-DEV-023-03): el HTML del servidor (ya saneado al guardar, DEC-AUTO-043)
 * se analiza con DOMParser en un documento inerte (no ejecuta scripts ni carga recursos) y se
 * RECONSTRUYE nodo a nodo con createElement/createTextNode/setAttribute solo para lo permitido: no
 * se usa innerHTML, outerHTML, insertAdjacentHTML ni bypassSecurityTrust*. La serialización para
 * el servidor también recorre la lista blanca y escapa texto y atributos.
 */
import { esHrefPermitido, esSlugValido } from '../domain/formulario-contenido';

const BLOQUES: Readonly<Record<string, string>> = {
  P: 'p',
  DIV: 'p',
  H2: 'h2',
  H3: 'h3',
  H4: 'h4',
  UL: 'ul',
  OL: 'ol',
  LI: 'li',
  BLOCKQUOTE: 'blockquote',
};
const EN_LINEA: Readonly<Record<string, string>> = { B: 'strong', STRONG: 'strong', I: 'em', EM: 'em' };
/** Se eliminan con todo su contenido. */
const DESCARTADOS = new Set(['SCRIPT', 'STYLE', 'TEMPLATE', 'IFRAME', 'OBJECT', 'EMBED', 'NOSCRIPT', 'SVG', 'MATH', 'HEAD', 'TITLE']);
const NIVEL_BLOQUE = new Set(['p', 'h2', 'h3', 'h4', 'ul', 'ol', 'blockquote']);

const NODO_ELEMENTO = 1;
const NODO_TEXTO = 3;

function elementoPermitido(origen: Element, doc: Document): Element | null {
  const etiqueta = origen.tagName.toUpperCase();
  const bloque = BLOQUES[etiqueta];
  if (bloque !== undefined) return doc.createElement(bloque);
  const enLinea = EN_LINEA[etiqueta];
  if (enLinea !== undefined) return doc.createElement(enLinea);
  if (etiqueta === 'A') {
    const href = (origen.getAttribute('href') ?? '').trim();
    if (!esHrefPermitido(href)) return null;
    const enlace = doc.createElement('a');
    enlace.setAttribute('href', href);
    const glosario = origen.getAttribute('data-glosario');
    if (esSlugValido(glosario)) enlace.setAttribute('data-glosario', glosario);
    return enlace;
  }
  return null;
}

/** Copia los hijos de `origen` en `destino` aplicando la lista blanca. */
function copiarPermitido(origen: Node, destino: Node, doc: Document): void {
  for (const hijo of Array.from(origen.childNodes)) {
    if (hijo.nodeType === NODO_TEXTO) {
      destino.appendChild(doc.createTextNode(hijo.textContent ?? ''));
      continue;
    }
    if (hijo.nodeType !== NODO_ELEMENTO) continue;
    const elemento = hijo as Element;
    const etiqueta = elemento.tagName.toUpperCase();
    if (DESCARTADOS.has(etiqueta)) continue;
    if (etiqueta === 'BR') {
      destino.appendChild(doc.createTextNode(' '));
      continue;
    }
    const nuevo = elementoPermitido(elemento, doc);
    if (nuevo === null) {
      copiarPermitido(elemento, destino, doc);
    } else {
      copiarPermitido(elemento, nuevo, doc);
      destino.appendChild(nuevo);
    }
  }
}

/** Agrupa el texto y los elementos en línea sueltos del primer nivel en párrafos. */
function normalizarPrimerNivel(contenedor: Node, doc: Document): void {
  let parrafo: Element | null = null;
  for (const hijo of Array.from(contenedor.childNodes)) {
    const esBloque =
      hijo.nodeType === NODO_ELEMENTO && NIVEL_BLOQUE.has((hijo as Element).tagName.toLowerCase());
    if (esBloque) {
      parrafo = null;
      continue;
    }
    if (hijo.nodeType === NODO_TEXTO && (hijo.textContent ?? '').trim() === '' && parrafo === null) {
      contenedor.removeChild(hijo);
      continue;
    }
    if (parrafo === null) {
      parrafo = doc.createElement('p');
      contenedor.insertBefore(parrafo, hijo);
    }
    parrafo.appendChild(hijo);
  }
}

/**
 * Sustituye el contenido de `destino` por el HTML saneado (para mostrarlo en el área editable).
 * @param analizar Función que devuelve el documento inerte (DOMParser) del HTML de entrada.
 */
export function pintarHtmlSaneado(destino: HTMLElement, html: string, analizar: (html: string) => Document): void {
  const doc = destino.ownerDocument;
  while (destino.firstChild) destino.removeChild(destino.firstChild);
  if (html.trim() === '') return;
  const origen = analizar(html).body;
  copiarPermitido(origen, destino, doc);
  normalizarPrimerNivel(destino, doc);
}

function escaparTexto(texto: string): string {
  return texto.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\u00a0/g, ' ');
}

function escaparAtributo(valor: string): string {
  return escaparTexto(valor).replace(/"/g, '&quot;');
}

function serializarNodo(nodo: Node, salida: string[]): void {
  for (const hijo of Array.from(nodo.childNodes)) serializarUno(hijo, salida);
}

function serializarUno(hijo: Node, salida: string[]): void {
  if (hijo.nodeType === NODO_TEXTO) {
    salida.push(escaparTexto(hijo.textContent ?? ''));
    return;
  }
  if (hijo.nodeType !== NODO_ELEMENTO) return;
  const elemento = hijo as Element;
  const etiquetaOrigen = elemento.tagName.toUpperCase();
  if (DESCARTADOS.has(etiquetaOrigen)) return;
  if (etiquetaOrigen === 'BR') {
    salida.push(' ');
    return;
  }
  const permitido = elementoPermitido(elemento, elemento.ownerDocument);
  if (permitido === null) {
    serializarNodo(elemento, salida);
    return;
  }
  const etiqueta = permitido.tagName.toLowerCase();
  const interior: string[] = [];
  serializarNodo(elemento, interior);
  const contenido = interior.join('');
  // Bloques y enlaces vacíos no aportan nada (p. ej. el <p><br></p> de un área vacía).
  if (contenido.trim() === '' && etiqueta !== 'li') return;
  const atributos = Array.from(permitido.attributes)
    .map((a) => ` ${a.name}="${escaparAtributo(a.value)}"`)
    .join('');
  salida.push(`<${etiqueta}${atributos}>${contenido}</${etiqueta}>`);
}

function esBloqueDeOrigen(nodo: Node): boolean {
  if (nodo.nodeType !== NODO_ELEMENTO) return false;
  const bloque = BLOQUES[(nodo as Element).tagName.toUpperCase()];
  return bloque !== undefined && NIVEL_BLOQUE.has(bloque);
}

/**
 * HTML de lista blanca del área editable ('' si no hay texto). El texto y los elementos en línea
 * sueltos del primer nivel (lo que escribe el navegador en un área vacía) se envuelven en <p>.
 */
export function serializarHtmlSaneado(origen: Node): string {
  const salida: string[] = [];
  let enLinea: string[] = [];
  const volcar = (): void => {
    const contenido = enLinea.join('');
    if (contenido.trim() !== '') salida.push(`<p>${contenido.trim()}</p>`);
    enLinea = [];
  };
  for (const hijo of Array.from(origen.childNodes)) {
    if (esBloqueDeOrigen(hijo)) {
      volcar();
      serializarUno(hijo, salida);
    } else {
      serializarUno(hijo, enLinea);
    }
  }
  volcar();
  const html = salida.join('');
  return html.replace(/<[^>]*>/g, '').trim() === '' ? '' : html;
}
