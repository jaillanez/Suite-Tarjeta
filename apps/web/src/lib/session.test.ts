// §12 P1-A: la sesión web guarda el access en memoria y hace un refresh silencioso contra la
// cookie HttpOnly cuando no lo tiene (p. ej. tras recargar). No usa localStorage.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { guardarAccessToken, limpiarAccessToken, obtenerAccessToken } from './session';

const jsonOk = (obj: unknown) =>
  new Response(JSON.stringify(obj), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });

beforeEach(() => {
  limpiarAccessToken();
});

afterEach(() => {
  vi.unstubAllGlobals();
  limpiarAccessToken();
});

describe('session web (P1-A)', () => {
  it('devuelve el access en memoria sin ir a la red', async () => {
    const fn = vi.fn();
    vi.stubGlobal('fetch', fn);
    guardarAccessToken('acc-en-memoria');

    expect(await obtenerAccessToken()).toBe('acc-en-memoria');
    expect(fn).not.toHaveBeenCalled();
  });

  it('sin access hace refresh silencioso con la cookie (credentials include) y lo guarda', async () => {
    const fn = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(jsonOk({ access_token: 'acc-nuevo' })),
    );
    vi.stubGlobal('fetch', fn);

    const token = await obtenerAccessToken();

    expect(token).toBe('acc-nuevo');
    const [url, init] = fn.mock.calls[0] ?? [];
    expect(String(url)).toContain('/api/v1/auth/refresh');
    expect(init?.credentials).toBe('include');
    expect(new Headers(init?.headers).get('x-auth-mode')).toBe('cookie');
    // Queda en memoria: una segunda lectura no vuelve a la red.
    expect(await obtenerAccessToken()).toBe('acc-nuevo');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('coalesce: dos lecturas concurrentes hacen un solo refresh', async () => {
    const fn = vi.fn((_url: string, _init?: RequestInit) =>
      Promise.resolve(jsonOk({ access_token: 'acc-unico' })),
    );
    vi.stubGlobal('fetch', fn);

    const [a, b] = await Promise.all([obtenerAccessToken(), obtenerAccessToken()]);

    expect(a).toBe('acc-unico');
    expect(b).toBe('acc-unico');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('si el refresh falla (401), devuelve null y no rompe', async () => {
    const fn = vi.fn(() => Promise.resolve(new Response('', { status: 401 })));
    vi.stubGlobal('fetch', fn);

    expect(await obtenerAccessToken()).toBeNull();
  });
});
