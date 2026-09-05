'use client';

// §12 P1-B: almacén seguro para credenciales. Es el "puerto": la sesión guarda access/refresh a
// través de este seam en vez de escribirlos en `@capacitor/preferences` (legible en el dispositivo).
//
// En el dispositivo resuelve, de forma perezosa y esperada, un backend respaldado por
// Keychain (iOS) / Keystore (Android) vía `capacitor-secure-storage-plugin`. En web (dev) usa
// Preferences como fallback (avisa por consola). La resolución es un `await` en el primer uso, así
// que NO hay carrera: un login apenas abierta la app espera a que el backend nativo esté listo
// antes de guardar el token (antes, si el login ocurría antes de cablear el plugin, el token caía
// en Preferences y se perdía → 401). `AlmacenSeguroInit` sigue disponible como calentamiento y para
// inyectar un backend explícito; los tests inyectan uno falso con `configurarAlmacenSeguro`.
//
// Nota: CI no compila el proyecto nativo, así que el plugin se verifica en el dispositivo
// (`pnpm --filter @tarjeta/mobile cap:sync` + build nativo). Ver docs/estado-funcional.md.

import { Preferences } from '@capacitor/preferences';

export interface AlmacenSeguro {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  remove(key: string): Promise<void>;
}

let avisado = false;

const preferenciasFallback: AlmacenSeguro = {
  async get(key) {
    return (await Preferences.get({ key })).value;
  },
  async set(key, value) {
    if (!avisado) {
      console.warn(
        '[almacen-seguro] usando Preferences como fallback (solo dev web). ' +
          'En el dispositivo se usa Keychain/Keystore automáticamente.',
      );
      avisado = true;
    }
    await Preferences.set({ key, value });
  },
  async remove(key) {
    await Preferences.remove({ key });
  },
};

// Backend inyectado explícitamente (tests, o `AlmacenSeguroInit`). Tiene prioridad.
let inyectado: AlmacenSeguro | null = null;
// Resolución perezosa del backend por defecto (nativo si se puede; si no, fallback).
let resolucion: Promise<AlmacenSeguro> | null = null;

async function resolverPorDefecto(): Promise<AlmacenSeguro> {
  try {
    const { Capacitor } = await import('@capacitor/core');
    if (Capacitor.isNativePlatform()) {
      const { SecureStoragePlugin } = await import('capacitor-secure-storage-plugin');
      return {
        async get(key) {
          try {
            return (await SecureStoragePlugin.get({ key })).value;
          } catch {
            return null; // el plugin lanza si la clave no existe
          }
        },
        async set(key, value) {
          await SecureStoragePlugin.set({ key, value });
        },
        async remove(key) {
          try {
            await SecureStoragePlugin.remove({ key });
          } catch {
            // no existía: nada que borrar
          }
        },
      };
    }
  } catch {
    // Capacitor o el plugin no disponibles: queda el fallback.
  }
  return preferenciasFallback;
}

function backend(): Promise<AlmacenSeguro> {
  if (inyectado) return Promise.resolve(inyectado);
  resolucion ??= resolverPorDefecto();
  return resolucion;
}

/** Inyecta un adaptador explícito (Keychain/Keystore real, o un doble en tests). Tiene prioridad. */
export function configurarAlmacenSeguro(impl: AlmacenSeguro): void {
  inyectado = impl;
}

export const almacenSeguro: AlmacenSeguro = {
  get: async (k) => (await backend()).get(k),
  set: async (k, v) => (await backend()).set(k, v),
  remove: async (k) => (await backend()).remove(k),
};
