'use client';

import { Preferences } from '@capacitor/preferences';

const ACCESS = 'tarjeta_access';
const REFRESH = 'tarjeta_refresh';
const PERFIL = 'tarjeta_perfil_activo';

export async function guardarSesion(access: string, refresh: string): Promise<void> {
  await Preferences.set({ key: ACCESS, value: access });
  await Preferences.set({ key: REFRESH, value: refresh });
}

export async function getAccessToken(): Promise<string | null> {
  return (await Preferences.get({ key: ACCESS })).value;
}

export async function guardarPerfilActivo(clave: string): Promise<void> {
  await Preferences.set({ key: PERFIL, value: clave });
}

export async function getPerfilActivo(): Promise<string | null> {
  return (await Preferences.get({ key: PERFIL })).value;
}

export async function limpiarSesion(): Promise<void> {
  await Preferences.remove({ key: ACCESS });
  await Preferences.remove({ key: REFRESH });
  await Preferences.remove({ key: PERFIL });
}
