import { isPlatformBrowser } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  PLATFORM_ID,
  afterNextRender,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';

/**
 * Distancia de pre-carga (TKT-018): margen del `IntersectionObserver` propio que sustituye la
 * confianza ciega en `loading="lazy"` nativo. Medido con evidencia real (stack Docker + semilla +
 * Playwright): el umbral nativo de Chromium en una conexión sin limitar es tan generoso que una
 * rejilla de 24 tarjetas dispara sus 24 peticiones de imagen casi en el mismo milisegundo (confirmado
 * por captura de red real), lo que por sí solo agota una fracción relevante del burst=60 del
 * limitador de nginx (infra/proxy/nginx.conf) -- y se suma al de la página anterior si el visitante
 * navega poco después (TKT-008/009). Un margen de 300px (~0.4 alturas de viewport de escritorio)
 * solo adelanta las imágenes realmente próximas a aparecer, escalonando el resto con el scroll real
 * del usuario en vez de una ráfaga única al montar la ruta.
 */
const MARGEN_PRECARGA_PX = 300;

/**
 * Formatos de derivado que publica el backend (contrato `FormatoDerivado`, DEC-AUTO-044). Se
 * redeclaran aquí como tipo de presentación propio: `shared/ui` no importa DTOs del cliente
 * generado (Skill_Frontend Regla 04).
 */
export type FormatoImagen = 'AVIF' | 'WEBP' | 'JPEG';

/**
 * Derivado responsivo de una imagen (DEC-AUTO-044): URL de mismo origen, ancho intrínseco y, si el
 * llamador lo conoce, su formato. Sin `formato` se deduce de la extensión (`formatoDeUrl`).
 */
export interface DerivadoImagen {
  readonly url: string;
  readonly ancho: number;
  readonly formato?: FormatoImagen;
}

const TIPO_MIME: Readonly<Record<FormatoImagen, string>> = {
  AVIF: 'image/avif',
  WEBP: 'image/webp',
  JPEG: 'image/jpeg',
};

/**
 * Orden de los `<source>` (TKT-020): el navegador usa el PRIMER `<source>` cuyo `type` soporta, así
 * que va del formato más eficiente al menos eficiente. JPEG nunca va en un `<source>`: es el
 * respaldo universal del `<img>`.
 */
const FORMATOS_EN_SOURCE: readonly FormatoImagen[] = ['AVIF', 'WEBP'];

/**
 * Formato deducido de la extensión de la URL, o `null` si no es reconocible. Los derivados
 * públicos se nombran `<huella>-<ancho>.<avif|webp|jpeg>` (backend/apps/medios, DEC-AUTO-110) y el
 * proxy solo sirve esas extensiones bajo `/media/publico/`, con el `Content-Type` derivado de ella:
 * la extensión ES el tipo que recibe el navegador. Solo se usa si el llamador no pasa `formato`.
 */
export function formatoDeUrl(url: string): FormatoImagen | null {
  const extension = /\.([A-Za-z0-9]+)(?:[?#].*)?$/.exec(url)?.[1]?.toLowerCase();
  switch (extension) {
    case 'avif':
      return 'AVIF';
    case 'webp':
      return 'WEBP';
    case 'jpg':
    case 'jpeg':
      return 'JPEG';
    default:
      return null;
  }
}

function formatoDe(derivado: DerivadoImagen): FormatoImagen | null {
  return derivado.formato ?? formatoDeUrl(derivado.url);
}

function esValido(d: DerivadoImagen): boolean {
  return Number.isInteger(d.ancho) && d.ancho > 0 && d.url.trim() !== '';
}

/** `srcset` ordenado por ancho, sin duplicados ni anchos inválidos. */
export function construirSrcset(derivados: readonly DerivadoImagen[]): string {
  const vistos = new Set<number>();
  return [...derivados]
    .filter(esValido)
    .sort((a, b) => a.ancho - b.ancho)
    .filter((d) => (vistos.has(d.ancho) ? false : (vistos.add(d.ancho), true)))
    .map((d) => `${encodeURI(d.url)} ${d.ancho}w`)
    .join(', ');
}

/** Un `<source>` del `<picture>`: un único formato, con su tipo MIME declarado. */
export interface FuenteImagen {
  readonly formato: FormatoImagen;
  readonly tipo: string;
  readonly srcset: string;
  /** URLs (codificadas como en el `srcset`) para reconocer qué `<source>` falló. */
  readonly urls: readonly string[];
}

/** Reparto de los derivados entre los `<source>` y el `<img>` de respaldo. */
export interface PlanImagen {
  readonly fuentes: readonly FuenteImagen[];
  /** Candidatos del `<img>`: el formato más compatible disponible (JPEG si existe). */
  readonly respaldo: readonly DerivadoImagen[];
}

/**
 * TKT-020 (F-2): reparte los derivados por formato. Antes todos los anchos iban mezclados en un único
 * `srcset` sin tipo y, al deduplicar por ancho, ganaba siempre el primer formato listado (AVIF): un
 * navegador sin AVIF descargaba el archivo y no podía decodificarlo. Ahora:
 * - cada formato eficiente (AVIF, WebP) va en su `<source type>`, que un navegador sin soporte
 *   salta SIN descargarlo;
 * - el `<img>` lleva el formato más compatible disponible: JPEG (más los de formato no reconocible,
 *   que conservan el comportamiento anterior); si no hay ninguno, el menos exigente de los
 *   eficientes (WebP antes que AVIF), que entonces no se repite en un `<source>`.
 * `descartados` son formatos cuyo `<source>` ya falló en este navegador (ver `alFallar`).
 */
export function planificarFormatos(
  derivados: readonly DerivadoImagen[],
  descartados: ReadonlySet<FormatoImagen> = new Set<FormatoImagen>(),
): PlanImagen {
  const validos = derivados.filter(esValido);
  const deFormato = (f: FormatoImagen) => validos.filter((d) => formatoDe(d) === f);
  let respaldo = validos.filter((d) => {
    const formato = formatoDe(d);
    return formato === null || formato === 'JPEG';
  });
  let formatoRespaldo: FormatoImagen | null = null;
  if (respaldo.length === 0) {
    formatoRespaldo =
      [...FORMATOS_EN_SOURCE].reverse().find((f) => deFormato(f).length > 0) ?? null;
    respaldo = formatoRespaldo === null ? [] : deFormato(formatoRespaldo);
  }
  const fuentes = FORMATOS_EN_SOURCE.filter(
    (f) => f !== formatoRespaldo && !descartados.has(f) && deFormato(f).length > 0,
  ).map((f) => {
    const candidatos = deFormato(f);
    return {
      formato: f,
      tipo: TIPO_MIME[f],
      srcset: construirSrcset(candidatos),
      urls: candidatos.map((d) => encodeURI(d.url)),
    };
  });
  return { fuentes, respaldo };
}

/**
 * `src` del `<img>` de respaldo. Debe ser de un formato del respaldo: si el llamador pasó como `src`
 * un derivado AVIF/WebP (los mappers usan el primer derivado de la lista), se sustituye por el
 * candidato del respaldo del MISMO ancho o, si no lo hay, por el más pequeño. Sin respaldo
 * (p. ej. sin derivados), el `src` recibido tal cual.
 */
export function elegirSrcRespaldo(
  src: string,
  derivados: readonly DerivadoImagen[],
  respaldo: readonly DerivadoImagen[],
): string {
  if (respaldo.length === 0 || respaldo.some((d) => d.url === src)) return src;
  const formatoSrc = formatoDeUrl(src);
  if (formatoSrc === null || respaldo.some((d) => formatoDe(d) === formatoSrc)) return src;
  const anchoSrc = derivados.find((d) => d.url === src)?.ancho;
  const ordenados = [...respaldo].sort((a, b) => a.ancho - b.ancho);
  return (ordenados.find((d) => d.ancho === anchoSrc) ?? ordenados[0]).url;
}

/**
 * Imagen responsiva (DEC-AUTO-072, PERFORMANCE_SPEC): `<picture>` con un `<source>` por formato
 * eficiente (AVIF, WebP) y un `<img>` de respaldo (JPEG) -- TKT-020 --, `sizes`, width/height o
 * aspect-ratio reservados (CLS 0), `loading=lazy` salvo la imagen LCP (`prioritaria`: eager +
 * fetchpriority high). Si la imagen no carga en NINGÚN formato utilizable (ALT-009) el contenedor
 * conserva su tamaño y muestra el texto alternativo. `alt=""` marca la imagen como decorativa
 * (p. ej. en tarjetas cuyo título ya nombra el contenido).
 *
 * Cuándo se emiten `src`/`srcset` (TKT-018 + TKT-020 F-1):
 * - prioritaria (LCP): siempre, en SSR y en cliente, sin diferir;
 * - informativa (`alt` no vacío: galerías, miniaturas de créditos): siempre, también en el HTML del
 *   SSR, para que cargue sin JavaScript y la vean los rastreadores; el escalonado lo hace el
 *   `loading="lazy"` nativo;
 * - decorativa (`alt=""`, p. ej. las rejillas de tarjetas, origen de la ráfaga de TKT-018): la
 *   petición de red se retiene hasta que un `IntersectionObserver` propio (margen
 *   `MARGEN_PRECARGA_PX`) confirma que está próxima al viewport. SIN JavaScript estas NO cargan:
 *   no aportan contenido (su título ya está en texto), solo se pierde el adorno.
 * La decisión depende solo de las entradas, así que es idéntica en SSR y en el primer render del
 * cliente (sin incompatibilidades de hidratación). El `<img>` permanece siempre en el DOM (Regla de
 * composición de TarjetaContenido y sus pruebas): solo se retienen los atributos de red.
 */
@Component({
  selector: 'app-imagen-responsiva',
  template: `
    <div class="marco" [style.aspect-ratio]="proporcion()" [attr.data-testid]="testId()">
      @if (!fallida()) {
        <picture>
          @for (fuente of plan().fuentes; track fuente.formato) {
            <source
              [attr.type]="fuente.tipo"
              [attr.sizes]="mostrar() ? sizes() : null"
              [attr.srcset]="mostrar() ? fuente.srcset : null"
            />
          }
          <img
            [alt]="alt()"
            [attr.width]="ancho()"
            [attr.height]="alto()"
            [attr.loading]="prioritaria() ? 'eager' : 'lazy'"
            [attr.fetchpriority]="prioritaria() ? 'high' : null"
            decoding="async"
            [attr.sizes]="mostrar() && srcsetRespaldo() ? sizes() : null"
            [attr.srcset]="mostrar() && srcsetRespaldo() ? srcsetRespaldo() : null"
            [attr.src]="mostrar() ? srcRespaldo() : null"
            (error)="alFallar($event)"
          />
        </picture>
      } @else if (alt()) {
        <p class="alternativo" data-testid="imagen-fallida">{{ alt() }}</p>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    .marco {
      position: relative;
      overflow: hidden;
      background: var(--bs-color-bg-sunken);
      border-radius: inherit;
    }
    picture {
      display: block;
      width: 100%;
      height: 100%;
    }
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center;
    }
    .alternativo {
      position: absolute;
      inset: auto 0 0 0;
      padding: var(--bs-space-2) var(--bs-space-3);
      font-size: var(--bs-typography-caption-font-size);
      line-height: var(--bs-typography-caption-line-height);
      color: var(--bs-color-text-muted);
    }
  `,
})
export class ImagenResponsiva {
  readonly src = input.required<string>();
  readonly alt = input.required<string>();
  readonly ancho = input.required<number>();
  readonly alto = input.required<number>();
  readonly derivados = input<readonly DerivadoImagen[]>([]);
  /** Atributo sizes por plantilla (PERFORMANCE_SPEC.Sizes_Recomendados). */
  readonly sizes = input('100vw');
  readonly prioritaria = input(false);
  /** Relación de aspecto CSS (p. ej. `var(--bs-aspect-card)` o `4 / 3`); por defecto ancho/alto. */
  readonly relacion = input<string | null>(null);
  readonly testId = input('imagen-responsiva');

  private readonly elementoHost = inject(ElementRef<HTMLElement>);
  private readonly injector = inject(Injector);
  private readonly destroyRef = inject(DestroyRef);
  private readonly esNavegador = isPlatformBrowser(inject(PLATFORM_ID));

  private readonly _fallida = signal(false);
  protected readonly fallida = this._fallida.asReadonly();
  /** Formatos cuyo `<source>` ya falló en este navegador (TKT-020). */
  private readonly _descartados = signal<ReadonlySet<FormatoImagen>>(new Set<FormatoImagen>());
  protected readonly plan = computed(() =>
    planificarFormatos(this.derivados(), this._descartados()),
  );
  protected readonly srcsetRespaldo = computed(() => construirSrcset(this.plan().respaldo));
  protected readonly srcRespaldo = computed(() =>
    elegirSrcRespaldo(this.src(), this.derivados(), this.plan().respaldo),
  );
  protected readonly proporcion = computed(
    () => this.relacion() ?? `${this.ancho()} / ${this.alto()}`,
  );

  /**
   * TKT-018: las decorativas no prioritarias esperan al IntersectionObserver. Arranca en `false`
   * IGUAL en SSR y en el primer render del cliente: si SSR mostrara una imagen que el cliente
   * arrancara ocultando, la hidratación quitaría el `src` ya emitido (petición cancelada y parpadeo).
   */
  private readonly _cercaDelViewport = signal(false);
  protected readonly mostrar = computed(
    () => this.prioritaria() || this.alt().trim() !== '' || this._cercaDelViewport(),
  );

  constructor() {
    afterNextRender(
      () => {
        if (!this.esNavegador || this.prioritaria()) return;
        if (typeof IntersectionObserver === 'undefined') {
          // Sin soporte (o entorno de pruebas sin polyfill): degrada al comportamiento previo,
          // carga inmediata confiando solo en el `loading="lazy"` nativo del <img>.
          this._cercaDelViewport.set(true);
          return;
        }
        const observador = new IntersectionObserver(
          (entradas) => {
            if (entradas.some((e) => e.isIntersecting)) {
              this._cercaDelViewport.set(true);
              observador.disconnect();
            }
          },
          { rootMargin: `${MARGEN_PRECARGA_PX}px 0px` },
        );
        observador.observe(this.elementoHost.nativeElement);
        this.destroyRef.onDestroy(() => observador.disconnect());
      },
      { injector: this.injector },
    );
  }

  /**
   * TKT-020 (AC_TKT020_06): un fallo NO es definitivo mientras quede otro formato. Un `<picture>` no
   * pasa solo al siguiente `<source>` si el elegido falla (red, o un navegador que declara soportar
   * AVIF pero no lo decodifica): se descarta ese formato y el navegador vuelve a elegir entre los
   * restantes (quitar un `<source>` es una "mutación relevante" que reinicia la selección). Solo
   * cuando falla el `<img>` de respaldo -- no queda ningún formato utilizable -- se muestra el texto
   * alternativo (ALT-009).
   */
  protected alFallar(evento: Event): void {
    const fuentes = this.plan().fuentes;
    const actual = (evento.target as HTMLImageElement | null)?.currentSrc ?? '';
    const fuenteFallida =
      actual === '' ? fuentes[0] : fuentes.find((f) => f.urls.some((url) => actual.endsWith(url)));
    if (fuenteFallida === undefined) {
      this._fallida.set(true);
      return;
    }
    this._descartados.update((previos) => new Set([...previos, fuenteFallida.formato]));
  }
}
