import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express, { NextFunction, Request, Response } from 'express';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Servidor SSR (Node + Express 5) detrás del proxy de mismo origen (DEVOPS_HANDOFF §5 y §6.4):
 * - GET /healthz → 200 sin llamar a la API (healthcheck del contenedor).
 * - Estáticos del build con caché larga (nombres con hash) salvo el HTML.
 * - Renderizado de Angular; el nonce CSP llega en `X-CSP-Nonce` (app.config.server.ts) y las
 *   llamadas a la API usan `API_INTERNAL_URL` reenviando X-Forwarded-For/traceparent/X-Request-Id
 *   (core/http/reenvio-ssr-interceptor.ts).
 * - Hosts permitidos: variable NG_ALLOWED_HOSTS (la lee AngularNodeAppEngine).
 * - Si el renderizado falla: HTTP 500 con la página estática SCR-025 (sin datos ni scripts).
 */
const browserDistFolder = join(import.meta.dirname, '../browser');

const app = express();
const angularApp = new AngularNodeAppEngine();

app.disable('x-powered-by');
app.set('trust proxy', false);

app.get('/healthz', (_req: Request, res: Response) => {
  res.set('Cache-Control', 'no-store');
  res.status(200).json({ status: 'ok' });
});

app.use(
  express.static(browserDistFolder, {
    index: false,
    redirect: false,
    dotfiles: 'ignore',
    setHeaders: (res, ruta) => {
      const conHash = /[.-][A-Z0-9]{8,}\.(?:js|css|woff2)$/i.test(ruta);
      res.setHeader('Cache-Control', conHash ? 'public, max-age=31536000, immutable' : 'public, max-age=3600');
      res.setHeader('X-Content-Type-Options', 'nosniff');
    },
  }),
);

app.use((req: Request, res: Response, next: NextFunction) => {
  angularApp
    .handle(req)
    .then((response) => (response ? writeResponseToNodeResponse(response, res) : next()))
    .catch(next);
});

let paginaError: string | null = null;
function paginaErrorEstatica(): string {
  if (paginaError === null) {
    try {
      paginaError = readFileSync(join(browserDistFolder, '500.html'), 'utf8');
    } catch {
      paginaError = '<!doctype html><html lang="es"><meta charset="utf-8"><title>Error del servidor</title><h1>Tuvimos un problema de nuestro lado</h1><p><a href="/">Ir al inicio</a></p></html>';
    }
  }
  return paginaError;
}

// Manejador final de errores: nunca expone trazas (ST-ERROR, THREAT-028); registra sin PII.
app.use((error: unknown, req: Request, res: Response, _next: NextFunction) => {
  console.error(
    JSON.stringify({
      evento: 'error_ssr',
      nombre: error instanceof Error ? error.name : typeof error,
      ruta: req.path,
      traceparent: typeof req.headers['traceparent'] === 'string' ? req.headers['traceparent'] : null,
    }),
  );
  if (res.headersSent) return;
  res.status(500).set({ 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }).send(paginaErrorEstatica());
});

/**
 * Arranca el servidor si este módulo es el punto de entrada (o se ejecuta con PM2).
 * Puerto: variable PORT (4000 por defecto, igual que el Dockerfile).
 */
if (isMainModule(import.meta.url) || process.env['pm_id']) {
  const port = Number(process.env['PORT'] ?? 4000);
  app.listen(port, (error) => {
    if (error) {
      throw error;
    }
    console.log(JSON.stringify({ evento: 'ssr_iniciado', puerto: port }));
  });
}

/** Manejador usado por el Angular CLI (dev-server y build). */
export const reqHandler = createNodeRequestHandler(app);
