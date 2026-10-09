/**
 * Soporte de las E2E de medios del panel (TKT-022): imágenes de prueba generadas en memoria (sin
 * archivos binarios en el repositorio) y atajos de la API para preparar datos.
 *
 * Las imágenes se generan con un codificador PNG mínimo (zlib de Node): cada una lleva bytes
 * aleatorios para que su huella SHA-256 sea única en cada ejecución (la biblioteca detecta
 * duplicados por huella y la BD del stack se conserva entre pruebas). Para megapíxeles y archivos
 * corruptos basta con la cabecera: el servidor valida el tamaño declarado antes de decodificar.
 */
import { randomBytes } from 'node:crypto';
import { deflateSync } from 'node:zlib';

import { Page, expect } from '@playwright/test';

export interface ArchivoPrueba {
  readonly name: string;
  readonly mimeType: string;
  readonly buffer: Buffer;
}

const TABLA_CRC = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(datos: Buffer): number {
  let c = 0xffffffff;
  for (const byte of datos) c = TABLA_CRC[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function bloque(tipo: string, datos: Buffer): Buffer {
  const longitud = Buffer.alloc(4);
  longitud.writeUInt32BE(datos.length);
  const cuerpo = Buffer.concat([Buffer.from(tipo, 'ascii'), datos]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(cuerpo));
  return Buffer.concat([longitud, cuerpo, crc]);
}

const FIRMA_PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function cabecera(ancho: number, alto: number): Buffer {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(ancho, 0);
  ihdr.writeUInt32BE(alto, 4);
  ihdr[8] = 8; // profundidad
  ihdr[9] = 2; // RGB
  return bloque('IHDR', ihdr);
}

/** PNG válido de un color con una fila de ruido aleatorio (huella única). */
export function pngValido(nombre: string, ancho = 1600, alto = 1000): ArchivoPrueba {
  const fila = ancho * 3 + 1;
  const crudo = Buffer.alloc(fila * alto);
  const color = randomBytes(3);
  for (let y = 0; y < alto; y++) {
    for (let x = 0; x < ancho; x++) color.copy(crudo, y * fila + 1 + x * 3);
  }
  randomBytes(ancho * 3).copy(crudo, 1);
  const png = Buffer.concat([
    FIRMA_PNG,
    cabecera(ancho, alto),
    bloque('IDAT', deflateSync(crudo, { level: 1 })),
    bloque('IEND', Buffer.alloc(0)),
  ]);
  return { name: nombre, mimeType: 'image/png', buffer: png };
}

/** PNG con cabecera válida y datos de imagen basura (cabecera de `ancho` × `alto`). */
export function pngSoloCabecera(nombre: string, ancho: number, alto: number): ArchivoPrueba {
  const png = Buffer.concat([
    FIRMA_PNG,
    cabecera(ancho, alto),
    bloque('IDAT', randomBytes(64)),
    bloque('IEND', Buffer.alloc(0)),
  ]);
  return { name: nombre, mimeType: 'image/png', buffer: png };
}

/** GIF mínimo válido (1×1) con el nombre y tipo que se pidan. */
export function gif(nombre: string, mimeType = 'image/gif'): ArchivoPrueba {
  const datos = Buffer.from(
    '47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b',
    'hex',
  );
  return { name: nombre, mimeType, buffer: Buffer.concat([datos, randomBytes(8)]) };
}

/** Archivo mayor de 10 MB (lo rechaza la validación previa del cliente, sin enviarlo). */
export function archivoGrande(nombre: string): ArchivoPrueba {
  return { name: nombre, mimeType: 'image/jpeg', buffer: Buffer.alloc(10 * 1024 * 1024 + 1, 0xff) };
}

// ---------------------------------------------------------------------------------------------
// API (preparación de datos; comparte las cookies de la página)
// ---------------------------------------------------------------------------------------------
const API = '/api/v1/panel';

async function csrf(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  return cookies.find((c) => c.name === 'csrftoken')?.value ?? '';
}

export interface MedioApi {
  readonly id: number;
  readonly estado: string;
  readonly en_uso_publicado: boolean;
  readonly numero_usos: number;
  readonly texto_alternativo: string | null;
  readonly autor_credito: string | null;
  readonly licencia: { id: number; codigo: string } | null;
}

/** Sube una imagen por la API y devuelve el medio aceptado. */
export async function subirPorApi(page: Page, archivo: ArchivoPrueba): Promise<MedioApi> {
  const respuesta = await page.request.post(`${API}/medios`, {
    multipart: { archivos: archivo },
    headers: { 'X-CSRFToken': await csrf(page) },
  });
  expect(respuesta.status(), await respuesta.text()).toBe(200);
  const cuerpo = (await respuesta.json()) as { resultados: { resultado: string; medio: MedioApi }[] };
  expect(cuerpo.resultados[0].resultado).toBe('ACEPTADO');
  return cuerpo.resultados[0].medio;
}

export async function catalogarPorApi(
  page: Page,
  id: number,
  datos: Record<string, unknown>,
): Promise<MedioApi> {
  const respuesta = await page.request.put(`${API}/medios/${id}`, {
    data: datos,
    headers: { 'X-CSRFToken': await csrf(page) },
  });
  expect(respuesta.status(), await respuesta.text()).toBe(200);
  return (await respuesta.json()) as MedioApi;
}

export async function obtenerPorApi(page: Page, id: number): Promise<MedioApi> {
  const respuesta = await page.request.get(`${API}/medios/${id}`);
  expect(respuesta.status()).toBe(200);
  return (await respuesta.json()) as MedioApi;
}

/** Un medio DISPONIBLE usado por contenido publicado (la semilla tiene varios). */
export async function medioEnUsoPublicado(page: Page): Promise<MedioApi> {
  for (let pagina = 1; pagina <= 5; pagina++) {
    const respuesta = await page.request.get(`${API}/medios?en_uso=true&estado=DISPONIBLE&pagina=${pagina}`);
    expect(respuesta.status()).toBe(200);
    const cuerpo = (await respuesta.json()) as { resultados: MedioApi[]; siguiente: string | null };
    const medio = cuerpo.resultados.find((m) => m.en_uso_publicado);
    if (medio) return medio;
    if (cuerpo.siguiente === null) break;
  }
  throw new Error('La semilla no tiene medios en uso por contenido publicado');
}

export interface LicenciaApi {
  readonly id: number;
  readonly codigo: string;
  readonly nombre: string;
}

/** Crea una licencia (solo Administrador). */
export async function crearLicencia(page: Page, compatible: boolean): Promise<LicenciaApi> {
  const codigo = `E2E-${randomBytes(4).toString('hex').toUpperCase()}`;
  const respuesta = await page.request.post(`${API}/taxonomias/licencias`, {
    data: {
      codigo,
      nombre: `Licencia ${codigo}`,
      requiere_atribucion: false,
      compatible_publicacion: compatible,
      activo: true,
    },
    headers: { 'X-CSRFToken': await csrf(page) },
  });
  expect(respuesta.status(), await respuesta.text()).toBe(201);
  return (await respuesta.json()) as LicenciaApi;
}
