// P2-C (móvil): manejo de errores por código. La API normaliza los errores como
// `ApiError { code, status }` (status 0 == error de red). Solo una sesión vencida (401) expulsa
// al login; el resto se muestra. En particular, el error al confirmar un canje NO se ignora.

import { ApiError } from '@tarjeta/api-client';

export type ClaseError =
  | 'sesion'
  | 'permiso'
  | 'no_encontrado'
  | 'negocio'
  | 'limite'
  | 'servidor'
  | 'red'
  | 'desconocido';

export function clasificarError(err: unknown): ClaseError {
  if (err instanceof ApiError) {
    if (err.status === 401) return 'sesion';
    if (err.status === 403) return 'permiso';
    if (err.status === 404) return 'no_encontrado';
    if (err.status === 409 || err.status === 422) return 'negocio';
    if (err.status === 429) return 'limite';
    if (err.status >= 500) return 'servidor';
    if (err.status === 0 || err.code === 'network_error') return 'red';
  }
  return 'desconocido';
}

const MENSAJES: Record<ClaseError, string> = {
  sesion: 'Tu sesión venció. Volvé a iniciar sesión.',
  permiso: 'No tenés permiso para esta acción.',
  no_encontrado: 'No encontramos lo que buscabas.',
  negocio: 'No pudimos completar la operación.',
  limite: 'Alcanzaste el máximo permitido por ahora. Probá más tarde.',
  servidor: 'Tuvimos un problema de nuestro lado. Probá de nuevo en un momento.',
  red: 'Sin conexión. Revisá tu internet y reintentá.',
  desconocido: 'Ocurrió un error inesperado.',
};

/** Mensaje para la UI. En errores de negocio se prefiere el texto del backend. */
export function mensajeDeError(err: unknown): string {
  const clase = clasificarError(err);
  if (clase === 'negocio' && err instanceof ApiError && err.message) return err.message;
  return MENSAJES[clase];
}

/** Única condición para expulsar al login: la sesión venció (401). */
export function esSesionVencida(err: unknown): boolean {
  return clasificarError(err) === 'sesion';
}
