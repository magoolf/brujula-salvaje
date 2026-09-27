import { Injectable, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterStateSnapshot, TitleStrategy } from '@angular/router';

import { tituloConMarca } from './seo';

/** Aplica «{título de la ruta} — {marca}» a toda ruta con `title` (un title único por vista). */
@Injectable()
export class EstrategiaTitulo extends TitleStrategy {
  private readonly titulo = inject(Title);

  override updateTitle(snapshot: RouterStateSnapshot): void {
    const titulo = this.buildTitle(snapshot);
    if (titulo !== undefined) {
      this.titulo.setTitle(tituloConMarca(titulo));
    }
  }
}
