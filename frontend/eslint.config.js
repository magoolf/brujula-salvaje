// @ts-check
// ESLint (flat config) — reglas arquitectónicas de Skill_Frontend §13-§14 y seguridad de §27.4.
// Reglas ESLint del estándar: 01, 02, 03, 04, 05, 06, 08, 09, 10, 13. Revisión humana: 07 y 11.
// Compilador: 12 (los comandos devuelven `ErrorApi | null`, ver core/http/ejecutar.ts).
const eslint = require('@eslint/js');
const { defineConfig } = require('eslint/config');
const tseslint = require('typescript-eslint');
const angular = require('angular-eslint');

// Selectores reutilizados ---------------------------------------------------------------------
const EN_COMPONENTE = "ClassDeclaration:has(Decorator[expression.callee.name='Component'])";

const SEGURIDAD = [
  {
    selector: 'MemberExpression[property.name=/^bypassSecurityTrust/]',
    message: '§27.4: prohibido bypassSecurityTrust*.',
  },
  { selector: "CallExpression[callee.name='eval']", message: '§27.4: prohibido eval.' },
  { selector: "NewExpression[callee.name='Function']", message: '§27.4: prohibido new Function.' },
  {
    selector: 'AssignmentExpression[left.property.name=/^(innerHTML|outerHTML)$/]',
    message: '§27.4: prohibido innerHTML/outerHTML.',
  },
  {
    selector: "CallExpression[callee.property.name='insertAdjacentHTML']",
    message: '§27.4: prohibido insertAdjacentHTML.',
  },
  {
    selector: "CallExpression[callee.object.name='document'][callee.property.name='write']",
    message: '§27.4: prohibido document.write.',
  },
];

const REGLA_06 = {
  selector: `${EN_COMPONENTE} CallExpression[callee.property.name='subscribe']`,
  message:
    'Regla 06: no uses subscribe() en componentes; usa signals (toSignal/httpResource) o el store.',
};
const REGLA_13 = {
  selector: `${EN_COMPONENTE} MemberExpression[property.name='status']`,
  message: 'Regla 13: los componentes no dependen de códigos HTTP; usa ErrorApi.categoria.',
};
const REGLA_02 = {
  selector: 'Literal[value=/^\\/(api|health)\\//]',
  message: 'Regla 02: las URL del backend solo viven en data/ (y en el cliente generado).',
};
const REGLA_02_PLANTILLA = {
  selector: 'TemplateElement[value.raw=/^\\/(api|health)\\//]',
  message: 'Regla 02: las URL del backend solo viven en data/ (y en el cliente generado).',
};

const IMPORT_HTTP_ERROR = {
  name: '@angular/common/http',
  importNames: ['HttpErrorResponse'],
  message: 'Regla 09: HttpErrorResponse solo en core/http.',
};
const IMPORT_HTTP_CLIENT = {
  name: '@angular/common/http',
  importNames: ['HttpClient', 'httpResource'],
  message: 'Regla 01: HttpClient/httpResource solo en data/ y core/http.',
};
const IMPORT_CATCH = [
  {
    name: 'rxjs',
    importNames: ['catchError'],
    message: 'Regla 10: sin catchError en state/ ni ui/; usa ejecutar().',
  },
  {
    name: 'rxjs/operators',
    importNames: ['catchError'],
    message: 'Regla 10: sin catchError en state/ ni ui/.',
  },
];
const PATRON_DTO = {
  group: ['**/api', '**/api/**'],
  message: 'Regla 04: los DTO generados solo se importan en data/.',
};
// Desde features/<f>/<capa>/archivo.ts, «../../<otra>» llega a otra feature (aproximación para
// archivos en la raíz de cada capa; «../../../» sale a app/ y está permitido para shared/ y core/).
const PATRON_FEATURES = {
  regex: String.raw`(^|/)features/|^\.\./\.\./(?!\.\.)`,
  message: 'Regla 05: sin imports entre features; lo común va en shared/ o core/.',
};
const PATRON_FEATURES_DESDE_CORE = {
  group: ['**/features/**'],
  message: 'shared/ y core/ no dependen de features.',
};

module.exports = defineConfig([
  {
    ignores: [
      'dist/**',
      'coverage/**',
      '.angular/**',
      'node_modules/**',
      'src/app/api/**',
      'playwright-report/**',
      'test-results/**',
    ],
  },
  {
    files: ['**/*.ts'],
    extends: [
      eslint.configs.recommended,
      tseslint.configs.recommended,
      tseslint.configs.stylistic,
      angular.configs.tsRecommended,
    ],
    processor: angular.processInlineTemplates,
    rules: {
      '@angular-eslint/directive-selector': [
        'error',
        { type: 'attribute', prefix: 'app', style: 'camelCase' },
      ],
      '@angular-eslint/component-selector': [
        'error',
        { type: 'element', prefix: 'app', style: 'kebab-case' },
      ],
      '@angular-eslint/prefer-on-push-component-change-detection': 'off', // OnPush es el valor por defecto en Angular 22
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', destructuredArrayIgnorePattern: '^_' },
      ],
      'no-restricted-syntax': ['error', ...SEGURIDAD, REGLA_06, REGLA_13],
      'no-restricted-imports': ['error', { paths: [IMPORT_HTTP_ERROR, IMPORT_HTTP_CLIENT] }],
    },
  },
  // Código de aplicación fuera de data/ y de la infraestructura HTTP: Regla 02 (URL del backend).
  {
    files: ['src/app/**/*.ts'],
    ignores: [
      'src/app/features/*/data/**',
      'src/app/core/http/**',
      'src/app/core/auth/**',
      'src/app/**/*.spec.ts',
    ],
    rules: {
      'no-restricted-syntax': [
        'error',
        ...SEGURIDAD,
        REGLA_06,
        REGLA_13,
        REGLA_02,
        REGLA_02_PLANTILLA,
      ],
    },
  },
  // core/http: única ubicación de HttpErrorResponse (09) y, con data/, de HttpClient (01).
  {
    files: ['src/app/core/http/**/*.ts'],
    rules: { 'no-restricted-imports': 'off' },
  },
  // data/ de cada feature: HttpClient y DTO permitidos; HttpErrorResponse no (09).
  {
    files: ['src/app/features/*/data/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        { paths: [IMPORT_HTTP_ERROR], patterns: [PATRON_FEATURES] },
      ],
    },
  },
  // state/ y ui/ de las features: 01, 04, 05, 09 y 10.
  {
    files: ['src/app/features/*/state/**/*.ts', 'src/app/features/*/ui/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [IMPORT_HTTP_ERROR, IMPORT_HTTP_CLIENT, ...IMPORT_CATCH],
          patterns: [PATRON_DTO, PATRON_FEATURES],
        },
      ],
    },
  },
  // state/: Regla 03, sin señales escribibles públicas.
  {
    files: ['src/app/features/*/state/**/*.ts'],
    rules: {
      'no-restricted-syntax': [
        'error',
        ...SEGURIDAD,
        REGLA_02,
        {
          selector:
            "PropertyDefinition:not([accessibility='private']):not([key.type='PrivateIdentifier']) > CallExpression[callee.name=/^(signal|linkedSignal)$/]",
          message:
            'Regla 03: las señales escribibles del store deben ser privadas; expón computed()/asReadonly().',
        },
      ],
    },
  },
  // domain/: Regla 08, sin Angular ni RxJS.
  {
    files: ['src/app/features/*/domain/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@angular/*', 'rxjs', 'rxjs/*'],
              message: 'Regla 08: domain/ no depende de Angular ni RxJS.',
            },
            PATRON_DTO,
            PATRON_FEATURES,
          ],
        },
      ],
    },
  },
  // shared/ y core/layout|seo|forms: presentación e infraestructura sin DTO ni catchError.
  {
    files: [
      'src/app/shared/**/*.ts',
      'src/app/core/layout/**/*.ts',
      'src/app/core/seo/**/*.ts',
      'src/app/core/forms/**/*.ts',
    ],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [IMPORT_HTTP_ERROR, IMPORT_HTTP_CLIENT, ...IMPORT_CATCH],
          patterns: [PATRON_DTO, PATRON_FEATURES_DESDE_CORE],
        },
      ],
    },
  },
  // Pruebas y configuración de herramientas.
  {
    files: ['**/*.spec.ts', 'e2e/**/*.ts', 'playwright.config.ts', 'vitest-base.config.mts'],
    rules: {
      'no-restricted-imports': 'off',
      'no-restricted-syntax': ['error', ...SEGURIDAD],
      '@typescript-eslint/no-non-null-assertion': 'off',
    },
  },
  {
    files: ['**/*.html'],
    extends: [angular.configs.templateRecommended, angular.configs.templateAccessibility],
    rules: {},
  },
]);
