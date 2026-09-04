'use client';

// §12 P1-B: almacén seguro para credenciales. Es el "puerto": la sesión guarda access/refresh a
// través de este seam en vez de escribirlos en `@capacitor/preferences` (legible en el dispositivo).
//
// En el dispositivo, `AlmacenSeguroInit` (montado en el layout) inyecta un backend respaldado por
// Keychain (iOS) / Keystore (Android) vía `capacitor-secure-storage-plugin` con
// `configurarAlmacenSeguro(...)`. El fallback por defecto usa Preferences y es SOLO para el
// desarrollo web (que no es el artefacto que se distribuye); avisa por consola.
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
