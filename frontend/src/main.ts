import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { trasPrimerPintado } from './app/core/arranque/tras-primer-pintado';

// TKT-056: la hidratación espera al primer pintado del HTML del SSR (ver tras-primer-pintado.ts).
trasPrimerPintado(window)
  .then(() => bootstrapApplication(App, appConfig))
  .catch((err) => console.error(err));
