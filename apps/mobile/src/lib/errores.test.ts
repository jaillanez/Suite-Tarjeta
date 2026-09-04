import { ApiError } from '@tarjeta/api-client';
import { describe, expect, it } from 'vitest';
import { clasificarError, esSesionVencida, mensajeDeError } from './errores';

const err = (status: number, code = `http_${status}`, message = '') =>
  new ApiError(message, code, status);

describe('clasificarError (móvil)', () => {
  it.each([
    [401, 'sesion'],
    [403, 'permiso'],
    [404, 'no_encontrado'],
    [409, 'negocio'],
    [422, 'negocio'],
    [429, 'limite'],
    [500, 'servidor'],
    [0, 'red'],
  ] as const)('status %i => %s', (status, clase) => {
    expect(clasificarError(err(status))).toBe(clase);
  });

  it('lo que no es ApiError es desconocido', () => {
    expect(clasificarError(new Error('x'))).toBe('desconocido');
  });
});

describe('esSesionVencida (móvil)', () => {
  it('solo 401 expulsa al login', () => {
    expect(esSesionVencida(err(401))).toBe(true);
    for (const s of [403, 409, 422, 429, 500, 0]) {
      expect(esSesionVencida(err(s))).toBe(false);
    }
  });
});

describe('mensajeDeError (móvil)', () => {
  it('en negocio prefiere el mensaje del backend', () => {
    expect(mensajeDeError(err(409, 'tope', 'Se agotó el cupo'))).toBe('Se agotó el cupo');
  });

  it('un 500 no se disfraza de límite', () => {
    expect(mensajeDeError(err(500))).not.toMatch(/máximo/i);
  });
});
