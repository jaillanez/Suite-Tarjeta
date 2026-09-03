import { createApiClient } from '@tarjeta/api-client';
import { getAccessToken } from './session';

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const api = createApiClient({ baseUrl, getToken: () => getAccessToken() });
