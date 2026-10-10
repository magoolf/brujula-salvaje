import { DOCUMENT } from '@angular/common';
import { Component, Injector, WritableSignal, afterNextRender, computed, effect, inject, signal, untracked } from '@angular/core';

import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  CAMPOS_DESTACADOS,
  CampoDestacados,
  FormularioDestacados,
  LIMITE_SUBTITULO,
  LIMITE_TITULAR,
  LISTAS_DESTACADAS,
  ListaDestacada,
  erroresDestacados,
  hayCambiosDestacados,
} from '../domain/destacados';
import { sinError } from '../domain/errores-formulario';
import { formatearFechaHora } from '../domain/fechas';
import { MedioRef, RefContenido, ResultadoBusqueda } from '../domain/formulario-contenido';
import { DerivadoMedio, ETIQUETA_ESTADO_MEDIO, Medio, derivadoPara, varianteEstadoMedio } from '../domain/medios';
import { RUTA_TABLERO } from '../domain/secciones';
import { DestacadosStore } from '../state/destacados.store';
import { AccesoDenegado } from './acceso-denegado';
import { CampoTexto } from './campo-texto';
import { ControlSalida } from './control-salida';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { ListaDestacados } from './lista-destacados';
import { MiniaturaMedio } from './miniatura-medio';
import { ConSalidaControlada } from './salida-editor.guard';
import { SelectorMedios } from './selector-medios';

const ID_CAMPO: Readonly<Record<CampoDestacados, string>> = {
  titular: 'destacados-titular',
  subtitulo: 'destacados-subtitulo',
  medio: 'destacados-imagen',
  destinos: 'destacados-destinos-buscar',
  itinerarios: 'destacados-itinerarios-buscar',
  guias: 'destacados-guias-buscar',
};

function aMedioRef(medio: Medio): MedioRef {
  return {
    id: medio.id,
    estado: medio.estado,
    miniatura: derivadoPara(medio.derivados, 320)?.url ?? null,
    textoAlternativo: medio.textoAlternativo,
  };
}

/**
 * SCR-042 Destacados de inicio (FEAT-043, FLOW-014, RULE-016, AC-011, TPL-PANEL-SHELL): bloque
 * principal (titular ≤80 y subtítulo ≤160 con contadores, imagen con SCR-041 en modo único) y
 * listas de destinos (6-12), itinerarios (3-6) y guías (3-6), cada una con Combobox de contenido
 * PUBLICADO y lista ordenable. Validación de mínimos al guardar; el cambio se aplica al instante
 * (auditoría CONFIG_INICIO) y se ofrece «Ver inicio».
 */
@Component({
  selector: 'app-pagina-destacados',
  imports: [
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    Insignia,
    AccesoDenegado,
    CampoTexto,
    DialogoConfirmacion,
    ListaDestacados,
    MiniaturaMedio,
    SelectorMedios,
  ],
  providers: [DestacadosStore],
  template: `
    @if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina ancho-880" data-testid="pagina-destacados">
        <h1 tabindex="-1">Destacados de inicio</h1>

        @if (store.config(); as config) {
          <p class="nota" data-testid="destacados-actualizado">Última modificación: {{ config.actualizadoPor }} · {{ fechaHora(config.actualizadoEn) }}</p>
          @if (store.guardadoOk()) {
            <app-banner variante="success" testId="destacados-exito" [permitirCerrar]="true" (cerrado)="store.descartarAviso()">
              Los cambios ya se ven en el inicio.
              <a banner-accion href="/" target="_blank" rel="noopener" data-testid="destacados-ver-inicio">Ver inicio<span class="bs-solo-lectores"> (se abre en una pestaña nueva)</span></a>
            </app-banner>
          }
          @if (resumen().length > 0) {
            <div id="destacados-errores" class="resumen-errores" tabindex="-1" role="alert" data-testid="destacados-errores">
              <h2>No se pudo guardar</h2>
              <ul>
                @for (mensaje of resumen(); track $index) {
                  <li>{{ mensaje }}</li>
                }
              </ul>
            </div>
          }

          <form class="formulario" novalidate (submit)="guardar($event)" data-testid="destacados-formulario">
            <section class="seccion" aria-labelledby="destacados-principal-titulo">
              <h2 id="destacados-principal-titulo">Bloque principal</h2>
              <app-campo-texto [campo]="titular" etiqueta="Titular" [idCampo]="id.titular" nombreCampo="hero_titular" [obligatorio]="true" [maximo]="limiteTitular" [error]="errores().titular ?? null" testId="destacados-campo-titular" (editado)="limpiarError('titular')" />
              <app-campo-texto [campo]="subtitulo" etiqueta="Subtítulo" tipo="textarea" [idCampo]="id.subtitulo" nombreCampo="hero_subtitulo" [obligatorio]="true" [maximo]="limiteSubtitulo" [error]="errores().subtitulo ?? null" testId="destacados-campo-subtitulo" (editado)="limpiarError('subtitulo')" />
              <div class="campo">
                <p class="etiqueta-campo" id="destacados-imagen-etiqueta">Imagen <span class="obligatorio">(obligatorio)</span></p>
                @if (medio(); as m) {
                  <div class="mosaico" data-testid="destacados-imagen-elegida">
                    <app-miniatura-medio class="miniatura" [derivados]="derivados()" />
                    <div class="datos-mosaico">
                      <span>{{ m.textoAlternativo || 'Imagen ' + m.id }}</span>
                      @if (m.estado; as estado) {
                        <app-insignia [variante]="varianteMedio(estado)">{{ etiquetaEstadoMedio[estado] }}</app-insignia>
                      }
                    </div>
                  </div>
                } @else {
                  <p class="ayuda">Sin imagen.</p>
                }
                @if (errores().medio; as mensaje) {
                  <p class="error-campo" id="destacados-imagen-error" data-testid="destacados-imagen-error">{{ mensaje }}</p>
                }
                <div class="acciones">
                  <button
                    type="button"
                    appBoton
                    variante="secondary"
                    [id]="id.medio"
                    aria-describedby="destacados-imagen-etiqueta"
                    data-testid="destacados-elegir-imagen"
                    (click)="selectorAbierto.set(true)"
                  >
                    {{ medio() ? 'Cambiar imagen' : 'Elegir imagen' }}
                  </button>
                </div>
              </div>
            </section>

            @for (lista of listas; track lista) {
              <app-lista-destacados
                [lista]="lista"
                [elementos]="elementos[lista]()"
                [error]="errores()[lista] ?? null"
                [buscar]="buscadores[lista]"
                (cambio)="cambiarLista(lista, $event)"
              />
            }

            <div class="acciones">
              <button type="submit" appBoton [cargando]="guardando()" [deshabilitadoEnfocable]="!enLinea()" data-testid="destacados-guardar">
                {{ guardando() ? 'Guardando…' : 'Guardar' }}
              </button>
              @if (!enLinea()) {
                <p class="ayuda">Sin conexión: podrás guardar cuando vuelva.</p>
              }
            </div>
          </form>

          <app-selector-medios
            [abierto]="selectorAbierto()"
            (abiertoChange)="selectorAbierto.set($event)"
            modo="uno"
            titulo="Elegir la imagen del bloque principal"
            idBase="destacados-selector"
            (confirmar)="alElegirImagen($event)"
          />
          <app-dialogo-confirmacion
            [abierto]="salida.abierta()"
            (abiertoChange)="salida.responder(false)"
            titulo="¿Salir sin guardar?"
            textoConfirmar="Salir sin guardar"
            idBase="destacados-dialogo-salir"
            (confirmar)="salida.responder(true)"
          >
            <p>Se perderán los cambios de los destacados que aún no guardaste.</p>
          </app-dialogo-confirmacion>
        } @else if (store.error(); as error) {
          <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaTablero" etiquetaSalida="Ir al Tablero" testId="destacados-error" (reintentar)="store.recargar()" />
        } @else {
          <app-estado-cargando forma="linea" [cantidad]="6" etiqueta="Cargando los destacados…" testId="destacados-cargando" />
        }
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
  styles: `
    .mosaico {
      display: grid;
      grid-template-columns: 8rem 1fr;
      gap: var(--bs-space-3);
      align-items: start;
    }
    .datos-mosaico {
      display: grid;
      gap: var(--bs-space-2);
      justify-items: start;
      overflow-wrap: anywhere;
    }
  `,
})
export class PaginaDestacados implements ConSalidaControlada {
  protected readonly store = inject(DestacadosStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);

  protected readonly id = ID_CAMPO;
  protected readonly listas = LISTAS_DESTACADAS;
  protected readonly limiteTitular = LIMITE_TITULAR;
  protected readonly limiteSubtitulo = LIMITE_SUBTITULO;
  protected readonly rutaTablero = RUTA_TABLERO;
  protected readonly fechaHora = formatearFechaHora;
  protected readonly etiquetaEstadoMedio = ETIQUETA_ESTADO_MEDIO;
  protected readonly varianteMedio = varianteEstadoMedio;

  protected readonly titular = signal('');
  protected readonly subtitulo = signal('');
  protected readonly medio = signal<MedioRef | null>(null);
  protected readonly elementos: Readonly<Record<ListaDestacada, WritableSignal<readonly RefContenido[]>>> = {
    destinos: signal<readonly RefContenido[]>([]),
    itinerarios: signal<readonly RefContenido[]>([]),
    guias: signal<readonly RefContenido[]>([]),
  };
  protected readonly buscadores: Readonly<Record<ListaDestacada, (q: string) => Promise<ResultadoBusqueda>>> = {
    destinos: (q) => this.store.buscar('destinos', q),
    itinerarios: (q) => this.store.buscar('itinerarios', q),
    guias: (q) => this.store.buscar('guias', q),
  };

  protected readonly selectorAbierto = signal(false);
  protected readonly errores = signal<Partial<Record<CampoDestacados, string>>>({});
  protected readonly erroresGenerales = signal<readonly string[]>([]);
  protected readonly guardando = signal(false);

  protected readonly derivados = computed<readonly DerivadoMedio[]>(() => {
    const miniatura = this.medio()?.miniatura;
    return miniatura ? [{ formato: 'WEBP', ancho: 320, alto: null, url: miniatura }] : [];
  });
  private readonly formulario = computed<FormularioDestacados>(() => ({
    titular: this.titular(),
    subtitulo: this.subtitulo(),
    medio: this.medio(),
    destinos: this.elementos.destinos(),
    itinerarios: this.elementos.itinerarios(),
    guias: this.elementos.guias(),
  }));
  /** ErrorSummary: errores generales + los de cada sección (enlazados por su texto). */
  protected readonly resumen = computed(() => [
    ...this.erroresGenerales(),
    ...CAMPOS_DESTACADOS.map((c) => this.errores()[c]).filter((m): m is string => m !== undefined),
  ]);
  protected readonly salida = new ControlSalida(() => hayCambiosDestacados(this.formulario(), this.store.guardado()));

  constructor() {
    inject(Seo).establecer({ titulo: 'Destacados de inicio', indexable: false });
    effect(() => {
      const guardado = this.store.guardado();
      if (guardado === null) return;
      untracked(() => {
        this.titular.set(guardado.titular);
        this.subtitulo.set(guardado.subtitulo);
        this.medio.set(guardado.medio);
        for (const lista of LISTAS_DESTACADAS) this.elementos[lista].set(guardado[lista]);
      });
    });
  }

  puedeSalir(): boolean | Promise<boolean> {
    return this.salida.puedeSalir();
  }

  protected limpiarError(campo: CampoDestacados): void {
    this.errores.update((actual) => sinError(actual, campo));
  }

  protected cambiarLista(lista: ListaDestacada, elementos: readonly RefContenido[]): void {
    this.elementos[lista].set(elementos);
    this.limpiarError(lista);
  }

  protected alElegirImagen(medios: readonly Medio[]): void {
    const medio = medios[0];
    if (!medio) return;
    this.medio.set(aMedioRef(medio));
    this.limpiarError('medio');
  }

  protected async guardar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.guardando() || !this.enLinea()) return;
    const formulario = this.formulario();
    this.erroresGenerales.set([]);
    const locales = this.store.validar(formulario);
    this.errores.set(locales);
    if (Object.keys(locales).length > 0) {
      this.enfocarResumen();
      return;
    }
    this.guardando.set(true);
    const error = await this.store.guardar(formulario);
    this.guardando.set(false);
    if (error === null) return;
    const { porCampo, generales } = erroresDestacados(error.campos, error.mensaje);
    this.errores.set(porCampo);
    this.erroresGenerales.set(generales);
    this.enfocarResumen();
  }

  /** Con errores, el foco va al resumen (FLOW-014: validación de mínimos al guardar). */
  private enfocarResumen(): void {
    afterNextRender(() => this.documento.getElementById('destacados-errores')?.focus(), { injector: this.injector });
  }
}
