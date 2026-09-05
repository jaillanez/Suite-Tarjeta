import { createApiClient } from '@tarjeta/api-client';
import { getAccessToken, getHuellaDispositivo } from './session';

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const api = createApiClient({
  baseUrl,
  getToken: () => getAccessToken(),
  // La sesión de cajero está atada a la huella del dispositivo (§06.5): se envía en toda request.
  getHuella: () => getHuellaDispositivo(),
});
