'use client';

import { Preferences } from '@capacitor/preferences';
import { almacenSeguro } from './almacen-seguro';

// §12 P1-B: access/refresh viven en el almacén seguro (Keychain/Keystore vía almacen-seguro).
// El perfil activo y la huella del dispositivo NO son credenciales: quedan en Preferences.
const ACCESS = 'tarjeta_access';
const REFRESH = 'tarjeta_refresh';
const PERFIL = 'tarjeta_perfil_activo';

export async function guardarSesion(access: string, refresh: string): Promise<void> {
  await almacenSeguro.set(ACCESS, access);
  await almacenSeguro.set(REFRESH, refresh);
  // Limpia restos de versiones previas que guardaban el token en el almacén no seguro.
  await Preferences.remove({ key: ACCESS });
  await Preferences.remove({ key: REFRESH });
}

/**
 * Lee una credencial del almacén seguro. Si todavía vive en Preferences (app instalada antes de
 * este cambio), la migra al almacén seguro y la borra del inseguro. Migración transparente.
 */
async function leerConMigracion(key: string): Promise<string | null> {
  const seguro = await almacenSeguro.get(key);
  if (seguro !== null) return seguro;
  const legacy = (await Preferences.get({ key })).value;
  if (legacy !== null) {
    await almacenSeguro.set(key, legacy);
    await Preferences.remove({ key });
    return legacy;
  }
  return null;
}

export async function getAccessToken(): Promise<string | null> {
  return leerConMigracion(ACCESS);
}

export async function getRefreshToken(): Promise<string | null> {
  return leerConMigracion(REFRESH);
}

export async function guardarPerfilActivo(clave: string): Promise<void> {
  await Preferences.set({ key: PERFIL, value: clave });
}

export async function getPerfilActivo(): Promise<string | null> {
  return (await Preferences.get({ key: PERFIL })).value;
}

export async function limpiarSesion(): Promise<void> {
  await almacenSeguro.remove(ACCESS);
  await almacenSeguro.remove(REFRESH);
  // También borra cualquier resto legacy en Preferences.
  await Preferences.remove({ key: ACCESS });
  await Preferences.remove({ key: REFRESH });
  await Preferences.remove({ key: PERFIL });
}

const HUELLA = 'tarjeta_huella_dispositivo';

/**
 * Huella estable del dispositivo (§06.5): el PIN del cajero se ata a ella. Se genera una vez
 * y persiste en Preferences; identifica a este dispositivo registrado (no es una credencial).
 */
export async function getHuellaDispositivo(): Promise<string> {
  const existente = (await Preferences.get({ key: HUELLA })).value;
  if (existente) return existente;
  const nueva = crypto.randomUUID();
  await Preferences.set({ key: HUELLA, value: nueva });
  return nueva;
}
