import { createApiClient } from '@tarjeta/api-client';
import { obtenerAccessToken } from './session';

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// §12 P1-A: modo cookie (refresh en cookie HttpOnly). getToken hace refresh silencioso si hace falta.
export const api = createApiClient({
  baseUrl,
  authMode: 'cookie',
  getToken: () => obtenerAccessToken(),
});
