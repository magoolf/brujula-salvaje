"""Saneado de texto enriquecido del panel (RULE-021, RULE-022, DEC-AUTO-043/109, THREAT-005).

Lista blanca estricta: p, h2-h4, ul, ol, li, strong, em, blockquote y a[href] (solo http, https o
ruta interna que empiece por "/"). Cualquier otra etiqueta se elimina conservando su texto; los
atributos no admitidos se descartan. Se usa al guardar (crear/actualizar) los campos de texto
enriquecido de todos los tipos de contenido, nunca en la lectura pública (ya saneada en el origen).
"""

from __future__ import annotations

from html.parser import HTMLParser

ETIQUETAS_PERMITIDAS = frozenset(
    {"p", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "blockquote", "a"}
)


def _href_seguro(href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith(("http://", "https://", "/")):
        return href
    return None


class _Saneador(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self._pila: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ETIQUETAS_PERMITIDAS:
            return
        if tag == "a":
            href = _href_seguro(dict(attrs).get("href"))
            if href is None:
                # Enlace sin destino seguro: se conserva como texto plano (se ignora el tag).
                self._pila.append("__a_sin_href__")
                return
            self.partes.append(f'<a href="{_escapar_attr(href)}" rel="nofollow">')
        else:
            self.partes.append(f"<{tag}>")
        self._pila.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in ETIQUETAS_PERMITIDAS or not self._pila:
            return
        # Cierra el tag correspondiente más reciente (tolera HTML no perfectamente anidado).
        if tag in self._pila:
            while self._pila:
                abierto = self._pila.pop()
                if abierto == "__a_sin_href__":
                    continue
                self.partes.append(f"</{abierto}>")
                if abierto == tag:
                    break

    def handle_data(self, data: str) -> None:
        self.partes.append(_escapar_texto(data))


def _escapar_texto(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escapar_attr(texto: str) -> str:
    return _escapar_texto(texto).replace('"', "&quot;")


def sanear_html(html: str | None) -> str | None:
    """Reduce `html` a la lista blanca de RULE-022. None y cadena vacía se devuelven tal cual."""
    if not html:
        return html
    saneador = _Saneador()
    saneador.feed(html)
    saneador.close()
    # Cierra cualquier etiqueta que quedó abierta al final del documento.
    while saneador._pila:
        abierto = saneador._pila.pop()
        if abierto != "__a_sin_href__":
            saneador.partes.append(f"</{abierto}>")
    return "".join(saneador.partes)
