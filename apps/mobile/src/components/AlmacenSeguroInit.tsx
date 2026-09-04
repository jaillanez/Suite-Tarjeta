'use client';

// §12 P1-B: en el dispositivo, cablea el almacén seguro (Keychain iOS / Keystore Android) detrás
// del seam `almacenSeguro`. En web (dev) no hace nada: queda el fallback de Preferences.
// Se monta una vez en el layout raíz. El plugin nativo NO lo verifica CI (no compila el proyecto
// nativo); se prueba en el dispositivo. Ver docs/estado-funcional.md (Almacén seguro móvil).

import { useEffect } from 'react';
import { Capacitor } from '@capacitor/core';
import { configurarAlmacenSeguro } from '@/lib/almacen-seguro';

export function AlmacenSeguroInit(): null {
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return; // en web dev queda el fallback (Preferences)
    let vivo = true;
    void (async () => {
      try {
        const { SecureStoragePlugin } = await import('capacitor-secure-storage-plugin');
        if (!vivo) return;
        configurarAlmacenSeguro({
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
        });
      } catch {
        // plugin no disponible: queda el fallback del seam
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);
  return null;
}
