import { DOCUMENT } from '@angular/common';
import {
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Conectividad } from '../../../core/layout/conectividad';
import { Seo } from '../../../core/seo/seo';
import { Banner } from '../../../shared/ui/banner/banner';
import { Boton } from '../../../shared/ui/boton/boton';
import { EstadoCargando } from '../../../shared/ui/estado-cargando/estado-cargando';
import { EstadoError } from '../../../shared/ui/estado-error/estado-error';
import { Insignia } from '../../../shared/ui/insignia/insignia';
import {
  AVISO_PENDIENTE_ACTIVACION,
  AYUDA_USUARIO,
  AccionCuenta,
  CAMPOS_CUENTA,
  CampoCuenta,
  DEFINICION_ACCION,
  ETIQUETA_ESTADO_CUENTA,
  FormularioCuenta,
  LIMITE_NOMBRE_VISIBLE,
  ROLES,
  erroresCuenta,
  esAnonimizada,
  formularioDesdeCuenta,
  mensajeConflictoCuenta,
  pendienteDeActivacion,
  TEXTO_SALIDA_SECRETO,
  varianteEstadoCuenta,
} from '../domain/cuentas';
import { sinError } from '../domain/errores-formulario';
import { formatearFechaHora } from '../domain/fechas';
import { RolPanel } from '../domain/modelos';
import { ETIQUETA_ROL, RUTA_USUARIOS } from '../domain/secciones';
import { FormularioCuentaStore } from '../state/cuentas-equipo.store';
import { AccesoDenegado } from './acceso-denegado';
import { CampoTexto } from './campo-texto';
import { ControlSalida } from './control-salida';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { PaginaNoEncontradaPanel } from './pagina-no-encontrada-panel';
import { ConSalidaControlada } from './salida-editor.guard';
import { SecretoTemporal } from './secreto-temporal';

const ID_CAMPO: Readonly<Record<CampoCuenta, string>> = {
  usuario: 'cuenta-usuario',
  nombreVisible: 'cuenta-nombre',
  rol: 'cuenta-rol',
};

const DESCRIPCION_ROL: Readonly<Record<RolPanel, string>> = {
  EDITOR: 'Crea, edita y publica contenido, medios, destacados y taxonomías.',
  ADMINISTRADOR: 'Además gestiona las cuentas, la auditoría, las licencias, las escalas y la configuración del sitio.',
};

/**
 * SCR-045 Formulario de cuenta (FEAT-045, FLOW-015, RULE-015, AC-106/107/108, TPL-PANEL-SHELL;
 * solo Administrador). Alta: usuario, nombre visible y rol → «Crear» → OneTimeSecret con la
 * contraseña temporal (se muestra una sola vez). Edición: usuario inmutable, nombre visible y rol →
 * «Guardar»; sección «Acciones de la cuenta» con Restablecer contraseña, Restablecer verificación
 * en dos pasos, Desactivar, Reactivar y Anonimizar ahora (solo DESACTIVADA), cada una con su efecto
 * descrito y confirmación. Lo que RULE-015 impide se muestra deshabilitado con el motivo.
 */
@Component({
  selector: 'app-pagina-formulario-cuenta',
  imports: [
    RouterLink,
    Banner,
    Boton,
    EstadoCargando,
    EstadoError,
    Insignia,
    AccesoDenegado,
    CampoTexto,
    DialogoConfirmacion,
    PaginaNoEncontradaPanel,
    SecretoTemporal,
  ],
  providers: [FormularioCuentaStore],
  template: `
    @if (store.noEncontrado()) {
      <app-pagina-no-encontrada-panel />
    } @else if (store.accesoDenegado()) {
      <app-acceso-denegado />
    } @else {
      <div class="pagina ancho-640" data-testid="pagina-formulario-cuenta">
        @if (!store.secreto()) {
          <p class="volver"><a [routerLink]="rutaUsuarios" data-testid="cuenta-volver">Volver a Cuentas del equipo</a></p>
        }

        @if (store.secreto(); as secreto) {
          <app-secreto-temporal [usuario]="secreto.usuario" [secreto]="secreto.contrasena" (guardado)="alGuardarSecreto()" />
        } @else {
          @if (store.esAlta()) {
            <h1 tabindex="-1" #encabezado>Nueva cuenta</h1>
            <p class="nota">La cuenta queda pendiente de activación: en su primer acceso deberá cambiar la contraseña temporal y autorizar el tratamiento de datos.</p>
          } @else if (store.cuenta(); as cuenta) {
            <header class="titulo-insignia">
              <h1 tabindex="-1" #encabezado data-testid="cuenta-titulo">{{ cuenta.etiqueta }}</h1>
              <app-insignia [variante]="varianteEstado(cuenta.estado)" data-testid="cuenta-estado">{{ etiquetaEstado[cuenta.estado] }}</app-insignia>
            </header>
            @if (store.avisoExito(); as aviso) {
              <app-banner variante="success" testId="cuenta-exito">{{ aviso }}</app-banner>
            }
            @if (errorAccion(); as mensaje) {
              <app-banner variante="error" testId="cuenta-error-accion">{{ mensaje }}</app-banner>
            }
            <dl class="datos" data-testid="cuenta-datos">
              <div><dt>Verificación en dos pasos</dt><dd>{{ cuenta.mfaActivo ? 'Activada' : 'No activada' }}</dd></div>
              <div><dt>Último acceso</dt><dd>{{ cuenta.ultimoAccesoEn ? fechaHora(cuenta.ultimoAccesoEn) : 'Nunca' }}</dd></div>
              <div><dt>Alta</dt><dd>{{ fechaHora(cuenta.creadoEn) }}</dd></div>
              @if (cuenta.desactivadoEn; as fecha) {
                <div><dt>Desactivada</dt><dd>{{ fechaHora(fecha) }}</dd></div>
              }
            </dl>
            @if (avisoPendiente()) {
              <app-banner variante="info" testId="cuenta-aviso-pendiente">{{ textoPendiente }}</app-banner>
            }
            @if (anonimizada()) {
              <p class="nota" data-testid="cuenta-anonimizada">Esta cuenta está anonimizada: sus datos se eliminaron y la auditoría muestra un seudónimo. No admite cambios.</p>
            }
          } @else if (store.error(); as error) {
            <h1 tabindex="-1">Cuenta del equipo</h1>
            <app-estado-error [mensaje]="error.mensaje" [anunciar]="true" [rutaSalida]="rutaUsuarios" etiquetaSalida="Volver a Cuentas del equipo" testId="cuenta-error" (reintentar)="store.recargar()" />
          } @else {
            <h1 tabindex="-1">Cuenta del equipo</h1>
            <app-estado-cargando forma="linea" [cantidad]="4" etiqueta="Cargando la cuenta…" testId="cuenta-cargando" />
          }
          @if (mostrarFormulario()) {
            @if (erroresGenerales().length > 0) {
              <div id="cuenta-errores" class="resumen-errores" tabindex="-1" role="alert" data-testid="cuenta-errores">
                @for (mensaje of erroresGenerales(); track $index) {
                  <p>{{ mensaje }}</p>
                }
              </div>
            }
            <form class="formulario seccion" novalidate (submit)="enviar($event)" data-testid="cuenta-formulario">
              <h2 class="bs-solo-lectores">Datos de la cuenta</h2>
              @if (store.esAlta()) {
                <app-campo-texto [campo]="usuario" etiqueta="Usuario" [idCampo]="id.usuario" nombreCampo="usuario" [obligatorio]="true" [ayuda]="ayudaUsuario" autocomplete="off" [error]="errores().usuario ?? null" testId="cuenta-campo-usuario" (editado)="limpiarError('usuario')" />
              } @else {
                <div class="campo">
                  <label [for]="id.usuario">Usuario</label>
                  <input class="entrada-texto mono" type="text" readonly [id]="id.usuario" name="usuario" [value]="usuario()" aria-describedby="cuenta-usuario-ayuda" data-testid="cuenta-campo-usuario" />
                  <p class="ayuda" id="cuenta-usuario-ayuda">El usuario no se puede cambiar.</p>
                </div>
              }
              <app-campo-texto [campo]="nombreVisible" etiqueta="Nombre visible" [idCampo]="id.nombreVisible" nombreCampo="nombre_visible" [obligatorio]="true" [maximo]="limiteNombre" [error]="errores().nombreVisible ?? null" testId="cuenta-campo-nombre" (editado)="limpiarError('nombreVisible')" />
              <fieldset class="grupo" [id]="id.rol" tabindex="-1" [attr.aria-describedby]="motivoRol() ? 'cuenta-rol-motivo' : null" data-testid="cuenta-campo-rol">
                <legend>Rol <span class="obligatorio">(obligatorio)</span></legend>
                @if (motivoRol(); as motivo) {
                  <p class="ayuda" id="cuenta-rol-motivo" data-testid="cuenta-rol-motivo">{{ motivo }}</p>
                }
                @for (r of roles; track r) {
                  <label class="casilla">
                    <input type="radio" name="rol" [value]="r" [checked]="rol() === r" [disabled]="motivoRol() !== null" [attr.data-testid]="'cuenta-rol-' + r" (change)="elegirRol(r)" />
                    <span><strong>{{ etiquetaRol[r] }}</strong> <span class="ayuda">{{ descripcionRol[r] }}</span></span>
                  </label>
                }
                @if (errores().rol; as mensaje) {
                  <p class="error-campo" data-testid="cuenta-campo-rol-error">{{ mensaje }}</p>
                }
              </fieldset>
              <div class="acciones">
                <button type="submit" appBoton [cargando]="guardando()" [deshabilitadoEnfocable]="!enLinea()" data-testid="cuenta-guardar">
                  {{ guardando() ? 'Guardando…' : store.esAlta() ? 'Crear' : 'Guardar' }}
                </button>
                @if (!enLinea()) {
                  <p class="ayuda">Sin conexión: podrás guardar cuando vuelva.</p>
                }
              </div>
            </form>
          }
          @if (mostrarAcciones()) {
              <section class="seccion acciones-cuenta" aria-labelledby="cuenta-acciones-titulo" data-testid="cuenta-acciones">
                <h2 id="cuenta-acciones-titulo">Acciones de la cuenta</h2>
                <ul class="lista-acciones">
                  @for (a of store.acciones(); track a.accion) {
                    <li>
                      <p class="efecto" [id]="'cuenta-accion-' + a.accion + '-efecto'">{{ definiciones[a.accion].efecto }}</p>
                      @if (a.motivo; as motivo) {
                        <p class="ayuda" [id]="'cuenta-accion-' + a.accion + '-motivo'" [attr.data-testid]="'cuenta-accion-' + a.accion + '-motivo'">{{ motivo }}</p>
                      }
                      <button
                        type="button"
                        appBoton
                        [variante]="definiciones[a.accion].destructiva ? 'danger' : 'secondary'"
                        [deshabilitadoEnfocable]="a.motivo !== null || !enLinea()"
                        [attr.aria-describedby]="'cuenta-accion-' + a.accion + '-efecto' + (a.motivo ? ' cuenta-accion-' + a.accion + '-motivo' : '')"
                        [attr.data-testid]="'cuenta-accion-' + a.accion"
                        (click)="pedirAccion(a.accion, a.motivo)"
                      >
                        {{ definiciones[a.accion].etiqueta }}
                      </button>
                    </li>
                  }
                </ul>
              </section>
          }
        }

        <app-dialogo-confirmacion
          [abierto]="accionPendiente() !== null"
          (abiertoChange)="accionPendiente.set(null)"
          [titulo]="tituloConfirmacion()"
          [textoConfirmar]="textoConfirmar()"
          [variante]="varianteConfirmar()"
          [procesando]="procesando()"
          [respaldoFoco]="encabezado()?.nativeElement ?? null"
          idBase="cuenta-dialogo-accion"
          (confirmar)="confirmarAccion()"
        >
          <p>{{ efectoPendiente() }}</p>
        </app-dialogo-confirmacion>
        <app-dialogo-confirmacion
          [abierto]="salida.abierta()"
          (abiertoChange)="responderSalida(false)"
          titulo="¿Salir sin guardar la contraseña temporal?"
          textoConfirmar="Salir sin guardarla"
          idBase="cuenta-dialogo-salir"
          (confirmar)="responderSalida(true)"
        >
          <p>{{ textoSalidaSecreto }}</p>
        </app-dialogo-confirmacion>
      </div>
    }
  `,
  styleUrls: ['./panel-formularios.css', './panel-pantallas.css'],
  styles: `
    .volver {
      margin: 0;
    }
    .datos {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
      gap: var(--bs-space-3);
      margin: 0;
    }
    .datos dt {
      font-size: var(--bs-typography-body-sm-font-size);
      color: var(--bs-color-text-muted);
    }
    .datos dd {
      margin: 0;
    }
    .grupo {
      display: grid;
      gap: var(--bs-space-2);
      margin: 0;
      padding: 0;
      border: 0;
    }
    legend {
      margin-bottom: var(--bs-space-2);
      font-weight: var(--bs-font-weight-semibold);
    }
    .casilla {
      display: flex;
      align-items: flex-start;
      gap: var(--bs-space-2);
      min-height: var(--bs-size-target);
    }
    .casilla input {
      margin-top: 0.3em;
    }
    .acciones-cuenta {
      border-top: var(--bs-border-width-strong) solid var(--bs-color-border-subtle);
    }
    .acciones-cuenta h2 {
      margin: 0;
    }
    .lista-acciones {
      display: grid;
      gap: var(--bs-space-4);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .lista-acciones li {
      display: grid;
      gap: var(--bs-space-2);
      justify-items: start;
    }
    .efecto {
      margin: 0;
    }
  `,
})
export class PaginaFormularioCuenta implements ConSalidaControlada {
  protected readonly store = inject(FormularioCuentaStore);
  protected readonly enLinea = inject(Conectividad).enLinea;
  private readonly router = inject(Router);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly seo = inject(Seo);
  protected readonly encabezado = viewChild<ElementRef<HTMLElement>>('encabezado');

  protected readonly id = ID_CAMPO;
  protected readonly roles = ROLES;
  protected readonly etiquetaRol = ETIQUETA_ROL;
  protected readonly descripcionRol = DESCRIPCION_ROL;
  protected readonly etiquetaEstado = ETIQUETA_ESTADO_CUENTA;
  protected readonly varianteEstado = varianteEstadoCuenta;
  protected readonly definiciones = DEFINICION_ACCION;
  protected readonly ayudaUsuario = AYUDA_USUARIO;
  protected readonly limiteNombre = LIMITE_NOMBRE_VISIBLE;
  protected readonly rutaUsuarios = RUTA_USUARIOS;
  protected readonly fechaHora = formatearFechaHora;

  protected readonly usuario = signal('');
  protected readonly nombreVisible = signal('');
  protected readonly rol = signal<RolPanel | ''>('');
  protected readonly errores = signal<Partial<Record<CampoCuenta, string>>>({});
  protected readonly erroresGenerales = signal<readonly string[]>([]);
  protected readonly guardando = signal(false);
  protected readonly procesando = signal(false);
  protected readonly errorAccion = signal<string | null>(null);
  protected readonly accionPendiente = signal<AccionCuenta | null>(null);

  protected readonly textoPendiente = AVISO_PENDIENTE_ACTIVACION;
  protected readonly textoSalidaSecreto = TEXTO_SALIDA_SECRETO;
  /** OneTimeSecret: salir sin «Ya la guardé» pide confirmación (y aviso nativo al recargar o cerrar). */
  protected readonly salida = new ControlSalida(() => this.store.secreto() !== null);
  protected readonly mostrarFormulario = computed(
    () => this.store.esAlta() || (this.store.cuenta() !== null && !this.anonimizada()),
  );
  protected readonly mostrarAcciones = computed(
    () => !this.store.esAlta() && this.mostrarFormulario() && this.store.acciones().length > 0,
  );
  protected readonly avisoPendiente = computed(() => {
    const cuenta = this.store.cuenta();
    return cuenta !== null && pendienteDeActivacion(cuenta);
  });
  protected readonly anonimizada = computed(() => {
    const cuenta = this.store.cuenta();
    return cuenta !== null && esAnonimizada(cuenta);
  });
  protected readonly motivoRol = computed(() => (this.store.esAlta() ? null : this.store.motivoRol()));
  protected readonly tituloConfirmacion = computed(() => {
    const accion = this.accionPendiente();
    const cuenta = this.store.cuenta();
    return accion === null ? '' : `¿${DEFINICION_ACCION[accion].etiqueta} la cuenta ${cuenta?.etiqueta ?? ''}?`;
  });
  protected readonly textoConfirmar = computed(() => {
    const accion = this.accionPendiente();
    return accion === null ? 'Confirmar' : DEFINICION_ACCION[accion].confirmar;
  });
  protected readonly varianteConfirmar = computed(() => {
    const accion = this.accionPendiente();
    return accion !== null && DEFINICION_ACCION[accion].destructiva ? 'danger' : 'primary';
  });
  protected readonly efectoPendiente = computed(() => {
    const accion = this.accionPendiente();
    return accion === null ? '' : DEFINICION_ACCION[accion].efecto;
  });

  constructor() {
    this.seo.establecer({ titulo: 'Cuenta del equipo', indexable: false });
    effect(() => {
      const cuenta = this.store.cuenta();
      const alta = this.store.esAlta();
      untracked(() => {
        if (alta) {
          this.seo.establecer({ titulo: 'Nueva cuenta', indexable: false });
          return;
        }
        if (cuenta === null) return;
        const f = formularioDesdeCuenta(cuenta);
        this.usuario.set(f.usuario);
        this.nombreVisible.set(f.nombreVisible);
        this.rol.set(f.rol);
        this.seo.establecer({ titulo: `${cuenta.etiqueta} · Cuentas del equipo`, indexable: false });
      });
    });
  }

  protected limpiarError(campo: CampoCuenta): void {
    this.errores.update((actual) => sinError(actual, campo));
  }

  protected elegirRol(rol: RolPanel): void {
    this.rol.set(rol);
    this.limpiarError('rol');
  }

  protected async enviar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.guardando() || !this.enLinea()) return;
    const formulario: FormularioCuenta = {
      usuario: this.usuario(),
      nombreVisible: this.nombreVisible(),
      rol: this.rol(),
    };
    this.erroresGenerales.set([]);
    this.errorAccion.set(null);
    const locales = this.store.validar(formulario);
    this.errores.set(locales);
    if (Object.keys(locales).length > 0) {
      this.enfocarPrimerError();
      return;
    }
    this.guardando.set(true);
    const esAlta = this.store.esAlta();
    const error = esAlta ? await this.store.crear(formulario) : await this.store.guardar(formulario);
    this.guardando.set(false);
    if (error === null) {
      // Tras el alta, la URL pasa a la ficha de la cuenta creada (sin entrada nueva en el historial):
      // una recarga no vuelve a ofrecer el alta (QA TKT-024 FALLO-01).
      const secreto = this.store.secreto();
      if (esAlta && secreto !== null) {
        await this.router.navigate([RUTA_USUARIOS, secreto.cuentaId], { replaceUrl: true });
        // El foco de cambio de ruta (FocoRuta) iría al contenido: se devuelve al título del secreto.
        afterNextRender(() => this.documento.getElementById('secreto-titulo')?.focus(), { injector: this.injector });
      }
      return;
    }
    if (error.codigo === 'duplicado') {
      this.errores.set({ usuario: 'Ya existe una cuenta con ese usuario.' });
    } else if (error.categoria === 'conflicto') {
      this.errores.set({});
      this.erroresGenerales.set([mensajeConflictoCuenta(error.codigo, error.mensaje, 'rol')]);
    } else {
      const { porCampo, generales } = erroresCuenta(error.campos, error.mensaje);
      this.errores.set(porCampo);
      this.erroresGenerales.set(generales);
    }
    this.enfocarPrimerError();
  }

  protected pedirAccion(accion: AccionCuenta, motivo: string | null): void {
    if (motivo !== null || !this.enLinea()) return;
    this.errorAccion.set(null);
    this.accionPendiente.set(accion);
  }

  protected async confirmarAccion(): Promise<void> {
    const accion = this.accionPendiente();
    if (accion === null || this.procesando()) return;
    this.procesando.set(true);
    const error = await this.store.ejecutarAccion(accion);
    this.procesando.set(false);
    this.accionPendiente.set(null);
    if (error !== null) {
      this.errorAccion.set(error.categoria === 'conflicto' ? mensajeConflictoCuenta(error.codigo, error.mensaje, accion) : error.mensaje);
    }
  }

  /** «Ya la guardé»: se olvida el secreto; tras el alta se va a la ficha de la cuenta creada. */
  protected alGuardarSecreto(): void {
    this.store.olvidarSecreto();
    afterNextRender(() => this.encabezado()?.nativeElement.focus(), { injector: this.injector });
  }

  /**
   * canDeactivate (QA TKT-024 FALLO-01): con la contraseña temporal sin confirmar, salir (Volver,
   * menú, Atrás) pide confirmación; el paso del alta a la ficha de la cuenta creada no cuenta.
   */
  puedeSalir(destino: string): boolean | Promise<boolean> {
    const secreto = this.store.secreto();
    if (secreto !== null && destino === `${RUTA_USUARIOS}/${secreto.cuentaId}`) return true;
    return this.salida.puedeSalir();
  }

  protected responderSalida(salir: boolean): void {
    if (salir) this.store.olvidarSecreto();
    this.salida.responder(salir);
  }

  private enfocarPrimerError(): void {
    afterNextRender(
      () => {
        const campo = CAMPOS_CUENTA.find((c) => this.errores()[c] !== undefined);
        this.documento.getElementById(campo ? ID_CAMPO[campo] : 'cuenta-errores')?.focus();
      },
      { injector: this.injector },
    );
  }
}
