// Cliente TypeScript de la API. Los tipos se generan desde el OpenAPI 3.1 de FastAPI
// (`pnpm generate:api` -> src/schema.generated.ts, commiteado).

export type { components, paths } from './schema.generated';

export interface ApiClientOptions {
  baseUrl: string;
  /** Devuelve el token de acceso (o null si no hay sesión). */
  getToken?: () => string | null | Promise<string | null>;
  maxRetries?: number;
  retryBaseMs?: number;
}

/** Error normalizado para la UI. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

interface BackendError {
  error?: { code?: string; message?: string };
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export interface HealthResponse {
  status: string;
}

export interface HealthDbResponse {
  uuid: string;
  server_version: string;
}

export function createApiClient(options: ApiClientOptions) {
  const { baseUrl, getToken, maxRetries = 3, retryBaseMs = 300 } = options;

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = `${baseUrl.replace(/\/$/, '')}${path}`;
    const headers = new Headers(init.headers);
    headers.set('accept', 'application/json');

    const token = getToken ? await getToken() : null;
    if (token) headers.set('authorization', `Bearer ${token}`);

    let lastError: unknown;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await fetch(url, { ...init, headers });
        if (res.ok) {
          if (res.status === 204) return undefined as T;
          return (await res.json()) as T;
        }
        // 5xx: reintentable; 4xx: error de negocio, no se reintenta.
        if (res.status >= 500 && attempt < maxRetries) {
          await sleep(retryBaseMs * 2 ** attempt);
          continue;
        }
        let body: BackendError = {};
        try {
          body = (await res.json()) as BackendError;
        } catch {
          // respuesta sin cuerpo JSON
        }
        throw new ApiError(
          body.error?.message ?? res.statusText ?? 'Error de la API',
          body.error?.code ?? `http_${res.status}`,
          res.status,
        );
      } catch (err) {
        if (err instanceof ApiError) throw err;
        lastError = err;
        if (attempt < maxRetries) {
          await sleep(retryBaseMs * 2 ** attempt);
          continue;
        }
      }
    }
    throw new ApiError(
      lastError instanceof Error ? lastError.message : 'Error de red',
      'network_error',
      0,
    );
  }

  return {
    request,
    health: () => request<HealthResponse>('/health'),
    healthDb: () => request<HealthDbResponse>('/health/db'),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
