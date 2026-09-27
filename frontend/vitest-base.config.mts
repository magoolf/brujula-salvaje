import { defineConfig } from 'vitest/config';

/**
 * Configuración base de Vitest que carga el builder `@angular/build:unit-test` (runnerConfig).
 * Umbrales de cobertura de Skill_Frontend §27.2 (el comando falla si no se cumplen):
 *   domain/ ≥ 90 % (líneas y ramas) · state/ ≥ 80 % · global ≥ 70 %.
 * El cliente generado (src/app/api) se excluye: es código generado desde el contrato, no escrito
 * a mano (angular.json → test.options.coverageExclude).
 */
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text-summary', 'text', 'lcov'],
      thresholds: {
        lines: 70,
        statements: 70,
        functions: 70,
        branches: 70,
        '**/domain/**': { lines: 90, branches: 90, statements: 90, functions: 90 },
        '**/state/**': { lines: 80, branches: 80, statements: 80, functions: 80 },
      },
    },
  },
});
