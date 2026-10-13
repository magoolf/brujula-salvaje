import { WritableSignal, computed, signal } from '@angular/core';

import {
  ChecklistItemForm,
  DiaForm,
  ElementoColeccionForm,
  FormularioContenido,
  FuenteForm,
  MedioRef,
  OpcionCatalogo,
  RefContenido,
  formularioVacio,
} from '../domain/formulario-contenido';
import { TipoContenido } from '../domain/modelos';

/** Campos de texto del formulario (cada uno con su señal para EnlaceValor / CampoTexto). */
export const CAMPOS_TEXTO = [
  'titulo',
  'slug',
  'fechaRevision',
  'seoTitulo',
  'seoDescripcion',
  'resumen',
  'descripcion',
  'dificultad',
  'pais',
  'tipoPrincipal',
  'duracionMin',
  'duracionMax',
  'presupuesto',
  'clima',
  'altitud',
  'comoLlegar',
  'seguridad',
  'sostenibilidad',
  'latitud',
  'longitud',
  'duracionDias',
  'distanciaTotal',
  'desnivelAcumulado',
  'riesgos',
  'categoria',
  'nivelExigencia',
  'orden',
  'definicion',
  'versionDocumento',
  'vigenteDesde',
] as const;

export type CampoTexto = (typeof CAMPOS_TEXTO)[number];

/**
 * Valores del formulario del editor (SCR-036) como señales de la UI: una por campo de texto (para
 * los controles nativos con EnlaceValor, sin @angular/forms) y una por lista. `valor` compone el
 * `FormularioContenido` que reciben los comandos del store. No es un store: vive en el componente
 * del editor (las señales escribibles no salen de la UI, Regla 03).
 */
export class ModeloFormulario {
  readonly texto: Readonly<Record<CampoTexto, WritableSignal<string>>>;
  readonly fuentes = signal<readonly FuenteForm[]>([]);
  readonly relaciones = signal<readonly RefContenido[]>([]);
  readonly terminos = signal<readonly OpcionCatalogo[]>([]);
  readonly portada = signal<MedioRef | null>(null);
  readonly galeria = signal<readonly MedioRef[]>([]);
  readonly tipos = signal<readonly number[]>([]);
  readonly meses = signal<readonly number[]>([]);
  readonly destino = signal<RefContenido | null>(null);
  readonly dias = signal<readonly DiaForm[]>([]);
  readonly destinos = signal<readonly RefContenido[]>([]);
  readonly remiteMetodologia = signal(false);
  readonly checklist = signal<readonly ChecklistItemForm[]>([]);
  readonly elementos = signal<readonly ElementoColeccionForm[]>([]);

  readonly valor = computed<FormularioContenido>(() => {
    const t = this.texto;
    return {
      tipo: this.tipo,
      titulo: t.titulo(),
      slug: t.slug(),
      fechaRevision: t.fechaRevision(),
      seoTitulo: t.seoTitulo(),
      seoDescripcion: t.seoDescripcion(),
      fuentes: this.fuentes(),
      relaciones: this.relaciones(),
      terminos: this.terminos(),
      resumen: t.resumen(),
      descripcion: t.descripcion(),
      portada: this.portada(),
      galeria: this.galeria(),
      tipos: this.tipos(),
      dificultad: t.dificultad(),
      pais: t.pais(),
      tipoPrincipal: t.tipoPrincipal(),
      meses: this.meses(),
      duracionMin: t.duracionMin(),
      duracionMax: t.duracionMax(),
      presupuesto: t.presupuesto(),
      clima: t.clima(),
      altitud: t.altitud(),
      comoLlegar: t.comoLlegar(),
      seguridad: t.seguridad(),
      sostenibilidad: t.sostenibilidad(),
      latitud: t.latitud(),
      longitud: t.longitud(),
      destino: this.destino(),
      duracionDias: t.duracionDias(),
      distanciaTotal: t.distanciaTotal(),
      desnivelAcumulado: t.desnivelAcumulado(),
      dias: this.dias(),
      riesgos: t.riesgos(),
      categoria: t.categoria(),
      destinos: this.destinos(),
      remiteMetodologia: this.remiteMetodologia(),
      nivelExigencia: t.nivelExigencia(),
      orden: t.orden(),
      checklist: this.checklist(),
      elementos: this.elementos(),
      definicion: t.definicion(),
      versionDocumento: t.versionDocumento(),
      vigenteDesde: t.vigenteDesde(),
    };
  });

  constructor(private readonly tipo: TipoContenido) {
    const vacio = formularioVacio(tipo);
    const texto = {} as Record<CampoTexto, WritableSignal<string>>;
    for (const campo of CAMPOS_TEXTO) texto[campo] = signal(vacio[campo]);
    this.texto = texto;
  }

  /** Sustituye todos los valores (carga, restauración, recarga). */
  cargar(f: FormularioContenido): void {
    for (const campo of CAMPOS_TEXTO) this.texto[campo].set(f[campo]);
    this.fuentes.set(f.fuentes);
    this.relaciones.set(f.relaciones);
    this.terminos.set(f.terminos);
    this.portada.set(f.portada);
    this.galeria.set(f.galeria);
    this.tipos.set(f.tipos);
    this.meses.set(f.meses);
    this.destino.set(f.destino);
    this.dias.set(f.dias);
    this.destinos.set(f.destinos);
    this.remiteMetodologia.set(f.remiteMetodologia);
    this.checklist.set(f.checklist);
    this.elementos.set(f.elementos);
  }
}
