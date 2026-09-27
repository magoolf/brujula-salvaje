import { Component, input } from '@angular/core';

import { MedidorSegmentado } from '../medidor/medidor-segmentado';

/**
 * DifficultyMeter (DEC-AUTO-063, FEAT-015): 5 segmentos + «3/5» + etiqueta de la escala + enlace
 * «¿Qué significa?» a /acerca-de#escala-de-dificultad (RULE-012). Variante compacta para tarjetas.
 */
@Component({
  selector: 'app-medidor-dificultad',
  imports: [MedidorSegmentado],
  template: `
    <app-medidor-segmentado
      concepto="Dificultad"
      [maximo]="5"
      [valor]="valor()"
      [etiqueta]="etiqueta()"
      [compacto]="compacto()"
      enlaceEscala="escala-de-dificultad"
      testId="medidor-dificultad"
    />
  `,
})
export class MedidorDificultad {
  readonly valor = input<number | null>(null);
  readonly etiqueta = input<string | null>(null);
  readonly compacto = input(false);
}
