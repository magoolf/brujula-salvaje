/** Cabecera con la que el proxy entrega el nonce CSP de cada petición al SSR (DEVOPS_HANDOFF §5.3). */
export const CABECERA_NONCE_CSP = 'x-csp-nonce';

/** Formato del nonce que genera el proxy (`$request_id` de nginx: 32 hex) o base64/base64url. */
const NONCE_VALIDO = /^[A-Za-z0-9+/=_-]{16,128}$/;

/**
 * Nonce CSP por petición (RSK-UX-001): el proxy lo genera, descarta el que envíe el cliente y lo
 * pasa al SSR; Angular lo aplica a sus <script> y <style> en línea. Un valor con formato
 * inesperado se ignora (null), de modo que nunca se refleja texto arbitrario en el HTML.
 */
export function nonceDesdePeticion(cabecera: string | null | undefined): string | null {
  return typeof cabecera === 'string' && NONCE_VALIDO.test(cabecera) ? cabecera : null;
}
