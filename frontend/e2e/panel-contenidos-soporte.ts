/**
 * Soporte de las E2E de contenidos del panel (TKT-023). Prepara datos por la API del panel (con la
 * sesión de la página: page.request comparte sus cookies) para que cada caso sea independiente y
 * se pueda repetir en los 3 motores: títulos y descripciones SEO con sufijo aleatorio (RULE-008 y
 * RULE-027 exigen unicidad). Reintenta tras el Retry-After de un 429 `limite_tasa` (límites reales
 * del entorno compartido).
 */
import { randomBytes } from 'node:crypto';

import { APIResponse, Page, expect } from '@playwright/test';

const API = '/api/v1/panel';

async function csrf(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  return cookies.find((c) => c.name === 'csrftoken')?.value ?? '';
}

async function conReintento(peticion: () => Promise<APIResponse>): Promise<APIResponse> {
  for (let intento = 0; intento < 8; intento++) {
    const respuesta = await peticion();
    if (respuesta.status() !== 429) return respuesta;
    const segundos = Number(respuesta.headers()['retry-after'] ?? '5');
    await new Promise((r) => setTimeout(r, ((Number.isFinite(segundos) ? segundos : 5) + 1) * 1000));
  }
  throw new Error('Límite de tasa persistente en la API del panel');
}

export async function apiGet<T>(page: Page, ruta: string): Promise<T> {
  const respuesta = await conReintento(() => page.request.get(`${API}${ruta}`));
  expect(respuesta.status(), `${ruta}: ${await respuesta.text()}`).toBe(200);
  return (await respuesta.json()) as T;
}

export async function apiEscribir<T>(
  page: Page,
  metodo: 'post' | 'put',
  ruta: string,
  datos: unknown,
  esperado = metodo === 'post' ? 201 : 200,
): Promise<T> {
  const respuesta = await conReintento(async () =>
    page.request[metodo](`${API}${ruta}`, { data: datos, headers: { 'X-CSRFToken': await csrf(page) } }),
  );
  expect(respuesta.status(), `${metodo.toUpperCase()} ${ruta}: ${await respuesta.text()}`).toBe(esperado);
  return (await respuesta.json()) as T;
}

export function sufijo(): string {
  return randomBytes(4).toString('hex');
}

interface Pagina<T> {
  readonly resultados: T[];
}

export interface ContenidoApi {
  readonly id: number;
  readonly version: number;
  readonly titulo: string;
  readonly slug: string | null;
  readonly estado_editorial: string;
}

/** Un medio DISPONIBLE de la semilla (portada). */
async function medioDisponible(page: Page): Promise<number> {
  const medios = await apiGet<Pagina<{ id: number }>>(page, '/medios?estado=DISPONIBLE');
  expect(medios.resultados.length, 'la semilla debe tener medios DISPONIBLES').toBeGreaterThan(0);
  return medios.resultados[0].id;
}

/** Tres destinos publicados de la semilla (relacionados de una guía, RULE-006). */
async function destinosPublicados(page: Page): Promise<{ tipo: string; id: number }[]> {
  const destinos = await apiGet<Pagina<{ id: number }>>(page, '/contenidos/destinos?estado=PUBLICADO');
  expect(destinos.resultados.length, 'la semilla debe tener destinos publicados').toBeGreaterThanOrEqual(3);
  return destinos.resultados.slice(0, 3).map((d) => ({ tipo: 'DESTINO', id: d.id }));
}

/**
 * Guía en BORRADOR que cumple los requisitos de publicación (RULE-004/006/009/027): categoría,
 * resumen, cuerpo, portada DISPONIBLE, revisión, fuente, 3 relacionados publicados y SEO único.
 */
export async function crearGuiaPublicable(page: Page, titulo = `Guía E2E ${sufijo()}`): Promise<ContenidoApi> {
  const categorias = await apiGet<Pagina<{ id: number }>>(page, '/taxonomias/categorias-guia');
  // Ayer en UTC: nunca es futura para el navegador, sea cual sea su zona horaria (UTC−12..+14). Con la
  // fecha UTC de hoy, a partir de las 19:00 en Colombia el editor la ve como futura (RULE-009).
  const revision = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
  return apiEscribir<ContenidoApi>(page, 'post', '/contenidos/guias', {
    titulo,
    categoria_id: categorias.resultados[0].id,
    resumen: 'Resumen de una guía creada por las pruebas de extremo a extremo.',
    cuerpo: '<p>Cuerpo de la guía con <strong>consejos</strong> prácticos para la montaña.</p>',
    portada_id: await medioDisponible(page),
    fecha_ultima_revision: revision,
    fuentes: [{ titulo: 'Fuente de prueba', url: 'https://example.org/fuente' }],
    relaciones: await destinosPublicados(page),
    seo_titulo: titulo.slice(0, 70),
    seo_descripcion: `Descripción SEO única ${sufijo()} para la guía de prueba.`,
  });
}

/** Borrador mínimo (solo título) de cualquier tipo con alta. */
export async function crearBorrador(page: Page, ruta: string, titulo: string): Promise<ContenidoApi> {
  return apiEscribir<ContenidoApi>(page, 'post', `/contenidos/${ruta}`, { titulo });
}

/** Publica por la API (sin co-publicación). */
export async function publicarPorApi(page: Page, ruta: string, contenido: ContenidoApi): Promise<void> {
  await apiEscribir(page, 'post', `/contenidos/${ruta}/${contenido.id}/publicar`, { version: contenido.version }, 200);
}

/** Otro editor guarda un cambio (incrementa la versión: bloqueo optimista, AC-110). */
export async function editarComoOtro(page: Page, ruta: string, id: number, cambios: Record<string, unknown>): Promise<ContenidoApi> {
  const actual = await apiGet<ContenidoApi & Record<string, unknown>>(page, `/contenidos/${ruta}/${id}`);
  return apiEscribir<ContenidoApi>(page, 'put', `/contenidos/${ruta}/${id}`, {
    titulo: actual.titulo,
    version: actual.version,
    ...cambios,
  });
}

export async function obtenerContenido(page: Page, ruta: string, id: number): Promise<ContenidoApi & Record<string, unknown>> {
  return apiGet(page, `/contenidos/${ruta}/${id}`);
}
