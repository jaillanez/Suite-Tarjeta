'use client';

// §12 P1-B: almacén seguro para credenciales. Es el "puerto": la sesión guarda access/refresh a
// través de este seam en vez de escribirlos en `@capacitor/preferences` (legible en el dispositivo).
//
// En el dispositivo, el bootstrap nativo inyecta un backend respaldado por Keychain (iOS) /
// Keystore (Android) con `configurarAlmacenSeguro(...)`. El fallback por defecto usa Preferences y
// es SOLO para el desarrollo web (que no es el artefacto que se distribuye); avisa por consola.
//
// Elegir y cablear el plugin nativo concreto (p. ej. un plugin de secure-storage compatible con
// Capacitor 8) es una decisión de build nativo: ver docs/auditoria-12.md (P1-B) y el informe.

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
          'En el dispositivo cableá Keychain/Keystore con configurarAlmacenSeguro().',
      );
      avisado = true;
    }
    await Preferences.set({ key, value });
  },
  async remove(key) {
    await Preferences.remove({ key });
  },
};

let backend: AlmacenSeguro = preferenciasFallback;

/** El bootstrap nativo inyecta el adaptador de Keychain/Keystore. */
export function configurarAlmacenSeguro(impl: AlmacenSeguro): void {
  backend = impl;
}

export const almacenSeguro: AlmacenSeguro = {
  get: (k) => backend.get(k),
  set: (k, v) => backend.set(k, v),
  remove: (k) => backend.remove(k),
};
