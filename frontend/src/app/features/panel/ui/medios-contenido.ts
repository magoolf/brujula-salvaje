import { DOCUMENT } from '@angular/common';
import { Component, Injector, afterNextRender, computed, inject, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Boton } from '../../../shared/ui/boton/boton';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  LIMITES,
  MINIMOS,
  MedioRef,
  anadirSinDuplicados,
  anuncioMovido,
  idCampo,
  moverEn,
  quitarEn,
  textoMinimo,
} from '../domain/formulario-contenido';
import {
  DerivadoMedio,
  ETIQUETA_ESTADO_MEDIO,
  Medio,
  derivadoPara,
  varianteEstadoMedio,
} from '../domain/medios';
import { RUTA_MEDIOS } from '../domain/secciones';
import { MiniaturaMedio } from './miniatura-medio';
import { SelectorMedios } from './selector-medios';

/** La miniatura del contrato como único derivado (MiniaturaMedio elige el que haya). */
function derivadosDe(medio: MedioRef | null): readonly DerivadoMedio[] {
  return medio?.miniatura ? [{ formato: 'WEBP', ancho: 320, alto: null, url: medio.miniatura }] : [];
}

function aMedioRef(medio: Medio): MedioRef {
  return {
    id: medio.id,
    estado: medio.estado,
    miniatura: derivadoPara(medio.derivados, 320)?.url ?? null,
    textoAlternativo: medio.textoAlternativo,
  };
}

/**
 * Sección Medios del editor (SCR-036, FEAT-034, RULE-005): portada (MediaTile + «Elegir portada» →
 * SCR-041 en modo único) y, si el tipo la tiene, galería (rejilla ordenable con «Subir»/«Bajar»,
 * alternativa sin arrastre WCAG 2.5.7, + «Añadir imágenes» → SCR-041 múltiple; «{n} de 3 mínimo»).
 * Controlado: recibe la portada y la galería y emite los cambios.
 */
@Component({
  selector: 'app-medios-contenido',
  imports: [RouterLink, Boton, Insignia, MiniaturaMedio, SelectorMedios],
  template: `
    <div class="medios">
      <fieldset class="grupo" [id]="idPortada">
        <legend>Portada @if (obligatorioPublicar()) { <span class="obligatorio">(obligatoria para publicar)</span> }</legend>
        @if (portada(); as medio) {
          <div class="mosaico" data-testid="editor-portada">
            <app-miniatura-medio class="miniatura" [derivados]="derivadosPortada()" />
            <div class="datos-mosaico">
              <span class="titulo-mosaico">{{ medio.textoAlternativo || 'Imagen ' + medio.id }}</span>
              @if (medio.estado; as estado) {
                <app-insignia [variante]="variante(estado)">{{ etiquetaEstado[estado] }}</app-insignia>
              }
              @if (!soloLectura()) {
                <button type="button" class="boton-enlace" data-testid="editor-portada-quitar" (click)="portadaCambio.emit(null)">
                  Quitar portada
                </button>
              }
            </div>
          </div>
        } @else {
          <p class="ayuda">Sin portada.</p>
        }
        @if (errorPortada(); as mensaje) {
          <p class="error-campo" data-testid="campo-portada-error">{{ mensaje }}</p>
        }
        @if (!soloLectura()) {
          <div class="acciones">
            <button type="button" appBoton variante="secondary" data-testid="editor-elegir-portada" (click)="abiertoPortada.set(true)">
              Elegir portada
            </button>
          </div>
        }
      </fieldset>

      @if (conGaleria()) {
        <fieldset class="grupo" [id]="idGaleria">
          <legend>Galería @if (obligatorioPublicar()) { <span class="obligatorio">(mínimo {{ minimo }} para publicar)</span> }</legend>
          <p class="ayuda" data-testid="editor-galeria-recuento">{{ recuento() }}</p>
          @if (galeria().length > 0) {
            <ol class="rejilla" aria-label="Imágenes de la galería, en orden" data-testid="editor-galeria">
              @for (elemento of galeriaVista(); track elemento.medio.id; let i = $index; let ultimo = $last; let primero = $first) {
                @let medio = elemento.medio;
                <li class="mosaico-galeria">
                  <app-miniatura-medio class="miniatura" [derivados]="elemento.derivados" />
                  <span class="posicion">{{ i + 1 }}. {{ medio.textoAlternativo || 'Imagen ' + medio.id }}</span>
                  @if (medio.estado; as estado) {
                    <app-insignia [variante]="variante(estado)">{{ etiquetaEstado[estado] }}</app-insignia>
                  }
                  @if (!soloLectura()) {
                    <div class="acciones-mosaico">
                      <button type="button" appBoton tamano="sm" variante="ghost" [id]="idGaleria + '-subir-' + i" [disabled]="primero" (click)="mover(i, -1)">
                        Subir <span class="bs-solo-lectores">imagen {{ i + 1 }}</span>
                      </button>
                      <button type="button" appBoton tamano="sm" variante="ghost" [id]="idGaleria + '-bajar-' + i" [disabled]="ultimo" (click)="mover(i, 1)">
                        Bajar <span class="bs-solo-lectores">imagen {{ i + 1 }}</span>
                      </button>
                      <button type="button" appBoton tamano="sm" variante="ghost" (click)="quitar(i)">
                        Quitar <span class="bs-solo-lectores">imagen {{ i + 1 }}</span>
                      </button>
                    </div>
                  }
                </li>
              }
            </ol>
          }
          @if (errorGaleria(); as mensaje) {
            <p class="error-campo" data-testid="campo-galeria-error">{{ mensaje }}</p>
          }
          @if (!soloLectura()) {
            <div class="acciones">
              <button type="button" appBoton variante="secondary" data-testid="editor-anadir-imagenes" [disabled]="galeria().length >= limiteGaleria" (click)="abiertoGaleria.set(true)">
                Añadir imágenes
              </button>
              <a [routerLink]="rutaMedios" class="enlace-ayuda">Gestionar la biblioteca de medios</a>
            </div>
          }
        </fieldset>
      }
      <p class="bs-solo-lectores" role="status">{{ anuncio() }}</p>
    </div>

    <app-selector-medios
      [abierto]="abiertoPortada()"
      (abiertoChange)="abiertoPortada.set($event)"
      modo="uno"
      titulo="Elegir portada"
      idBase="editor-selector-portada"
      (confirmar)="alElegirPortada($event)"
    />
    @if (conGaleria()) {
      <app-selector-medios
        [abierto]="abiertoGaleria()"
        (abiertoChange)="abiertoGaleria.set($event)"
        modo="varios"
        titulo="Elegir imágenes"
        idBase="editor-selector-galeria"
        [maximo]="limiteGaleria - galeria().length"
        (confirmar)="alAnadirGaleria($event)"
      />
    }
  `,
  styleUrls: ['./panel-formularios.css'],
  styles: `
    .medios {
      display: grid;
      gap: var(--bs-space-5);
    }
    .grupo {
      display: grid;
      gap: var(--bs-space-3);
      margin: 0;
      padding: 0;
      border: 0;
    }
    legend {
      margin-bottom: var(--bs-space-2);
      font-weight: var(--bs-font-weight-semibold);
    }
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
    }
    .rejilla {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
      gap: var(--bs-space-3);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .mosaico-galeria {
      display: grid;
      gap: var(--bs-space-1);
      align-content: start;
    }
    .posicion {
      font-size: var(--bs-typography-body-sm-font-size);
      overflow-wrap: anywhere;
    }
    .acciones-mosaico {
      display: flex;
      flex-wrap: wrap;
      gap: var(--bs-space-1);
    }
  `,
})
export class MediosContenido {
  readonly portada = input.required<MedioRef | null>();
  readonly galeria = input<readonly MedioRef[]>([]);
  readonly conGaleria = input(false);
  readonly soloLectura = input(false);
  readonly obligatorioPublicar = input(true);
  readonly errorPortada = input<string | null>(null);
  readonly errorGaleria = input<string | null>(null);
  readonly portadaCambio = output<MedioRef | null>();
  readonly galeriaCambio = output<readonly MedioRef[]>();

  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  protected readonly idPortada = idCampo('portada');
  protected readonly idGaleria = idCampo('galeria');
  protected readonly minimo = MINIMOS.galeriaDestino;
  protected readonly limiteGaleria = LIMITES.galeria;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO_MEDIO;
  protected readonly rutaMedios = RUTA_MEDIOS;
  protected readonly abiertoPortada = signal(false);
  protected readonly abiertoGaleria = signal(false);
  protected readonly anuncio = signal('');
  protected readonly derivadosPortada = computed(() => derivadosDe(this.portada()));
  protected readonly galeriaVista = computed(() =>
    this.galeria().map((medio) => ({ medio, derivados: derivadosDe(medio) })),
  );
  protected readonly recuento = computed(() => textoMinimo(this.galeria().length, MINIMOS.galeriaDestino));

  protected variante(estado: MedioRef['estado']) {
    return estado === null ? 'neutral' : varianteEstadoMedio(estado);
  }

  protected alElegirPortada(medios: readonly Medio[]): void {
    const medio = medios[0];
    if (!medio) return;
    this.portadaCambio.emit(aMedioRef(medio));
    this.anuncio.set('Se eligió la portada.');
  }

  protected alAnadirGaleria(medios: readonly Medio[]): void {
    const antes = this.galeria().length;
    const nueva = anadirSinDuplicados(this.galeria(), medios.map(aMedioRef), LIMITES.galeria);
    this.galeriaCambio.emit(nueva);
    const n = nueva.length - antes;
    this.anuncio.set(n === 1 ? 'Se añadió 1 imagen.' : `Se añadieron ${n} imágenes.`);
  }

  protected mover(indice: number, desplazamiento: number): void {
    const destino = indice + desplazamiento;
    const lista = this.galeria();
    if (destino < 0 || destino >= lista.length) return;
    this.galeriaCambio.emit(moverEn(lista, indice, destino));
    this.anuncio.set(anuncioMovido(`Imagen ${indice + 1}`, destino + 1, lista.length));
    const id = `${this.idGaleria}-${desplazamiento < 0 ? 'subir' : 'bajar'}-${destino}`;
    afterNextRender(
      () => {
        const boton = this.documento.getElementById(id) as HTMLButtonElement | null;
        (boton && !boton.disabled ? boton : this.documento.getElementById(`${this.idGaleria}-${desplazamiento < 0 ? 'bajar' : 'subir'}-${destino}`))?.focus();
      },
      { injector: this.injector },
    );
  }

  protected quitar(indice: number): void {
    this.galeriaCambio.emit(quitarEn(this.galeria(), indice));
    this.anuncio.set(`Imagen ${indice + 1} quitada de la galería.`);
  }
}
