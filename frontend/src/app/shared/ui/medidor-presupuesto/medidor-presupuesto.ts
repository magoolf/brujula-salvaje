import { Component, input } from '@angular/core';

import { MedidorSegmentado } from '../medidor/medidor-segmentado';

/**
 * BudgetMeter (DEC-AUTO-063): 4 segmentos + «2/4» + etiqueta de la escala + enlace a
 * /acerca-de#escala-de-presupuesto. Sin símbolos de moneda ni cifras (RULE-020, CON-006).
 */
@Component({
  selector: 'app-medidor-presupuesto',
  imports: [MedidorSegmentado],
  template: `
    <app-medidor-segmentado
      concepto="Presupuesto"
      [maximo]="4"
      [valor]="valor()"
      [etiqueta]="etiqueta()"
      [compacto]="compacto()"
      enlaceEscala="escala-de-presupuesto"
      testId="medidor-presupuesto"
    />
  `,
})
export class MedidorPresupuesto {
  readonly valor = input<number | null>(null);
  readonly etiqueta = input<string | null>(null);
  readonly compacto = input(false);
}
