import { ApiError } from '@tarjeta/api-client';
import { describe, expect, it } from 'vitest';
import { clasificarError, esSesionVencida, mensajeDeError } from './errores';

const err = (status: number, code = `http_${status}`, message = '') =>
  new ApiError(message, code, status);

describe('clasificarError', () => {
  it.each([
    [401, 'sesion'],
    [403, 'permiso'],
    [404, 'no_encontrado'],
    [409, 'negocio'],
    [422, 'negocio'],
    [429, 'limite'],
    [500, 'servidor'],
    [503, 'servidor'],
    [0, 'red'],
  ] as const)('status %i => %s', (status, clase) => {
    expect(clasificarError(err(status))).toBe(clase);
  });

  it('network_error (code) cuenta como red', () => {
    expect(clasificarError(new ApiError('x', 'network_error', 0))).toBe('red');
  });

  it('un error que no es ApiError es desconocido', () => {
    expect(clasificarError(new Error('boom'))).toBe('desconocido');
    expect(clasificarError('cualquier cosa')).toBe('desconocido');
  });
});

describe('esSesionVencida', () => {
  it('solo 401 expulsa al login', () => {
    expect(esSesionVencida(err(401))).toBe(true);
    for (const s of [403, 404, 409, 422, 429, 500, 0]) {
      expect(esSesionVencida(err(s))).toBe(false);
    }
  });
});

describe('mensajeDeError', () => {
  it('en negocio prefiere el mensaje del backend', () => {
    expect(mensajeDeError(err(422, 'topes', 'Alcanzaste el tope del día'))).toBe(
      'Alcanzaste el tope del día',
    );
  });

  it('un 500 no se disfraza de límite ni de código inválido', () => {
    const m = mensajeDeError(err(500));
    expect(m).not.toMatch(/máximo|inválido/i);
    expect(m.length).toBeGreaterThan(0);
  });

  it('un error de red tiene su propio mensaje', () => {
    expect(mensajeDeError(err(0))).toMatch(/conexión/i);
  });
});
