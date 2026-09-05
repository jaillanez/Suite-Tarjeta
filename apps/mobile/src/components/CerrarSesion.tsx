'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut } from 'lucide-react';
import { Button } from '@tarjeta/ui';
import { api } from '@/lib/api';
import { getRefreshToken, limpiarSesion } from '@/lib/session';

/**
 * Botón de cierre de sesión: revoca el refresh en el servidor (best-effort) y borra las
 * credenciales del almacén seguro y de Preferences, luego vuelve al inicio.
 */
export function CerrarSesion({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [saliendo, setSaliendo] = useState(false);

  async function salir(): Promise<void> {
    setSaliendo(true);
    try {
      const refresh = await getRefreshToken();
      if (refresh) {
        try {
          await api.logout(refresh);
        } catch {
          // Best-effort: si falla la revocación en el server igual limpiamos el dispositivo.
        }
      }
    } finally {
      await limpiarSesion();
      router.replace('/');
    }
  }

  if (compact) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => void salir()}
        disabled={saliendo}
        aria-label="Cerrar sesión"
      >
        <LogOut className="size-4" aria-hidden="true" />
        Salir
      </Button>
    );
  }

  return (
    <Button variant="outline" className="w-full" onClick={() => void salir()} disabled={saliendo}>
      <LogOut className="size-4" aria-hidden="true" />
      Cerrar sesión
    </Button>
  );
}
