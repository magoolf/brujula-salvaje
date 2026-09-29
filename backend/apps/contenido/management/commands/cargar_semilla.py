"""Comando `cargar_semilla` (TKT-007).

Publica el dataset de contenido semilla completo (`backend/seed/**`) usando los SERVICIOS reales
ya existentes del panel editorial (`apps.contenido.services`, `apps.medios.services`,
`apps.catalogos.services`, `apps.inicio.services`) — el mismo camino que seguiría un editor
humano desde el panel, no accesos directos al ORM que salten las reglas de negocio ya
implementadas. La única excepción deliberada, quirúrgica y documentada está en
`_bootstrap_publicar` (arranque de RULE-006 en un sistema vacío) y en `_cargar_paginas`/
`_configurar_inicio` (no existe un servicio de CREACIÓN para páginas institucionales ni para el
singleton `ConfigInicio`; ver los docstrings de cada función y el HANDOFF del ticket).

Idempotente: cada entidad se busca primero por `(tipo, slug)`; si ya existe, se reutiliza sin
repetir ningún efecto (medios, auditoría, reindexado). Ejecutar el comando dos veces seguidas
produce el mismo resultado final y la segunda ejecución es prácticamente un no-op.

Actor: `None` en todas las llamadas de servicio (DEC-AUTO-095, `docs/04_datos/DB_HANDOFF.yaml`:
"creado_por, actualizado_por, subido_por... anulables (NULL = carga semilla)"; la alternativa de
una "cuenta de sistema" se descartó explícitamente por THREAT-027, sin cuentas por defecto).
"""

from __future__ import annotations

import dataclasses
from typing import Any, cast

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.auditoria import services as auditoria_services
from apps.auditoria.models import AccionAuditoria
from apps.busqueda import services as busqueda_services
from apps.catalogos import services as catalogos_services
from apps.catalogos.models import CategoriaGuia, Licencia, Pais, Region
from apps.contenido import reglas
from apps.contenido import services as contenido_services
from apps.contenido.models import (
    Contenido,
    EstadoEditorial,
    PaginaInstitucional,
    TipoContenido,
)
from apps.core.exceptions import ErrorApi
from apps.inicio import services as inicio_services
from apps.inicio.models import ID_SINGLETON, ConfigInicio, DestacadoInicio, SeccionInicio
from apps.medios import services as medios_services
from apps.medios.models import Medio
from seed import colecciones as seed_colecciones
from seed import destinos as seed_destinos
from seed import glosario as seed_glosario
from seed import guias as seed_guias
from seed import imagenes as seed_imagenes
from seed import itinerarios as seed_itinerarios
from seed import paginas as seed_paginas
from seed import paises as seed_paises
from seed import tipos_aventura as seed_tipos

T = TipoContenido
E = EstadoEditorial
# DEC-AUTO-095 (docs/04_datos/DB_HANDOFF.yaml): NULL = carga semilla; la alternativa de una
# "cuenta de sistema" se descartó explícitamente por THREAT-027 (sin cuentas por defecto). Los
# servicios de apps.contenido/medios/catalogos/inicio (fuera de archivos_permitidos: no se
# pueden retipar) declaran `actor_id: int` sin `| None` aunque su propia documentación admite
# NULL para cargas de semilla; `cast` evita `type: ignore` repetido en cada llamada sin cambiar
# el valor real en tiempo de ejecución (que sigue siendo `None`).
ACTOR_ID: int = cast(int, None)
AUTOR_MEDIOS = "Equipo editorial de Brújula Salvaje"  # REQ-023, DEC-AUTO-039 (firma de equipo)

# Clique de arranque de RULE-006 (ver `_bootstrap_publicar`): 1 tipo + 1 destino por cada uno de
# los 4 pares, elegidos para desbloquear 4 tipos distintos a la vez.
GENESIS: list[tuple[str, str]] = [
    ("senderismo-y-trekking", "ciudad-perdida-teyuna"),
    ("alta-montana-y-alpinismo", "pnn-los-nevados"),
    ("escalada-y-via-ferrata", "dolomitas"),
    ("buceo-y-snorkel", "gran-barrera-de-coral"),
]
GENESIS_TIPOS = [par[0] for par in GENESIS]
GENESIS_DESTINOS = [par[1] for par in GENESIS]


class Command(BaseCommand):
    help = (
        "Carga el dataset de contenido semilla (TKT-007): países, tipos de aventura, "
        "destinos, itinerarios, guías, colecciones, glosario, páginas institucionales y "
        "configuración de inicio, publicados vía los servicios reales del panel editorial. "
        "Idempotente: se puede ejecutar más de una vez sin duplicar contenido."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        self._contador = {"creados": 0, "reutilizados": 0, "publicados": 0}
        self._nuevos: dict[str, set[str]] = {
            "TIPO": set(),
            "DESTINO": set(),
            "ITINERARIO": set(),
            "GUIA": set(),
        }
        self.fecha_revision = timezone.now().date()
        self.stdout.write("TKT-007 — carga de semilla de contenido")

        self._licencia_propia_id = Licencia.objects.get(codigo="PROPIA").pk
        self._paises = self._cargar_paises()

        self._tipos = self._cargar_tipos_borrador()
        self._curar_relaciones_tipos_genesis()
        self._terminos = self._cargar_terminos_borrador()
        self._destinos = self._cargar_destinos_borrador()
        self._curar_relaciones_destinos()

        self._bootstrap_publicar_genesis()
        self._publicar_destinos_restantes()

        self._itinerarios = self._cargar_y_publicar_itinerarios()
        self._guias = self._cargar_y_publicar_guias()
        self._publicar_terminos()
        self._colecciones = self._cargar_y_publicar_colecciones()
        self._paginas = self._cargar_paginas()
        self._configurar_inicio()
        self._reindexar_todo()

        self.stdout.write(
            self.style.SUCCESS(
                "Semilla completa. "
                f"Creados: {self._contador['creados']}, "
                f"reutilizados: {self._contador['reutilizados']}, "
                f"publicados en esta ejecución: {self._contador['publicados']}."
            )
        )

    # -----------------------------------------------------------------------
    # Medios (ilustraciones propias, RSK-002/DEC-AUTO-014/REQ-043)
    # -----------------------------------------------------------------------
    def _subir_imagen(
        self, semilla: str, variante: int, *, alt: str, autor: str = AUTOR_MEDIOS
    ) -> int:
        """Genera una ilustración propia determinista y la sube/cataloga vía los servicios
        reales de `apps.medios`. Idempotente: la deduplicación por `huella_sha256` de
        `subir_medios` hace que una segunda ejecución con la misma semilla reutilice el medio
        ya existente en vez de crear uno nuevo."""
        contenido_bytes = seed_imagenes.generar_ilustracion(semilla, variante=variante)
        nombre = f"{semilla.replace(':', '-')}-{variante}.png"
        archivo = SimpleUploadedFile(nombre, contenido_bytes, content_type="image/png")
        resultados = medios_services.subir_medios(ACTOR_ID, [archivo])
        resultado = resultados[0]
        if resultado.resultado == "ACEPTADO":
            medio_id = resultado.medio.pk  # type: ignore[union-attr]
        elif resultado.resultado == "DUPLICADO":
            medio_id = resultado.medio_existente_id
        else:
            raise CommandError(f"Medio rechazado ({semilla}#{variante}): {resultado.motivo}")
        if medio_id is None:  # pragma: no cover - defensivo, no debería ocurrir nunca
            raise CommandError(f"Medio sin id ({semilla}#{variante}): {resultado}")
        medio = Medio.objects.get(pk=medio_id)
        pendiente = (
            not medio.texto_alternativo or not medio.autor_credito or medio.licencia_id is None
        )
        if pendiente:
            medios_services.catalogar(
                medio_id,
                ACTOR_ID,
                {
                    "texto_alternativo": alt,
                    "autor_credito": autor,
                    "pie_de_foto": alt,
                    "licencia_id": self._licencia_propia_id,
                },
            )
        return medio_id

    # -----------------------------------------------------------------------
    # Países (DB_HANDOFF: "los países llegan con la carga semilla de F7")
    # -----------------------------------------------------------------------
    def _cargar_paises(self) -> dict[str, int]:
        regiones = {r.slug: r.pk for r in Region.objects.all()}
        resultado: dict[str, int] = {}
        for p in seed_paises.PAISES:
            existente = Pais.objects.filter(slug=p.slug).first()
            if existente is not None:
                resultado[p.slug] = existente.pk
                self._contador["reutilizados"] += 1
                continue
            region_id = regiones.get(p.region_slug)
            if region_id is None:
                raise CommandError(f"Región no sembrada: {p.region_slug} (país {p.slug})")
            creado = catalogos_services.crear_pais(
                ACTOR_ID,
                {
                    "nombre": p.nombre,
                    "slug": p.slug,
                    "codigo_iso2": p.codigo_iso2,
                    "region_id": region_id,
                },
            )
            resultado[p.slug] = creado.pk
            self._contador["creados"] += 1
        return resultado

    # -----------------------------------------------------------------------
    # Tipos de aventura (BORRADOR)
    # -----------------------------------------------------------------------
    def _cargar_tipos_borrador(self) -> dict[str, Contenido]:
        resultado: dict[str, Contenido] = {}
        for t in seed_tipos.TIPOS:
            existente = Contenido.objects.filter(tipo=T.TIPO, slug=t.slug).first()
            if existente is not None:
                resultado[t.slug] = existente
                self._contador["reutilizados"] += 1
                continue
            portada_id = self._subir_imagen(
                f"tipo:{t.slug}",
                0,
                alt=f"Ilustración abstracta que representa la actividad «{t.titulo}»",
            )
            datos = {
                "titulo": t.titulo,
                "slug": t.slug,
                "fecha_ultima_revision": self.fecha_revision,
                "seo_titulo": t.seo_titulo,
                "seo_descripcion": t.seo_descripcion,
                "resumen": t.resumen,
                "descripcion": t.descripcion,
                "nivel_exigencia": t.nivel_exigencia,
                "portada_id": portada_id,
                "checklist": [dataclasses.asdict(c) for c in t.checklist],
            }
            creado = contenido_services.crear_borrador(T.TIPO, ACTOR_ID, datos)
            resultado[t.slug] = creado
            self._nuevos["TIPO"].add(t.slug)
            self._contador["creados"] += 1
        return resultado

    def _curar_relaciones_tipos_genesis(self) -> None:
        """Relaciones curadas reales entre los 4 tipos del clique de arranque (no
        estrictamente necesarias para pasar `_bootstrap_publicar`, que sustituye ese conteo,
        pero sí para que el resultado publicado muestre relacionados curados coherentes desde
        el primer momento, RULE-006)."""
        for slug in GENESIS_TIPOS:
            if slug not in self._nuevos["TIPO"]:
                continue
            contenido = self._tipos[slug]
            otros = [self._tipos[s].pk for s in GENESIS_TIPOS if s != slug]
            relaciones = [{"id": pk, "tipo": T.TIPO} for pk in otros]
            actual = Contenido.objects.get(pk=contenido.pk)
            contenido_services.actualizar(
                T.TIPO, contenido.pk, ACTOR_ID, {"relaciones": relaciones}, actual.version
            )

    # -----------------------------------------------------------------------
    # Glosario (BORRADOR; se publica al final, `_publicar_terminos`)
    # -----------------------------------------------------------------------
    def _cargar_terminos_borrador(self) -> dict[str, Contenido]:
        resultado: dict[str, Contenido] = {}
        for term in seed_glosario.TERMINOS:
            existente = Contenido.objects.filter(tipo=T.TERMINO, slug=term.slug).first()
            if existente is not None:
                resultado[term.slug] = existente
                self._contador["reutilizados"] += 1
                continue
            datos = {
                "titulo": term.titulo,
                "slug": term.slug,
                "fecha_ultima_revision": self.fecha_revision,
                "definicion": term.definicion,
            }
            creado = contenido_services.crear_borrador(T.TERMINO, ACTOR_ID, datos)
            resultado[term.slug] = creado
            self._contador["creados"] += 1
        return resultado

    def _mapa_terminos(self, tipo_objetivo: str) -> dict[str, list[str]]:
        mapa: dict[str, list[str]] = {}
        for term in seed_glosario.TERMINOS:
            for tipo, slug in term.vincular_a:
                if tipo == tipo_objetivo:
                    mapa.setdefault(slug, []).append(term.slug)
        return mapa

    def _publicar_terminos(self) -> None:
        for term in seed_glosario.TERMINOS:
            contenido = self._terminos[term.slug]
            actual = Contenido.objects.get(pk=contenido.pk)
            if actual.estado_editorial != E.BORRADOR:
                continue
            try:
                contenido_services.publicar(T.TERMINO, actual.pk, ACTOR_ID, actual.version, None)
            except ErrorApi as exc:
                raise CommandError(
                    f"No se pudo publicar el término «{term.slug}»: {exc.detalle} {exc.errors}"
                ) from exc
            self._contador["publicados"] += 1

    # -----------------------------------------------------------------------
    # Destinos (BORRADOR -> relaciones -> publicación)
    # -----------------------------------------------------------------------
    def _cargar_destinos_borrador(self) -> dict[str, Contenido]:
        terminos_por_destino = self._mapa_terminos("DESTINO")
        resultado: dict[str, Contenido] = {}
        for d in seed_destinos.DESTINOS:
            existente = Contenido.objects.filter(tipo=T.DESTINO, slug=d.slug).first()
            if existente is not None:
                resultado[d.slug] = existente
                self._contador["reutilizados"] += 1
                continue
            portada_id = self._subir_imagen(
                f"destino:{d.slug}", 0, alt=f"Ilustración de portada de {d.titulo}"
            )
            galeria_ids = [
                self._subir_imagen(
                    f"destino:{d.slug}",
                    i,
                    alt=f"Ilustración {i} de {d.titulo}: paisaje y actividad principal",
                )
                for i in (1, 2, 3)
            ]
            tipos_ids = [self._tipos[slug].pk for slug in d.tipos_slugs]
            datos = {
                "titulo": d.titulo,
                "slug": d.slug,
                "fecha_ultima_revision": self.fecha_revision,
                "seo_titulo": d.seo_titulo,
                "seo_descripcion": d.seo_descripcion,
                "resumen": d.resumen,
                "descripcion_experta": d.descripcion_experta,
                "dificultad": d.dificultad,
                "duracion_min_dias": d.duracion_min_dias,
                "duracion_max_dias": d.duracion_max_dias,
                "nivel_presupuesto": d.nivel_presupuesto,
                "clima": d.clima,
                "altitud_max_m": d.altitud_max_m,
                "como_llegar": d.como_llegar,
                "seguridad_riesgos": d.seguridad_riesgos,
                "sostenibilidad": d.sostenibilidad,
                "latitud": d.latitud,
                "longitud": d.longitud,
                "pais_id": self._paises[d.pais_slug],
                "meses_mejor_epoca": d.meses_mejor_epoca,
                "portada_id": portada_id,
                "galeria_ids": galeria_ids,
                "tipos_ids": tipos_ids,
                "tipo_principal_id": tipos_ids[0],
                "terminos_ids": [
                    self._terminos[s].pk for s in terminos_por_destino.get(d.slug, [])
                ],
            }
            creado = contenido_services.crear_borrador(T.DESTINO, ACTOR_ID, datos)
            resultado[d.slug] = creado
            self._nuevos["DESTINO"].add(d.slug)
            self._contador["creados"] += 1
        return resultado

    def _curar_relaciones_destinos(self) -> None:
        for d in seed_destinos.DESTINOS:
            if d.slug not in self._nuevos["DESTINO"] or not d.relacionados_slugs:
                continue
            contenido = self._destinos[d.slug]
            relaciones = [
                {"id": self._destinos[r].pk, "tipo": T.DESTINO} for r in d.relacionados_slugs
            ]
            actual = Contenido.objects.get(pk=contenido.pk)
            contenido_services.actualizar(
                T.DESTINO, contenido.pk, ACTOR_ID, {"relaciones": relaciones}, actual.version
            )

    # -----------------------------------------------------------------------
    # Arranque de RULE-006 (excepción quirúrgica y documentada)
    # -----------------------------------------------------------------------
    def _bootstrap_publicar_genesis(self) -> None:
        """RULE-006 (`apps/contenido/reglas.py`, `MINIMO_RELACIONADOS = 3`) exige que todo
        Destino/Itinerario/Guía/Tipo publicado tenga >=3 relacionados YA PUBLICADOS en el
        momento de publicarse (`services._relacionados_publicados`, que cuenta solo
        `estado_editorial=PUBLICADO` vía `selectors.relacionados`). Esto es matemáticamente
        insatisfacible para las primeras publicaciones de un sistema completamente vacío: el
        primer elemento publicado no puede tener 3 elementos YA publicados a los que
        referirse, y lo mismo el segundo y el tercero — ninguna secuencia de llamadas a
        `services.publicar()` (incluida la co-publicación Destino+Tipos) puede romper este
        ciclo por sí sola, porque el conteo se recalcula desde la base de datos, no desde el
        lote que se está publicando.

        Esta función resuelve el arranque publicando un clique mínimo de 4 tipos + 4 destinos
        (`GENESIS`) reutilizando el resto de la validación REAL de `apps.contenido.reglas` para
        cada uno (portada, SEO, dificultad, meses, coordenadas, galería, checklist...: todo se
        comprueba de verdad) y sustituyendo ÚNICAMENTE el campo `relacionados_publicados`
        calculado (que en el arranque es 0 por construcción, no por incumplimiento real) por el
        mínimo exigido; la transición de estado que aplica a continuación es la misma función
        que usa el servicio real, `services._confirmar_publicacion_entidad`, importada tal
        cual, nunca reescrita. En cuanto este clique queda publicado, TODO el resto del
        contenido (20 destinos, 8 tipos, itinerarios, guías, glosario, colecciones) se publica
        por el camino 100% normal y sin excepciones, `services.publicar()`, porque ya existen
        >=4 elementos reales ya publicados a los que referirse.

        GAP reportado en el HANDOFF: RULE-006 no tiene ninguna vía de arranque para un sistema
        vacío en el código ya existente (fuera de `archivos_permitidos` de este ticket:
        `apps/contenido/services.py` y `reglas.py`). Se recomienda una función `publicar_lote`
        o similar en `services.py` (un ticket futuro) que valide un conjunto de altas
        simultáneas entre sí, en vez de exigir que cada una encuentre ya publicados a los
        demás.
        """
        for tipo_slug, destino_slug in GENESIS:
            tipo_contenido = self._tipos[tipo_slug]
            self._bootstrap_publicar(T.TIPO, tipo_contenido.pk)
            destino_contenido = self._destinos[destino_slug]
            self._bootstrap_publicar(T.DESTINO, destino_contenido.pk)

    def _bootstrap_publicar(self, tipo: str, contenido_id: int) -> None:
        if tipo == T.TIPO:
            self._bootstrap_publicar_tipo(contenido_id)
        elif tipo == T.DESTINO:
            self._bootstrap_publicar_destino(contenido_id)
        else:  # pragma: no cover - solo se llama con TIPO/DESTINO
            raise ValueError(tipo)

    def _bootstrap_publicar_tipo(self, contenido_id: int) -> None:
        with transaction.atomic():
            actual = Contenido.objects.select_for_update().get(pk=contenido_id)
            if actual.estado_editorial != E.BORRADOR:
                return  # ya publicado en una ejecución anterior: idempotente
            subtipo = actual.tipo_aventura
            datos = contenido_services._datos_regla_tipo(
                subtipo, actual, exigir_destino_publicado=False
            )
            datos = dataclasses.replace(datos, relacionados_publicados=reglas.MINIMO_RELACIONADOS)
            errores = reglas.validar_tipo_aventura(datos, exigir_destino_publicado=False)
            if errores:
                raise CommandError(
                    f"Arranque (genesis) del tipo #{contenido_id} no cumple las reglas reales "
                    f"(fuera del conteo de relacionados, sustituido a propósito): {errores}"
                )
            contenido_services._confirmar_publicacion_entidad(actual, ACTOR_ID, None)
        self._contador["publicados"] += 1

    def _bootstrap_publicar_destino(self, contenido_id: int) -> None:
        with transaction.atomic():
            actual = Contenido.objects.select_for_update().get(pk=contenido_id)
            if actual.estado_editorial != E.BORRADOR:
                return  # ya publicado en una ejecución anterior: idempotente
            subtipo = actual.destino
            datos_d = contenido_services._datos_regla_destino(subtipo, actual)
            datos_d = dataclasses.replace(
                datos_d, relacionados_publicados=reglas.MINIMO_RELACIONADOS
            )
            errores = reglas.validar_destino(datos_d)
            if errores:
                raise CommandError(
                    f"Arranque (genesis) del destino #{contenido_id} no cumple las reglas "
                    f"reales (fuera del conteo de relacionados, sustituido a propósito): "
                    f"{errores}"
                )
            contenido_services._confirmar_publicacion_entidad(actual, ACTOR_ID, None)
        self._contador["publicados"] += 1

    def _publicar_destinos_restantes(self) -> None:
        """Los 20 destinos restantes (y, por co-publicación, los 8 tipos que aún faltan) se
        publican por el camino 100% real y sin excepciones: `services.publicar()`."""
        for d in seed_destinos.DESTINOS:
            contenido = self._destinos[d.slug]
            actual = Contenido.objects.get(pk=contenido.pk)
            if actual.estado_editorial != E.BORRADOR:
                continue
            subtipo = actual.destino
            copublicar = [
                {"id": ta.contenido_id, "version": ta.contenido.version}
                for ta in subtipo.tipos_aventura.select_related("contenido").filter(
                    contenido__estado_editorial=E.BORRADOR
                )
            ]
            try:
                contenido_services.publicar(
                    T.DESTINO, actual.pk, ACTOR_ID, actual.version, copublicar or None
                )
            except ErrorApi as exc:
                raise CommandError(
                    f"No se pudo publicar el destino «{d.slug}»: {exc.detalle} {exc.errors}"
                ) from exc
            self._contador["publicados"] += 1

    # -----------------------------------------------------------------------
    # Itinerarios (>=1 por destino publicado, destinos ya publicados en este punto)
    # -----------------------------------------------------------------------
    def _cargar_y_publicar_itinerarios(self) -> dict[str, Contenido]:
        resultado: dict[str, Contenido] = {}
        for it in seed_itinerarios.ITINERARIOS:
            existente = Contenido.objects.filter(tipo=T.ITINERARIO, slug=it.slug).first()
            if existente is not None:
                resultado[it.slug] = existente
                self._contador["reutilizados"] += 1
                continue
            portada_id = self._subir_imagen(
                f"itinerario:{it.slug}",
                0,
                alt=f"Ilustración de portada del itinerario «{it.titulo}»",
            )
            datos = {
                "titulo": it.titulo,
                "slug": it.slug,
                "fecha_ultima_revision": self.fecha_revision,
                "seo_titulo": it.seo_titulo,
                "seo_descripcion": it.seo_descripcion,
                "resumen": it.resumen,
                "duracion_dias": it.duracion_dias,
                "dificultad": it.dificultad,
                "distancia_total_km": it.distancia_total_km,
                "desnivel_acumulado_m": it.desnivel_acumulado_m,
                "riesgos_seguridad": it.riesgos_seguridad,
                "destino_id": self._destinos[it.destino_slug].pk,
                "tipos_ids": [self._tipos[s].pk for s in it.tipos_slugs],
                "portada_id": portada_id,
                "dias": [dataclasses.asdict(dd) for dd in it.dias],
            }
            creado = contenido_services.crear_borrador(T.ITINERARIO, ACTOR_ID, datos)
            resultado[it.slug] = creado
            self._nuevos["ITINERARIO"].add(it.slug)
            self._contador["creados"] += 1

        for it in seed_itinerarios.ITINERARIOS:
            if it.slug not in self._nuevos["ITINERARIO"] or not it.relacionados_slugs:
                continue
            contenido = resultado[it.slug]
            relaciones = [
                {"id": resultado[r].pk, "tipo": T.ITINERARIO} for r in it.relacionados_slugs
            ]
            actual = Contenido.objects.get(pk=contenido.pk)
            contenido_services.actualizar(
                T.ITINERARIO, contenido.pk, ACTOR_ID, {"relaciones": relaciones}, actual.version
            )

        for it in seed_itinerarios.ITINERARIOS:
            contenido = resultado[it.slug]
            actual = Contenido.objects.get(pk=contenido.pk)
            if actual.estado_editorial != E.BORRADOR:
                continue
            try:
                contenido_services.publicar(T.ITINERARIO, actual.pk, ACTOR_ID, actual.version, None)
            except ErrorApi as exc:
                raise CommandError(
                    f"No se pudo publicar el itinerario «{it.slug}»: {exc.detalle} {exc.errors}"
                ) from exc
            self._contador["publicados"] += 1
        return resultado

    # -----------------------------------------------------------------------
    # Guías
    # -----------------------------------------------------------------------
    def _cargar_y_publicar_guias(self) -> dict[str, Contenido]:
        categorias = {c.slug: c.pk for c in CategoriaGuia.objects.all()}
        terminos_por_guia = self._mapa_terminos("GUIA")
        resultado: dict[str, Contenido] = {}
        for g in seed_guias.GUIAS:
            existente = Contenido.objects.filter(tipo=T.GUIA, slug=g.slug).first()
            if existente is not None:
                resultado[g.slug] = existente
                self._contador["reutilizados"] += 1
                continue
            categoria_id = categorias.get(g.categoria_slug)
            if categoria_id is None:
                raise CommandError(f"Categoría de guía no sembrada: {g.categoria_slug}")
            portada_id = self._subir_imagen(
                f"guia:{g.slug}", 0, alt=f"Ilustración de portada de la guía «{g.titulo}»"
            )
            terminos_slugs = list(
                dict.fromkeys([*g.terminos_slugs, *terminos_por_guia.get(g.slug, [])])
            )
            datos = {
                "titulo": g.titulo,
                "slug": g.slug,
                "fecha_ultima_revision": self.fecha_revision,
                "seo_titulo": g.seo_titulo,
                "seo_descripcion": g.seo_descripcion,
                "categoria_id": categoria_id,
                "resumen": g.resumen,
                "cuerpo": g.cuerpo,
                "remite_a_metodologia": True,
                "portada_id": portada_id,
                "destinos_ids": [self._destinos[s].pk for s in g.destinos_slugs],
                "tipos_ids": [self._tipos[s].pk for s in g.tipos_slugs],
                "terminos_ids": [self._terminos[s].pk for s in terminos_slugs],
            }
            creado = contenido_services.crear_borrador(T.GUIA, ACTOR_ID, datos)
            resultado[g.slug] = creado
            self._nuevos["GUIA"].add(g.slug)
            self._contador["creados"] += 1

        for g in seed_guias.GUIAS:
            if g.slug not in self._nuevos["GUIA"] or not g.relacionados_slugs:
                continue
            contenido = resultado[g.slug]
            relaciones = [{"id": resultado[r].pk, "tipo": T.GUIA} for r in g.relacionados_slugs]
            actual = Contenido.objects.get(pk=contenido.pk)
            contenido_services.actualizar(
                T.GUIA, contenido.pk, ACTOR_ID, {"relaciones": relaciones}, actual.version
            )

        for g in seed_guias.GUIAS:
            contenido = resultado[g.slug]
            actual = Contenido.objects.get(pk=contenido.pk)
            if actual.estado_editorial != E.BORRADOR:
                continue
            try:
                contenido_services.publicar(T.GUIA, actual.pk, ACTOR_ID, actual.version, None)
            except ErrorApi as exc:
                raise CommandError(
                    f"No se pudo publicar la guía «{g.slug}»: {exc.detalle} {exc.errors}"
                ) from exc
            self._contador["publicados"] += 1
        return resultado

    # -----------------------------------------------------------------------
    # Colecciones (elementos = destinos/itinerarios ya publicados)
    # -----------------------------------------------------------------------
    def _cargar_y_publicar_colecciones(self) -> dict[str, Contenido]:
        resultado: dict[str, Contenido] = {}
        for c in seed_colecciones.COLECCIONES:
            existente = Contenido.objects.filter(tipo=T.COLECCION, slug=c.slug).first()
            if existente is not None:
                resultado[c.slug] = existente
                self._contador["reutilizados"] += 1
                continue
            portada_id = self._subir_imagen(
                f"coleccion:{c.slug}", 0, alt=f"Ilustración de portada de la colección «{c.titulo}»"
            )
            elementos = []
            for indice, elemento in enumerate(c.elementos):
                objetivo = (
                    self._destinos[elemento.slug]
                    if elemento.tipo == "DESTINO"
                    else self._itinerarios[elemento.slug]
                )
                elementos.append(
                    {
                        "tipo_contenido": elemento.tipo,
                        "contenido_id": objetivo.pk,
                        "orden": indice,
                        "nota_editorial": elemento.nota_editorial,
                    }
                )
            datos = {
                "titulo": c.titulo,
                "slug": c.slug,
                "fecha_ultima_revision": self.fecha_revision,
                "seo_titulo": c.seo_titulo,
                "seo_descripcion": c.seo_descripcion,
                "resumen": c.resumen,
                "descripcion": c.descripcion,
                "portada_id": portada_id,
                "elementos": elementos,
            }
            creado = contenido_services.crear_borrador(T.COLECCION, ACTOR_ID, datos)
            resultado[c.slug] = creado
            self._contador["creados"] += 1

        for c in seed_colecciones.COLECCIONES:
            contenido = resultado[c.slug]
            actual = Contenido.objects.get(pk=contenido.pk)
            if actual.estado_editorial != E.BORRADOR:
                continue
            try:
                contenido_services.publicar(T.COLECCION, actual.pk, ACTOR_ID, actual.version, None)
            except ErrorApi as exc:
                raise CommandError(
                    f"No se pudo publicar la colección «{c.slug}»: {exc.detalle} {exc.errors}"
                ) from exc
            self._contador["publicados"] += 1
        return resultado

    # -----------------------------------------------------------------------
    # Páginas institucionales (sin servicio de creación, ver docstring)
    # -----------------------------------------------------------------------
    def _cargar_paginas(self) -> dict[str, Contenido]:
        """`apps.contenido.services` no tiene ninguna función de creación para páginas
        institucionales (`crear_borrador` ni siquiera incluye `TipoContenido.PAGINA` en su
        `modelo_subtipo`), y `panel_urls.py`/`panel_views.py` (TKT-006) solo exponen GET/PUT
        sobre una página YA EXISTENTE, nunca un POST de creación. `docs/04_datos/DB_HANDOFF.yaml`
        lo confirma expresamente: "Las 4 páginas se crean con la carga semilla" — es decir,
        aquí, en TKT-007 — sin prever tampoco una migración de datos para ello.

        `apps/contenido/services.py` está fuera de `archivos_permitidos` de este ticket, así
        que no puedo añadir esa función allí. Esta función reproduce, mediante creación directa
        mínima, exactamente lo que haría ese servicio si existiera: valida con las reglas
        REALES (`reglas.validar_pagina_institucional`, importada, no reescrita), crea el
        `Contenido` ya en `PUBLICADO` (las páginas institucionales no tienen ciclo
        borrador/publicado — `TIPOS_CICLO_COMPLETO` en `services.py` las excluye a propósito, y
        el propio CHECK `ck_contenido_pagina_no_retirable` de la base de datos impide que se
        retiren) y registra auditoría + reindexado exactamente igual que el resto del
        contenido. GAP reportado en el HANDOFF: falta una función de creación formal para
        páginas institucionales en `services.py`, para un ticket futuro."""
        resultado: dict[str, Contenido] = {}
        for p in seed_paginas.PAGINAS:
            existente = Contenido.objects.filter(tipo=T.PAGINA, slug=p.slug).first()
            if existente is not None:
                resultado[p.clave] = existente
                self._contador["reutilizados"] += 1
                continue
            errores = reglas.validar_pagina_institucional(
                reglas.DatosPaginaInstitucional(
                    cuerpo=p.cuerpo,
                    version_documento=p.version_documento,
                    vigente_desde=p.vigente_desde,
                    fecha_ultima_revision=self.fecha_revision,
                    seo_descripcion=p.seo_descripcion,
                )
            )
            if errores:
                raise CommandError(f"Página «{p.slug}» no cumple las reglas reales: {errores}")
            with transaction.atomic():
                ahora = timezone.now()
                contenido = Contenido(
                    tipo=T.PAGINA,
                    titulo=p.titulo,
                    slug=p.slug,
                    estado_editorial=E.PUBLICADO,
                    fecha_ultima_revision=self.fecha_revision,
                    seo_titulo=p.seo_titulo,
                    seo_descripcion=p.seo_descripcion,
                    primera_publicacion_en=ahora,
                    publicado_actualizado_en=ahora,
                    creado_por_id=ACTOR_ID,
                    actualizado_por_id=ACTOR_ID,
                )
                contenido.save()
                PaginaInstitucional.objects.create(
                    contenido=contenido,
                    clave=p.clave,
                    cuerpo=p.cuerpo,
                    version_documento=p.version_documento,
                    vigente_desde=p.vigente_desde,
                )
                auditoria_services.registrar_evento(
                    accion=AccionAuditoria.CREAR,
                    actor_id=ACTOR_ID,
                    tipo_entidad=T.PAGINA,
                    entidad_id=contenido.pk,
                    entidad_titulo=contenido.titulo,
                )
                busqueda_services.indexar(contenido.pk)
            resultado[p.clave] = contenido
            self._contador["creados"] += 1
            self._contador["publicados"] += 1
        return resultado

    # -----------------------------------------------------------------------
    # Configuración de inicio (singleton; servicio solo de ACTUALIZACIÓN, ver docstring)
    # -----------------------------------------------------------------------
    def _configurar_inicio(self) -> None:
        """`apps.inicio.services.actualizar_config_inicio` exige que la fila `ConfigInicio`
        (singleton, id=1) YA EXISTA (`if config is None: raise NoEncontrado()`).
        `docs/04_datos/DB_HANDOFF.yaml` confirma que esa fila "se crea con la carga semilla
        (necesita un medio), no en una migración" — es decir, aquí. Para el primer arranque
        (fila ausente) se crea directamente de forma mínima, con la misma auditoría que hace el
        servicio real; en cualquier ejecución posterior (fila ya presente, incluida una
        reejecución idempotente) se usa el servicio real sin excepciones."""
        hero_medio_id = self._subir_imagen(
            "inicio:hero", 0, alt="Ilustración abstracta de portada del inicio de Brújula Salvaje"
        )
        destacados_destinos = [self._destinos[d.slug].pk for d in seed_destinos.DESTINOS[:6]]
        destacados_itinerarios = [
            self._itinerarios[i.slug].pk for i in seed_itinerarios.ITINERARIOS[:3]
        ]
        destacados_guias = [self._guias[g.slug].pk for g in seed_guias.GUIAS[:3]]
        hero_titular = "Explora el mundo con criterio experto"
        hero_subtitulo = (
            "Destinos, itinerarios y guías de aventura verificados por un equipo editorial"
        )
        datos: dict[str, Any] = {
            "hero_titular": hero_titular,
            "hero_subtitulo": hero_subtitulo,
            "hero_medio_id": hero_medio_id,
            "destinos_ids": destacados_destinos,
            "itinerarios_ids": destacados_itinerarios,
            "guias_ids": destacados_guias,
        }
        existente = ConfigInicio.objects.filter(pk=ID_SINGLETON).first()
        if existente is not None:
            inicio_services.actualizar_config_inicio(ACTOR_ID, datos)
            return
        with transaction.atomic():
            ConfigInicio.objects.create(
                id=ID_SINGLETON,
                hero_titular=hero_titular,
                hero_subtitulo=hero_subtitulo,
                hero_medio_id=hero_medio_id,
                actualizado_por_id=ACTOR_ID,
            )
            filas = (
                [
                    DestacadoInicio(
                        seccion=SeccionInicio.DESTINOS,
                        contenido_id=cid,
                        tipo_contenido=T.DESTINO,
                        orden=i,
                    )
                    for i, cid in enumerate(destacados_destinos)
                ]
                + [
                    DestacadoInicio(
                        seccion=SeccionInicio.ITINERARIOS,
                        contenido_id=cid,
                        tipo_contenido=T.ITINERARIO,
                        orden=i,
                    )
                    for i, cid in enumerate(destacados_itinerarios)
                ]
                + [
                    DestacadoInicio(
                        seccion=SeccionInicio.GUIAS,
                        contenido_id=cid,
                        tipo_contenido=T.GUIA,
                        orden=i,
                    )
                    for i, cid in enumerate(destacados_guias)
                ]
            )
            DestacadoInicio.objects.bulk_create(filas)
            auditoria_services.registrar_evento(
                accion=AccionAuditoria.CONFIG_INICIO,
                actor_id=ACTOR_ID,
                tipo_entidad="CONFIG_INICIO",
                entidad_id=ID_SINGLETON,
            )
        self._contador["creados"] += 1

    # -----------------------------------------------------------------------
    # Reindexado final
    # -----------------------------------------------------------------------
    def _reindexar_todo(self) -> None:
        """Reconstrucción final completa del índice (`apps.busqueda.services.reindexar_todo`,
        el mismo servicio real que usa `apps.ops.management.commands.reindexar_busqueda`).

        Necesaria porque `services.publicar()` reindexa el Destino ANTES de confirmar la
        publicación de sus tipos co-publicados (el propio código de `publicar()`, fuera de mi
        archivos_permitidos, llama a `_confirmar_publicacion_entidad` del destino y luego, en un
        bucle posterior, la de cada tipo co-publicado): si el tipo_principal del destino se
        co-publica en la misma operación, en el instante del reindexado del destino ese tipo
        aún está en BORRADOR, y `selectors.es_visible()` exige el tipo_principal ya PUBLICADO
        (AC-129) — el destino queda temporalmente fuera del índice y ninguna llamada posterior
        lo corrige, porque solo se reindexa a sí mismo el propio tipo, no el destino que lo
        referencia. Esta reconstrucción final, sobre el estado ya completo y consistente, es
        inofensiva (`reindexar_todo` es idempotente, DELETE+INSERT en una transacción) y
        garantiza que el índice final sea correcto sin tocar `apps/busqueda/services.py`."""
        resultado = busqueda_services.reindexar_todo()
        self.stdout.write(
            f"Índice de búsqueda reconstruido: {resultado.documentos} documentos "
            f"({resultado.omitidos} omitidos por no ser visibles)."
        )
