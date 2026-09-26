import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NOMBRE_MARCA } from '../../seo/marca';
import { NAVEGACION_INSTITUCIONAL, NAVEGACION_PRINCIPAL } from '../navegacion';

/**
 * SiteFooter GI-02 (HANDOFF_UI_UX): fondo bg.inverse; 3 columnas ≥ md (Explorar · Institucional ·
 * Marca), apiladas < md; enlaces subrayados con foco ring-inverse. Los enlaces institucionales se
 * mantienen siempre en el mismo orden (3.2.6). Incluye la frase de privacidad enlazada a la
 * Política de cookies (RULE-029).
 */
@Component({
  selector: 'app-pie-sitio',
  imports: [RouterLink],
  template: `
    <footer class="pie" data-testid="pie-sitio">
      <div class="bs-contenedor columnas">
        <nav aria-labelledby="pie-explorar">
          <h2 id="pie-explorar" class="titulo">Explorar</h2>
          <ul>
            @for (enlace of explorar; track enlace.id) {
              <li>
                <a [routerLink]="enlace.ruta" [attr.data-testid]="'pie-' + enlace.id">{{
                  enlace.etiqueta
                }}</a>
              </li>
            }
          </ul>
        </nav>
        <nav aria-labelledby="pie-institucional">
          <h2 id="pie-institucional" class="titulo">Institucional</h2>
          <ul>
            @for (enlace of institucional; track enlace.id) {
              <li>
                <a [routerLink]="enlace.ruta" [attr.data-testid]="'pie-' + enlace.id">{{
                  enlace.etiqueta
                }}</a>
              </li>
            }
          </ul>
        </nav>
        <div class="marca">
          <p class="nombre">{{ marca }}</p>
          <p>
            <a routerLink="/politica-de-cookies" data-testid="pie-sin-cookies"
              >Sin cookies ni rastreadores en el sitio público</a
            >
          </p>
        </div>
      </div>
    </footer>
  `,
  styles: `
    .pie {
      margin-top: var(--bs-space-section);
      padding-block: var(--bs-space-12);
      background: var(--bs-color-bg-inverse);
      color: var(--bs-color-text-inverse);
    }
    .columnas {
      display: grid;
      gap: var(--bs-space-8);
    }
    .titulo {
      margin-bottom: var(--bs-space-3);
      font-family: var(--bs-typography-overline-font-family);
      font-size: var(--bs-typography-overline-font-size);
      font-weight: var(--bs-typography-overline-font-weight);
      letter-spacing: var(--bs-typography-overline-letter-spacing);
      text-transform: uppercase;
      color: var(--bs-color-text-inverse-muted);
    }
    ul {
      display: grid;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    a {
      display: inline-flex;
      align-items: center;
      min-height: var(--bs-size-target);
      color: var(--bs-color-text-inverse);
    }
    a:hover {
      color: var(--bs-color-text-inverse);
    }
    a:focus-visible {
      outline-color: var(--bs-color-focus-ring-inverse);
    }
    .nombre {
      font-family: var(--bs-font-family-display);
      font-size: 1.25rem;
      font-weight: var(--bs-font-weight-extrabold);
      margin-bottom: var(--bs-space-2);
    }
    @media (min-width: 48rem) {
      .columnas {
        grid-template-columns: repeat(3, 1fr);
      }
    }
  `,
})
export class PieSitio {
  protected readonly marca = NOMBRE_MARCA;
  protected readonly explorar = NAVEGACION_PRINCIPAL;
  protected readonly institucional = NAVEGACION_INSTITUCIONAL;
}
