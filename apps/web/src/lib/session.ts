'use client';

// §12 P1-A: la sesión web ya NO usa localStorage. El refresh token vive en una cookie HttpOnly
// (la pone el backend, inaccesible a JS) y el access token, de vida corta, se guarda en memoria.
// Al recargar la página se pierde el access en memoria: se recupera con un refresh silencioso
// contra la cookie HttpOnly. No se guarda ninguna cookie manipulable como "prueba de sesión".

const baseUrl = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

let accessToken: string | null = null;
let refrescando: Promise<string | null> | null = null;

export function guardarAccessToken(token: string): void {
  accessToken = token;
}

export function limpiarAccessToken(): void {
  accessToken = null;
}

async function refrescar(): Promise<string | null> {
  try {
    const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // envía la cookie HttpOnly de refresh
      headers: { 'content-type': 'application/json', 'x-auth-mode': 'cookie' },
      body: '{}',
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { access_token: string };
    accessToken = data.access_token;
    return accessToken;
  } catch {
    return null;
  }
}

/**
 * Devuelve el access token en memoria; si no hay (p. ej. tras recargar), intenta un refresh
 * silencioso con la cookie HttpOnly. Coalesce las llamadas concurrentes en un único refresh.
 */
export async function obtenerAccessToken(): Promise<string | null> {
  if (accessToken) return accessToken;
  if (!refrescando) {
    refrescando = refrescar().finally(() => {
      refrescando = null;
    });
  }
  return refrescando;
}
