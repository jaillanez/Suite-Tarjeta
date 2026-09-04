// P0 (§12.2-A): el cliente NO debe reintentar mutaciones. Un reintento automático de un POST cuya
// respuesta se perdió aplicaría la operación dos veces (un canje = doble descuento).

import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, createApiClient } from './index';

function contarFetch(impl: () => Promise<Response>) {
  const fn = vi.fn(impl);
  vi.stubGlobal('fetch', fn);
  const api = createApiClient({ baseUrl: 'http://test', maxRetries: 3, retryBaseMs: 0 });
  return { api, fn };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('reintentos del cliente', () => {
  it('un POST con respuesta perdida (error de red) NO se reintenta', async () => {
    const { api, fn } = contarFetch(() => Promise.reject(new Error('conexión perdida')));
    await expect(api.request('/api/v1/canje/iniciar', { method: 'POST' })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fn).toHaveBeenCalledTimes(1); // exactamente un intento: no se duplica la operación
  });

  it('un POST 5xx NO se reintenta', async () => {
    const { api, fn } = contarFetch(() => Promise.resolve(new Response('', { status: 500 })));
    await expect(api.request('/api/v1/canje/iniciar', { method: 'POST' })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('un GET sí se reintenta ante error de red (idempotente)', async () => {
    const { api, fn } = contarFetch(() => Promise.reject(new Error('conexión perdida')));
    await expect(api.request('/api/v1/promociones/feed')).rejects.toBeInstanceOf(ApiError);
    expect(fn).toHaveBeenCalledTimes(4); // 1 + maxRetries(3)
  });

  it('un GET 5xx se reintenta y luego falla', async () => {
    const { api, fn } = contarFetch(() => Promise.resolve(new Response('', { status: 503 })));
    await expect(api.request('/api/v1/promociones/feed')).rejects.toBeInstanceOf(ApiError);
    expect(fn).toHaveBeenCalledTimes(4);
  });

  it('un DELETE NO se reintenta', async () => {
    const { api, fn } = contarFetch(() => Promise.reject(new Error('conexión perdida')));
    await expect(
      api.request('/api/v1/personas/me/dispositivos/x', { method: 'DELETE' }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});
