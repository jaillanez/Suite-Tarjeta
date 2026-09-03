'use client';

const ACCESS = 'tarjeta_access';
const REFRESH = 'tarjeta_refresh';

export function guardarSesion(access: string, refresh: string): void {
  try {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
    // Cookie mínima para que el middleware sepa que hay sesión (la validez real la valida la API).
    document.cookie = 'tarjeta_sesion=1; path=/; SameSite=Lax';
  } catch {
    // almacenamiento no disponible
  }
}

export function limpiarSesion(): void {
  try {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
    document.cookie = 'tarjeta_sesion=; path=/; Max-Age=0; SameSite=Lax';
  } catch {
    // ignore
  }
}

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(ACCESS);
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH);
  } catch {
    return null;
  }
}
